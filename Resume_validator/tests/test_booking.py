from datetime import datetime

from ats_agent.persistence.database import Database
from ats_agent.services.scheduling.booking import book_interview


db = Database()

with db.get_session() as session:

    print("--- INTERVIEW BOOKING TEST ---")

    scheduled_at = datetime(2026, 9, 29, 10, 0)

    interview = book_interview(
        session=session,
        application_id="test-application-001",
        recruiter_id="recruiter_1",
        scheduled_at=scheduled_at,
        candidate_email="candidate@example.com",
        duration_minutes=60,
        provider="Mock Meet",
        meeting_url="https://example.com/meeting/test-001",
        notes="Initial technical interview.",
    )

    print("✅ Interview booked")
    print("ID:", interview.id)
    print("Application:", interview.application_id)
    print("Recruiter:", interview.recruiter_id)
    print("Scheduled:", interview.scheduled_at)
    print("Duration:", interview.duration_minutes)
    print("Candidate:", interview.candidate_email)
    print("Status:", interview.status)

    print("\n--- DOUBLE BOOKING TEST ---")

    try:
        book_interview(
            session=session,
            application_id="test-application-002",
            recruiter_id="recruiter_1",
            scheduled_at=datetime(2026, 9, 29, 10, 30),
            candidate_email="candidate2@example.com",
            duration_minutes=60,
        )

        print("❌ Double booking was incorrectly allowed.")

    except ValueError as exc:
        print("✅ Double booking prevented:", exc)