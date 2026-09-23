"""External recruiter actions with an idempotent SQLite outbox."""

import datetime
import json
import sqlite3
import uuid
from typing import Any

from ats_agent.config import ACTIONS_DB_PATH, EMAIL_PROVIDER


# ============================================================
# Constants
# ============================================================


INTERVIEW_INVITE = "INTERVIEW_INVITE"
REJECTION_NOTICE = "REJECTION_NOTICE"

PENDING = "PENDING"
SENT = "SENT"
FAILED = "FAILED"


# ============================================================
# Database helpers
# ============================================================


def _utc_now() -> str:
    """Return the current UTC timestamp as an ISO string."""

    return datetime.datetime.now(
        datetime.timezone.utc
    ).isoformat()


def init_outbox() -> None:
    """Initialize the action outbox table."""

    with sqlite3.connect(ACTIONS_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS action_outbox (
                action_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sent_at TEXT,
                error TEXT
            )
            """
        )

        conn.commit()


# ============================================================
# Outbox operations
# ============================================================


def _record_action(
    thread_id: str,
    action_type: str,
    payload: dict[str, Any],
) -> str:
    """
    Create an idempotent outbox action.

    If the same action was already successfully sent for the
    same thread, return the existing action ID.
    """

    if not thread_id:
        raise ValueError("thread_id is required.")

    if not action_type:
        raise ValueError("action_type is required.")

    action_id = str(uuid.uuid4())
    now = _utc_now()

    with sqlite3.connect(ACTIONS_DB_PATH) as conn:

        existing = conn.execute(
            """
            SELECT action_id
            FROM action_outbox
            WHERE thread_id = ?
              AND action_type = ?
              AND status = ?
            LIMIT 1
            """,
            (
                thread_id,
                action_type,
                SENT,
            ),
        ).fetchone()

        if existing:
            return existing[0]

        conn.execute(
            """
            INSERT INTO action_outbox (
                action_id,
                thread_id,
                action_type,
                status,
                payload,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                thread_id,
                action_type,
                PENDING,
                json.dumps(payload),
                now,
            ),
        )

        conn.commit()

    return action_id


def _get_action_status(action_id: str) -> str | None:
    """Return the current status of an action."""

    with sqlite3.connect(ACTIONS_DB_PATH) as conn:
        result = conn.execute(
            """
            SELECT status
            FROM action_outbox
            WHERE action_id = ?
            """,
            (action_id,),
        ).fetchone()

    if not result:
        return None

    return result[0]


def _mark_sent(action_id: str) -> None:
    """Mark an action as successfully sent."""

    with sqlite3.connect(ACTIONS_DB_PATH) as conn:
        conn.execute(
            """
            UPDATE action_outbox
            SET status = ?,
                sent_at = ?,
                error = NULL
            WHERE action_id = ?
            """,
            (
                SENT,
                _utc_now(),
                action_id,
            ),
        )

        conn.commit()


def _mark_failed(
    action_id: str,
    error: str,
) -> None:
    """Mark an action as failed."""

    with sqlite3.connect(ACTIONS_DB_PATH) as conn:
        conn.execute(
            """
            UPDATE action_outbox
            SET status = ?,
                error = ?
            WHERE action_id = ?
            """,
            (
                FAILED,
                error,
                action_id,
            ),
        )

        conn.commit()


# ============================================================
# Payload validation
# ============================================================


def _validate_candidate_data(
    candidate_data: dict[str, Any],
) -> None:
    """Validate the minimum candidate information required for email."""

    if not isinstance(candidate_data, dict):
        raise TypeError(
            "candidate_data must be a dictionary."
        )

    email = candidate_data.get("email")

    if not email:
        raise ValueError(
            "Candidate email is required."
        )


# ============================================================
# Interview invitation
# ============================================================


def send_interview_invite(
    thread_id: str,
    candidate_data: dict[str, Any],
) -> tuple[str, str]:
    """
    Send an interview invitation through the configured provider.

    This function does not decide whether an interview should be
    scheduled. The recruiter/API layer must make that decision first.
    """

    init_outbox()

    _validate_candidate_data(candidate_data)

    action_id = _record_action(
        thread_id=thread_id,
        action_type=INTERVIEW_INVITE,
        payload=candidate_data,
    )

    status = _get_action_status(action_id)

    if status == SENT:
        return action_id, SENT

    try:
        print(
            f"[EMAIL PROVIDER {EMAIL_PROVIDER}] "
            f"Sending interview invite to "
            f"{candidate_data.get('email')}..."
        )

        # TODO:
        # Replace this mock provider call with the actual
        # email provider integration.

        _mark_sent(action_id)

        return action_id, SENT

    except Exception as exc:
        _mark_failed(
            action_id,
            str(exc),
        )

        raise


# ============================================================
# Rejection notice
# ============================================================


def send_rejection_notice(
    thread_id: str,
    candidate_data: dict[str, Any],
) -> tuple[str, str]:
    """
    Send a rejection notice through the configured provider.

    This function does not decide whether the candidate should
    be rejected. The recruiter/API layer must make that decision.
    """

    init_outbox()

    _validate_candidate_data(candidate_data)

    action_id = _record_action(
        thread_id=thread_id,
        action_type=REJECTION_NOTICE,
        payload=candidate_data,
    )

    status = _get_action_status(action_id)

    if status == SENT:
        return action_id, SENT

    try:
        print(
            f"[EMAIL PROVIDER {EMAIL_PROVIDER}] "
            f"Sending rejection notice to "
            f"{candidate_data.get('email')}..."
        )

        # TODO:
        # Replace this mock provider call with the actual
        # email provider integration.

        _mark_sent(action_id)

        return action_id, SENT

    except Exception as exc:
        _mark_failed(
            action_id,
            str(exc),
        )

        raise