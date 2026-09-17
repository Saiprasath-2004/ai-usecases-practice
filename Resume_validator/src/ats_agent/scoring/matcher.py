"""Deterministic and semantic matching of resume facts against JD requirements."""

from typing import Any

import numpy as np
from langchain_core.embeddings import Embeddings


RESPONSIBILITY_SIMILARITY_THRESHOLD = 0.45


def _cosine_similarity(
    vector_a: list[float],
    vector_b: list[float],
) -> float:
    """Calculate cosine similarity between two embedding vectors."""

    if len(vector_a) != len(vector_b):
        raise ValueError(
            "Embedding vectors must have the same dimensions."
        )

    a = np.array(vector_a, dtype=float)
    b = np.array(vector_b, dtype=float)

    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(
        np.dot(a, b) / (norm_a * norm_b)
    )


def _normalize_text(value: Any) -> str:
    """Normalize text for deterministic comparison."""

    if not isinstance(value, str):
        value = str(value) if value is not None else ""

    return " ".join(
        value.casefold().strip().split()
    )


def _tokenize(value: str) -> set[str]:
    """Convert text into normalized word tokens."""

    normalized = _normalize_text(value)

    cleaned = (
        normalized
        .replace("/", " ")
        .replace("-", " ")
        .replace(",", " ")
        .replace(".", " ")
        .replace("(", " ")
        .replace(")", " ")
        .replace(":", " ")
        .replace(";", " ")
    )

    return {
        token
        for token in cleaned.split()
        if len(token) > 2
    }


def _lexical_overlap(
    text_a: str,
    text_b: str,
) -> float:
    """Calculate token overlap between two pieces of text."""

    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    overlap = tokens_a.intersection(tokens_b)

    return len(overlap) / min(
        len(tokens_a),
        len(tokens_b),
    )


def _responsibility_similarity(
    semantic_similarity: float,
    lexical_similarity: float,
) -> float:
    """
    Combine semantic and lexical evidence.

    Semantic similarity is the primary signal because two responsibilities
    can describe the same work using different wording.

    Lexical overlap is supporting evidence only.
    """

    return (
        semantic_similarity * 0.75
        + lexical_similarity * 0.25
    )


def _extract_string_name(item: Any) -> str:
    """Safely extract a plain string from a skill or responsibility."""

    if isinstance(item, dict):
        if "description" in item:
            return str(
                item.get("description", "") or ""
            ).strip()

        return str(
            item.get("name", "") or ""
        ).strip()

    if isinstance(item, str):
        return item.strip()

    return ""


def _extract_responsibility_type(
    item: Any,
) -> str:
    """Extract the responsibility classification from a JD item."""

    if not isinstance(item, dict):
        return "core"

    responsibility_type = str(
        item.get("type", "core") or "core"
    ).casefold().strip()

    if responsibility_type not in {
        "core",
        "supporting",
        "generic",
    }:
        return "core"

    return responsibility_type


def _responsibility_weight(
    responsibility_type: str,
) -> float:
    """Return the relative importance of a responsibility type."""

    weights = {
        "core": 1.0,
        "supporting": 0.5,
        "generic": 0.0,
    }

    return weights.get(
        responsibility_type,
        1.0,
    )


def _evidence_level(
    confidence: float,
    matched: bool,
    responsibility_type: str,
) -> str:
    """Convert matching confidence into an evidence label."""

    if responsibility_type == "generic":
        return "neutral"

    if matched and confidence >= 0.70:
        return "strong"

    if matched and confidence >= 0.55:
        return "moderate"

    if confidence >= 0.40:
        return "weak"

    return "none"


def _skill_forms(
    skill: dict[str, Any] | str,
) -> set[str]:
    """Return normalized canonical name and explicit variants."""

    if isinstance(skill, str):
        normalized = _normalize_text(skill)

        return {
            normalized
        } if normalized else set()

    forms = {
        skill.get("name", ""),
        *skill.get("variants", []),
    }

    return {
        _normalize_text(form)
        for form in forms
        if isinstance(form, (str, int, float))
        and str(form).strip()
    }


