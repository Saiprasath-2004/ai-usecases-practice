"""Structured, deterministic email templates for recruiter-agent communications.

Kept template-based (not LLM-generated) so wording is predictable and never
invents facts. If you later want LLM-polished phrasing, generate it here and
keep this module as the single place that assembles the final subject/body.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Email:
    to: str
    subject: str
    body: str


def interview_invite_email(
    candidate_name: str,
    job_title: str,
    slot_start: datetime,
    slot_end: datetime,
    recruiter_name: str = "The Hiring Team",
    meeting_link: str = "https://meet.example.com/interview",
    to_email: str = "",
) -> Email:
    when = slot_start.strftime("%A, %d %B %Y")
    time_range = f"{slot_start.strftime('%I:%M %p')} - {slot_end.strftime('%I:%M %p')}"

    subject = f"Interview Invitation - {job_title} at Our Company"
    body = f"""Dear {candidate_name},

Thank you for applying for the {job_title} position. We were impressed with
your profile and would like to invite you to a virtual interview.

Interview details:
  Date: {when}
  Time: {time_range}
  Format: Virtual (video call)
  Join link: {meeting_link}

Please confirm your availability for this slot by replying to this email.
If this time doesn't work for you, let us know and we will find an
alternative.

We look forward to speaking with you.

Best regards,
{recruiter_name}
"""
    return Email(to=to_email, subject=subject, body=body)


def rejection_email(
    candidate_name: str,
    job_title: str,
    reason: str,
    recruiter_name: str = "The Hiring Team",
    to_email: str = "",
) -> Email:
    subject = f"Update on your application - {job_title}"
    body = f"""Dear {candidate_name},

Thank you for taking the time to apply for the {job_title} position and for
your interest in joining our team.

After careful review, we've decided not to move forward with your
application at this time. {reason}

We know this isn't the news you were hoping for, and we genuinely
appreciate the effort you put into your application. We'll keep your
profile on file and would welcome an application from you for future roles
that better match your background.

We wish you the very best in your job search.

Best regards,
{recruiter_name}
"""
    return Email(to=to_email, subject=subject, body=body)


def followup_request_email(
    candidate_name: str,
    job_title: str,
    questions: list[str],
    recruiter_name: str = "The Hiring Team",
    to_email: str = "",
) -> Email:
    subject = f"A couple of quick questions - {job_title} application"
    numbered = "\n".join(f"  {i + 1}. {q}" for i, q in enumerate(questions))
    body = f"""Dear {candidate_name},

Thank you for applying for the {job_title} position. Your resume doesn't
mention experience with a few things we'd like to understand better before
proceeding:

{numbered}

Could you reply directly to this email with a short answer for each? Your
response will be used to update your evaluation for this role.

Thanks in advance,
{recruiter_name}
"""
    return Email(to=to_email, subject=subject, body=body)
