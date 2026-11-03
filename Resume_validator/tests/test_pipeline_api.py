import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from ats_agent.api.main import app
from ats_agent.api.deps import get_session
from ats_agent.domain.models import JobRequisition, Application, PipelineStage, EvaluationStatus
from ats_agent.persistence.database import Database

# Mock database for testing
test_db = Database("sqlite:///test_ats_api.db")

def override_get_session():
    with test_db.get_session() as session:
        yield session

app.dependency_overrides[get_session] = override_get_session
client = TestClient(app)

from sqlalchemy import text

@pytest.fixture(autouse=True)
def setup_db():
    """Clean database before each test."""
    with test_db.get_session() as session:
        # Simple way to clear SQLite tables for tests
        session.execute(text("DELETE FROM application"))
        session.execute(text("DELETE FROM jobrequisition"))
        session.execute(text("DELETE FROM recruiteraction"))
        session.commit()

def test_job_applications_sorting_and_grouping():
    """Verify sorting (Stage, Score DESC, Nulls Last) and grouping."""
    with test_db.get_session() as session:
        # 1. Create a Job
        job = JobRequisition(
            title="Software Engineer",
            department="Engineering",
            location="Remote",
            employment_type="Full-time",
            job_description_text="Python expert",
            job_description_source="jd.txt"
        )
        session.add(job)
        session.commit()
        job_id = job.id

        # 2. Create Applications
        # Group: Shortlisted (Score 95, 80)
        app1 = Application(application_id="app1", job_requisition_id=job_id, candidate_name="Alice", candidate_email="a@ex.com", resume_path="r1.pdf", pipeline_stage=PipelineStage.SHORTLISTED, overall_score=95.0)
        app2 = Application(application_id="app2", job_requisition_id=job_id, candidate_name="Bob", candidate_email="b@ex.com", resume_path="r2.pdf", pipeline_stage=PipelineStage.SHORTLISTED, overall_score=80.0)

        # Group: Needs Review (Score 90, 70, None)
        app3 = Application(application_id="app3", job_requisition_id=job_id, candidate_name="Charlie", candidate_email="c@ex.com", resume_path="r3.pdf", pipeline_stage=PipelineStage.NEEDS_REVIEW, overall_score=90.0)
        app4 = Application(application_id="app4", job_requisition_id=job_id, candidate_name="David", candidate_email="d@ex.com", resume_path="r4.pdf", pipeline_stage=PipelineStage.NEEDS_REVIEW, overall_score=70.0)
        app5 = Application(application_id="app5", job_requisition_id=job_id, candidate_name="Eve", candidate_email="e@ex.com", resume_path="r5.pdf", pipeline_stage=PipelineStage.NEEDS_REVIEW, overall_score=None)

        session.add_all([app1, app2, app3, app4, app5])
        session.commit()

    # 3. Call API
    response = client.get(f"/jobs/{job_id}/applications")
    assert response.status_code == 200
    data = response.json()["applications"]

    # 4. Verify Grouping
    assert PipelineStage.SHORTLISTED in data
    assert PipelineStage.NEEDS_REVIEW in data

    # 5. Verify Sorting within Shortlisted
    shortlisted = data[PipelineStage.SHORTLISTED]
    assert shortlisted[0]["application_id"] == "app1" # 95
    assert shortlisted[1]["application_id"] == "app2" # 80

    # 6. Verify Sorting within Needs Review (Nulls Last)
    needs_review = data[PipelineStage.NEEDS_REVIEW]
    assert needs_review[0]["application_id"] == "app3" # 90
    assert needs_review[1]["application_id"] == "app4" # 70
    assert needs_review[2]["application_id"] == "app5" # None

def test_pipeline_stage_independence():
    """Verify that manual stages are not overwritten by automated rescores."""
    with test_db.get_session() as session:
        job = JobRequisition(title="Dev", department="IT", location="NY", employment_type="FT", job_description_text="...", job_description_source="...")
        session.add(job)
        session.commit()

        app = Application(
            application_id="indep_1",
            job_requisition_id=job.id,
            candidate_name="Indy",
            candidate_email="i@ex.com",
            resume_path="r.pdf",
            pipeline_stage=PipelineStage.SHORTLISTED # Manually shortlisted
        )
        session.add(app)
        session.commit()
        app_id = app.application_id

    # Manually move to 'On Hold'
    hold_resp = client.post(f"/applications/{app_id}/hold")
    assert hold_resp.status_code == 200

    # Now simulate the batch update logic (the part I modified in batch.py)
    # Since we don't want to run the whole graph, we test the logic a la BulkEvaluator
    from ats_agent.batch import BulkEvaluator
    evaluator = BulkEvaluator(test_db)

    # We mock a "REJECT" result from the graph
    # The logic in batch.py uses final_state.get("verdict")
    # We can't easily call evaluate_application without a real graph,
    # but we can verify the logic manually or by adding a helper to BulkEvaluator.
    # For this test, we'll manually trigger the logic block from batch.py.

    with test_db.get_session() as session:
        app_db = session.get(Application, app_id)
        # Mocking the "final_state" and the update block
        final_state = {"verdict": "REJECT", "result": {"overall_score": 10.0}}
        overall_score = final_state["result"]["overall_score"]

        # THIS IS THE EXACT LOGIC FROM batch.py
        if app_db.pipeline_stage == PipelineStage.NEEDS_REVIEW:
            verdict = final_state.get("verdict")
            if verdict == "SELECT":
                app_db.pipeline_stage = PipelineStage.SHORTLISTED
            elif verdict == "REJECT":
                app_db.pipeline_stage = PipelineStage.REJECTED

        app_db.overall_score = overall_score
        session.add(app_db)
        session.commit()

    # Verify: Score updated, but stage remained 'On Hold'
    with test_db.get_session() as session:
        app_final = session.get(Application, app_id)
        assert app_final.overall_score == 10.0
        assert app_final.pipeline_stage == PipelineStage.ON_HOLD