def match_skills(
    required_skills: list[dict[str, Any] | str],
    candidate_skills: list[dict[str, Any] | str],
) -> dict[str, Any]:
    """
    Match JD skills against resume skills deterministically.

    Skills are treated as the primary ATS matching signal.
    Only canonical names and explicitly supported variants
    are considered equivalent.
    """

    valid_required_skills = [
        skill
        for skill in required_skills
        if _extract_string_name(skill)
    ]

    valid_candidate_skills = [
        skill
        for skill in candidate_skills
        if _extract_string_name(skill)
    ]

    required_names = [
        _extract_string_name(skill)
        for skill in valid_required_skills
    ]

    candidate_names = [
        _extract_string_name(skill)
        for skill in valid_candidate_skills
    ]

    if not required_names:
        return {
            "matched_skills": [],
            "missing_skills": [],
            "skill_matches": [],
            "skill_coverage": 1.0,
            "matched_skill_count": 0,
            "required_skill_count": 0,
        }

    if not candidate_names:
        return {
            "matched_skills": [],
            "missing_skills": required_names,
            "skill_matches": [
                {
                    "required_skill": name,
                    "matched_candidate_skill": None,
                    "similarity": 0.0,
                    "matched": False,
                    "match_method": None,
                }
                for name in required_names
            ],
            "skill_coverage": 0.0,
            "matched_skill_count": 0,
            "required_skill_count": len(required_names),
        }

    candidate_forms = [
        _skill_forms(skill)
        for skill in valid_candidate_skills
    ]

    matched: list[str] = []
    missing: list[str] = []
    skill_matches: list[dict[str, Any]] = []

    used_candidate_indexes: set[int] = set()

    for required_index, required_skill in enumerate(
        valid_required_skills
    ):
        required_name = required_names[required_index]

        required_forms = _skill_forms(required_skill)

        exact_match_index = next(
            (
                index
                for index, candidate_form in enumerate(
                    candidate_forms
                )
                if index not in used_candidate_indexes
                and required_forms.intersection(
                    candidate_form
                )
            ),
            None,
        )

        if exact_match_index is not None:
            candidate_name = candidate_names[
                exact_match_index
            ]

            matched.append(required_name)

            used_candidate_indexes.add(
                exact_match_index
            )

            skill_matches.append(
                {
                    "required_skill": required_name,
                    "matched_candidate_skill": candidate_name,
                    "similarity": 1.0,
                    "matched": True,
                    "match_method": "exact_variant",
                }
            )

        else:
            missing.append(required_name)

            skill_matches.append(
                {
                    "required_skill": required_name,
                    "matched_candidate_skill": None,
                    "similarity": 0.0,
                    "matched": False,
                    "match_method": None,
                }
            )

    required_skill_count = len(required_names)
    matched_skill_count = len(matched)

    skill_coverage = (
        matched_skill_count / required_skill_count
        if required_skill_count
        else 1.0
    )

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_matches": skill_matches,
        "skill_coverage": round(skill_coverage, 4),
        "matched_skill_count": matched_skill_count,
        "required_skill_count": required_skill_count,
    }


def match_keywords(
    required_keywords: list[str],
    candidate_keywords: list[str],
) -> dict[str, Any]:
    """Match keywords using normalized exact and phrase comparison."""

    candidate_normalized = {
        _normalize_text(keyword)
        for keyword in candidate_keywords
        if isinstance(keyword, (str, int, float))
        and str(keyword).strip()
    }

    candidate_tokens = [
        _tokenize(keyword)
        for keyword in candidate_normalized
    ]

    matched: list[str] = []
    missing: list[str] = []
    seen: set[str] = set()

    for keyword in required_keywords:
        normalized = _normalize_text(keyword)

        if not normalized or normalized in seen:
            continue

        seen.add(normalized)

        if normalized in candidate_normalized:
            matched.append(str(keyword))
            continue

        required_tokens = _tokenize(normalized)

        phrase_match = False

        if required_tokens:
            for candidate_token_set in candidate_tokens:
                if required_tokens.issubset(
                    candidate_token_set
                ):
                    phrase_match = True
                    break

        if phrase_match:
            matched.append(str(keyword))
        else:
            missing.append(str(keyword))

    required_keyword_count = (
        len(matched) + len(missing)
    )

    keyword_coverage = (
        len(matched) / required_keyword_count
        if required_keyword_count
        else 1.0
    )

    return {
        "matched_keywords": matched,
        "missing_keywords": missing,
        "keyword_coverage": round(
            keyword_coverage,
            4,
        ),
    }


def _semantic_evidence(
    required_text: str,
    candidate_texts: list[str],
    required_embedding: list[float],
    candidate_embeddings: list[list[float]],
) -> tuple[str | None, float, float, float]:
    """Find the strongest semantic and lexical candidate."""

    best_candidate: str | None = None
    best_semantic = 0.0
    best_lexical = 0.0
    best_confidence = 0.0

    for index, candidate in enumerate(candidate_texts):
        semantic_similarity = _cosine_similarity(
            required_embedding,
            candidate_embeddings[index],
        )

        lexical_similarity = _lexical_overlap(
            required_text,
            candidate,
        )

        confidence = _responsibility_similarity(
            semantic_similarity,
            lexical_similarity,
        )

        if (
            confidence > best_confidence
            or (
                confidence == best_confidence
                and semantic_similarity > best_semantic
            )
            or (
                confidence == best_confidence
                and semantic_similarity == best_semantic
                and lexical_similarity > best_lexical
            )
        ):
            best_candidate = candidate
            best_semantic = semantic_similarity
            best_lexical = lexical_similarity
            best_confidence = confidence

    return (
        best_candidate,
        best_semantic,
        best_lexical,
        best_confidence,
    )

