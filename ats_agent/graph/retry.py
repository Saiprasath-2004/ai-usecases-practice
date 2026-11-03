"""Retry utility for LLM-based extraction nodes."""

import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

def with_retries(
    fn: Callable[[], T],
    max_attempts: int,
    node_name: str
) -> T:
    """
    Calls fn() and retries on any exception up to max_attempts times.
    Logs each failed attempt and re-raises the last exception if all fail.
    """
    last_exception = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_exception = e
            logger.warning(
                f"Node '{node_name}' attempt {attempt}/{max_attempts} failed: {str(e)}"
            )

    if last_exception:
        raise last_exception

    raise RuntimeError(f"Node '{node_name}' failed after {max_attempts} attempts.")
