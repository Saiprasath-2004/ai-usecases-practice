"""Calculate weighted ATS scores from normalized candidate facts."""

from ats_agent.scoring.normalizer import normalize_skill


def calculate_skill_score(
    required_skills: list[str],
    candidate_skills: list[str],
) -> int:
    """Score required skills on a 40-point scale."""

    required = {normalize_skill(skill) for skill in required_skills}

    candidate = {normalize_skill(skill) for skill in candidate_skills}

    if not required:
        return 0

    matched = required.intersection(candidate)

    return round((len(matched) / len(required)) * 40)


def calculate_experience_score(
    required_min: int,
    required_max: int,
    candidate_years: float,
) -> int:
    """Score experience on a 25-point scale using the requested range."""
    if required_min <= candidate_years <= required_max:
        return 25

    if candidate_years < required_min:
        gap = required_min - candidate_years

        if gap >= 2:
            return 0
        return 15

    # Candidate exceeds the requested range.
    return 25


def calculate_keyword_score(
    required_keywords: list[str],
    candidate_keywords: list[str],
) -> int:
    """Score normalized keywords on a 15-point scale."""

    required = {k.lower().strip() for k in required_keywords}
    candidate = {k.lower().strip() for k in candidate_keywords}

    if not required:
        return 0

    matched = required.intersection(candidate)
    return round((len(matched) / len(required)) * 15)


def calculate_responsibility_score(
    required_responsibilities: list[str],
    matched_responsibilities: list[str],
) -> int:
    """Score matched responsibilities on a 20-point scale."""

    if not required_responsibilities:
        return 0

    return round((len(matched_responsibilities) / len(required_responsibilities)) * 20)


def calculate_overall_score(
    skill_score: int,
    experience_score: int,
    keyword_score: int,
    responsibility_score: int,
) -> int:
    """Sum the four weighted component scores into the final score."""

    return skill_score + experience_score + keyword_score + responsibility_score
