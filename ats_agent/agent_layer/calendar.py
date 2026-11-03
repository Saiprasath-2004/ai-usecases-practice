"""Mock recruiter calendar used for interview scheduling.

This is a stand-in for a real calendar integration (Google Calendar /
Outlook). It models the recruiter's availability as a simple recurring
weekly schedule and finds the next free slot for a given job, taking already
-booked ``Interview`` rows into account so two candidates don't get double
-booked into the same slot.

Swap this module out for a real provider later: keep the function
signatures (``find_next_available_slot``) the same and the rest of the app
(``agent_layer/actions.py``) won't need to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, time
from typing import Optional

from sqlmodel import Session, select

from ats_agent.domain.models import Interview, InterviewSlot

# --- Recruiter working-hours configuration (mock) ---
WORKING_DAYS = {0, 1, 2, 3, 4}  # Monday=0 ... Friday=4
WORKING_HOURS_START = time(9, 30)
WORKING_HOURS_END = time(17, 30)
INTERVIEW_DURATION_MINUTES = 45
SLOT_STEP_MINUTES = 45  # back-to-back slots
BUSINESS_DAYS_LOOKAHEAD = 14  # give up searching after 2 working weeks


@dataclass
class Slot:
    start: datetime
    end: datetime


def _candidate_slots_for_day(day: datetime) -> list[Slot]:
    """All fixed interview slots for a single working day."""
    slots: list[Slot] = []
    day_end = datetime.combine(day.date(), WORKING_HOURS_END)
    cursor = datetime.combine(day.date(), WORKING_HOURS_START)
    while cursor + timedelta(minutes=INTERVIEW_DURATION_MINUTES) <= day_end:
        slots.append(Slot(cursor, cursor + timedelta(minutes=INTERVIEW_DURATION_MINUTES)))
        cursor += timedelta(minutes=SLOT_STEP_MINUTES)
    return slots


def find_next_available_slot(
    session: Session,
    job_requisition_id: int,
    earliest: Optional[datetime] = None,
) -> Slot:
    """
    Find the next working-day, working-hours slot that isn't already booked
    for this job (across all candidates being interviewed for that role).

    Raises RuntimeError if nothing is free within BUSINESS_DAYS_LOOKAHEAD.
    """
    now = earliest or datetime.utcnow()

    # Load already-booked interview slots for this job so we don't double-book.
    booked_slot_ids = set(
        session.exec(
            select(Interview.slot_id).where(Interview.status != "Cancelled")
        ).all()
    )
    booked_ranges: list[tuple[datetime, datetime]] = []
    if booked_slot_ids:
        existing_slots = session.exec(
            select(InterviewSlot).where(InterviewSlot.id.in_(booked_slot_ids))
        ).all()
        booked_ranges = [(s.start_time, s.end_time) for s in existing_slots]

    day = now
    for _ in range(BUSINESS_DAYS_LOOKAHEAD):
        if day.weekday() in WORKING_DAYS:
            for slot in _candidate_slots_for_day(day):
                if slot.start <= now:
                    continue
                overlaps = any(
                    slot.start < b_end and b_start < slot.end
                    for b_start, b_end in booked_ranges
                )
                if not overlaps:
                    return slot
        day = day + timedelta(days=1)

    raise RuntimeError("No available interview slot found in the next two working weeks.")


def book_slot(session: Session, job_requisition_id: int, slot: Slot) -> InterviewSlot:
    """Persist the chosen slot as booked for this job."""
    db_slot = InterviewSlot(
        job_requisition_id=job_requisition_id,
        start_time=slot.start,
        end_time=slot.end,
        status="Booked",
    )
    session.add(db_slot)
    session.commit()
    session.refresh(db_slot)
    return db_slot
