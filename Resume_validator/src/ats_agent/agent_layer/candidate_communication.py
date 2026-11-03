"""Candidate-facing communication content generation."""

from typing import Any

from ats_agent.llm.client import get_chat_model


FOLLOWUP_EMAIL_SYSTEM_PROMPT = """
You write professional candidate-facing emails for a recruitment system.

Your job is to turn a set of recruiter-approved follow-up questions into
a natural, concise email.

Rules:
- Sound like a real recruiter, not a questionnaire generator.
- Be warm, professional, and concise.
- Do not repeat the same sentence structure for every question.
- Group related questions naturally when possible.
- Preserve the meaning of every supplied question.
- Do not invent candidate information.
- Do not invent job requirements.
- Do not add claims about the candidate.
- Do not add facts that are not provided.
- Do not change the purpose of the questions.
- Ask the candidate for clarification rather than implying they lack a skill.
- Do not mention AI, ATS, scoring, evaluation models, or internal recruitment systems.
- Return only valid JSON with exactly these fields:
  {
    "subject": "...",
    "body": "..."
  }
"""


def generate_followup_email(
    candidate_name: str,
    questions: list[str],
) -> dict[str, str]:
    """
    Generate a natural candidate-facing follow-up email.

    The supplied questions are authoritative. The LLM may improve
    presentation and wording but must preserve their meaning.
    """

    if not questions:
        raise ValueError(
            "At least one follow-up question is required."
        )

    candidate_name = (
        candidate_name.strip()
        if candidate_name
        else "Candidate"
    )

    questions_text = "\n".join(
        f"- {question}"
        for question in questions
    )

    prompt = f"""
Candidate name:
{candidate_name}

Recruiter-approved follow-up questions:
{questions_text}

Write a concise, natural email asking the candidate to provide
the requested clarification.

The questions should be incorporated conversationally rather than
repeating "Could you please let us know..." for every item.
"""

    llm = get_chat_model(json_mode=True)

    response = llm.invoke(
        [
            (
                "system",
                FOLLOWUP_EMAIL_SYSTEM_PROMPT,
            ),
            (
                "human",
                prompt,
            ),
        ]
    )

    content = response.content

    if not isinstance(content, str):
        raise ValueError(
            "LLM returned an invalid email response."
        )

    import json

    try:
        result: Any = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "LLM returned invalid JSON for candidate email."
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "Candidate email response must be a JSON object."
        )

    subject = result.get("subject")
    body = result.get("body")

    if not isinstance(subject, str) or not subject.strip():
        raise ValueError(
            "Generated candidate email is missing a subject."
        )

    if not isinstance(body, str) or not body.strip():
        raise ValueError(
            "Generated candidate email is missing a body."
        )

    return {
        "subject": subject.strip(),
        "body": body.strip(),
    }