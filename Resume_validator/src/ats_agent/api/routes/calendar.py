"""Recruiter calendar management API."""

from datetime import date, datetime, time, timedelta
from fastapi import HTTPException

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ats_agent.api.deps import get_session
from ats_agent.api.schemas.calendar import (
    AvailabilityCreate,
    AvailabilityUpdate,
    CalendarBlockCreate,
    FullDayBlockCreate,
    AvailabilityRead,
    CalendarBlockRead,
    AvailableSlotsResponse,
    InterviewCreate,
    InterviewRead,
)
from ats_agent.domain.models import (
    RecruiterAvailability,
    CalendarBlock,
    Interview,
)
from ats_agent.services.scheduling.slot_generator import (
    generate_available_slots,
)
from ats_agent.services.scheduling.booking import book_interview
from ats_agent.agent_layer.actions import send_interview_invite

router = APIRouter(
    prefix="/calendar",
    tags=["Calendar"],
)


# ============================================================
# Get weekly availability
# ============================================================

@router.get(
    "/availability",
    response_model=list[AvailabilityRead],
)
def get_availability(
    recruiter_id: str,
    session: Session = Depends(get_session),
):
    return session.exec(
        select(RecruiterAvailability)
        .where(
            RecruiterAvailability.recruiter_id == recruiter_id
        )
        .order_by(
            RecruiterAvailability.day_of_week,
            RecruiterAvailability.start_time,
        )
    ).all()


# ============================================================
# Create weekly availability
# ============================================================

@router.post(
    "/availability",
    response_model=AvailabilityRead,
    status_code=201,
)
def create_availability(
    request: AvailabilityCreate,
    session: Session = Depends(get_session),
):
    existing = session.exec(
        select(RecruiterAvailability).where(
            RecruiterAvailability.recruiter_id
            == request.recruiter_id,
            RecruiterAvailability.day_of_week
            == request.day_of_week,
        )
    ).all()

    for window in existing:
        if (
            request.start_time < window.end_time
            and request.end_time > window.start_time
        ):
            raise HTTPException(
                status_code=409,
                detail="Availability overlaps an existing window.",
            )

    availability = RecruiterAvailability(
        **request.model_dump()
    )

    session.add(availability)
    session.commit()
    session.refresh(availability)

    return availability


# ============================================================
# Update weekly availability
# ============================================================

@router.put(
    "/availability/{availability_id}",
    response_model=AvailabilityRead,
)
def update_availability(
    availability_id: int,
    request: AvailabilityUpdate,
    session: Session = Depends(get_session),
):
    availability = session.get(
        RecruiterAvailability,
        availability_id,
    )

    if availability is None:
        raise HTTPException(
            status_code=404,
            detail="Availability record not found.",
        )

    updates = request.model_dump(exclude_unset=True)

    start = updates.get(
        "start_time",
        availability.start_time,
    )
    end = updates.get(
        "end_time",
        availability.end_time,
    )

    if start >= end:
        raise HTTPException(
            status_code=422,
            detail="Start time must be before end time.",
        )

    if updates.get("active", availability.active):
        others = session.exec(
            select(RecruiterAvailability).where(
                RecruiterAvailability.recruiter_id
                == availability.recruiter_id,
                RecruiterAvailability.day_of_week
                == availability.day_of_week,
                RecruiterAvailability.id != availability_id,
                RecruiterAvailability.active == True,
            )
        ).all()

        for other in others:
            if start < other.end_time and end > other.start_time:
                raise HTTPException(
                    status_code=409,
                    detail="Updated availability overlaps another window.",
                )

    for key, value in updates.items():
        setattr(availability, key, value)

    session.add(availability)
    session.commit()
    session.refresh(availability)

    return availability


# ============================================================
# Delete weekly availability
# ============================================================

@router.delete("/availability/{availability_id}")
def delete_availability(
    availability_id: int,
    session: Session = Depends(get_session),
):
    availability = session.get(
        RecruiterAvailability,
        availability_id,
    )

    if availability is None:
        raise HTTPException(
            status_code=404,
            detail="Availability record not found.",
        )

    session.delete(availability)
    session.commit()

    return {"status": "deleted"}


