"""External recruiter actions with an idempotent SQLite outbox.

The email provider is intentionally mocked for now.
The rest of the application should interact only with these
action functions so a real provider can be plugged in later.
"""

import datetime
import json
import sqlite3
import uuid
from typing import Any

from ats_agent.config import ACTIONS_DB_PATH, EMAIL_PROVIDER
from ats_agent.agent_layer.candidate_communication import (
    generate_followup_email,
)

# ============================================================
# Constants
# ============================================================

INTERVIEW_INVITE = "INTERVIEW_INVITE"
REJECTION_NOTICE = "REJECTION_NOTICE"
FOLLOWUP_REQUEST = "FOLLOWUP_REQUEST"

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


def _get_action_status(
    action_id: str,
) -> str | None:
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
    """Validate minimum candidate information required for email."""

    if not isinstance(candidate_data, dict):
        raise TypeError(
            "candidate_data must be a dictionary."
        )

    email = candidate_data.get("email")

    if not email or not str(email).strip():
        raise ValueError(
            "Candidate email is required."
        )


# ============================================================
# Mock email provider
# ============================================================


def _mock_send_email(
    *,
    recipient: str,
    subject: str,
    body: str,
) -> None:
    """
    Mock email provider.

    This simulates successful email delivery.
    Replace this function with a real provider later.
    """

    print()
    print("=" * 60)
    print(f"[MOCK EMAIL PROVIDER: {EMAIL_PROVIDER}]")
    print(f"TO: {recipient}")
    print(f"SUBJECT: {subject}")
    print("-" * 60)
    print(body)
    print("=" * 60)
    print()


# ============================================================
# Generic email action
# ============================================================


def _send_email_action(
    *,
    thread_id: str,
    action_type: str,
    candidate_data: dict[str, Any],
    subject: str,
    body: str,
) -> tuple[str, str]:
    """
    Persist and execute an email action.

    Flow:

        create outbox action
            ↓
        PENDING
            ↓
        mock provider
            ↓
        SENT / FAILED
    """

    init_outbox()

    _validate_candidate_data(candidate_data)

    payload = {
        **candidate_data,
        "subject": subject,
        "body": body,
    }

    action_id = _record_action(
        thread_id=thread_id,
        action_type=action_type,
        payload=payload,
    )

    status = _get_action_status(action_id)

    if status == SENT:
        return action_id, SENT

    try:
        _mock_send_email(
            recipient=str(candidate_data["email"]),
            subject=subject,
            body=body,
        )

        _mark_sent(action_id)

        return action_id, SENT

    except Exception as exc:
        _mark_failed(
            action_id,
            str(exc),
        )
        raise


# ============================================================
# Interview invitation
# ============================================================


def send_interview_invite(
    thread_id: str,
    candidate_data: dict[str, Any],
) -> tuple[str, str]:
    """
    Send an interview invitation.

    The recruiter/API layer must already have decided that
    an interview should be scheduled.
    """

    candidate_name = (
        candidate_data.get("candidate_name")
        or "Candidate"
    )

    scheduled_at = (
        candidate_data.get("scheduled_at")
        or "To be confirmed"
    )

    duration = (
        candidate_data.get("duration_minutes")
        or 60
    )

    meeting_url = (
        candidate_data.get("meeting_url")
        or "Meeting link will be provided separately."
    )

    subject = "Interview Invitation"

    body = f"""Hello {candidate_name},

We are pleased to invite you for an interview.

Interview details:
Date and time: {scheduled_at}
Duration: {duration} minutes
Meeting link: {meeting_url}

Please let us know if you have any questions.

Best regards,
Recruitment Team
"""

    return _send_email_action(
        thread_id=thread_id,
        action_type=INTERVIEW_INVITE,
        candidate_data=candidate_data,
        subject=subject,
        body=body,
    )


# ============================================================
# Rejection notice
# ============================================================


def send_rejection_notice(
    thread_id: str,
    candidate_data: dict[str, Any],
) -> tuple[str, str]:
    """
    Send a candidate rejection notice.

    The recruiter/API layer must already have made the
    rejection decision.
    """

    candidate_name = (
        candidate_data.get("candidate_name")
        or "Candidate"
    )

    subject = "Application Update"

    body = f"""Hello {candidate_name},

Thank you for taking the time to apply for this position.

After reviewing your application, we have decided not to
move forward with your application at this time.

We appreciate your interest in our organization and wish
you the best in your future opportunities.

Best regards,
Recruitment Team
"""

    return _send_email_action(
        thread_id=thread_id,
        action_type=REJECTION_NOTICE,
        candidate_data=candidate_data,
        subject=subject,
        body=body,
    )


# ============================================================
# Follow-up request
# ============================================================
def send_followup_request(
    thread_id: str,
    candidate_data: dict[str, Any],
    questions: list[str],
) -> tuple[str, str]:
    """
    Send candidate follow-up questions.

    The candidate-facing email content is generated separately.
    This function handles the external communication and outbox.
    """

    if not questions:
        raise ValueError(
            "At least one follow-up question is required."
        )

    _validate_candidate_data(candidate_data)

    candidate_name = (
        candidate_data.get("candidate_name")
        or "Candidate"
    )

    # --------------------------------------------------------
    # Generate natural candidate-facing content
    # --------------------------------------------------------

    email_content = generate_followup_email(
        candidate_name=str(candidate_name),
        questions=questions,
    )

    # --------------------------------------------------------
    # Send through the existing outbox/provider layer
    # --------------------------------------------------------

    return _send_email_action(
        thread_id=thread_id,
        action_type=FOLLOWUP_REQUEST,
        candidate_data=candidate_data,
        subject=email_content["subject"],
        body=email_content["body"],
    )