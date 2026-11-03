"""Utility for auditing transitions and events in the ATS workflow."""

import datetime
from typing import Any
from ats_agent.graph.state import ATSState

def log_event(state: ATSState, node_name: str, event_type: str, details: Any = None) -> dict:
    """
    Creates an audit event and appends it to the state's audit_trail.

    Args:
        state: Current graph state.
        node_name: Name of the node where the event occurred.
        event_type: Type of event (e.g., 'TRANSITION', 'DECISION', 'ACTION').
        details: Additional metadata about the event.

    Returns:
        A dictionary containing the updated audit trail for the state.
    """
    event = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "node": node_name,
        "event": event_type,
        "details": details
    }

    # Ensure audit_trail is initialized
    trail = state.get("audit_trail") or []
    trail.append(event)

    return {"audit_trail": trail}
