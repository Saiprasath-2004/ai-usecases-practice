"""Interview booking service."""

from datetime import datetime, timedelta

from sqlmodel import Session, select

from ats_agent.domain.models import Interview
from ats_agent.services.scheduling.validator import validate_requested_slot

def book_interview(
    session: Session,
    application_id: str,
    recruiter_id: str,
    scheduled_at: datetime,
    candidate_email: str,
    duration_minutes: int = 60,
    provider: str | None = None,
    meeting_url: str | None = None,
    notes: str | None = None,
) -> Interview:
    """
    Validate and create an interview in PendingInvitation state.

    The interview is NOT considered confirmed until the invitation
    has been successfully sent by the caller.
    """

    if duration_minutes <= 0:
        raise ValueError(
            "duration_minutes must be greater than zero."
        )

    if not candidate_email.strip():
        raise ValueError("Candidate email is required.")

    # ---------------------------------------------------------
    # 1. Validate requested slot
    # ---------------------------------------------------------
    is_available, message = validate_requested_slot(
        session=session,
        recruiter_id=recruiter_id,
        start_at=scheduled_at,
        duration_minutes=duration_minutes,
    )

    if not is_available:
        raise ValueError(message)

    # ---------------------------------------------------------
    # 2. Final double-booking check
    # ---------------------------------------------------------
    requested_end = scheduled_at + timedelta(
        minutes=duration_minutes
    )

    existing_interviews = list(
        session.exec(
            select(Interview).where(
                Interview.recruiter_id == recruiter_id,
                Interview.scheduled_at < requested_end,
            )
        )
    )

    for interview in existing_interviews:
        interview_end = (
            interview.scheduled_at
            + timedelta(minutes=interview.duration_minutes)
        )

        if (
            scheduled_at < interview_end
            and requested_end > interview.scheduled_at
        ):
            raise ValueError(
                "Requested interview overlaps an existing interview."
            )

    # ---------------------------------------------------------
    # 3. Create interview as PendingInvitation
    # ---------------------------------------------------------
    interview = Interview(
        application_id=application_id,
        recruiter_id=recruiter_id,
        scheduled_at=scheduled_at,
        duration_minutes=duration_minutes,

        # Lifecycle state
        status="PendingInvitation",
        invitation_status="PENDING",
        candidate_response="AWAITING_RESPONSE",

        provider=provider,
        meeting_url=meeting_url,
        candidate_email=candidate_email,
        notes=notes,
    )

    # ---------------------------------------------------------
    # 4. Add to current DB transaction
    # ---------------------------------------------------------
    session.add(interview)
    session.flush()

    return interview