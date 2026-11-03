"""Recruiter-triggered actions: the things that happen when a recruiter
clicks a button on the dashboard (Schedule Interview / Get More Details /
Reject / Hold). Each function operates on a persisted ``Application`` row
and is safe to call directly from an API route.

Emails are "sent" through a local idempotent outbox (SQLite) rather than a
real provider -- see EMAIL_PROVIDER in config.py. Swap ``_deliver`` for a
real SMTP/API call later without touching the calling code.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
import datetime as dt
from typing import Optional

from sqlmodel import Session

from ats_agent.config import ACTIONS_DB_PATH, EMAIL_PROVIDER, SELECT_CUTOFF
from ats_agent.domain.models import (
    Application,
    JobRequisition,
    Interview,
    FollowUpRequest,
    CandidateReply,
    RecruiterAction,
    ActionType,
    PipelineStage,
    EvaluationRun,
    EvaluationResult,
    RunStatus,
)
from ats_agent.agent_layer import calendar
from ats_agent.agent_layer.email_templates import (
    Email,
    interview_invite_email,
    rejection_email,
    followup_request_email,
)
from ats_agent.agent_layer.decision import decide
from ats_agent.agent_layer.followup import (
    build_followup_questions,
    extract_confirmed_skills,
    apply_followup_reply,
)


# --- Outbox (mock email delivery) ---

def _init_outbox() -> None:
    with sqlite3.connect(ACTIONS_DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS action_outbox (
                action_id TEXT PRIMARY KEY,
                application_id TEXT,
                action_type TEXT,
                to_email TEXT,
                subject TEXT,
                body TEXT,
                status TEXT,
                created_at TEXT,
                sent_at TEXT
            )
        """)
        conn.commit()


def _deliver(application_id: str, action_type: str, email: Email) -> str:
    """Record the email in the outbox and 'send' it. Returns the action_id."""
    _init_outbox()
    action_id = str(uuid.uuid4())
    now = dt.datetime.utcnow().isoformat()

    with sqlite3.connect(ACTIONS_DB_PATH) as conn:
        conn.execute(
            "INSERT INTO action_outbox "
            "(action_id, application_id, action_type, to_email, subject, body, status, created_at, sent_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'SENT', ?, ?)",
            (action_id, application_id, action_type, email.to, email.subject, email.body, now, now),
        )
        conn.commit()

    # Mock provider: print instead of an actual network call.
    print(f"[EMAIL PROVIDER {EMAIL_PROVIDER}] -> {email.to}: {email.subject}")
    return action_id


