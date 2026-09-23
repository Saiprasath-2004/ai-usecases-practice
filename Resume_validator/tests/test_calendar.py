from datetime import datetime

from ats_agent.persistence.database import Database
from ats_agent.services.scheduling.validator import validate_requested_slot


db = Database()

with db.get_session() as session:

    tests = [
        ("10:00", True),
        ("11:00", True),
        ("12:00", False),
        ("13:00", False),
        ("14:00", True),
        ("16:00", True),
        ("11:30", False),
    ]

    for start_time, expected in tests:

        start_at = datetime.fromisoformat(
            f"2026-09-24T{start_time}:00"
        )

        result, message = validate_requested_slot(
            session=session,
            recruiter_id="recruiter_1",
            start_at=start_at,
            duration_minutes=60,
        )

        print(
            f"{start_time} -> "
            f"result={result}, "
            f"expected={expected}, "
            f"message={message}"
        )