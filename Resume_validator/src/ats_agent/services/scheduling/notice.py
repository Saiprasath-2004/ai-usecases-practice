"""Minimum-notice rules for interview scheduling."""

from datetime import datetime, timedelta

from ats_agent.config import MINIMUM_NOTICE_HOURS


def get_minimum_allowed_start(
    now: datetime | None = None,
) -> datetime:
    """
    Return the earliest time an interview may start.

    By default, interviews must be scheduled at least
    MINIMUM_NOTICE_HOURS into the future.
    """

    if now is None:
        now = datetime.now()

    return now + timedelta(
        hours=MINIMUM_NOTICE_HOURS
    )


def satisfies_minimum_notice(
    start_at: datetime,
    now: datetime | None = None,
) -> bool:
    """
    Return True when the requested interview satisfies
    the minimum-notice requirement.
    """

    minimum_allowed_start = get_minimum_allowed_start(
        now=now
    )

    return start_at >= minimum_allowed_start