"""Candidate follow-up logic for verifying ATS skill gaps."""

from typing import Any

from ats_agent.agent_layer.schemas import FollowupReply
from ats_agent.config import FOLLOWUP_MAX_QUESTIONS
from ats_agent.llm.client import get_chat_model, parse_llm_json


def build_followup_questions(
    missing_skills: list[str],
    max_questions: int | None = None,
) -> list[str]:
    """
    Generate polite candidate-facing questions for skills that
    were not sufficiently supported by the resume.

    The questions intentionally avoid saying that the candidate
    does not have the skill. They ask whether the candidate has
    relevant experience that may not have been captured in the resume.
    """

    if not missing_skills:
        return []

    limit = (
        max_questions
        if max_questions is not None
        else FOLLOWUP_MAX_QUESTIONS
    )

    if limit <= 0:
        return []

    questions: list[str] = []

    for skill in missing_skills[:limit]:
        clean_skill = skill.strip()

        if not clean_skill:
            continue

        questions.append(
            f"Could you please let us know if you have any professional, "
            f"project, internship, or academic experience with "
            f"{clean_skill}? If so, we would appreciate a brief description "
            f"of how you have used it."
        )

    return questions


def build_followup_email(
    candidate_name: str,
    questions: list[str],
) -> str:
    """
    Build a professional email asking the candidate to clarify
    experience related to skills that were not sufficiently evident
    from the submitted resume.

    This function only creates the email content.
    Sending the email belongs to the action/outbox layer.
    """

    if not questions:
        raise ValueError("At least one follow-up question is required.")

    question_lines = "\n".join(
        f"{index}. {question}"
        for index, question in enumerate(questions, start=1)
    )

    return f"""Subject: Additional Information Regarding Your Application

Dear {candidate_name},

Thank you for your interest in the position and for taking the time
to submit your application.

As part of our application review, we would like to clarify a few
areas of your experience that were not sufficiently evident from the
information provided in your resume.

If you have relevant experience, please feel free to share it with us.
This could include professional work, internships, academic projects,
personal projects, or other practical experience.

{question_lines}

Please provide any relevant details that you feel would help us
better understand your experience.

Thank you for your time and response.

Best regards,
Recruitment Team
"""


def extract_confirmed_skills(
    reply_text: str,
    questions: list[str],
    llm_call: Any = None,
) -> FollowupReply:
    """
    Analyze the candidate's response and determine which missing skills
    are explicitly supported by the candidate's answer.

    Returns a structured FollowupReply containing:
        - confirmed skills
        - evidence
        - additional comments

    A skill must not be considered confirmed merely because its name
    appears in the candidate's response.
    """

    if not reply_text or not reply_text.strip():
        return FollowupReply(
            confirmations=[],
            additional_comments=None,
        )

    if not questions:
        return FollowupReply(
            confirmations=[],
            additional_comments=None,
        )

    llm = (
        llm_call
        if llm_call is not None and hasattr(llm_call, "invoke")
        else get_chat_model()
    )

    question_text = "\n".join(
        f"- {question}"
        for question in questions
    )

    prompt = f"""
You are an ATS candidate-response verification system.

A resume was evaluated against a job description. Some skills were
not sufficiently supported by the candidate's resume.

The recruiter sent the candidate these clarification questions:

QUESTIONS:
{question_text}

The candidate replied:

CANDIDATE RESPONSE:
{reply_text}

Your task is to determine whether the candidate explicitly provides
credible evidence of experience with any of the skills mentioned
in the questions.

IMPORTANT RULES:

1. Do not assume that mentioning a skill means the candidate has
   practical experience with it.

2. Confirm a skill only when the candidate explicitly claims relevant
   experience.

3. Relevant experience may include:
   - professional employment
   - internships
   - freelance work
   - academic projects
   - personal projects
   - research
   - practical hands-on work

4. If the candidate says they are interested in learning a skill,
   studying it, or planning to use it, do NOT confirm the skill.

5. If the candidate gives vague or ambiguous information, do NOT
   confirm the skill.

6. Do not infer experience that the candidate did not state.

7. Preserve a concise explanation of the evidence supporting each
   confirmed skill.

8. Only evaluate skills that were asked about in the questions.

Return ONLY valid JSON in this structure:

{{
    "confirmations": [
        {{
            "skill_name": "React",
            "confirmed": true,
            "evidence": "Built and maintained two React applications during a software internship."
        }}
    ],
    "additional_comments": "Any other relevant information from the candidate response."
}}
"""

    try:
        response = llm.invoke(prompt)

        content = (
            response.content
            if hasattr(response, "content")
            else str(response)
        )

        data = parse_llm_json(content)

        return FollowupReply.model_validate(data)

    except Exception:
        # A failed LLM verification must never create a false-positive
        # skill confirmation.
        return FollowupReply(
            confirmations=[],
            additional_comments=None,
        )


def apply_followup_reply(
    result: dict[str, Any],
    followup_reply: FollowupReply,
) -> dict[str, Any]:
    """
    Apply verified candidate follow-up information to the ATS result.

    The scoring adjustment is deterministic.

    Each newly confirmed skill can recover up to 5 points in the
    skill component, while the skill component remains capped at 60.

    The overall score is capped at 100.

    No score is added for:
        - unconfirmed skills
        - ambiguous responses
        - empty responses
        - failed LLM verification
    """

    if not result:
        return result

    if not followup_reply.confirmations:
        return {
            **result,
            "followup_bonus": 0.0,
            "followup_confirmed_skills": [],
            "followup_evidence": [],
        }

    skill_score = float(result.get("skill_score", 0.0))
    overall_score = float(result.get("overall_score", 0.0))

    confirmed = [
        confirmation
        for confirmation in followup_reply.confirmations
        if confirmation.confirmed
    ]

    if not confirmed:
        return {
            **result,
            "followup_bonus": 0.0,
            "followup_confirmed_skills": [],
            "followup_evidence": [],
        }

    bonus_per_skill = 5.0

    requested_bonus = len(confirmed) * bonus_per_skill

    new_skill_score = min(
        60.0,
        skill_score + requested_bonus,
    )

    actual_bonus = new_skill_score - skill_score

    new_overall_score = min(
        100.0,
        overall_score + actual_bonus,
    )

    return {
        **result,
        "skill_score": new_skill_score,
        "overall_score": new_overall_score,
        "followup_bonus": actual_bonus,
        "followup_confirmed_skills": [
            confirmation.skill_name
            for confirmation in confirmed
        ],
        "followup_evidence": [
            {
                "skill": confirmation.skill_name,
                "evidence": confirmation.evidence,
            }
            for confirmation in confirmed
        ],
    }