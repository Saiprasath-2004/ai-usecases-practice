import re
import uuid
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import desc, select

from ats_agent.api.deps import get_graph, get_session
from ats_agent.api.schemas.applications import ApplicationListResponse, ApplicationRead
from ats_agent.api.schemas.jobs import JobCreate, JobRead
from ats_agent.batch import BulkEvaluator
from ats_agent.domain.models import Application, EvaluationStatus, JobRequisition, PipelineStage
from ats_agent.persistence.database import Database

RESUME_EXTENSIONS = {".pdf", ".txt", ".docx"}


class ResumeImportRequest(BaseModel):
    folder: str | None = None  # defaults to input/<job_id>/


def _name_from_filename(path: Path) -> str:
    stem = re.sub(r"[_\-]+", " ", path.stem).strip()
    return stem.title() if stem else "Unknown Candidate"

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def create_default_job_if_missing(session) -> JobRequisition | None:
    """Seed a job opening from the repo data directory if none exist."""
    existing = session.exec(select(JobRequisition)).first()
    if existing is not None:
        return None

    jd_path = Path("data/jd.txt")
    jd_text = jd_path.read_text(encoding="utf-8") if jd_path.exists() else "Sample job description"
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


@router.post("/seed/default", response_model=JobRead)
async def seed_default_job(session=Depends(get_session)):
    """Create a default requisition from the sample JD if the database is empty."""
    job = create_default_job_if_missing(session)
    if job is None:
        return session.exec(select(JobRequisition)).first()
    return job


@router.post("", response_model=JobRead, status_code=201)
async def create_job(job_data: JobCreate, session=Depends(get_session)):
    """Create a job requisition from provided data."""
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


@router.get("", response_model=List[JobRead])
async def list_jobs(session=Depends(get_session)):
    """List all job requisitions."""
    statement = select(JobRequisition)
    jobs = session.exec(statement).all()
    if not jobs:
        job = create_default_job_if_missing(session)
        if job is not None:
            jobs = [job]
    return jobs

@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: int, session=Depends(get_session)):
    """Get details for a specific job."""
    job = session.get(JobRequisition, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/{job_id}/applications", response_model=ApplicationListResponse)
async def list_job_applications(job_id: int, session=Depends(get_session)):
    """
    List applications for a job, grouped by stage and sorted by score.
    Sorting: Stage, then Score DESC (unscored last).
    """
    # Filter by job, sort by stage and score (Nulls last for SQLite)
    statement = (
        select(Application)
        .where(Application.job_requisition_id == job_id)
        .order_by(
            Application.pipeline_stage,
            desc(Application.overall_score)
        )
    )

    apps = session.exec(statement).all()

    # Group by stage in Python
    grouped: Dict[PipelineStage, List[ApplicationRead]] = {}
    for app in apps:
        stage = app.pipeline_stage
        if stage not in grouped:
            grouped[stage] = []
        grouped[stage].append(ApplicationRead.model_validate(app))

    return {"applications": grouped}

@router.post("/{job_id}/resumes/import")
async def import_resumes(
    job_id: int,
    request: ResumeImportRequest = ResumeImportRequest(),
    session=Depends(get_session),
):
    """
    Scan a local folder for resume files and create a pending Application for
    each one that isn't already linked to this job. Defaults to
    ``input/<job_id>/``. This is the "resumes submitted for this JD, stored
    in a local folder" step of the pipeline -- run this before triggering
    bulk evaluation.

    Placeholder note: candidate name/email are inferred from the filename
    (e.g. "aarav_sharma.pdf" -> "Aarav Sharma" / a placeholder email). Wire
    this up to a real intake form or ATS webhook later for accurate contact
    info.
    """
    job = session.get(JobRequisition, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    folder = Path(request.folder) if request.folder else Path("input") / str(job_id)
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Resume folder not found: {folder}")

    existing_paths = set(
        session.exec(
            select(Application.resume_path).where(Application.job_requisition_id == job_id)
        ).all()
    )

    created: List[ApplicationRead] = []
    for resume_path in sorted(folder.iterdir()):
        if not resume_path.is_file() or resume_path.suffix.lower() not in RESUME_EXTENSIONS:
            continue
        if str(resume_path) in existing_paths:
            continue

        candidate_name = _name_from_filename(resume_path)
        placeholder_email = f"{resume_path.stem.lower().replace(' ', '.')}@candidate.example"

        app = Application(
            application_id=str(uuid.uuid4()),
            job_requisition_id=job_id,
            candidate_name=candidate_name,
            candidate_email=placeholder_email,
            resume_path=str(resume_path),
            pipeline_stage=PipelineStage.NEEDS_REVIEW,
            evaluation_status=EvaluationStatus.PENDING,
        )
        session.add(app)
        created.append(ApplicationRead.model_validate(app))

    session.commit()
    return {"imported": len(created), "applications": created}


@router.post("/{job_id}/evaluations", status_code=202)
async def trigger_bulk_evaluation(
    job_id: int,
    background_tasks: BackgroundTasks,
    session=Depends(get_session)
):
    """Trigger bulk evaluation for all pending applications of a job."""
    job = session.get(JobRequisition, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Use the Database instance for BulkEvaluator
    db = Database()
    evaluator = BulkEvaluator(db)

    # Run in background
    background_tasks.add_task(evaluator.bulk_evaluate, job_id)

    return {"status": "accepted", "message": f"Bulk evaluation started for job {job_id}"}
