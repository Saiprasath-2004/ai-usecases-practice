from datetime import datetime

from ats_agent.services.scheduling.intent import SchedulingIntent
from ats_agent.services.scheduling.selector import select_interview_slot


def test_scheduling_intent_structure():
    intent = SchedulingIntent(
        preferred_weekdays=[1],  # Tuesday
        preferred_time_start="12:00",
        preferred_time_end="17:00",
        duration_minutes=60,
        flexibility="flexible",
    )

    assert intent.preferred_weekdays == [1]
    assert intent.duration_minutes == 60
    assert intent.flexibility == "flexible"


def test_exact_scheduling_intent():
    intent = SchedulingIntent(
        preferred_date="2026-09-29",
        preferred_time_start="13:00",
        preferred_time_end="13:00",
        duration_minutes=60,
        flexibility="exact",
    )

    assert str(intent.preferred_date) == "2026-09-29"
    assert intent.duration_minutes == 60
    assert intent.flexibility == "exact"