"""Match extracted resume facts against job requirements."""

from ats_agent.extraction.schemas import ResponsibilityMatch
from ats_agent.scoring.normalizer import normalize_skill


def match_skills(
    required_skills: list[dict],
    candidate_skills: list[dict],
) -> dict:
    """Return required skills split into matched and missing groups."""

    matched = []
    missing = []

    for required_skill in required_skills:
        required_name = normalize_skill(required_skill["name"])

        required_variants = {
            normalize_skill(variant) for variant in required_skill.get("variants", [])
        }

        required_forms = {
            required_name,
            *required_variants,
        }

        found = False

        for candidate_skill in candidate_skills:
            candidate_name = normalize_skill(candidate_skill["name"])

            candidate_variants = {
                normalize_skill(variant)
                for variant in candidate_skill.get("variants", [])
            }

            candidate_forms = {
                candidate_name,
                *candidate_variants,
            }

            if required_forms.intersection(candidate_forms):
                found = True
                break

        if found:
            matched.append(required_skill["name"])
        else:
            missing.append(required_skill["name"])

    return {
        "matched_skills": matched,
        "missing_skills": missing,
    }


def match_keywords(
    required_keywords: list[str],
    candidate_keywords: list[str],
) -> dict:
    """Return normalized required keywords split into matched and missing groups."""

    required = {normalize_skill(keyword) for keyword in required_keywords}

    candidate = {normalize_skill(keyword) for keyword in candidate_keywords}

    matched = required.intersection(candidate)

    return {
        "matched_keywords": sorted(matched),
        "missing_keywords": sorted(required - candidate),
    }


def match_responsibilities(
    required_responsibilities: list[str],
    resume_text: str,
    llm,
) -> dict:
    """Ask the LLM for direct evidence supporting each responsibility."""

    # Create the structured LLM once.
    # We don't need to recreate it for every responsibility.
    structured_llm = llm.with_structured_output(ResponsibilityMatch)

    matches = []

    for responsibility in required_responsibilities:
        prompt = f"""
You are an evidence matching system.

Determine whether the candidate's resume provides
direct evidence that they have performed the following
job responsibility.

JOB RESPONSIBILITY:
{responsibility}

CANDIDATE RESUME:
{resume_text}

Rules:

1. Return supported=true only when the resume contains
   reasonable direct evidence that the candidate performed
   this responsibility.

2. Do not assume a responsibility simply because the
   candidate has a related technical skill.

3. Do not infer experience that is not present.

4. Related technologies do not automatically prove that
   the responsibility was performed.

5. If evidence is insufficient, return supported=false.

6. If supported=true, provide concise evidence from the resume.

7. If supported=false, evidence must be an empty string.

Return only the structured result.
"""

        try:
            result = structured_llm.invoke(prompt)

            if result is None:
                matches.append(
                    {
                        "responsibility": responsibility,
                        "supported": False,
                        "evidence": "",
                    }
                )

            else:
                matches.append(result.model_dump())

        except Exception as exc:
            print(
                f"Warning: responsibility matching failed for '{responsibility}': {exc}"
            )

            matches.append(
                {
                    "responsibility": responsibility,
                    "supported": False,
                    "evidence": "",
                }
            )

    matched = [item["responsibility"] for item in matches if item["supported"]]

    missing = [item["responsibility"] for item in matches if not item["supported"]]

    return {
        "matched_responsibilities": matched,
        "missing_responsibilities": missing,
        "responsibility_evidence": matches,
    }