def _matched_skill_evidence(
    candidate_skills: list[dict[str, Any] | str],
    skill_matches: dict[str, Any],
) -> list[str]:
    """
    Return candidate skills that were deterministically matched
    against the JD skill requirements.

    This function does not know anything about specific technologies.
    It simply uses the result produced by match_skills().
    """

    matched_required_skills = {
        _normalize_text(skill)
        for skill in skill_matches.get(
            "matched_skills",
            [],
        )
        if isinstance(skill, str) and skill.strip()
    }

    evidence: list[str] = []

    for skill in candidate_skills:
        skill_name = _extract_string_name(skill)

        if not skill_name:
            continue

        skill_forms = _skill_forms(skill)

        if any(
            form in matched_required_skills
            for form in skill_forms
        ):
            evidence.append(skill_name)

    return list(dict.fromkeys(evidence))

def _direct_keyword_evidence(
    responsibility: str,
    candidate_keywords: list[str],
) -> list[str]:
    """
    Find candidate keywords explicitly present in a JD responsibility.
    """

    normalized_responsibility = _normalize_text(
        responsibility
    )

    evidence: list[str] = []

    for keyword in candidate_keywords:
        normalized_keyword = _normalize_text(keyword)

        if (
            normalized_keyword
            and normalized_keyword
            in normalized_responsibility
        ):
            evidence.append(str(keyword))

    return evidence

def _combine_responsibility_evidence(
    base_confidence: float,
    skill_evidence: list[str],
    keyword_evidence: list[str],
) -> float:
    """
    Combine responsibility evidence.

    Semantic responsibility similarity remains the primary signal.

    Deterministically matched skills and explicit keyword evidence
    provide supporting evidence only.

    Supporting evidence cannot independently create a responsibility
    match when semantic similarity is weak.
    """

    confidence = base_confidence

    if skill_evidence:
        confidence += min(
            0.10,
            0.05 * len(skill_evidence),
        )

    if keyword_evidence:
        confidence += min(
            0.05,
            0.025 * len(keyword_evidence),
        )

    return min(confidence, 1.0)


