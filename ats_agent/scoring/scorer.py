"""Calculate deterministic ATS scores from matching results."""

SKILL_WEIGHT = 60
EXPERIENCE_WEIGHT = 25
KEYWORD_WEIGHT = 5
RESPONSIBILITY_WEIGHT = 10

TOTAL_SCORE = (
    SKILL_WEIGHT
    + EXPERIENCE_WEIGHT
    + KEYWORD_WEIGHT
    + RESPONSIBILITY_WEIGHT
)


def _percentage_score(
    matched_count: int,
    required_count: int,
    maximum_score: int,
) -> int:
    """
    Convert a match count into a deterministic weighted score.

    A category with no requirements contributes zero points.
    """

    if required_count <= 0:
        return 0

    matched_count = max(
        0,
        min(matched_count, required_count),
    )

    return round(
        (matched_count / required_count) * maximum_score
    )


def calculate_experience_score(
    required_min: float | None,
    required_max: float | None,
    candidate_years: float | None,
) -> int:
    """
    Score candidate experience on a 20-point scale.

    Rules:
    - Unknown candidate experience -> 0.
    - No JD experience requirement -> full score.
    - Below minimum by 2+ years -> 0.
    - Below minimum by less than 2 years -> partial score.
    - Meeting minimum -> full score.
    - Exceeding maximum -> full score.
    """

    if candidate_years is None:
        return 0

    if required_min is None and required_max is None:
        return EXPERIENCE_WEIGHT

    if required_min is not None:
        if candidate_years < required_min:
            gap = required_min - candidate_years

            if gap >= 2:
                return 0

            return round(
                EXPERIENCE_WEIGHT * 0.60
            )

    return EXPERIENCE_WEIGHT


def _evidence_score(
    evidence: str,
) -> float:
    """
    Convert responsibility evidence into a scoring factor.

    Unknown or absent evidence receives zero.
    It does not create a negative score.
    """

    evidence_scores = {
        "strong": 1.00,
        "moderate": 0.75,
        "weak": 0.40,
        "none": 0.00,
        "neutral": 0.00,
    }

    return evidence_scores.get(
        evidence,
        0.00,
    )


def _responsibility_score_factor(
    responsibility_type: str,
) -> float:
    """
    Return the relative importance of a responsibility type.

    Core responsibilities carry full importance.
    Supporting responsibilities carry reduced importance.
    Generic responsibilities are excluded.
    """

    type_weights = {
        "core": 1.00,
        "supporting": 0.50,
        "generic": 0.00,
    }

    return type_weights.get(
        responsibility_type,
        0.00,
    )


def calculate_responsibility_score(
    responsibility_matches: list[dict],
) -> int:
    """
    Calculate responsibility score using graded evidence.

    Generic responsibilities are excluded.

    Missing or unmentioned responsibilities do not subtract
    points; they simply contribute zero positive evidence.
    """

    weighted_possible_score = 0.0
    weighted_earned_score = 0.0

    for responsibility in responsibility_matches:
        responsibility_type = str(
            responsibility.get(
                "type",
                "core",
            )
        ).casefold().strip()

        if responsibility_type == "generic":
            continue

        type_weight = _responsibility_score_factor(
            responsibility_type
        )

        if type_weight <= 0:
            continue

        weighted_possible_score += type_weight

        evidence = str(
            responsibility.get(
                "evidence",
                "none",
            )
        ).casefold().strip()

        evidence_factor = _evidence_score(
            evidence
        )

        weighted_earned_score += (
            type_weight * evidence_factor
        )

    if weighted_possible_score <= 0:
        return 0

    return round(
        (
            weighted_earned_score
            / weighted_possible_score
        )
        * RESPONSIBILITY_WEIGHT
    )


def calculate_overall_score(
    skill_score: int,
    experience_score: int,
    keyword_score: int,
    responsibility_score: int,
) -> int:
    """Calculate the final ATS score from component scores."""

    total = (
        skill_score
        + experience_score
        + keyword_score
        + responsibility_score
    )

    return max(
        0,
        min(total, TOTAL_SCORE),
    )


def calculate_ats_score(
    jd_requirements: dict,
    resume_profile: dict,
    matches: dict,
) -> dict:
    """
    Calculate the complete ATS score deterministically.

    Matching is performed before this function.
    This function only converts matching evidence into scores.
    """

    total_required_skills = len(
        jd_requirements.get(
            "skills",
            [],
        )
    )

    matched_skills = len(
        matches.get(
            "matched_skills",
            [],
        )
    )

    skill_score = _percentage_score(
        matched_count=matched_skills,
        required_count=total_required_skills,
        maximum_score=SKILL_WEIGHT,
    )

    total_required_keywords = len(
        jd_requirements.get(
            "keywords",
            [],
        )
    )

    matched_keywords = len(
        matches.get(
            "matched_keywords",
            [],
        )
    )

    keyword_score = _percentage_score(
        matched_count=matched_keywords,
        required_count=total_required_keywords,
        maximum_score=KEYWORD_WEIGHT,
    )

    responsibility_score = calculate_responsibility_score(
        responsibility_matches=matches.get(
            "responsibility_matches",
            [],
        )
    )

    experience_score = calculate_experience_score(
        required_min=jd_requirements.get(
            "experience_min"
        ),
        required_max=jd_requirements.get(
            "experience_max"
        ),
        candidate_years=resume_profile.get(
            "experience_years"
        ),
    )

    overall_score = calculate_overall_score(
        skill_score=skill_score,
        experience_score=experience_score,
        keyword_score=keyword_score,
        responsibility_score=responsibility_score,
    )

    return {
        "overall_score": overall_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "keyword_score": keyword_score,
        "responsibility_score": responsibility_score,
    }