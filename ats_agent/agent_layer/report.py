"""Evidence assembly and narrative rendering for ATS evaluations."""

from typing import Any, Optional
from ats_agent.llm.client import get_chat_model

def build_evidence(matches: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """
    Purely assembles evidence from the matching and scoring results.
    No LLM calls here.
    """
    return {
        "skills": {
            "matched": matches.get("matched_skills", []),
            "missing": matches.get("missing_skills", []),
            "coverage": matches.get("skill_coverage", 0.0),
        },
        "keywords": {
            "matched": matches.get("matched_keywords", []),
            "missing": matches.get("missing_keywords", []),
        },
        "responsibilities": {
            "matched": matches.get("matched_responsibilities", []),
            "missing": matches.get("missing_responsibilities", []),
        },
        "score_breakdown": result,
    }

def render_narrative(evidence: dict[str, Any], llm_call: Optional[Any] = None) -> str:
    """
    Renders a textual narrative of the evidence.

    If llm_call is provided, it may rephrase the facts, but must not add new ones.
    By default, uses a deterministic template.
    """
    skills_matched = ", ".join(evidence["skills"]["matched"]) or "None"
    skills_missing = ", ".join(evidence["skills"]["missing"]) or "None"
    score = evidence["score_breakdown"].get("overall_score", 0.0)

    narrative = (
        f"The candidate achieved an overall score of {score}. "
        f"Matched skills: {skills_matched}. "
        f"Missing skills: {skills_missing}."
    )

    if llm_call:
        # Use the provided LLM call to rephrase the narrative
        # The llm_call should be a pre-configured model.invoke or similar
        prompt = f"Rephrase the following ATS evaluation narrative for a recruiter, preserving all facts exactly: {narrative}"
        try:
            response = llm_call(prompt)
            # Handle both string and BaseMessage responses
            return response.content if hasattr(response, "content") else str(response)
        except Exception:
            return narrative

    return narrative
