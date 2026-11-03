from fastapi import APIRouter, Depends, HTTPException

from ats_agent.api.deps import get_session
from ats_agent.api.schemas.applications import (
    ApplicationRead,
    ApplicationDetailRead,
    ActionRequest,
    RejectRequest,
    HoldRequest,
    FollowupReplyRequest,
)
from ats_agent.domain.models import Application, JobRequisition, PipelineStage, RecruiterAction
from ats_agent.agent_layer import actions

router = APIRouter(prefix="/applications", tags=["Applications"])


def _get_app_and_job(session, application_id: str) -> tuple[Application, JobRequisition]:
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    job = session.get(JobRequisition, app.job_requisition_id) if app.job_requisition_id else None
    if not job:
        raise HTTPException(status_code=404, detail="Job requisition for this application not found")
    return app, job


@router.get("/{application_id}", response_model=ApplicationDetailRead)
async def get_application(application_id: str, session=Depends(get_session)):
    """Get full details for a specific application, including skills/gaps/follow-up state."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.get("/{application_id}/emails")
async def get_application_emails(application_id: str, session=Depends(get_session)):
    """List every email sent to this candidate (interview invites, rejections, follow-ups)."""
    if not session.get(Application, application_id):
        raise HTTPException(status_code=404, detail="Application not found")
    return {"emails": actions.list_outbox_for_application(application_id)}


@router.post("/{application_id}/actions")
async def perform_application_action(
    application_id: str,
    request: ActionRequest,
    session=Depends(get_session)
):
    """Generic pipeline-stage move (kept for simple stage transitions)."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    action_map = {
        "HOLD": PipelineStage.ON_HOLD,
        "MOVE_TO_REVIEW": PipelineStage.NEEDS_REVIEW,
        "SHORTLIST": PipelineStage.SHORTLISTED,
    }

    action_type = request.action_type.upper()
    if action_type not in action_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type: {request.action_type}. Use /reject for rejections (requires a reason).",
        )

    app.pipeline_stage = action_map[action_type]
    session.add(app)
    session.add(RecruiterAction(
        application_id=application_id,
        actor="Recruiter",
        action_type=request.action_type,
        note=request.note,
    ))
    session.commit()

    return {"status": "success", "message": f"Application moved to {app.pipeline_stage}"}


@router.post("/{application_id}/hold")
async def hold_application(application_id: str, request: HoldRequest = HoldRequest(), session=Depends(get_session)):
    """Put an application on hold (from the Review tab)."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    actions.hold_application(session, app, note=request.note)
    return {"status": "success", "message": "Application placed on hold"}


@router.post("/{application_id}/move-to-review")
async def move_application_to_review(application_id: str, session=Depends(get_session)):
    """Send a candidate from the Reject tab back to Review instead of finalizing rejection."""
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    actions.move_to_review(session, app)
    return {"status": "success", "message": "Application moved back to review"}


@router.post("/{application_id}/reject")
async def reject_application(application_id: str, request: RejectRequest, session=Depends(get_session)):
    """
    Finalize a rejection. Requires reasoning, which is included in the
    candidate's rejection email.
    """
    app, job = _get_app_and_job(session, application_id)
    actions.reject_application_with_reason(session, app, job, request.reason)
    return {"status": "success", "message": "Rejection email sent and application closed out"}


@router.post("/{application_id}/interview")
async def schedule_interview(application_id: str, session=Depends(get_session)):
    """
    Schedule a virtual interview: finds the next open slot on the recruiter's
    calendar (mocked) and emails a structured interview invite.
    """
    app, job = _get_app_and_job(session, application_id)
    try:
        result = actions.schedule_interview_for_application(session, app, job)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"status": "success", **result}


@router.get("/{application_id}/interview-slots")
async def preview_next_interview_slot(application_id: str, session=Depends(get_session)):
    """Preview the next slot that would be booked, without booking it."""
    app, job = _get_app_and_job(session, application_id)
    from ats_agent.agent_layer import calendar
    try:
        slot = calendar.find_next_available_slot(session, job.id)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"next_available_start": slot.start.isoformat(), "next_available_end": slot.end.isoformat()}


@router.post("/{application_id}/follow-up/request")
async def request_followup(application_id: str, session=Depends(get_session)):
    """
    'Get more details from candidate': generates gap questions from the
    application's missing_skills and emails them.
    """
    app, job = _get_app_and_job(session, application_id)
    questions = actions.request_followup_for_application(session, app, job)
    return {"status": "success", "questions": questions}


@router.post("/{application_id}/follow-up/reply")
async def submit_followup_reply(application_id: str, request: FollowupReplyRequest, session=Depends(get_session)):
    """
    Candidate's answer to the follow-up questions. Rescores using the
    application's existing score history (same evaluation_thread_id) and
    re-derives the pipeline stage.
    """
    app = session.get(Application, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    result = actions.submit_followup_reply_for_application(session, app, request.reply_text)
    return {"status": "success", **result}
