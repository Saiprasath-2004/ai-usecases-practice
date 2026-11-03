"""Application API routes for the ATS recruiter product."""

import asyncio
import json
import uuid
from datetime import datetime

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
    InterviewResponseRequest

)
from ats_agent.batch import BulkEvaluator
from ats_agent.domain.models import (
    ActionType,
    ActorType,
    Application,
    EvaluationRun,
    EvaluationStatus,
    EvaluationResult,
    Interview,
    JobRequisition,
    PipelineStage,
    RecruiterAction,
    RunStatus
)
from ats_agent.persistence.database import Database
from ats_agent.llm.client import get_chat_model
from ats_agent.agent_layer.actions import send_rejection_notice

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
        "CONFIRM_REJECTION": PipelineStage.REJECTED,

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

    normalized = (
        action_type.strip()
        .upper()
        .replace(" ", "_")
        .replace("-", "_")
    )

    action_map = {
        "HOLD": ActionType.HOLD,
        "ON_HOLD": ActionType.HOLD,

        "REJECT": ActionType.REJECT,
        "REJECTED": ActionType.REJECT,
        "CONFIRM_REJECTION": ActionType.REJECT,

        "MOVE_TO_REVIEW": ActionType.MOVE_TO_REVIEW,
        "NEEDS_REVIEW": ActionType.MOVE_TO_REVIEW,

        "GET_MORE_DETAILS": ActionType.APPROVE_FOLLOWUP,

        "SCHEDULE_INTERVIEW": ActionType.SCHEDULE_INTERVIEW,

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
# Get Evaluation history
# ============================================================

@router.get("/{application_id}/evaluations")
def get_evaluation_history(
    application_id: str,
    session: Session = Depends(get_session),
):
    runs = session.exec(
        select(EvaluationRun)
        .where(EvaluationRun.application_id == application_id)
        .order_by(EvaluationRun.started_at.desc())
    ).all()

    results = []

    for run in runs:
        evaluation = session.exec(
            select(EvaluationResult)
            .where(EvaluationResult.run_id == run.run_id)
        ).first()

        results.append(
            {
                "run_id": run.run_id,
                "status": run.status,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "user_facing_error": run.user_facing_error,
                "result": (
                    {
                        "score": evaluation.score,
                        "breakdown": evaluation.breakdown,
                        "evidence": evaluation.evidence,
                        "narrative": evaluation.narrative,
                    }
                    if evaluation
                    else None
                ),
            }
        )

    return results


# ============================================================
# Get Current Evaluation
# ============================================================

@router.get("/{application_id}/evaluation")
def get_current_evaluation(
    application_id: str,
    session: Session = Depends(get_session),
):
    application = session.get(
        Application,
        application_id,
    )

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found",
        )

    if not application.current_evaluation_run_id:
        return {
            "application_id": application_id,
            "evaluation": None,
        }

    run = session.get(
        EvaluationRun,
        application.current_evaluation_run_id,
    )

    if not run:
        return {
            "application_id": application_id,
            "evaluation": None,
        }

    evaluation = session.exec(
        select(EvaluationResult)
        .where(
            EvaluationResult.run_id == run.run_id
        )
    ).first()

    return {
        "application_id": application_id,
        "run_id": run.run_id,
        "status": run.status,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "user_facing_error": run.user_facing_error,
        "result": (
            {
                "score": evaluation.score,
                "breakdown": evaluation.breakdown,
                "evidence": evaluation.evidence,
                "narrative": evaluation.narrative,
            }
            if evaluation
            else None
        ),
    }
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
            "application_id": application_id,
            "evaluation_status": updated_application.evaluation_status,
            "pipeline_stage": updated_application.pipeline_stage,
            "overall_score": updated_application.overall_score,
            "thread_id": updated_application.thread_id,
            "run_id": latest_run.run_id if latest_run else None,
            "run_status": latest_run.status if latest_run else None,
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

    Schedule Interview:
        recruiter comments
            -> LLM scheduling intent
            -> deterministic slot selection
            -> interview booking
            -> interview invite

    Get More Details:
        recruiter decision
            -> LangGraph generates follow-up questions
            -> graph pauses at candidate interrupt
            -> mock follow-up email is sent
            -> candidate can later reply through /followup-reply
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

    # --------------------------------------------------------
    # Validate domain action
    # --------------------------------------------------------

    domain_action = map_action_to_domain_type(
        action_type
    )

    # --------------------------------------------------------
    # Schedule Interview validation
    # --------------------------------------------------------

    if action_type.upper() == "SCHEDULE INTERVIEW":
        if not request.comments or not request.comments.strip():
            raise HTTPException(
                status_code=400,
                detail=(
                    "comments are required when scheduling an "
                    "interview. Provide a scheduling instruction "
                    "such as 'next Tuesday afternoon'."
                ),
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
        print("\n========== FOLLOW-UP DEBUG ==========")
        print("final_state type:", type(final_state))
        print("final_state:", repr(final_state))
        print(
            "interrupts:",
            repr(final_state.get("__interrupt__"))
        )
        print("====================================\n")

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume ATS workflow: {exc}",
        ) from exc

    # --------------------------------------------------------
    # External communication state
    # --------------------------------------------------------

    interview = None

    action_id = None
    email_status = None

    followup_action_id = None
    followup_status = None

    # --------------------------------------------------------
    # Schedule Interview
    # --------------------------------------------------------

    if action_type.upper() == "SCHEDULE INTERVIEW":

        from ats_agent.services.scheduling.intent_parser import (
            parse_scheduling_intent,
        )

        from ats_agent.services.scheduling.selector import (
            select_interview_slot,
        )

        from ats_agent.services.scheduling.booking import (
            book_interview,
        )

        from ats_agent.agent_layer.actions import (
            send_interview_invite,
        )

        try:

            # ------------------------------------------------
            # 1. Get configured LLM
            # ------------------------------------------------

            llm = get_chat_model(
                json_mode=False
            )

            # ------------------------------------------------
            # 2. Parse recruiter natural language
            # ------------------------------------------------

            scheduling_intent = parse_scheduling_intent(
                llm=llm,
                recruiter_comment=request.comments,
            )

            # ------------------------------------------------
            # 3. Select actual available slot
            # ------------------------------------------------

            scheduled_at = select_interview_slot(
                session=session,
                recruiter_id="recruiter_1",
                intent=scheduling_intent,
            )

            # ------------------------------------------------
            # 4. Create interview as PendingInvitation
            # ------------------------------------------------

            interview = book_interview(
                session=session,
                application_id=application.application_id,
                recruiter_id="recruiter_1",
                scheduled_at=scheduled_at,
                candidate_email=application.candidate_email,
                duration_minutes=scheduling_intent.duration_minutes,
            )

            # ------------------------------------------------
            # 5. Send candidate invitation
            # ------------------------------------------------

            action_id, email_status = send_interview_invite(
                thread_id=application.thread_id,
                candidate_data={
                    "candidate_name": application.candidate_name,
                    "email": application.candidate_email,
                    "scheduled_at": interview.scheduled_at.isoformat(),
                    "duration_minutes": interview.duration_minutes,
                    "meeting_url": interview.meeting_url,
                    "provider": interview.provider,
                    "notes": interview.notes,
                },
            )

            # ------------------------------------------------
            # 6. Invitation result controls interview state
            # ------------------------------------------------

            if email_status != "SENT":
                # The invitation failed.
                # Do not allow the interview to become a confirmed
                # scheduled interview.
                session.rollback()

                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Interview slot was selected, but the candidate "
                        "invitation could not be sent. The interview was "
                        "not confirmed."
                    ),
                )

            # ------------------------------------------------
            # 7. Invitation succeeded
            # ------------------------------------------------

            interview.status = "Scheduled"
            interview.invitation_status = "SENT"
            interview.invitation_action_id = action_id
            interview.candidate_response = "AWAITING_RESPONSE"

            session.add(interview)

        except ValueError as exc:
            session.rollback()

            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from exc

        except HTTPException:
            raise

        except Exception as exc:
            session.rollback()

            raise HTTPException(
                status_code=500,
                detail=f"Failed to schedule interview: {exc}",
            ) from exc

    # --------------------------------------------------------
    # Get More Details → Send candidate follow-up email
    # --------------------------------------------------------

    if action_type.upper() == "GET MORE DETAILS":

        from ats_agent.agent_layer.actions import (
            send_followup_request,
        )

        

        questions = final_state.get(
            "followup_questions"
        ) or []

        if not questions:

            interrupts = final_state.get(
                "__interrupt__"
            ) or []

            if interrupts:

                interrupt_item = interrupts[0]

                if isinstance(interrupt_item, dict):
                    interrupt_value = interrupt_item.get("value")
                else:
                    interrupt_value = getattr(
                        interrupt_item,
                        "value",
                        None,
                    )

                if isinstance(interrupt_value, dict):
                    questions = (
                        interrupt_value.get("questions")
                        or []
                    )

        # ----------------------------------------------------
        # Validate questions
        # ----------------------------------------------------

        if not questions:
            raise HTTPException(
                status_code=500,
                detail=(
                    "LangGraph reached the candidate follow-up "
                    "interrupt, but no follow-up questions were found."
                ),
            )

        # ----------------------------------------------------
        # Send mock candidate email
        # ----------------------------------------------------

        try:

            (
                followup_action_id,
                followup_status,
            ) = send_followup_request(
                thread_id=application.thread_id,
                candidate_data={
                    "candidate_name": application.candidate_name,
                    "email": application.candidate_email,
                },
                questions=questions,
            )

        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Follow-up questions were generated, "
                    f"but the candidate notification failed: {exc}"
                ),
            ) from exc

    # --------------------------------------------------------
    # Determine resulting pipeline state
    # --------------------------------------------------------

    new_stage = map_recruiter_action_to_stage(
        action_type
    )

    application.pipeline_stage = new_stage

    if request.comments:
        application.recruiter_comments = request.comments

    # --------------------------------------------------------
    # Persist recruiter action
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Build response
    # --------------------------------------------------------

    return {
        "status": "success",
        "application_id": application_id,
        "action": domain_action,
        "pipeline_stage": application.pipeline_stage,
        "thread_id": application.thread_id,

        "interview": (
            {
                "id": interview.id,
                "application_id": interview.application_id,
                "recruiter_id": interview.recruiter_id,

                "scheduled_at": interview.scheduled_at,
                "duration_minutes": interview.duration_minutes,

                "status": interview.status,

                "invitation_status": interview.invitation_status,
                "invitation_action_id": interview.invitation_action_id,

                "candidate_response": interview.candidate_response,
                "candidate_responded_at": interview.candidate_responded_at,

                "provider": interview.provider,
                "external_event_id": interview.external_event_id,
                "meeting_url": interview.meeting_url,

                "candidate_email": interview.candidate_email,
                "notes": interview.notes,
            }
            if interview
            else None
        ),

        "communication": {
            "action_id": (
                action_id
                if action_type.upper() == "SCHEDULE INTERVIEW"
                else followup_action_id
            ),
            "status": (
                email_status
                if action_type.upper() == "SCHEDULE INTERVIEW"
                else followup_status
            ),
        },
    }


