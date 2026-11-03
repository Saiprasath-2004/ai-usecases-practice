from datetime import datetime
from typing import Any

from ats_agent.services.scheduling.intent import SchedulingIntent


SCHEDULING_SYSTEM_PROMPT = """
You are a scheduling intent parser for a recruiter application.

Your job is ONLY to convert the recruiter's natural-language scheduling
request into structured scheduling intent.

Do NOT choose an actual interview slot.
Do NOT book anything.
Do NOT make calendar decisions.

Extract only what the recruiter explicitly requests.

Rules:

- Resolve relative dates using the provided current date.

- "next week" should become an appropriate date range.

- "Tuesday" should be represented using weekday number:
    Monday=0, Tuesday=1, Wednesday=2, Thursday=3,
    Friday=4, Saturday=5, Sunday=6

- "morning" means approximately 09:00:00-12:00:00.

- "afternoon" means approximately 12:00:00-17:00:00.

- "evening" means approximately 17:00:00-20:00:00.

- All time values MUST use HH:MM:SS format.
- Example: 13:00 must be returned as 13:00:00.

- If the recruiter gives an exact date, use preferred_date.

- If the recruiter gives a date range, use date_range_start/date_range_end.

- If the recruiter gives preferred weekdays, populate preferred_weekdays.

- If no time preference is given, leave time fields null.

- Default duration is 60 minutes.

- Use flexibility="exact" only when the recruiter explicitly requests
  an exact time/date.

- Otherwise use flexibility="flexible".

Return ONLY structured data matching the SchedulingIntent schema.
"""


def parse_scheduling_intent(
    llm: Any,
    recruiter_comment: str,
    current_datetime: datetime | None = None,
) -> SchedulingIntent:
    """
    Convert recruiter scheduling instructions into structured intent.

    The LLM only extracts intent. It does not select or book a slot.
    """

    if not recruiter_comment or not recruiter_comment.strip():
        raise ValueError(
            "Scheduling comments are required when scheduling an interview."
        )

    if current_datetime is None:
        current_datetime = datetime.now()

    user_prompt = f"""
Current date: {current_datetime.date().isoformat()}
Current time: {current_datetime.time().isoformat(timespec="minutes")}

Recruiter's scheduling instruction:
{recruiter_comment.strip()}
"""

    structured_llm = llm.with_structured_output(SchedulingIntent)

    result = structured_llm.invoke(
        [
            ("system", SCHEDULING_SYSTEM_PROMPT),
            ("human", user_prompt),
        ]
    )

    if isinstance(result, SchedulingIntent):
        return result

    if isinstance(result, dict):
        return SchedulingIntent.model_validate(result)

    raise ValueError(
        f"LLM returned an invalid scheduling intent: {type(result).__name__}"
    )