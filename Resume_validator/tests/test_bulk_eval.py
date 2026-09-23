"""Tests for bulk evaluation and isolation."""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from src.ats_agent.domain.models import (
    JobRequisition, Application, EvaluationRun,
    PipelineStage, EvaluationStatus, RunStatus
)
from src.ats_agent.persistence.database import Database
from src.ats_agent.batch import BulkEvaluator

@pytest.fixture
def db():
    database = Database(db_url="sqlite:///:memory:")
    return database

@pytest.fixture
def evaluator(db):
    return BulkEvaluator(db)

def test_bulk_evaluate_creates_distinct_runs(db, evaluator):
    # Setup
    job = JobRequisition(
        title="Engineer", department="Eng", location="Remote",
        employment_type="FT", job_description_text="JD", job_description_source="jd.txt"
    )
    created_job = db.create_job(job)

    apps = [
        Application(application_id=f"APP-{i}", job_requisition_id=created_job.id,
                   candidate_name=f"C{i}", candidate_email=f"c{i}@test.com", resume_path=f"r{i}.pdf")
        for i in range(3)
    ]
    for app in apps:
        db.create_application(app)

    # Mock the graph.invoke to return different results based on resume_path
    def mock_invoke(input_data, config):
        # Return a result that mirrors the input to verify isolation
        resume = input_data["resume_path"]
        return {
            "result": {"overall_score": 80.0 if "r0" in resume else 70.0},
            "verdict": "Shortlisted" if "r0" in resume else "Needs Review",
            "narrative": f"Narrative for {resume}"
        }

    with patch("src.ats_agent.batch.build_graph") as mock_build:
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = mock_invoke
        mock_build.return_value = mock_graph

        # Run bulk eval
        asyncio.run(evaluator.bulk_evaluate(created_job.id))

    # Verify 3 distinct runs
    with db.get_session() as session:
        from sqlmodel import select
        runs = session.exec(select(EvaluationRun).where(EvaluationRun.status == RunStatus.COMPLETED)).all()
        assert len(runs) == 3

        # Verify distinct thread_ids
        thread_ids = {run.thread_id for run in runs}
        assert len(thread_ids) == 3

        # Verify final status on applications
        apps_db = session.exec(select(Application)).all()
        for app in apps_db:
            assert app.evaluation_status == EvaluationStatus.COMPLETED

def test_concurrent_isolation(db, evaluator):
    """Verify that concurrent runs do not leak state."""
    job = JobRequisition(
        title="Engineer", department="Eng", location="Remote",
        employment_type="FT", job_description_text="JD", job_description_source="jd.txt"
    )
    created_job = db.create_job(job)

    app1 = Application(application_id="APP-1", job_requisition_id=created_job.id,
                      candidate_name="C1", candidate_email="c1@test.com", resume_path="r1.pdf")
    app2 = Application(application_id="APP-2", job_requisition_id=created_job.id,
                      candidate_name="C2", candidate_email="c2@test.com", resume_path="r2.pdf")
    db.create_application(app1)
    db.create_application(app2)

    # Mock invoke to simulate some delay and return distinct results
    async def mock_invoke_async(input_data, config):
        # Simulate processing time
        await asyncio.sleep(0.1)
        resume = input_data["resume_path"]
        return {
            "result": {"overall_score": 90.0 if "r1" in resume else 60.0},
            "narrative": f"Narrative for {resume}"
        }

    with patch("src.ats_agent.batch.build_graph") as mock_build:
        mock_graph = MagicMock()
        # Since we use asyncio.to_thread, we need to wrap our async mock in a sync wrapper
        def sync_wrapper(input_data, config):
            return asyncio.run(mock_invoke_async(input_data, config))

        mock_graph.invoke.side_effect = sync_wrapper
        mock_build.return_value = mock_graph

        asyncio.run(evaluator.bulk_evaluate(created_job.id))

    with db.get_session() as session:
        from sqlmodel import select
        a1 = session.get(Application, "APP-1")
        a2 = session.get(Application, "APP-2")

        assert a1.overall_score == 90.0
        assert a2.overall_score == 60.0
        assert a1.evaluation_thread_id != a2.evaluation_thread_id

def test_retry_single_application(db, evaluator):
    """Verify retrying one failed application doesn't touch others."""
    job = JobRequisition(
        title="Engineer", department="Eng", location="Remote",
        employment_type="FT", job_description_text="JD", job_description_source="jd.txt"
    )
    created_job = db.create_job(job)

    app1 = Application(application_id="APP-1", job_requisition_id=created_job.id,
                      candidate_name="C1", candidate_email="c1@test.com", resume_path="r1.pdf")
    app2 = Application(application_id="APP-2", job_requisition_id=created_job.id,
                      candidate_name="C2", candidate_email="c2@test.com", resume_path="r2.pdf")
    db.create_application(app1)
    db.create_application(app2)

    # First run: app1 fails, app2 succeeds
    def mock_invoke_fail_one(input_data, config):
        resume = input_data["resume_path"]
        if "r1" in resume:
            raise Exception("Simulation Failure")
        return {"result": {"overall_score": 70.0}, "narrative": "Success"}

    with patch("src.ats_agent.batch.build_graph") as mock_build:
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = mock_invoke_fail_one
        mock_build.return_value = mock_graph

        asyncio.run(evaluator.bulk_evaluate(created_job.id))

    # Verify app1 failed, app2 succeeded
    with db.get_session() as session:
        a1 = session.get(Application, "APP-1")
        a2 = session.get(Application, "APP-2")
        assert a1.evaluation_status == EvaluationStatus.FAILED
        assert a2.evaluation_status == EvaluationStatus.COMPLETED

    # Now retry just app1
    with patch("src.ats_agent.batch.build_graph") as mock_build:
        mock_graph = MagicMock()
        mock_graph.invoke.side_effect = lambda i, c: {"result": {"overall_score": 85.0}, "narrative": "Fixed"}
        mock_build.return_value = mock_graph

        asyncio.run(evaluator.retry_application("APP-1"))

    with db.get_session() as session:
        a1 = session.get(Application, "APP-1")
        a2 = session.get(Application, "APP-2")

        # app1 should be updated, app2 should remain unchanged
        assert a1.overall_score == 85.0
        assert a2.overall_score == 70.0
        # Verify a new run was created for app1
        runs = session.exec(select(EvaluationRun).where(EvaluationRun.application_id == "APP-1")).all()
        assert len(runs) == 2
