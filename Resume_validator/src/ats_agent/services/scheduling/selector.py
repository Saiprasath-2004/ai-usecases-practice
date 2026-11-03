"""Select an interview slot from recruiter scheduling intent."""

from datetime import datetime, timedelta

from sqlmodel import Session

from ats_agent.services.scheduling.intent import SchedulingIntent
from ats_agent.services.scheduling.slot_generator import (
    generate_available_slots,
)


def select_interview_slot(
    session: Session,
    recruiter_id: str,
    intent: SchedulingIntent,
    now: datetime | None = None,
    max_days: int = 30,
) -> datetime:
    """
    Select the earliest available interview slot matching the recruiter intent.

    The LLM only produces SchedulingIntent.

    This function deterministically selects an actual calendar slot by
    applying the recruiter's date, weekday, and time preferences against
    the existing scheduling system.
    """

    if now is None:
        now = datetime.now()

    duration = intent.duration_minutes

    if duration <= 0:
        raise ValueError(
            "Interview duration must be greater than zero."
        )

    if max_days <= 0:
        raise ValueError(
            "max_days must be greater than zero."
        )

    # ---------------------------------------------------------
    # Determine search range
    # ---------------------------------------------------------

    if intent.preferred_date:
        start_date = intent.preferred_date
        end_date = intent.preferred_date

    elif intent.date_range_start:
        start_date = intent.date_range_start
        end_date = (
            intent.date_range_end
            or start_date + timedelta(days=max_days)
        )

    else:
        start_date = now.date()
        end_date = start_date + timedelta(days=max_days)

    # ---------------------------------------------------------
    # Convert LLM time strings into Python time objects
    # ---------------------------------------------------------

    preferred_time_start = intent.get_time_start()
    preferred_time_end = intent.get_time_end()

    # ---------------------------------------------------------
    # Search day by day
    # ---------------------------------------------------------

    current_date = start_date

    while current_date <= end_date:

        # -----------------------------------------------------
        # Apply preferred weekday
        # -----------------------------------------------------

        if (
            intent.preferred_weekdays
            and current_date.weekday()
            not in intent.preferred_weekdays
        ):
            current_date += timedelta(days=1)
            continue

        # -----------------------------------------------------
        # Generate valid calendar slots
        #
        # generate_available_slots() already handles:
        # - availability
        # - holidays
        # - blocks
        # - existing interviews
        # - minimum notice
        # -----------------------------------------------------

        slots = generate_available_slots(
            session=session,
            recruiter_id=recruiter_id,
            target_date=current_date,
            duration_minutes=duration,
            slot_interval_minutes=30,
        )

        # -----------------------------------------------------
        # Filter generated slots using recruiter preferences
        # -----------------------------------------------------

        for slot in slots:

            slot_start = slot["start"]
            slot_end = slot["end"]

            # -------------------------------------------------
            # Preferred start time
            # -------------------------------------------------

            if (
                preferred_time_start
                and slot_start.time() < preferred_time_start
            ):
                continue

            # -------------------------------------------------
            # Preferred end time
            #
            # Check the END of the interview, not only the
            # starting time.
            # -------------------------------------------------

            if (
                preferred_time_end
                and slot_end.time() > preferred_time_end
            ):
                continue

            # -------------------------------------------------
            # First matching deterministic slot
            # -------------------------------------------------

            return slot_start

        current_date += timedelta(days=1)

    raise ValueError(
        "No available interview slot matches the "
        "recruiter's scheduling request."
    )