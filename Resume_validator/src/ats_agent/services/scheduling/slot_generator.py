"""Generate available interview slots."""

from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from ats_agent.domain.models import Interview

from ats_agent.services.scheduling.availability import (
    get_calendar_blocks,
    get_weekly_availability,
    is_full_day_blocked,
)
from ats_agent.services.scheduling.holidays import is_public_holiday
from ats_agent.services.scheduling.notice import (
    get_minimum_allowed_start,
)

def _overlaps(
    start: datetime,
    end: datetime,
    blocked_start: datetime,
    blocked_end: datetime,
) -> bool:
    """Return True when two time ranges overlap."""

    return start < blocked_end and end > blocked_start


def generate_available_slots(
    session: Session,
    recruiter_id: str,
    target_date: date,
    duration_minutes: int = 60,
    slot_interval_minutes: int = 30,
) -> list[dict[str, datetime]]:
    """
    Generate available interview slots for a recruiter on a date.

    Rules:
        - Supports multiple availability windows.
        - Default Monday-Friday is 10:00-17:00.
        - Saturday/Sunday are unavailable by default.
        - Full-day blocks make the entire day unavailable.
        - Partial calendar blocks remove conflicting slots.
        - Existing interviews remove conflicting slots.
        - Interview duration must fit completely inside an availability window.
    """

    if duration_minutes <= 0:
        raise ValueError(
            "duration_minutes must be greater than zero."
        )

    if slot_interval_minutes <= 0:
        raise ValueError(
            "slot_interval_minutes must be greater than zero."
        )

    availability_windows = get_weekly_availability(
        session=session,
        recruiter_id=recruiter_id,
        target_date=target_date,
    )

    if not availability_windows:
        return []

    if is_public_holiday(session, target_date):
        return []

    minimum_allowed_start = get_minimum_allowed_start()

    

    blocks = get_calendar_blocks(
        session=session,
        recruiter_id=recruiter_id,
        target_date=target_date,
    )

    if is_full_day_blocked(blocks):
        return []

    # Used only to fetch interviews affecting this date.
    day_start = datetime.combine(
        target_date,
        time.min,
    )

    day_end = datetime.combine(
        target_date + timedelta(days=1),
        time.min,
    )

    existing_interviews = list(
        session.exec(
            select(Interview)
            .where(
                Interview.recruiter_id == recruiter_id,
                Interview.scheduled_at < day_end,
            )
        )
    )

    slots: list[dict[str, datetime]] = []

    duration = timedelta(minutes=duration_minutes)
    interval = timedelta(minutes=slot_interval_minutes)

    # Generate slots independently for every availability window.
    for available_start, available_end in availability_windows:

        window_start = datetime.combine(
            target_date,
            available_start,
        )

        window_end = datetime.combine(
            target_date,
            available_end,
        )

        candidate_start = window_start

        while candidate_start + duration <= window_end:

            candidate_end = candidate_start + duration

            if candidate_start < minimum_allowed_start:
                candidate_start += interval
                continue

            # Check calendar blocks.
            blocked = any(
                _overlaps(
                    candidate_start,
                    candidate_end,
                    block.start_at,
                    block.end_at,
                )
                for block in blocks
            )

            # Check existing interviews.
            already_booked = any(
                _overlaps(
                    candidate_start,
                    candidate_end,
                    interview.scheduled_at,
                    interview.scheduled_at
                    + timedelta(
                        minutes=interview.duration_minutes
                    ),
                )
                for interview in existing_interviews
            )

            if not blocked and not already_booked:
                slots.append(
                    {
                        "start": candidate_start,
                        "end": candidate_end,
                    }
                )

            candidate_start += interval

    # Keep results chronologically ordered.
    slots.sort(key=lambda slot: slot["start"])

    return slots

def find_next_available_slot(
    session: Session,
    recruiter_id: str,
    duration_minutes: int = 60,
    slot_interval_minutes: int = 30,
    max_days: int = 30,
) -> dict[str, datetime] | None:
    """
    Find the earliest available interview slot.

    The search automatically skips:
        - slots before minimum notice
        - weekends
        - unavailable days
        - full-day blocks
        - partial calendar blocks
        - existing interviews

    Searches forward up to max_days.
    """

    if duration_minutes <= 0:
        raise ValueError(
            "duration_minutes must be greater than zero."
        )

    if slot_interval_minutes <= 0:
        raise ValueError(
            "slot_interval_minutes must be greater than zero."
        )

    if max_days <= 0:
        raise ValueError(
            "max_days must be greater than zero."
        )

    minimum_allowed_start = get_minimum_allowed_start()

    search_date = minimum_allowed_start.date()

    for _ in range(max_days):

        slots = generate_available_slots(
            session=session,
            recruiter_id=recruiter_id,
            target_date=search_date,
            duration_minutes=duration_minutes,
            slot_interval_minutes=slot_interval_minutes,
        )

        if slots:
            return slots[0]

        search_date += timedelta(days=1)

    return None