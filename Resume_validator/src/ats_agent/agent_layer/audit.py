"""Utility for auditing transitions and events in the ATS workflow."""

import datetime
from typing import Any

from ats_agent.graph.state import ATSState


def log_event(
    state: ATSState,
    node_name: str,
    event_type: str,
    details: Any = None,
) -> dict:
    """
    Create a single audit event for the current graph step.

    The ATSState.audit_trail field uses operator.add as its
    reducer, so this function returns only the new event.
    LangGraph will append it to the existing audit trail.
    """

    event = {
        "timestamp": datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        "node": node_name,
        "event": event_type,
        "details": details,
    }

    return {
        "audit_trail": [event],
    }