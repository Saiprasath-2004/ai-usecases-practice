"""Decision logic for ATS candidate evaluation."""

from enum import Enum
from typing import Any

from ats_agent.config import REJECT_FLOOR, SELECT_CUTOFF


class Verdict(str, Enum):
    """ATS candidate verdicts."""

    SELECT = "SELECT"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"


def decide(
    score_result: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> Verdict:
    """
    Determine the ATS recommendation from the overall score.

    Rules:
        overall_score >= SELECT_CUTOFF -> SELECT
        overall_score <= REJECT_FLOOR -> REJECT
        otherwise -> ESCALATE

    This function only produces an ATS recommendation.
    It does not perform recruiter actions.
    """

    if not score_result:
        return Verdict.ESCALATE

    select_cutoff = (
        thresholds.get("select_cutoff", SELECT_CUTOFF)
        if thresholds
        else SELECT_CUTOFF
    )

    reject_floor = (
        thresholds.get("reject_floor", REJECT_FLOOR)
        if thresholds
        else REJECT_FLOOR
    )

    score = score_result.get("overall_score")

    if score is None:
        return Verdict.ESCALATE

    try:
        score = float(score)
    except (TypeError, ValueError):
        return Verdict.ESCALATE

    if score >= select_cutoff:
        return Verdict.SELECT

    if score <= reject_floor:
        return Verdict.REJECT

    return Verdict.ESCALATE