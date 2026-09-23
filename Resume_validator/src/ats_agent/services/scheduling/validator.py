"""Validation for requested interview times."""

from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from ats_agent.domain.models import Interview

from ats_agent.services.scheduling.availability import (
    get_calendar_blocks,
    get_weekly_availability,
    is_full_day_blocked,
)


def validate_requested_slot(
    session: Session,
    recruiter_id: str,
    start_at: datetime,
    duration_minutes: int = 60,
) -> tuple[bool, str]:
    """
    Validate a specific requested interview slot.

    Returns:
        (True, "Slot is available")
        or
        (False, reason)
    """

    if duration_minutes <= 0:
        return False, "Interview duration must be greater than zero."

    end_at = start_at + timedelta(
        minutes=duration_minutes
    )

    target_date: date = start_at.date()

    availability_windows = get_weekly_availability(
        session=session,
        recruiter_id=recruiter_id,
        target_date=target_date,
    )

    if not availability_windows:
        return False, "Recruiter is unavailable on this day."

    # The requested interview must fit completely
    # inside at least one availability window.
    fits_availability = False

    for available_start, available_end in availability_windows:
        available_start_at = datetime.combine(
            target_date,
            available_start,
        )

        available_end_at = datetime.combine(
            target_date,
            available_end,
        )

        if (
            start_at >= available_start_at
            and end_at <= available_end_at
        ):
            fits_availability = True
            break

    if not fits_availability:
        return (
            False,
            "Requested interview is outside recruiter availability.",
        )

    # Check temporary calendar blocks.
    blocks = get_calendar_blocks(
        session=session,
        recruiter_id=recruiter_id,
        target_date=target_date,
    )

    if is_full_day_blocked(blocks):
        return (
            False,
            "Recruiter is unavailable for the entire day.",
        )

    for block in blocks:
        if (
            start_at < block.end_at
            and end_at > block.start_at
        ):
            return (
                False,
                "Requested interview overlaps a blocked period.",
            )

    # Check existing interviews.
    existing_interviews = list(
        session.exec(
            select(Interview)
            .where(
                Interview.recruiter_id == recruiter_id,
                Interview.scheduled_at < end_at,
            )
        )
    )

    for interview in existing_interviews:
        interview_end = (
            interview.scheduled_at
            + timedelta(
                minutes=interview.duration_minutes
            )
        )

        if (
            start_at < interview_end
            and end_at > interview.scheduled_at
        ):
            return (
                False,
                "Requested interview overlaps an existing interview.",
            )

    return True, "Slot is available."