# ============================================================
# Get calendar blocks
# ============================================================

@router.get(
    "/blocks",
    response_model=list[CalendarBlockRead],
)
def get_blocks(
    recruiter_id: str,
    session: Session = Depends(get_session),
):
    return session.exec(
        select(CalendarBlock)
        .where(CalendarBlock.recruiter_id == recruiter_id)
        .order_by(CalendarBlock.start_at)
    ).all()


# ============================================================
# Create partial-day block
# ============================================================

@router.post(
    "/blocks",
    response_model=CalendarBlockRead,
    status_code=201,
)
def create_block(
    request: CalendarBlockCreate,
    session: Session = Depends(get_session),
):
    if request.start_at.tzinfo or request.end_at.tzinfo:
        raise HTTPException(
            status_code=422,
            detail="Use local datetimes without UTC offsets for now.",
        )

    block = CalendarBlock(**request.model_dump())

    session.add(block)
    session.commit()
    session.refresh(block)

    return block


# ============================================================
# Create full-day block
# ============================================================

@router.post(
    "/blocks/full-day",
    response_model=CalendarBlockRead,
    status_code=201,
)
def create_full_day_block(
    request: FullDayBlockCreate,
    session: Session = Depends(get_session),
):
    block = CalendarBlock(
        recruiter_id=request.recruiter_id,
        start_at=datetime.combine(
            request.target_date,
            time.min,
        ),
        end_at=datetime.combine(
            request.target_date + timedelta(days=1),
            time.min,
        ),
        all_day=True,
        reason=request.reason,
    )

    session.add(block)
    session.commit()
    session.refresh(block)

    return block


# ============================================================
# Delete calendar block
# ============================================================

@router.delete("/blocks/{block_id}")
def delete_block(
    block_id: int,
    session: Session = Depends(get_session),
):
    block = session.get(CalendarBlock, block_id)

    if block is None:
        raise HTTPException(
            status_code=404,
            detail="Calendar block not found.",
        )

    session.delete(block)
    session.commit()

    return {"status": "deleted"}


# ============================================================
# Get available interview slots
# ============================================================

@router.get(
    "/slots",
    response_model=AvailableSlotsResponse,
)
def get_available_slots(
    recruiter_id: str,
    target_date: date,
    duration_minutes: int = Query(
        default=60,
        ge=15,
        le=240,
    ),
    session: Session = Depends(get_session),
):
    slots = generate_available_slots(
        session=session,
        recruiter_id=recruiter_id,
        target_date=target_date,
        duration_minutes=duration_minutes,
    )

    return {
        "recruiter_id": recruiter_id,
        "target_date": target_date,
        "duration_minutes": duration_minutes,
        "slots": slots,
    }

@router.get("/interviews", response_model=list[InterviewRead])
def get_interviews(
    recruiter_id: str,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    session: Session = Depends(get_session),
):
    statement = select(Interview).where(
        Interview.recruiter_id == recruiter_id
    )

    if start_at is not None:
        statement = statement.where(
            Interview.scheduled_at >= start_at
        )

    if end_at is not None:
        statement = statement.where(
            Interview.scheduled_at < end_at
        )

    statement = statement.order_by(Interview.scheduled_at)

    return session.exec(statement).all()

# Create interview booking
@router.post(
    "/interviews",
    response_model=InterviewRead,
    status_code=201,
)
def create_interview(
    request: InterviewCreate,
    session: Session = Depends(get_session),
):
    try:
        interview = book_interview(
            session=session,
            application_id=request.application_id,
            recruiter_id=request.recruiter_id,
            scheduled_at=request.scheduled_at,
            candidate_email=request.candidate_email,
            duration_minutes=request.duration_minutes,
            provider=request.provider,
            meeting_url=request.meeting_url,
            notes=request.notes,
        )

        action_id, action_status = send_interview_invite(
            thread_id=request.application_id,
            candidate_data={
                "email": interview.candidate_email,
                "scheduled_at": interview.scheduled_at.isoformat(),
                "duration_minutes": interview.duration_minutes,
                "meeting_url": interview.meeting_url,
                "provider": interview.provider,
                "notes": interview.notes,
            },
        )

        return interview

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc