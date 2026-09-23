"""Evidence assembly and recruiter-facing ATS report generation."""

from typing import Any


def build_evidence(
    matches: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    """
    Assemble the deterministic evidence produced by the ATS pipeline.

    This function does not call an LLM and does not make decisions.
    It only organizes matching and scoring information so that it can
    be presented to the recruiter during human review.
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
            "matched": matches.get(
                "matched_responsibilities",
                [],
            ),
            "missing": matches.get(
                "missing_responsibilities",
                [],
            ),
        },
        "experience": {
            "candidate_years": matches.get(
                "candidate_experience_years"
            ),
            "required_min_years": matches.get(
                "required_experience_min"
            ),
            "required_max_years": matches.get(
                "required_experience_max"
            ),
            "status": matches.get(
                "experience_match"
            ),
        },
        "score_breakdown": {
            "overall_score": result.get(
                "overall_score"
            ),
            "skill_score": result.get(
                "skill_score"
            ),
            "experience_score": result.get(
                "experience_score"
            ),
            "keyword_score": result.get(
                "keyword_score"
            ),
            "responsibility_score": result.get(
                "responsibility_score"
            ),
        },
    }


def render_narrative(
    evidence: dict[str, Any],
) -> str:
    """
    Create a deterministic recruiter-facing summary.

    The narrative only uses facts already present in the evidence.
    It does not generate new claims or make an independent decision.
    """

    skills = evidence.get("skills", {})
    keywords = evidence.get("keywords", {})
    responsibilities = evidence.get(
        "responsibilities",
        {},
    )
    experience = evidence.get(
        "experience",
        {},
    )
    scores = evidence.get(
        "score_breakdown",
        {},
    )

    overall_score = scores.get(
        "overall_score",
        0.0,
    )

    matched_skills = skills.get(
        "matched",
        [],
    )
    missing_skills = skills.get(
        "missing",
        [],
    )

    matched_keywords = keywords.get(
        "matched",
        [],
    )
    missing_keywords = keywords.get(
        "missing",
        [],
    )

    matched_responsibilities = responsibilities.get(
        "matched",
        [],
    )
    missing_responsibilities = responsibilities.get(
        "missing",
        [],
    )

    candidate_years = experience.get(
        "candidate_years"
    )
    required_min_years = experience.get(
        "required_min_years"
    )

    lines = [
        f"Overall ATS score: {overall_score:.1f}/100.",
        "",
        "Skills:",
        f"- Matched: {', '.join(matched_skills) or 'None'}",
        f"- Missing: {', '.join(missing_skills) or 'None'}",
        "",
        "Keywords:",
        f"- Matched: {', '.join(matched_keywords) or 'None'}",
        f"- Missing: {', '.join(missing_keywords) or 'None'}",
        "",
        "Responsibilities:",
        (
            "- Matched: "
            f"{', '.join(matched_responsibilities) or 'None'}"
        ),
        (
            "- Missing: "
            f"{', '.join(missing_responsibilities) or 'None'}"
        ),
    ]

    if candidate_years is not None:
        lines.extend(
            [
                "",
                "Experience:",
                f"- Candidate experience: {candidate_years} years",
            ]
        )

        if required_min_years is not None:
            lines.append(
                f"- Minimum required experience: "
                f"{required_min_years} years"
            )

    return "\n".join(lines)