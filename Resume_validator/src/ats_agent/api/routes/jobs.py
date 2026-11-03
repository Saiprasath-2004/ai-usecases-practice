"""Job requisition API routes."""

from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel import desc, select

from ats_agent.api.deps import get_session
from ats_agent.api.schemas.applications import (
    ApplicationListResponse,
    ApplicationRead,
)
from ats_agent.api.schemas.jobs import JobCreate, JobRead
from ats_agent.batch import BulkEvaluator
from ats_agent.domain.models import (
    Application,
    JobRequisition,
    PipelineStage,
)
from ats_agent.persistence.database import Database


router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"],
)


def create_default_job_if_missing(
    session,
) -> JobRequisition | None:
    """Seed a default job from the repository JD if no jobs exist."""

    existing = session.exec(
        select(JobRequisition)
    ).first()

    if existing is not None:
        return None

    jd_path = Path("data/jd.txt")

    jd_text = (
        jd_path.read_text(encoding="utf-8")
        if jd_path.exists()
        else "Sample job description"
    )

    title = "AI Platform Engineer"

    if jd_text:
        first_line = jd_text.strip().splitlines()[0].strip()

        if first_line and len(first_line) > 3:
            title = first_line[:80]

    job = JobRequisition(
        title=title,
        department="Engineering",
        location="Remote",
        employment_type="Full-time",
        job_description_text=jd_text,
        job_description_source=str(jd_path),
        required_skills="[]",
        evaluation_status="Active",
    )

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


@router.post(
    "/seed/default",
    response_model=JobRead,
)
async def seed_default_job(
    session=Depends(get_session),
):
    """Create a default job if the database is empty."""

    job = create_default_job_if_missing(session)

    if job is None:
        return session.exec(
            select(JobRequisition)
        ).first()

    return job


@router.post(
    "",
    response_model=JobRead,
    status_code=201,
)
async def create_job(
    job_data: JobCreate,
    session=Depends(get_session),
):
    """Create a new job requisition."""

    job = JobRequisition(
        title=job_data.title,
        department=job_data.department,
        location=job_data.location,
        employment_type=job_data.employment_type,
        job_description_text=job_data.job_description_text,
        job_description_source=job_data.job_description_source,
        required_skills=job_data.required_skills or "[]",
        evaluation_status="Active",
    )

    session.add(job)
    session.commit()
    session.refresh(job)

    return job


@router.get(
    "",
    response_model=List[JobRead],
)
async def list_jobs(
    session=Depends(get_session),
):
    """List all job requisitions."""

    statement = select(JobRequisition)

    jobs = session.exec(statement).all()

    if not jobs:
        job = create_default_job_if_missing(session)

        if job is not None:
            jobs = [job]

    return jobs


@router.get(
    "/{job_id}",
    response_model=JobRead,
)
async def get_job(
    job_id: int,
    session=Depends(get_session),
):
    """Get details for a specific job."""

    job = session.get(JobRequisition, job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return job


@router.get(
    "/{job_id}/applications",
    response_model=ApplicationListResponse,
)
async def list_job_applications(
    job_id: int,
    session=Depends(get_session),
):
    """
    List applications belonging to a job.

    Applications are grouped by pipeline stage
    and sorted by overall score descending.
    """

    job = session.get(JobRequisition, job_id)

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    statement = (
        select(Application)
        .where(
            Application.job_requisition_id == job_id
        )
        .order_by(
            Application.pipeline_stage,
            desc(Application.overall_score),
        )
    )

    applications = session.exec(statement).all()

    grouped: Dict[
        PipelineStage,
        List[ApplicationRead],
    ] = {}

    for application in applications:
        stage = application.pipeline_stage

        if stage not in grouped:
            grouped[stage] = []

        grouped[stage].append(
            ApplicationRead.model_validate(application)
        )

    return {
        "applications": grouped,
    }


@router.post(
    "/{job_id}/evaluations",
    status_code=202,
)
async def trigger_bulk_evaluation(
    job_id: int,
    background_tasks: BackgroundTasks,
    session=Depends(get_session),
):
    """
    Trigger bulk evaluation for all pending applications
    belonging to a job.
    """

    job = session.get(
        JobRequisition,
        job_id,
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    db = Database()

    evaluator = BulkEvaluator(db)

    background_tasks.add_task(
        evaluator.bulk_evaluate,
        job_id,
    )

    return {
        "status": "accepted",
        "message": (
            f"Bulk evaluation started for job {job_id}"
        ),
    }