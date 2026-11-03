"""Follow-up logic for skill-gap verification."""

from typing import Any, Optional
from ats_agent.config import FOLLOWUP_MAX_QUESTIONS
from ats_agent.extraction.schemas import FollowupReply, SkillConfirmation
from ats_agent.llm.client import get_chat_model, parse_llm_json

def build_followup_questions(missing_skills: list[str], max_questions: int | None = None) -> list[str]:
    """
    Build a list of questions to verify missing skills.
    """
    limit = max_questions if max_questions is not None else FOLLOWUP_MAX_QUESTIONS
    target_skills = missing_skills[:limit]

    return [f"Do you have experience with {skill}? If so, please briefly describe your usage." for skill in target_skills]

def extract_confirmed_skills(reply_text: str, questions: list[str], llm_call=None) -> list[str]:
    """
    Turns the candidate's free-text reply into a list of confirmed skills.
    """
    if not reply_text:
        return []

    if not llm_call:
        # Fallback: very basic keyword search if no LLM provided
        confirmed = []
        # Extract skill names from questions
        for q in questions:
            # Simple extraction: "Do you have experience with {skill}? If so, please briefly describe your usage."
            # Find the part between "experience with " and the first "?"
            if "experience with " in q:
                start = q.find("experience with ") + len("experience with ")
                end = q.find("?", start)
                if end != -1:
                    skill = q[start:end].strip()
                    if skill.lower() in reply_text.lower():
                        confirmed.append(skill)
        return confirmed

    # LLM-based extraction
    llm = llm_call if hasattr(llm_call, "invoke") else get_chat_model()

    prompt = f"""
    Analyze the candidate's reply to the following follow-up questions about missing skills.

    Questions:
    {chr(10).join([f"- {q}" for q in questions])}

    Candidate Reply:
    {reply_text}

    Return a JSON object matching this structure:
    {{
        "confirmations": [
            {{
                "skill_name": "skill name",
                "confirmed": true/false,
                "evidence": "brief quote or summary from reply"
            }}
        ],
        "additional_comments": "any other relevant info"
    }}

    Only confirm a skill if the candidate explicitly claims experience.
    """

    try:
        response = llm.invoke(prompt)
        # Handle both string and BaseMessage responses
        content = response.content if hasattr(response, "content") else str(response)
        data = parse_llm_json(content)
        reply = FollowupReply.model_validate(data)
        return [c.skill_name for c in reply.confirmations if c.confirmed]
    except Exception:
        return []

def apply_followup_reply(result: dict[str, Any], questions: list[str], confirmed_skills: list[str]) -> dict[str, Any]:
    """
    Pure, deterministic bonus added to skill_score and overall_score based on confirmed skills.
    Capped at the 60-point skill ceiling.
    """
    # Current state
    skill_score = result.get("skill_score", 0.0)
    overall_score = result.get("overall_score", 0.0)

    # Each confirmed skill adds a bonus (e.g., 5 points)
    # In a real system, this might be weighted. Here we use a flat bonus.
    bonus = len(confirmed_skills) * 5.0

    new_skill_score = min(60.0, skill_score + bonus)
    actual_bonus = new_skill_score - skill_score

    new_overall_score = overall_score + actual_bonus

    return {
        **result,
        "skill_score": new_skill_score,
        "overall_score": new_overall_score,
        "followup_bonus": actual_bonus
    }
