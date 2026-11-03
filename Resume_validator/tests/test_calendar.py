from datetime import date, datetime, timedelta

from sqlmodel import select

from ats_agent.domain.models import PublicHoliday
from ats_agent.persistence.database import Database
from ats_agent.services.scheduling.slot_generator import (
    find_next_available_slot,
)
from ats_agent.services.scheduling.validator import (
    validate_requested_slot,
)


db = Database()

with db.get_session() as session:

    # ============================================================
    # 1. Minimum Notice Tests
    # ============================================================

    print("--- MINIMUM NOTICE TESTS ---")

    now = datetime.now()

    tests = [
        (
            "Too soon - 1 hour from now",
            now + timedelta(hours=1),
            False,
        ),
        (
            "Too soon - 23 hours from now",
            now + timedelta(hours=23),
            False,
        ),
    ]

    for name, start_at, expected in tests:

        result, message = validate_requested_slot(
            session=session,
            recruiter_id="recruiter_1",
            start_at=start_at,
            duration_minutes=60,
        )

        print(
            f"{name} -> "
            f"start={start_at.isoformat()}, "
            f"result={result}, "
            f"expected={expected}, "
            f"message={message}"
        )

        assert result == expected


    # ============================================================
    # 2. Add Test Public Holiday
    # ============================================================

    holiday_date = date(2026, 9, 28)

    existing_holiday = session.exec(
        select(PublicHoliday).where(
            PublicHoliday.holiday_date == holiday_date
        )
    ).first()

    if not existing_holiday:

        session.add(
            PublicHoliday(
                holiday_date=holiday_date,
                name="Test Company Holiday",
                active=True,
            )
        )

        session.commit()

        print(
            f"\n✅ Added test holiday: "
            f"{holiday_date} - Test Company Holiday"
        )

    else:

        print(
            f"\nℹ️ Test holiday already exists: "
            f"{holiday_date}"
        )


    # ============================================================
    # 3. Public Holiday Test
    # ============================================================

    print("\n--- PUBLIC HOLIDAY TEST ---")

    holiday_slot = validate_requested_slot(
        session=session,
        recruiter_id="recruiter_1",
        start_at=datetime(2026, 9, 28, 10, 0),
        duration_minutes=60,
    )

    result, message = holiday_slot

    print(
        f"Holiday slot -> "
        f"result={result}, "
        f"expected=False, "
        f"message={message}"
    )

    assert result is False


    # ============================================================
    # 4. Next Available Slot
    # ============================================================

    print("\n--- NEXT AVAILABLE SLOT TEST ---")

    next_slot = find_next_available_slot(
        session=session,
        recruiter_id="recruiter_1",
        duration_minutes=60,
        slot_interval_minutes=30,
        max_days=14,
    )

    if next_slot is None:

        print("❌ No available slot found")

    else:

        print(
            "✅ Next available slot:",
            next_slot["start"],
            "->",
            next_slot["end"],
        )

        # Make sure the result is not the public holiday.
        assert next_slot["start"].date() != holiday_date

        print(
            f"✅ Correctly skipped public holiday: "
            f"{holiday_date}"
        )