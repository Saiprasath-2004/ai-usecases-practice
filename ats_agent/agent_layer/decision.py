"""Decision logic for ATS candidate evaluation."""

from enum import Enum
from typing import Any
from ats_agent.config import SELECT_CUTOFF, REJECT_FLOOR

class Verdict(Enum):
    """ATS Candidate Verdicts."""
    SELECT = "SELECT"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"


def decide(score_result: dict[str, Any], thresholds: dict[str, float] | None = None) -> Verdict:
    """
    Determine the verdict based on the overall_score.

    - overall_score >= SELECT_CUTOFF -> SELECT
    - overall_score <= REJECT_FLOOR -> REJECT
    - otherwise -> ESCALATE
    """
    select_cutoff = thresholds.get("select_cutoff", SELECT_CUTOFF) if thresholds else SELECT_CUTOFF
    reject_floor = thresholds.get("reject_floor", REJECT_FLOOR) if thresholds else REJECT_FLOOR

    score = score_result.get("overall_score", 0.0)

    if score >= select_cutoff:
        return Verdict.SELECT
    if score <= reject_floor:
        return Verdict.REJECT

    return Verdict.ESCALATE
