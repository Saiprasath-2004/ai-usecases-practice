import pytest
from src.ats_agent.domain.models import JobRequisition, Application, EvaluationRun, PipelineStage, EvaluationStatus
from src.ats_agent.persistence.database import Database
import os

@pytest.fixture
def db():
    # Use in-memory database for unit tests to avoid Windows file locking issues
    database = Database(db_url="sqlite:///:memory:")
    yield database



def test_domain_persistence_flow(db):
    # 1. Create a Job Requisition
    job = JobRequisition(
        title="Senior Software Engineer",
        department="Engineering",
        location="Remote",
        employment_type="Full-time",
        job_description_text="Looking for a Python expert with 5+ years experience.",
        job_description_source="data/jd.txt",
        required_skills="['Python', 'SQL', 'Cloud']",
        evaluation_status="Active"
    )

    created_job = db.create_job(job)
    assert created_job.id is not None

    # 2. Create an Application
    app = Application(
        application_id="APP-001",
        job_requisition_id=created_job.id,
        candidate_name="John Doe",
        candidate_email="john.doe@example.com",
        resume_path="input/resume_1.pdf",
        submission_date=None, # defaults to now
        pipeline_stage=PipelineStage.NEEDS_REVIEW,
        evaluation_status=EvaluationStatus.PENDING
    )
    created_app = db.create_application(app)
    assert created_app.application_id == "APP-001"

    # 3. Create an Evaluation Run
    run = EvaluationRun(
        application_id="APP-001",
        thread_id="thread-abc-123",
        status="Pending"
    )
    created_run = db.create_evaluation_run(run)
    assert created_run.run_id is not None

    # 4. Verify we can read them back
    fetched_job = db.get_job(created_job.id)
    assert fetched_job.title == "Senior Software Engineer"

    fetched_app = db.get_application("APP-001")
    assert fetched_app.candidate_name == "John Doe"
    assert fetched_app.job_requisition_id == created_job.id

    # 5. Verify applicant count
    count = db.get_applicant_count(created_job.id)
    assert count == 1

def test_multiple_applications_count(db):
    job = JobRequisition(
        title="DevOps Engineer",
        department="Infrastructure",
        location="New York",
        employment_type="Full-time",
        job_description_text="JD text",
        job_description_source="source",
        required_skills="['Terraform', 'AWS']"
    )

    created_job = db.create_job(job)

    db.create_application(Application(
        application_id="APP-1", job_requisition_id=created_job.id,
        candidate_name="A", candidate_email="a@test.com", resume_path="p1"
    ))
    db.create_application(Application(
        application_id="APP-2", job_requisition_id=created_job.id,
        candidate_name="B", candidate_email="b@test.com", resume_path="p2"
    ))

    assert db.get_applicant_count(created_job.id) == 2