# ============================================================
# Candidate Interview Response
# ============================================================


@router.post(
    "/{application_id}/interview/respond",
)
async def submit_interview_response(
    application_id: str,
    request: InterviewResponseRequest,
    session: Session = Depends(get_session),
):
    """
    Record the candidate's response to an interview invitation.

    Supported responses:
        ACCEPTED
        DECLINED
    """

    application = get_application_or_404(
        application_id,
        session,
    )

    # --------------------------------------------------------
    # 1. Validate candidate response
    # --------------------------------------------------------

    response = request.response.strip().upper()

    if response not in {"ACCEPTED", "DECLINED"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid interview response. "
                "Use ACCEPTED or DECLINED."
            ),
        )

    # --------------------------------------------------------
    # 2. Find the application's active interview
    # --------------------------------------------------------

    interview = session.exec(
        select(Interview)
        .where(
            Interview.application_id == application_id,
            Interview.status == "Scheduled",
        )
        .order_by(Interview.scheduled_at.desc())
    ).first()

    if not interview:
        raise HTTPException(
            status_code=404,
            detail="No scheduled interview found for this application.",
        )

    # --------------------------------------------------------
    # 3. Validate invitation state
    # --------------------------------------------------------

    if interview.invitation_status != "SENT":
        raise HTTPException(
            status_code=409,
            detail=(
                "The interview invitation has not been successfully "
                "sent, so the candidate cannot respond to it."
            ),
        )

    # --------------------------------------------------------
    # 4. Prevent duplicate response
    # --------------------------------------------------------

    if interview.candidate_response != "AWAITING_RESPONSE":
        raise HTTPException(
            status_code=409,
            detail=(
                "The candidate has already responded to this "
                "interview invitation."
            ),
        )

    # --------------------------------------------------------
    # 5. Record candidate response
    # --------------------------------------------------------

    from datetime import datetime, timezone

    interview.candidate_response = response
    interview.candidate_responded_at = datetime.now(
        timezone.utc
    )

    session.add(interview)
    session.commit()
    session.refresh(interview)

    # --------------------------------------------------------
    # 6. Return recruiter-visible state
    # --------------------------------------------------------

    return {
        "status": "success",
        "application_id": application_id,
        "interview": {
            "id": interview.id,
            "scheduled_at": interview.scheduled_at,
            "duration_minutes": interview.duration_minutes,
            "status": interview.status,
            "invitation_status": interview.invitation_status,
            "candidate_response": interview.candidate_response,
            "candidate_responded_at": (
                interview.candidate_responded_at
            ),
            "meeting_url": interview.meeting_url,
        },
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

    A NEW EvaluationRun and EvaluationResult are created
    so that the previous evaluation remains in history.

    The Application is updated with the latest evaluation
    snapshot and points to the new current evaluation run.
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
    # Create NEW evaluation run
    # --------------------------------------------------------

    new_run = EvaluationRun(
        application_id=application.application_id,
        thread_id=application.thread_id,
        status=RunStatus.WAITING_REVIEW,
        started_at=datetime.utcnow(),
    )

    session.add(new_run)
    session.flush()

    # --------------------------------------------------------
    # Persist latest ATS score to Application snapshot
    # --------------------------------------------------------

    if result.get("overall_score") is not None:
        application.overall_score = result.get(
            "overall_score"
        )

    # --------------------------------------------------------
    # Persist latest score breakdown
    # --------------------------------------------------------

    breakdown = {
        "overall_score": result.get("overall_score"),
        "skill_score": result.get("skill_score"),
        "experience_score": result.get("experience_score"),
        "keyword_score": result.get("keyword_score"),
        "responsibility_score": result.get(
            "responsibility_score"
        ),
    }

    application.score_breakdown = json.dumps(breakdown)

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
    # Create historical EvaluationResult
    # --------------------------------------------------------

    evaluation_result = EvaluationResult(
        run_id=new_run.run_id,
        application_id=application.application_id,
        score=result.get("overall_score"),
        breakdown=json.dumps(breakdown),
        evidence=json.dumps(matches),
        narrative=final_state.get("narrative"),
    )

    session.add(evaluation_result)

    # --------------------------------------------------------
    # Update Application state
    # --------------------------------------------------------

    application.evaluation_status = (
        EvaluationStatus.COMPLETED
    )

    application.pipeline_stage = (
        PipelineStage.NEEDS_REVIEW
    )

    # IMPORTANT:
    # The new follow-up evaluation is now the current run.
    application.current_evaluation_run_id = new_run.run_id

    # --------------------------------------------------------
    # Complete the new evaluation run
    # --------------------------------------------------------

    new_run.completed_at = datetime.utcnow()

    # --------------------------------------------------------
    # Persist everything
    # --------------------------------------------------------

    session.add(application)
    session.add(new_run)
    session.add(evaluation_result)

    session.commit()

    session.refresh(application)

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "status": "success",
        "application_id": application_id,
        "thread_id": application.thread_id,
        "run_id": new_run.run_id,
        "run_status": new_run.status,
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
    Explicitly reject an application and send the
    candidate rejection notification.
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

    # --------------------------------------------------------
    # 1. Update application state
    # --------------------------------------------------------

    application.pipeline_stage = PipelineStage.REJECTED

    # --------------------------------------------------------
    # 2. Persist recruiter action
    # --------------------------------------------------------

    action_log = RecruiterAction(
        application_id=application_id,
        actor=ActorType.RECRUITER.value,
        action_type=ActionType.REJECT,
    )

    session.add(application)
    session.add(action_log)
    session.commit()
    session.refresh(application)

    # --------------------------------------------------------
    # 3. Send candidate rejection notification
    # --------------------------------------------------------

    try:
        action_id, email_status = send_rejection_notice(
            thread_id=application.thread_id,
            candidate_data={
                "candidate_name": application.candidate_name,
                "email": application.candidate_email,
            },
        )

    except Exception as exc:
        # Rejection itself remains persisted.
        # Communication failure is reported separately.
        raise HTTPException(
            status_code=500,
            detail=(
                "Application was rejected, but the candidate "
                f"notification failed: {exc}"
            ),
        ) from exc

    return {
        "status": "success",
        "application_id": application_id,
        "pipeline_stage": application.pipeline_stage,
        "communication": {
            "action_id": action_id,
            "status": email_status,
        },
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

@router.get("/{application_id}/actions")
def get_application_actions(
    application_id: str,
    session: Session = Depends(get_session),
):
    application = get_application_or_404(
        application_id,
        session,
    )

    statement = (
        select(RecruiterAction)
        .where(
            RecruiterAction.application_id == application.application_id
        )
        .order_by(RecruiterAction.timestamp.desc())
    )

    return session.exec(statement).all()