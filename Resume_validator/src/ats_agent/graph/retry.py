"""Retry utilities for graph nodes that call external or LLM services."""

import logging
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retries(
    fn: Callable[[], T],
    max_attempts: int,
    node_name: str,
) -> T:
    """
    Execute a function with a limited number of retry attempts.

    The last exception is raised if all attempts fail.
    """

    if max_attempts <= 0:
        raise ValueError("max_attempts must be greater than zero.")

    last_exception: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()

        except Exception as exc:
            last_exception = exc

            logger.warning(
                "Node '%s' attempt %s/%s failed: %s",
                node_name,
                attempt,
                max_attempts,
                exc,
            )

    raise last_exception