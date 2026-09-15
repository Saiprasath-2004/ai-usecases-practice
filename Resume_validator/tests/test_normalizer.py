"""Unit tests for skill-name canonicalization."""

import pytest

from ats_agent.scoring.normalizer import normalize_skill


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("React.js", "react"),
        ("ReactJS", "react"),
        ("GitHub", "git"),
        ("CI/CD", "cicd"),
        ("PowerBI", "power bi"),
    ],
)
def test_normalize_skill_aliases(value: str, expected: str) -> None:
    """Aliases should resolve to one canonical comparison value."""
    assert normalize_skill(value) == expected
