"""Unit tests for skill and keyword matching."""

from ats_agent.scoring.matcher import match_keywords, match_skills


def test_match_skills_supports_declared_variants() -> None:
    """A candidate alias should satisfy the corresponding requirement."""
    result = match_skills(
        [{"name": "React", "variants": ["React.js"]}],
        [{"name": "ReactJS", "variants": []}],
    )

    assert result == {"matched_skills": ["React"], "missing_skills": []}


def test_match_keywords_returns_sorted_missing_values() -> None:
    """Keyword matching should expose matched and missing requirements."""
    result = match_keywords(["React", "Jenkins"], ["React"])

    assert result == {
        "matched_keywords": ["react"],
        "missing_keywords": ["jenkins"],
    }
