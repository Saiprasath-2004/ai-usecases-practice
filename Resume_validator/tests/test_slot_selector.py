from datetime import datetime, time

from sqlmodel import Session, SQLModel, create_engine

from ats_agent.domain.models import RecruiterAvailability
from ats_agent.services.scheduling.intent import SchedulingIntent
from ats_agent.services.scheduling.selector import select_interview_slot


def test_select_afternoon_slot():

    engine = create_engine("sqlite://")

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:

        session.add(
            RecruiterAvailability(
                recruiter_id="recruiter_1",
                day_of_week=1,  # Tuesday
                start_time=time(10, 0),
                end_time=time(17, 0),
                active=True,
            )
        )

        session.commit()

        intent = {
            "preferred_weekdays": [1],
            "preferred_time_start": "12:00",
            "preferred_time_end": "17:00",
            "duration_minutes": 60,
            "flexibility": "flexible",
        }

        scheduling_intent = SchedulingIntent(**intent)

        slot = select_interview_slot(
            session=session,
            recruiter_id="recruiter_1",
            intent=scheduling_intent,
            now=datetime(2026, 9, 24, 9, 0),
            max_days=14,
        )

        assert slot.weekday() == 1
        assert slot.hour >= 12