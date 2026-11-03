"""Recruiter availability and calendar-block helpers."""

from datetime import date, datetime, time, timedelta

from sqlmodel import Session, select

from ats_agent.domain.models import (
    CalendarBlock,
    RecruiterAvailability,
)


DEFAULT_START_TIME = time(10, 0)
DEFAULT_END_TIME = time(17, 0)


def get_weekly_availability(
    session: Session,
    recruiter_id: str,
    target_date: date,
) -> list[tuple[time, time]]:
    """
    Return all availability windows for a recruiter on a given date.

    Returns:
        List of (start_time, end_time) windows.

    Example:
        [
            (10:00, 12:00),
            (14:00, 17:00),
        ]

    Default:
        Monday-Friday: 10:00-17:00
        Saturday/Sunday: unavailable
    """

    day_of_week = target_date.weekday()

    availability_windows = list(
        session.exec(
            select(RecruiterAvailability)
            .where(
                RecruiterAvailability.recruiter_id == recruiter_id,
                RecruiterAvailability.day_of_week == day_of_week,
                RecruiterAvailability.active.is_(True),
            )
            .order_by(RecruiterAvailability.start_time)
        )
    )

    # If recruiter has manually configured availability,
    # use all configured windows.
    if availability_windows:
        return [
            (
                availability.start_time,
                availability.end_time,
            )
            for availability in availability_windows
        ]

    # Default working days: Monday-Friday.
    if day_of_week < 5:
        return [
            (
                DEFAULT_START_TIME,
                DEFAULT_END_TIME,
            )
        ]

    # Saturday/Sunday are unavailable by default.
    return []


def get_calendar_blocks(
    session: Session,
    recruiter_id: str,
    target_date: date,
) -> list[CalendarBlock]:
    """
    Return all calendar blocks affecting the given date.
    """

    day_start = datetime.combine(
        target_date,
        time.min,
    )

    day_end = datetime.combine(
        target_date + timedelta(days=1),
        time.min,
    )

    return list(
        session.exec(
            select(CalendarBlock)
            .where(
                CalendarBlock.recruiter_id == recruiter_id,
                CalendarBlock.start_at < day_end,
                CalendarBlock.end_at > day_start,
            )
            .order_by(CalendarBlock.start_at)
        )
    )


def is_full_day_blocked(
    blocks: list[CalendarBlock],
) -> bool:
    """Return True when any block marks the day unavailable."""

    return any(block.all_day for block in blocks)