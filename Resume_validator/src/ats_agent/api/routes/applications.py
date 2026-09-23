"""Application API routes for the ATS recruiter product."""

import asyncio
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command
from sqlmodel import Session, select

from ats_agent.api.deps import get_session
from ats_agent.api.schemas.applications import (
    ActionRequest,
    ApplicationCreate,
    ApplicationRead,
    EvaluationResponse,
    FollowupReplyRequest,
    ReviewRequest,
)
from ats_agent.batch import BulkEvaluator
from ats_agent.domain.models import (
    ActionType,
    ActorType,
    Application,
    EvaluationRun,
    EvaluationStatus,
    JobRequisition,
    PipelineStage,
    RecruiterAction,
)
from ats_agent.persistence.database import Database


router = APIRouter(
    prefix="/applications",
    tags=["Applications"],
)


# ============================================================
# Helpers
# ============================================================


def get_application_or_404(
    application_id: str,
    session: Session,
) -> Application:
    """Get an application or raise a 404 error."""

    application = session.get(
        Application,
        application_id,
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    return application


def map_recruiter_action_to_stage(
    action_type: str,
) -> PipelineStage:
    """
    Convert a recruiter action into an application pipeline stage.

    This function only maps the action to state.
    External actions such as email/calendar operations are handled
    by their dedicated services.
    """

    normalized = action_type.strip().upper()

    action_map = {
        "HOLD": PipelineStage.ON_HOLD,
        "ON_HOLD": PipelineStage.ON_HOLD,

        "REJECT": PipelineStage.REJECTED,
        "REJECTED": PipelineStage.REJECTED,

        "MOVE_TO_REVIEW": PipelineStage.NEEDS_REVIEW,
        "NEEDS_REVIEW": PipelineStage.NEEDS_REVIEW,

        "GET_MORE_DETAILS": PipelineStage.NEEDS_REVIEW,
        "GET MORE DETAILS": PipelineStage.NEEDS_REVIEW,

        "SHORTLIST": PipelineStage.SHORTLISTED,
        "SHORTLISTED": PipelineStage.SHORTLISTED,

        "SCHEDULE_INTERVIEW": PipelineStage.SHORTLISTED,
        "SCHEDULE INTERVIEW": PipelineStage.SHORTLISTED,
    }

    if normalized not in action_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type: {action_type}",
        )

    return action_map[normalized]

def map_action_to_domain_type(
    action_type: str,
) -> ActionType:
    """Convert an API action string into the domain ActionType."""

    normalized = action_type.strip().upper()

    action_map = {
        "HOLD": ActionType.HOLD,
        "ON_HOLD": ActionType.HOLD,

        "REJECT": ActionType.REJECT,
        "REJECTED": ActionType.REJECT,

        "MOVE_TO_REVIEW": ActionType.MOVE_TO_REVIEW,
        "NEEDS_REVIEW": ActionType.MOVE_TO_REVIEW,

        "GET_MORE_DETAILS": ActionType.APPROVE_FOLLOWUP,
        "GET MORE DETAILS": ActionType.APPROVE_FOLLOWUP,

        "SCHEDULE_INTERVIEW": ActionType.SCHEDULE_INTERVIEW,
        "SCHEDULE INTERVIEW": ActionType.SCHEDULE_INTERVIEW,

        "APPROVE_FOLLOWUP": ActionType.APPROVE_FOLLOWUP,
        "RETURN_TO_PIPELINE": ActionType.RETURN_TO_PIPELINE,
    }

    if normalized not in action_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type: {action_type}",
        )

    return action_map[normalized]


# ============================================================
# Application Creation
# ============================================================


