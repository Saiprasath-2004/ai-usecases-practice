"""Routes for one-off ("Quick Evaluate") candidate evaluation, outside the
job/application pipeline. Useful for testing a resume against a JD without
creating a full Application record.

Note: the interactive follow-up-reply / human-review-resume endpoints that
used to live here were removed as part of the refactor that made the graph
evaluation-only (see ats_agent/graph/builder.py). The follow-up and review
workflows now operate on Application rows -- see
ats_agent/api/routes/applications.py.
"""

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ats_agent.api.deps import get_graph
from ats_agent.api.schemas.candidates import EvaluationRequest, EvaluationStatus

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.get("/available")
async def list_available_candidates():
    """Return the default resume files from the repo input folder."""
    input_dir = Path("input")
    resumes = []
    if input_dir.exists():
        for resume_path in sorted(input_dir.iterdir()):
            if resume_path.is_file() and resume_path.suffix.lower() in {".pdf", ".txt", ".docx"}:
                resumes.append({
                    "name": resume_path.stem,
                    "label": resume_path.name,
                    "path": str(resume_path),
                })
    if not resumes:
        resumes.append({"name": "resume", "label": "resume.pdf", "path": "input/resume.pdf"})
    return {"resumes": resumes}


async def run_evaluation(graph, thread_id: str, inputs: dict):
    """Background task to invoke the graph."""
    try:
        config = {"configurable": {"thread_id": thread_id}}
        await asyncio.to_thread(graph.invoke, inputs, config)
    except Exception as e:
        print(f"Error in background evaluation for {thread_id}: {e}")


@router.post("", status_code=202)
async def start_evaluation(
    request: EvaluationRequest,
    background_tasks: BackgroundTasks,
    graph=Depends(get_graph)
):
    """Start a new ad-hoc candidate evaluation (not tied to an Application)."""
    thread_id = str(uuid.uuid4())
    inputs = {"jd_path": request.jd_path, "resume_path": request.resume_path}

    background_tasks.add_task(run_evaluation, graph, thread_id, inputs)

    return {"id": thread_id, "status": "running"}


@router.get("/{id}", response_model=EvaluationStatus)
async def get_status(id: str, graph=Depends(get_graph)):
    """Check the current status and results of an ad-hoc evaluation."""
    config = {"configurable": {"thread_id": id}}
    state = graph.get_state(config)

    if not state.values:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    values = state.values
    status = "completed" if not state.next else "running"

    return EvaluationStatus(
        id=id,
        status=status,
        verdict=values.get("verdict"),
        narrative=values.get("narrative"),
        error=values.get("jd_extraction_error") or values.get("resume_extraction_error"),
    )