def list_outbox_for_application(application_id: str) -> list[dict]:
    _init_outbox()
    with sqlite3.connect(ACTIONS_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM action_outbox WHERE application_id = ? ORDER BY created_at DESC",
            (application_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def _log_action(session: Session, application_id: str, action_type: ActionType, note: Optional[str] = None):
    session.add(RecruiterAction(
        application_id=application_id,
        actor="Recruiter",
        action_type=action_type,
        note=note,
    ))


# --- Recruiter-triggered actions ---

def schedule_interview_for_application(session: Session, application: Application, job: JobRequisition) -> dict:
    """Find the next open slot on the recruiter's (mock) calendar and email an invite."""
    slot = calendar.find_next_available_slot(session, job.id)
    db_slot = calendar.book_slot(session, job.id, slot)

    interview = Interview(
        application_id=application.application_id,
        slot_id=db_slot.id,
        scheduled_at=slot.start,
        status="Scheduled",
    )
    session.add(interview)

    email = interview_invite_email(
        candidate_name=application.candidate_name,
        job_title=job.title,
        slot_start=slot.start,
        slot_end=slot.end,
        to_email=application.candidate_email,
    )
    _deliver(application.application_id, "INTERVIEW_INVITE", email)

    application.interview_status = "Scheduled"
    application.pipeline_stage = PipelineStage.SHORTLISTED
    session.add(application)
    _log_action(session, application.application_id, ActionType.SCHEDULE_INTERVIEW,
                note=f"Interview scheduled for {slot.start.isoformat()}")
    session.commit()

    return {"scheduled_at": slot.start.isoformat(), "ends_at": slot.end.isoformat()}


def reject_application_with_reason(session: Session, application: Application, job: JobRequisition, reason: str) -> None:
    """Send a final rejection with the recruiter's stated reasoning."""
    email = rejection_email(
        candidate_name=application.candidate_name,
        job_title=job.title,
        reason=reason,
        to_email=application.candidate_email,
    )
    _deliver(application.application_id, "REJECTION_NOTICE", email)

    application.pipeline_stage = PipelineStage.REJECTED
    session.add(application)
    _log_action(session, application.application_id, ActionType.REJECT, note=reason)
    session.commit()


def hold_application(session: Session, application: Application, note: Optional[str] = None) -> None:
    application.pipeline_stage = PipelineStage.ON_HOLD
    session.add(application)
    _log_action(session, application.application_id, ActionType.HOLD, note=note)
    session.commit()


def move_to_review(session: Session, application: Application, note: Optional[str] = None) -> None:
    application.pipeline_stage = PipelineStage.NEEDS_REVIEW
    session.add(application)
    _log_action(session, application.application_id, ActionType.MOVE_TO_REVIEW, note=note)
    session.commit()


def request_followup_for_application(session: Session, application: Application, job: JobRequisition) -> list[str]:
    """Ask the candidate about their top missing skills and email the questions."""
    missing_skills = json.loads(application.missing_skills or "[]")
    questions = build_followup_questions(missing_skills)

    if not questions:
        questions = ["Could you tell us more about your relevant experience for this role?"]

    followup = FollowUpRequest(
        application_id=application.application_id,
        request_text=json.dumps(questions),
        status="Pending",
    )
    session.add(followup)

    email = followup_request_email(
        candidate_name=application.candidate_name,
        job_title=job.title,
        questions=questions,
        to_email=application.candidate_email,
    )
    _deliver(application.application_id, "FOLLOWUP_REQUEST", email)

    application.follow_up_status = "Requested"
    session.add(application)
    _log_action(session, application.application_id, ActionType.MOVE_TO_REVIEW, note="Requested candidate follow-up")
    session.commit()

    return questions


def submit_followup_reply_for_application(session: Session, application: Application, reply_text: str) -> dict:
    """
    Apply a candidate's follow-up reply to their score, preserving history
    via the application's evaluation_thread_id, and re-derive the pipeline
    stage from the new score.
    """
    from sqlmodel import select

    followup = session.exec(
        select(FollowUpRequest)
        .where(FollowUpRequest.application_id == application.application_id)
        .where(FollowUpRequest.status == "Pending")
        .order_by(FollowUpRequest.sent_at.desc())
    ).first()

    questions = json.loads(followup.request_text) if followup else []

    session.add(CandidateReply(
        follow_up_id=followup.id if followup else 0,
        reply_text=reply_text,
    ))

    current_result = json.loads(application.score_breakdown or "{}")
    confirmed_skills = extract_confirmed_skills(reply_text, questions)
    new_result = apply_followup_reply(current_result, questions, confirmed_skills)

    # Move confirmed skills from missing -> matched for display purposes.
    matched = json.loads(application.matched_skills or "[]")
    missing = json.loads(application.missing_skills or "[]")
    for skill in confirmed_skills:
        if skill in missing:
            missing.remove(skill)
        if skill not in matched:
            matched.append(skill)

    application.overall_score = new_result.get("overall_score")
    application.score_breakdown = json.dumps(new_result)
    application.matched_skills = json.dumps(matched)
    application.missing_skills = json.dumps(missing)
    application.follow_up_status = "Replied"

    verdict = decide(new_result)
    if verdict.value == "SELECT":
        application.pipeline_stage = PipelineStage.SHORTLISTED
    elif verdict.value == "REJECT":
        application.pipeline_stage = PipelineStage.REJECTED
    else:
        application.pipeline_stage = PipelineStage.NEEDS_REVIEW

    if followup:
        followup.status = "Answered"
        session.add(followup)

    session.add(application)

    # Record score history on the *same* thread id, so a recruiter can see
    # the before/after of a follow-up without losing the original run.
    thread_id = application.evaluation_thread_id or f"eval_{uuid.uuid4().hex}"
    application.evaluation_thread_id = thread_id
    run = EvaluationRun(
        application_id=application.application_id,
        thread_id=thread_id,
        status=RunStatus.COMPLETED,
        completed_at=dt.datetime.utcnow(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)

    session.add(EvaluationResult(
        run_id=run.run_id,
        application_id=application.application_id,
        score=new_result.get("overall_score", 0.0),
        breakdown=json.dumps(new_result),
        evidence=json.dumps({"confirmed_skills": confirmed_skills}),
        narrative=f"Follow-up reply confirmed: {', '.join(confirmed_skills) or 'no additional skills'}.",
    ))
    session.commit()

    return {
        "confirmed_skills": confirmed_skills,
        "new_score": new_result.get("overall_score"),
        "new_stage": application.pipeline_stage,
    }