def match_responsibilities(
    required_responsibilities: list[str | dict[str, Any]],
    candidate_responsibilities: list[str | dict[str, Any]],
    skill_matches: dict[str, Any],
    candidate_skills: list[dict[str, Any] | str],
    candidate_keywords: list[str],
    embedder: Embeddings,
    threshold: float = RESPONSIBILITY_SIMILARITY_THRESHOLD,
) -> dict[str, Any]:
    """
    Match JD responsibilities against multiple resume evidence sources.

    Primary evidence:
        Resume responsibilities.

    Supporting evidence:
        Resume skills.
        Resume keywords.

    Generic responsibilities remain neutral.
    """

    required_items: list[dict[str, Any]] = []

    for responsibility in required_responsibilities:
        description = _extract_string_name(
            responsibility
        )

        if not description:
            continue

        responsibility_type = _extract_responsibility_type(
            responsibility
        )

        required_items.append(
            {
                "description": description,
                "type": responsibility_type,
            }
        )

    clean_candidate_responsibilities = [
        _extract_string_name(responsibility)
        for responsibility in candidate_responsibilities
        if _extract_string_name(responsibility)
    ]

    if not required_items:
        return {
            "matched_responsibilities": [],
            "missing_responsibilities": [],
            "responsibility_matches": [],
        }

    if not clean_candidate_responsibilities:
        responsibility_matches = []
        missing_responsibilities = []

        for item in required_items:
            responsibility_type = item["type"]

            if responsibility_type == "generic":
                evidence = "neutral"
            else:
                evidence = "none"
                missing_responsibilities.append(
                    item["description"]
                )

            responsibility_matches.append(
                {
                    "responsibility": item["description"],
                    "type": responsibility_type,
                    "matched_candidate_responsibility": None,
                    "similarity": 0.0,
                    "lexical_overlap": 0.0,
                    "skill_evidence": [],
                    "keyword_evidence": [],
                    "confidence": 0.0,
                    "evidence": evidence,
                    "matched": False,
                }
            )

        return {
            "matched_responsibilities": [],
            "missing_responsibilities": missing_responsibilities,
            "responsibility_matches": responsibility_matches,
        }

    clean_required = [
        item["description"]
        for item in required_items
    ]

    required_embeddings = embedder.embed_documents(
        clean_required
    )

    candidate_embeddings = embedder.embed_documents(
        clean_candidate_responsibilities
    )

    matched: list[str] = []
    missing: list[str] = []
    responsibility_matches: list[dict[str, Any]] = []

    for required_index, required in enumerate(
        required_items
    ):
        responsibility = required["description"]
        responsibility_type = required["type"]

        if responsibility_type == "generic":
            responsibility_matches.append(
                {
                    "responsibility": responsibility,
                    "type": responsibility_type,
                    "matched_candidate_responsibility": None,
                    "similarity": 0.0,
                    "lexical_overlap": 0.0,
                    "skill_evidence": [],
                    "keyword_evidence": [],
                    "confidence": 0.0,
                    "evidence": "neutral",
                    "matched": False,
                }
            )

            continue

        (
            best_candidate,
            best_similarity,
            best_lexical_overlap,
            base_confidence,
        ) = _semantic_evidence(
            required_text=responsibility,
            candidate_texts=clean_candidate_responsibilities,
            required_embedding=required_embeddings[
                required_index
            ],
            candidate_embeddings=candidate_embeddings,
        )

        skill_evidence = _matched_skill_evidence(
            candidate_skills=candidate_skills,
            skill_matches=skill_matches,
        )

        keyword_evidence = _direct_keyword_evidence(
            responsibility,
            candidate_keywords,
        )

        final_confidence = _combine_responsibility_evidence(
            base_confidence=base_confidence,
            skill_evidence=skill_evidence,
            keyword_evidence=keyword_evidence,
        )

        is_matched = final_confidence >= threshold

        if is_matched:
            matched.append(responsibility)
        else:
            missing.append(responsibility)

        responsibility_matches.append(
            {
                "responsibility": responsibility,
                "type": responsibility_type,
                "matched_candidate_responsibility": best_candidate,
                "similarity": round(
                    best_similarity,
                    4,
                ),
                "lexical_overlap": round(
                    best_lexical_overlap,
                    4,
                ),
                "skill_evidence": skill_evidence,
                "keyword_evidence": keyword_evidence,
                "base_confidence": round(
                    base_confidence,
                    4,
                ),
                "confidence": round(
                    final_confidence,
                    4,
                ),
                "evidence": _evidence_level(
                    final_confidence,
                    is_matched,
                    responsibility_type,
                ),
                "matched": is_matched,
            }
        )

    return {
        "matched_responsibilities": matched,
        "missing_responsibilities": missing,
        "responsibility_matches": responsibility_matches,
    }


def match_experience(
    required_min: float | None,
    required_max: float | None,
    candidate_years: float | None,
) -> dict[str, Any]:
    """Determine whether candidate experience satisfies the JD requirement."""

    if candidate_years is None:
        return {
            "experience_match": False,
            "experience_status": "unknown",
        }

    if required_min is None and required_max is None:
        return {
            "experience_match": True,
            "experience_status": "no_requirement",
        }

    if (
        required_min is not None
        and candidate_years < required_min
    ):
        return {
            "experience_match": False,
            "experience_status": "below_minimum",
        }

    if (
        required_max is not None
        and candidate_years > required_max
    ):
        return {
            "experience_match": True,
            "experience_status": "above_range",
        }

    return {
        "experience_match": True,
        "experience_status": "meets_requirement",
    }


def match_requirements(
    jd_requirements: dict[str, Any],
    resume_profile: dict[str, Any],
    embedder: Embeddings,
) -> dict[str, Any]:
    """Match all extracted resume information against JD requirements."""

    skill_matches = match_skills(
        required_skills=jd_requirements.get(
            "skills",
            [],
        ),
        candidate_skills=resume_profile.get(
            "skills",
            [],
        ),
    )

    keyword_matches = match_keywords(
        required_keywords=jd_requirements.get(
            "keywords",
            [],
        ),
        candidate_keywords=resume_profile.get(
            "keywords",
            [],
        ),
    )

    responsibility_matches = match_responsibilities(
        required_responsibilities=jd_requirements.get(
            "responsibilities",
            [],
        ),
        candidate_responsibilities=resume_profile.get(
            "responsibilities",
            [],
        ),
        skill_matches=skill_matches,
        candidate_skills=resume_profile.get(
            "skills",
            [],
        ),
        candidate_keywords=resume_profile.get(
            "keywords",
            [],
        ),
        embedder=embedder,
    )

    experience_match = match_experience(
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

    return {
        **skill_matches,
        **keyword_matches,
        **responsibility_matches,
        **experience_match,
    }