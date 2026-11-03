from datetime import date

from sqlmodel import Session, select

from ats_agent.domain.models import PublicHoliday


def is_public_holiday(
    session: Session,
    target_date: date,
) -> bool:
    holiday = session.exec(
        select(PublicHoliday).where(
            PublicHoliday.holiday_date == target_date,
            PublicHoliday.active.is_(True),
        )
    ).first()

    return holiday is not None