@router.post(
    "",
    response_model=ApplicationRead,
    status_code=201,
)
async def create_application(
    application_data: ApplicationCreate,
    session: Session = Depends(get_session),
):
    """Create a new candidate application for a job."""

    job = session.get(
        JobRequisition,
        application_data.job_requisition_id,
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    application = Application(
        application_id=str(uuid.uuid4()),
        job_requisition_id=application_data.job_requisition_id,
        candidate_name=application_data.candidate_name,
        candidate_email=application_data.candidate_email,
        resume_path=application_data.resume_path,
        pipeline_stage=PipelineStage.NEEDS_REVIEW,
        evaluation_status=EvaluationStatus.PENDING,
    )

    session.add(application)
    session.commit()
    session.refresh(application)

    return application


# ============================================================
# Application Retrieval
# ============================================================


@router.get(
    "/job/{job_id}",
)
async def get_job_applications(
    job_id: int,
    session: Session = Depends(get_session),
):
    """
    Get all applications belonging to a job.

    Used by the recruiter job/candidate dashboard.
    """

    statement = select(Application).where(
        Application.job_requisition_id == job_id
    )

    applications = session.exec(
        statement
    ).all()

    return applications


@router.get(
    "/{application_id}",
    response_model=ApplicationRead,
)
async def get_application(
    application_id: str,
    session: Session = Depends(get_session),
):
    """Get complete details for one application."""

    return get_application_or_404(
        application_id,
        session,
    )


# ============================================================
# Start Evaluation
# ============================================================


@router.post(
    "/{application_id}/evaluate",
    response_model=EvaluationResponse,
)
async def evaluate_application(
    application_id: str,
    session: Session = Depends(get_session),
):
    """
    Start ATS evaluation for one application.

    The evaluation executes the LangGraph workflow.

    The graph may finish at the human-review interrupt. The
    persistent thread is stored on Application.thread_id and
    can later be resumed through the /review endpoint.
    """

    application = get_application_or_404(
        application_id,
        session,
    )

    if not application.job_requisition_id:
        raise HTTPException(
            status_code=400,
            detail="Application is not associated with a job.",
        )

    job = session.get(
        JobRequisition,
        application.job_requisition_id,
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job requisition not found.",
        )

    if not job.job_description_source:
        raise HTTPException(
            status_code=400,
            detail="Job description source is not configured.",
        )

    if application.evaluation_status.value == "Running":
        raise HTTPException(
            status_code=409,
            detail="Application evaluation is already running.",
        )

    db = Database()
    evaluator = BulkEvaluator(db)

    await evaluator.evaluate_application(
        application_id=application_id,
        jd_path=job.job_description_source,
    )

    # Re-read the application because the evaluator used its
    # own database session.
    with db.get_session() as refreshed_session:
        updated_application = refreshed_session.get(
            Application,
            application_id,
        )

        if not updated_application:
            raise HTTPException(
                status_code=404,
                detail="Application not found after evaluation.",
            )

        latest_run = None

        if updated_application.current_evaluation_run_id:
            latest_run = refreshed_session.get(
                EvaluationRun,
                updated_application.current_evaluation_run_id,
            )

        return {
            "status": "completed",
            "application_id": application_id,
            "evaluation_status": (
                updated_application.evaluation_status
            ),
            "pipeline_stage": (
                updated_application.pipeline_stage
            ),
            "overall_score": (
                updated_application.overall_score
            ),
            "thread_id": (
                updated_application.thread_id
            ),
            "run_id": (
                latest_run.run_id
                if latest_run
                else None
            ),
            "run_status": (
                latest_run.status
                if latest_run
                else None
            ),
        }


# ============================================================
# Human Review
# ============================================================


@router.post(
    "/{application_id}/review",
)
async def submit_human_review(
    application_id: str,
    request: ReviewRequest,
    session: Session = Depends(get_session),
):
    """
    Resume the LangGraph human-review interrupt.

    The recruiter decision is passed back into LangGraph using
    Command(resume=...).

    After the graph resumes, the API records the recruiter action
    and updates the application pipeline stage.

    This endpoint does not send emails or schedule calendars.
    """

    application = get_application_or_404(
        application_id,
        session,
    )

    if not application.thread_id:
        raise HTTPException(
            status_code=400,
            detail="Application does not have an active LangGraph thread.",
        )

    action_type = request.decision.strip()

    # Validate that this is a domain-supported action.
    domain_action = map_action_to_domain_type(
        action_type
    )

    # --------------------------------------------------------
    # Resume LangGraph
    # --------------------------------------------------------

    db = Database()
    evaluator = BulkEvaluator(db)

    try:
        final_state = await asyncio.to_thread(
            evaluator.graph.invoke,
            Command(
                resume={
                    "decision": action_type,
                    "comments": request.comments,
                }
            ),
            config={
                "configurable": {
                    "thread_id": application.thread_id,
                }
            },
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume ATS workflow: {exc}",
        ) from exc

    # --------------------------------------------------------
    # Determine resulting pipeline state
    # --------------------------------------------------------

    new_stage = map_recruiter_action_to_stage(
        action_type
    )

    # --------------------------------------------------------
    # Persist recruiter decision
    # --------------------------------------------------------

    application.pipeline_stage = new_stage

    if request.comments:
        application.recruiter_comments = request.comments

    action_log = RecruiterAction(
        application_id=application_id,
        actor=ActorType.RECRUITER.value,
        action_type=domain_action,
        note=request.comments,
    )

    session.add(application)
    session.add(action_log)
    session.commit()
    session.refresh(application)

    return {
        "status": "success",
        "application_id": application_id,
        "action": domain_action,
        "pipeline_stage": application.pipeline_stage,
        "thread_id": application.thread_id,
        "workflow_state": final_state,
    }

# ============================================================
# Candidate Follow-up Reply
# ============================================================

@router.post(
    "/{application_id}/followup-reply",
)
async def submit_followup_reply(
    application_id: str,
    request: FollowupReplyRequest,
    session: Session = Depends(get_session),
):
    """
    Resume the LangGraph candidate follow-up interrupt.

    The candidate's reply is passed into LangGraph.

    The graph then:
    1. Extracts confirmed skills
    2. Recalculates the ATS score
    3. Updates matched/missing skills
    4. Rebuilds the report
    5. Pauses again at recruiter human review

    The latest evaluation state is also persisted into the
    Application's current snapshot.
    """

    application = get_application_or_404(
        application_id,
        session,
    )

    if not application.thread_id:
        raise HTTPException(
            status_code=400,
            detail="Application does not have an active LangGraph thread.",
        )

    db = Database()
    evaluator = BulkEvaluator(db)

    # --------------------------------------------------------
    # Resume LangGraph
    # --------------------------------------------------------

    try:
        final_state = await asyncio.to_thread(
            evaluator.graph.invoke,
            Command(
                resume={
                    "candidate_reply": request.candidate_reply,
                }
            ),
            config={
                "configurable": {
                    "thread_id": application.thread_id,
                }
            },
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process candidate follow-up reply: {exc}",
        ) from exc

    # --------------------------------------------------------
    # Extract updated LangGraph state
    # --------------------------------------------------------

    result = final_state.get("result") or {}
    matches = final_state.get("matches") or {}

    # --------------------------------------------------------
    # Persist latest ATS score
    # --------------------------------------------------------

    if result.get("overall_score") is not None:
        application.overall_score = result.get(
            "overall_score"
        )

    # --------------------------------------------------------
    # Persist latest score breakdown
    # --------------------------------------------------------

    application.score_breakdown = json.dumps(
        {
            "overall_score": result.get("overall_score"),
            "skill_score": result.get("skill_score"),
            "experience_score": result.get("experience_score"),
            "keyword_score": result.get("keyword_score"),
            "responsibility_score": result.get(
                "responsibility_score"
            ),
        }
    )

    # --------------------------------------------------------
    # Persist latest matched / missing skills
    # --------------------------------------------------------

    application.matched_skills = json.dumps(
        matches.get("matched_skills", [])
    )

    application.missing_skills = json.dumps(
        matches.get("missing_skills", [])
    )

    # --------------------------------------------------------
    # Persist latest strengths
    # --------------------------------------------------------

    application.strengths = json.dumps(
        {
            "skills": matches.get(
                "matched_skills",
                [],
            ),
            "keywords": matches.get(
                "matched_keywords",
                [],
            ),
            "responsibilities": matches.get(
                "matched_responsibilities",
                [],
            ),
        }
    )

    # --------------------------------------------------------
    # Persist latest gaps
    # --------------------------------------------------------

    application.gaps = json.dumps(
        {
            "skills": matches.get(
                "missing_skills",
                [],
            ),
            "keywords": matches.get(
                "missing_keywords",
                [],
            ),
            "responsibilities": matches.get(
                "missing_responsibilities",
                [],
            ),
        }
    )

    # --------------------------------------------------------
    # Persist latest responsibility results
    # --------------------------------------------------------

    application.responsibilities_matched = json.dumps(
        matches.get(
            "matched_responsibilities",
            [],
        )
    )

    application.responsibilities_missing = json.dumps(
        matches.get(
            "missing_responsibilities",
            [],
        )
    )

    # --------------------------------------------------------
    # Persist latest experience result
    # --------------------------------------------------------

    application.experience_result = json.dumps(
        {
            "candidate_years": matches.get(
                "candidate_experience_years"
            ),
            "required_min_years": matches.get(
                "required_experience_min"
            ),
            "required_max_years": matches.get(
                "required_experience_max"
            ),
            "status": matches.get(
                "experience_status"
            ),
            "matches_requirement": matches.get(
                "experience_match"
            ),
        }
    )

    # --------------------------------------------------------
    # Update application state
    # --------------------------------------------------------

    application.evaluation_status = (
        EvaluationStatus.COMPLETED
    )

    # Candidate follow-up sends the candidate back into
    # recruiter review.
    application.pipeline_stage = (
        PipelineStage.NEEDS_REVIEW
    )

    # --------------------------------------------------------
    # Persist
    # --------------------------------------------------------

    session.add(application)
    session.commit()
    session.refresh(application)

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "status": "success",
        "application_id": application_id,
        "thread_id": application.thread_id,
        "overall_score": application.overall_score,
        "verdict": final_state.get("verdict"),
        "pipeline_stage": application.pipeline_stage,
        "workflow_state": final_state,
    }

