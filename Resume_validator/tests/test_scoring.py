"""Unit tests for weighted ATS score calculations."""

from ats_agent.scoring.scorer import (
    calculate_experience_score,
    calculate_keyword_score,
    calculate_overall_score,
    calculate_responsibility_score,
    calculate_skill_score,
)


def test_calculate_component_scores() -> None:
    """Each scoring category should respect its configured maximum."""
    skill_score = calculate_skill_score(["React", "Jenkins"], ["React"])
    experience_score = calculate_experience_score(4, 6, 5)
    keyword_score = calculate_keyword_score(["React", "Jenkins"], ["React"])
    responsibility_score = calculate_responsibility_score(
        ["Build applications", "Review code"],
        ["Build applications"],
    )

    assert (skill_score, experience_score, keyword_score, responsibility_score) == (
        20,
        25,
        8,
        10,
    )
    assert (
        calculate_overall_score(
            skill_score,
            experience_score,
            keyword_score,
            responsibility_score,
        )
        == 63
    )