# ============================================================
# Explicit Pipeline Actions
# ============================================================


@router.post(
    "/{application_id}/hold",
)
async def hold_application(
    application_id: str,
    session: Session = Depends(get_session),
):
    """
    Explicitly place an application on hold.

    This is a convenience endpoint. The same operation can
    eventually be routed through the unified action service.
    """

    application = get_application_or_404(
        application_id,
        session,
    )

    application.pipeline_stage = PipelineStage.ON_HOLD

    action_log = RecruiterAction(
        application_id=application_id,
        actor=ActorType.RECRUITER.value,
        action_type=ActionType.HOLD,
    )

    session.add(application)
    session.add(action_log)
    session.commit()

    return {
        "status": "success",
        "application_id": application_id,
        "pipeline_stage": application.pipeline_stage,
    }


@router.post(
    "/{application_id}/reject",
)
async def reject_application(
    application_id: str,
    session: Session = Depends(get_session),
):
    """
    Explicitly reject an application.

    Email notification will be handled by the action/outbox
    service later.
    """

    application = get_application_or_404(
        application_id,
        session,
    )

    application.pipeline_stage = PipelineStage.REJECTED

    action_log = RecruiterAction(
        application_id=application_id,
        actor=ActorType.RECRUITER.value,
        action_type=ActionType.REJECT,
    )

    session.add(application)
    session.add(action_log)
    session.commit()

    return {
        "status": "success",
        "application_id": application_id,
        "pipeline_stage": application.pipeline_stage,
    }


# ============================================================
# Generic Application Action
# ============================================================


@router.post(
    "/{application_id}/actions",
)
async def perform_application_action(
    application_id: str,
    request: ActionRequest,
    session: Session = Depends(get_session),
):
    """
    Perform a recruiter pipeline action.

    This endpoint currently handles deterministic pipeline
    state changes.

    External effects such as:
        - sending rejection email
        - scheduling interview
        - sending follow-up email

    will be delegated to dedicated services/outbox later.
    """

    application = get_application_or_404(
        application_id,
        session,
    )

    domain_action = map_action_to_domain_type(
        request.action_type
    )

    new_stage = map_recruiter_action_to_stage(
        request.action_type
    )

    application.pipeline_stage = new_stage

    if request.note:
        application.recruiter_comments = request.note

    action_log = RecruiterAction(
        application_id=application_id,
        actor=ActorType.RECRUITER.value,
        action_type=domain_action,
        note=request.note,
    )

    session.add(application)
    session.add(action_log)
    session.commit()

    return {
        "status": "success",
        "application_id": application_id,
        "action": domain_action,
        "pipeline_stage": application.pipeline_stage,
    }