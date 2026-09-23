"""LangGraph node functions for the ATS evaluation pipeline."""

from pathlib import Path
from typing import Any

from langgraph.types import interrupt
from pydantic import ValidationError

from ats_agent.embeddings import get_embedding_model
from ats_agent.agent_layer.audit import log_event
from ats_agent.agent_layer.decision import decide
from ats_agent.agent_layer.followup import (
    apply_followup_reply,
    build_followup_questions,
    extract_confirmed_skills,
)
from ats_agent.agent_layer.report import (
    build_evidence,
    render_narrative,
)
from ats_agent.agent_layer.schemas import JDRequirements, ResumeProfile
from ats_agent.graph.state import ATSState
from ats_agent.ingestion.resume_parser import load_resume_text
from ats_agent.llm.client import (
    extract_text_from_response,
    get_chat_model,
    parse_llm_json,
)
from ats_agent.scoring.matcher import match_requirements
from ats_agent.scoring.scorer import calculate_ats_score


# ============================================================
# Input loading
# ============================================================


def load_inputs_node(state: ATSState):
    """Load the resume and job description into graph state."""

    resume_text = load_resume_text(state["resume_path"])

    jd_path = Path(state["jd_path"])

    if not jd_path.is_file():
        raise FileNotFoundError(
            f"Job description file not found: {jd_path}"
        )

    jd_text = jd_path.read_text(
        encoding="utf-8"
    ).strip()

    if not resume_text.strip():
        raise RuntimeError(
            "Resume PDF did not contain extractable text."
        )

    if not jd_text:
        raise RuntimeError(
            "Job description file is empty."
        )

    return {
        "resume_text": resume_text,
        "jd_text": jd_text,
    }


# ============================================================
# JD extraction
# ============================================================


def extract_job_description_requirements(state: ATSState):
    """Extract structured requirements from the job description."""

    def _extract():
        llm = get_chat_model()

        prompt = f"""
        Extract requirements from the job description below into a valid JSON object.

        Return ONLY valid JSON matching this exact structure:

        {{
            "skills": [
                {{
                    "name": "canonical skill name",
                    "variants": ["genuine aliases or alternate written forms"]
                }}
            ],
            "keywords": ["important terms explicitly present in the JD"],
            "responsibilities": [
                {{
                    "description": "explicit responsibility from the JD",
                    "type": "core | supporting | generic"
                }}
            ],
            "experience_min": number or null,
            "experience_max": number or null
        }}

        Rules:

        - Use only information explicitly supported by the JD.

        SKILLS:
        - Skills must be concrete technologies, tools, frameworks, libraries,
          platforms, databases, programming languages, build systems, or
          development/CI/CD tools explicitly required or mentioned as relevant
          technical capabilities.
        - Examples of skills: React, Angular, JavaScript, Python, PostgreSQL,
          GitHub, Jenkins, Maven, Power BI, CI/CD.
        - Do NOT treat general methodologies, workplace practices, behaviors,
          responsibilities, or generic concepts as skills.
        - Examples that should NOT normally be skills: Agile, teamwork,
          communication, code quality, unit testing, test-driven development,
          time management, ownership.
        - Technical concepts such as DOM or Web Services should not be treated
          as concrete technology skills unless the JD clearly presents them as
          a required technical tool/system.
        - Do not infer a technology from another technology.
        - Do not treat related technologies as aliases.
        - React != React Native.
        - SQL != PostgreSQL.
        - AWS != Azure.
        - Angular != AngularJS.
        - Canonicalize a skill only when the JD supports that identity.
        - Variants must be genuine aliases, abbreviations, or alternate written
          forms explicitly found or directly supported by the JD.
        - Do not invent aliases, technologies, or skill relationships.
        - If the same concrete skill appears multiple times, return it only once.

        KEYWORDS:
        - Keywords must be important non-skill terms that actually appear in the JD.
        - Keywords may include technical concepts, methodologies, practices,
          domain terminology, development practices, or other terms useful for
          ATS evaluation.
        - Do NOT repeat a term in keywords if it is already represented as a
          concrete skill.
        - Do NOT include company names, candidate names, locations, cities,
          countries, employment type, contract terms, salary information,
          contact information, or generic job-posting language.
        - Do not create synonyms or inferred keywords.
        - Every keyword must be explicitly present in the JD.

        RESPONSIBILITIES:
        - Responsibilities must be explicit actions, duties, or expectations
          stated in the JD.
        - Do not create responsibilities from skills or keywords.
        - Keep the original responsibility meaning.
        - Avoid duplicate responsibilities.

        Classify every responsibility into exactly one type:

        1. "core"
        Important job-specific technical or functional work.

        Examples:
        - building frontend applications
        - developing backend systems
        - developing integrations
        - implementing software
        - designing databases
        - performing code reviews

        2. "supporting"
        Relevant to the role but secondary to the main technical or
        functional work.

        Examples:
        - working with product managers
        - supporting applications
        - collaborating with development teams

        3. "generic"
        General workplace or behavioral expectations where absence from
        a resume should NOT be treated as evidence that the candidate lacks
        the ability.

        Examples:
        - managing your own time
        - working independently
        - working well in a team
        - communicating effectively
        - being flexible
        - taking ownership

        - Do not classify a responsibility as generic merely because it is short.
        - Do not classify technical responsibilities as generic.
        - Classification describes only the JD responsibility.
        - Do not score, rank, or evaluate the candidate.

        EXPERIENCE:
        - Extract only the general overall experience requirement.
        - Put the minimum required years into experience_min.
        - Put a maximum only when the JD explicitly states one.
        - Do not infer experience from seniority, responsibilities, or skills.
        - Use null when the JD does not specify the corresponding value.

        GENERAL:
        - Use [] when a list has no supported values.
        - Use null when a numeric value is unavailable.
        - Do not evaluate, score, rank, or match any candidate.
        - Return JSON only.
        - Do not return markdown.
        - Do not return explanations.

        JOB DESCRIPTION:
        {state["jd_text"]}
        """

        response = llm.invoke(prompt)
        raw_content = extract_text_from_response(response)

        if not raw_content:
            raise RuntimeError(
                "JD extraction returned an empty response."
            )

        data = parse_llm_json(raw_content)

        try:
            result = JDRequirements.model_validate(data)
        except ValidationError as exc:
            raise RuntimeError(
                "JD extraction JSON does not match "
                "JDRequirements schema:\n"
                f"{exc}"
            ) from exc

        return {
            "jd_requirements": result.model_dump()
        }

    from ats_agent.config import EXTRACTION_MAX_RETRIES
    from ats_agent.graph.retry import with_retries

    try:
        return with_retries(
            _extract,
            EXTRACTION_MAX_RETRIES,
            "extract_job_description_requirements",
        )
    except Exception as exc:
        return {
            "jd_extraction_error": str(exc)
        }


# ============================================================
# Resume extraction
# ============================================================

def extract_resume_profile(state: ATSState):
    """Extract and validate structured candidate information from a resume."""

    def _validate_profile(data: dict) -> ResumeProfile:
        try:
            return ResumeProfile.model_validate(data)
        except ValidationError as exc:
            raise RuntimeError(
                "Resume extraction JSON does not match "
                "ResumeProfile schema:\n"
                f"{exc}"
            ) from exc

    def _extract_initial() -> ResumeProfile:
        llm = get_chat_model()

        prompt = f"""
You are a resume information extraction system.

Your task is to extract FACTS from the complete resume provided below.

You are NOT evaluating the candidate.
You are NOT comparing the candidate with a job description.
You are NOT scoring the candidate.

You MUST inspect the ENTIRE resume before producing the JSON.

Return ONLY valid JSON matching this exact structure:

{{
    "skills": [
        {{
            "name": "canonical skill name",
            "variants": ["genuine aliases or alternate written forms"]
        }}
    ],
    "keywords": [
        "important non-skill terms explicitly present in the resume"
    ],
    "responsibilities": [
        "concrete work actions explicitly performed by the candidate"
    ],
    "experience_years": number or null
}}

EXTRACTION RULES

1. Extract only information supported by the resume.
2. Do not invent information.
3. Inspect every relevant section before responding.
4. Information can appear outside a dedicated Skills section.
5. Work experience, internships, projects, and technical descriptions are valid sources.

SKILLS

Extract concrete technical skills explicitly present anywhere in the resume.

Inspect:
- Skills sections
- Technical skills
- Work experience
- Internships
- Projects
- Certifications
- Technical descriptions

Include:
- programming languages
- frameworks
- libraries
- databases
- platforms
- development tools
- testing tools
- build tools
- CI/CD tools
- cloud technologies
- APIs
- other concrete technologies

Do not infer one technology from another.

Do not invent aliases.

RESPONSIBILITIES

This is a critical extraction task.

Inspect ALL:
- professional experience entries
- internships
- projects
- technical work descriptions
- every bullet describing work performed

Extract actual work performed by the candidate.

Convert explicit work activities into concise responsibility statements while preserving their original meaning.

Examples of valid responsibility patterns:

"Developed frontend screens and components using JavaScript and HTML5."

"Designed SQL Server schemas and queries."

"Integrated frontend applications with REST APIs."

"Developed backend services using ASP.NET Web API."

"Participated in code reviews."

IMPORTANT:

A technology by itself is a skill, not a responsibility.

For example:

"React.js"

is a skill.

But:

"Developed responsive web applications using React.js."

is a responsibility.

Do NOT invent responsibilities.

If the resume contains explicit employment, internship, project, or technical work descriptions, responsibilities MUST NOT be empty.

KEYWORDS

Extract meaningful NON-SKILL terms explicitly supported by the resume.

Inspect:
- professional experience
- internships
- projects
- technical descriptions
- responsibilities
- engineering practices
- development practices
- testing practices
- production-related terminology

Do not invent synonyms or terms that are not supported by the resume.

EXPERIENCE

Determine total professional experience from explicit information in the resume.

Inspect:
- employment dates
- internship dates
- professional experience sections
- explicit duration statements

Calculate duration from explicit dates whenever possible.

Combine non-overlapping professional periods.

Do not count academic coursework or ordinary academic projects unless the resume explicitly identifies them as professional employment.

Return the result in years.

Use decimals when appropriate.

Return null only when the resume genuinely does not provide enough information.

FINAL CHECK

Before returning the JSON, verify:

1. The complete resume was inspected.
2. All employment and internship descriptions were inspected.
3. All project descriptions were inspected.
4. Technical skills were extracted.
5. Meaningful non-skill keywords were extracted when present.
6. Explicit work activities were extracted as responsibilities.
7. Employment/internship dates were inspected.
8. Professional experience was calculated when possible.

RESUME:

{state["resume_text"]}
"""

        response = llm.invoke(prompt)

        raw_content = extract_text_from_response(response)

        if not raw_content:
            raise RuntimeError(
                "Resume extraction returned an empty response."
            )

        data = parse_llm_json(raw_content)

        return _validate_profile(data)

    def _repair_incomplete_profile(
        profile: ResumeProfile,
    ) -> ResumeProfile:

        missing_categories: list[str] = []

        if not profile.responsibilities:
            missing_categories.append("responsibilities")

        if profile.experience_years is None:
            missing_categories.append("experience_years")

        if not missing_categories:
            return profile

        llm = get_chat_model()

        missing_text = ", ".join(missing_categories)

        repair_prompt = f"""
You are performing a SECOND-PASS resume extraction.

The first extraction was structurally valid but incomplete.

The following information was not successfully extracted:

{missing_text}

You MUST re-examine the COMPLETE resume below specifically for the missing
information.

Do NOT invent information.

Do NOT use the job description.

Do NOT evaluate the candidate.

Do NOT score the candidate.

Return ONLY valid JSON using this structure:

{{
    "responsibilities": [
        "concrete work actions explicitly performed by the candidate"
    ],
    "experience_years": number or null
}}

RESPONSIBILITIES

Carefully inspect:

- every professional employment entry
- every internship
- every project
- every technical work description
- every bullet describing work performed

Extract actual actions performed by the candidate.

Examples:

"Developed frontend applications using React."

"Designed database schemas."

"Integrated REST APIs."

"Implemented backend services."

"Performed unit testing."

"Participated in code reviews."

A technology alone is NOT a responsibility.

For example:

"React"

is not a responsibility.

But:

"Developed web applications using React."

is a responsibility.

If explicit work activities exist in the resume, responsibilities MUST NOT
be empty.

EXPERIENCE

Inspect explicit:

- employment dates
- internship dates
- professional experience
- explicit duration statements

Calculate total professional experience from explicit information.

Combine non-overlapping professional periods.

Do not count ordinary academic projects unless explicitly identified as
professional employment.

Return the total in years.

Return null only when the resume genuinely does not contain enough
information to calculate it.

FIRST-PASS PROFILE

The first extraction produced:

{profile.model_dump_json(indent=2)}

Use this only as context. Re-examine the resume itself.

COMPLETE RESUME

{state["resume_text"]}
"""

        response = llm.invoke(repair_prompt)

        raw_content = extract_text_from_response(response)

        if not raw_content:
            raise RuntimeError(
                "Resume repair extraction returned an empty response."
            )

        repair_data = parse_llm_json(raw_content)

        if not isinstance(repair_data, dict):
            raise RuntimeError(
                "Resume repair extraction must return a JSON object."
            )

        responsibilities = profile.responsibilities

        if not responsibilities:
            responsibilities = repair_data.get(
                "responsibilities",
                [],
            )

        experience_years = profile.experience_years

        if experience_years is None:
            experience_years = repair_data.get(
                "experience_years"
            )

        merged_data = profile.model_dump()

        merged_data["responsibilities"] = responsibilities
        merged_data["experience_years"] = experience_years

        return _validate_profile(merged_data)

    def _extract():
        resume_text = state["resume_text"].strip()

        if not resume_text:
            raise RuntimeError(
                "Resume text is empty; cannot extract candidate profile."
            )

        profile = _extract_initial()

        # ----------------------------------------------------
        # Semantic completeness check
        # ----------------------------------------------------

        needs_repair = (
            not profile.responsibilities
            or profile.experience_years is None
        )

        if needs_repair:
            profile = _repair_incomplete_profile(profile)

        # ----------------------------------------------------
        # Final validation after repair
        # ----------------------------------------------------

        if not profile.responsibilities:
            raise RuntimeError(
                "Resume extraction returned no responsibilities after "
                "targeted re-extraction. The resume contains work "
                "information that could not be reliably structured."
            )

        if profile.experience_years is None:
            raise RuntimeError(
                "Resume extraction could not determine professional "
                "experience after targeted re-extraction."
            )

        return {
            "resume_profile": profile.model_dump()
        }

    from ats_agent.config import EXTRACTION_MAX_RETRIES
    from ats_agent.graph.retry import with_retries

    try:
        return with_retries(
            _extract,
            EXTRACTION_MAX_RETRIES,
            "extract_resume_profile",
        )
    except Exception as exc:
        return {
            "resume_extraction_error": str(exc)
        }
# ============================================================
# Extraction synchronization
# ============================================================


def extraction_complete_node(state: ATSState):
    """
    Validate that both extraction branches completed successfully.

    This node acts as the synchronization point before matching.
    """

    jd_error = state.get("jd_extraction_error")
    resume_error = state.get("resume_extraction_error")

    if jd_error or resume_error:
        errors = []

        if jd_error:
            errors.append(
                f"JD extraction failed: {jd_error}"
            )

        if resume_error:
            errors.append(
                f"Resume extraction failed: {resume_error}"
            )

        return {
            "escalation_reason": "\n".join(errors)
        }

    if not state.get("jd_requirements"):
        return {
            "escalation_reason": (
                "JD extraction completed without requirements."
            )
        }

    if not state.get("resume_profile"):
        return {
            "escalation_reason": (
                "Resume extraction completed without candidate profile."
            )
        }

    return {
        "escalation_reason": None
    }


# ============================================================
# Matching
# ============================================================


def match_requirements_node(state: ATSState):
    """Match extracted resume information against JD requirements."""

    embedder = get_embedding_model()

    matches = match_requirements(
        jd_requirements=state["jd_requirements"],
        resume_profile=state["resume_profile"],
        embedder=embedder,
    )

    return {
        "matches": matches
    }


# ============================================================
# Deterministic ATS scoring
# ============================================================


def calculate_ats_score_node(state: ATSState):
    """Calculate the deterministic ATS score from matching results."""

    result = calculate_ats_score(
        jd_requirements=state["jd_requirements"],
        resume_profile=state["resume_profile"],
        matches=state["matches"],
    )

    return {
        "result": result
    }


# ============================================================
# ATS decision
# ============================================================


def decision_node(state: ATSState):
    """
    Generate the ATS recommendation.

    This node only recommends a pipeline outcome.
    It does not perform recruiter actions.
    """

    result = state.get("result")

    if not result:
        return {
            "verdict": "ESCALATE",
            "escalation_reason": "ATS score is unavailable.",
            **log_event(
                state,
                "decision",
                "ERROR",
                "ATS score result was missing.",
            ),
        }

    verdict = decide(result)

    return {
        "verdict": verdict.value,
        "escalation_reason": None,
        **log_event(
            state,
            "decision",
            "DECISION",
            {
                "verdict": verdict.value,
                "overall_score": result.get("overall_score"),
            },
        ),
    }


# ============================================================
# Recruiter report
# ============================================================


def report_node(state: ATSState):
    """
    Build recruiter-facing evidence and narrative.

    The report is generated from existing matching and scoring
    results. It does not modify the candidate decision.
    """

    matches = state.get("matches", {})
    result = state.get("result", {})

    evidence = build_evidence(
        matches=matches,
        result=result,
    )

    narrative = render_narrative(
        evidence=evidence,
    )

    return {
        "evidence": evidence,
        "narrative": narrative,
        **log_event(
            state,
            "build_report",
            "REPORT",
            {
                "verdict": state.get("verdict"),
                "overall_score": result.get("overall_score"),
            },
        ),
    }


# ============================================================
# Candidate follow-up
# ============================================================

def skill_gap_followup_node(state: ATSState):
    """
    Generate candidate follow-up questions and pause the graph.

    The graph resumes when the candidate response is supplied
    on the same persistent LangGraph thread.
    """

    matches = state.get("matches", {})

    missing_skills = matches.get(
        "missing_skills",
        [],
    )

    if not missing_skills:
        return {
            "followup_questions": [],
            "followup_used": False,
        }

    questions = build_followup_questions(
        missing_skills=missing_skills,
    )

    candidate_response = interrupt(
        {
            "message": "Candidate follow-up required.",
            "questions": questions,
            "missing_skills": missing_skills,
        }
    )

    candidate_reply = ""

    if isinstance(candidate_response, dict):
        candidate_reply = (
            candidate_response.get("reply")
            or candidate_response.get("candidate_reply")
            or ""
        )
    elif isinstance(candidate_response, str):
        candidate_reply = candidate_response

    return {
        "followup_questions": questions,
        "candidate_reply": candidate_reply,
        "followup_used": True,
        **log_event(
            state,
            "skill_gap_followup",
            "FOLLOWUP_REQUESTED",
            {
                "questions": questions,
                "missing_skills": missing_skills,
            },
        ),
    }


# ============================================================
# Re-score after candidate follow-up
# ============================================================
def rescore_with_reply_node(state: ATSState):
    """
    Process the candidate's follow-up response and update:

    1. ATS score
    2. Matched skills
    3. Missing skills
    4. Skill coverage
    5. Follow-up evidence
    6. Recruiter-facing evidence
    7. Recruiter-facing narrative

    The follow-up verification and scoring adjustment logic lives
    in agent_layer.followup.
    """

    candidate_reply = state.get("candidate_reply")
    questions = state.get("followup_questions") or []

    # --------------------------------------------------------
    # 1. Validate candidate reply
    # --------------------------------------------------------

    if not candidate_reply:
        return {
            "escalation_reason": (
                "Candidate follow-up response was not provided."
            ),
            **log_event(
                state,
                "rescore_with_reply",
                "FOLLOWUP_ERROR",
                "Candidate response was empty.",
            ),
        }

    if not questions:
        return {
            "escalation_reason": (
                "No follow-up questions were available for verification."
            ),
            **log_event(
                state,
                "rescore_with_reply",
                "FOLLOWUP_ERROR",
                "Follow-up questions were missing.",
            ),
        }

    # --------------------------------------------------------
    # 2. Extract confirmed skills from candidate response
    # --------------------------------------------------------

    followup_reply = extract_confirmed_skills(
        reply_text=candidate_reply,
        questions=questions,
    )

    # --------------------------------------------------------
    # 3. Update ATS score
    # --------------------------------------------------------

    current_result = state.get("result", {})

    updated_result = apply_followup_reply(
        result=current_result,
        followup_reply=followup_reply,
    )

    # --------------------------------------------------------
    # 4. Collect confirmed skills and evidence
    # --------------------------------------------------------

    confirmed_skills = [
        confirmation.skill_name
        for confirmation in followup_reply.confirmations
        if confirmation.confirmed
    ]

    followup_evidence = [
        {
            "skill": confirmation.skill_name,
            "evidence": confirmation.evidence,
        }
        for confirmation in followup_reply.confirmations
        if confirmation.confirmed
    ]

    # --------------------------------------------------------
    # 5. Update matching information
    #
    # Before follow-up:
    #
    # matched_skills = React, Angular, ...
    # missing_skills = Power BI, Maven, Jenkins
    #
    # After candidate confirms Power BI + Maven:
    #
    # matched_skills = React, Angular, ..., Power BI, Maven
    # missing_skills = Jenkins
    # --------------------------------------------------------

    current_matches = state.get("matches") or {}

    updated_matches = {
        **current_matches,
    }

    matched_skills = list(
        current_matches.get("matched_skills", [])
    )

    missing_skills = list(
        current_matches.get("missing_skills", [])
    )

    for skill in confirmed_skills:

        # Add confirmed skill to matched skills.
        if not any(
            existing.lower() == skill.lower()
            for existing in matched_skills
        ):
            matched_skills.append(skill)

        # Remove confirmed skill from missing skills.
        missing_skills = [
            missing_skill
            for missing_skill in missing_skills
            if missing_skill.lower() != skill.lower()
        ]

    updated_matches["matched_skills"] = matched_skills
    updated_matches["missing_skills"] = missing_skills

    # --------------------------------------------------------
    # 6. Recalculate skill coverage
    # --------------------------------------------------------

    required_skill_count = updated_matches.get(
        "required_skill_count",
        0,
    )

    if required_skill_count:
        updated_matches["matched_skill_count"] = len(
            matched_skills
        )

        updated_matches["skill_coverage"] = round(
            len(matched_skills) / required_skill_count,
            4,
        )

    # --------------------------------------------------------
    # 7. Rebuild recruiter-facing evidence
    # --------------------------------------------------------

    updated_evidence = build_evidence(
        matches=updated_matches,
        result=updated_result,
    )

    # --------------------------------------------------------
    # 8. Rebuild recruiter-facing narrative
    # --------------------------------------------------------

    updated_narrative = render_narrative(
        evidence=updated_evidence,
    )
    print("\n========== RESCORE DEBUG ==========")
    print("CONFIRMED:", confirmed_skills)
    print("MATCHED:", updated_matches.get("matched_skills"))
    print("MISSING:", updated_matches.get("missing_skills"))
    print("COVERAGE:", updated_matches.get("skill_coverage"))
    print("RESULT SCORE:", updated_result.get("overall_score"))
    print("===================================\n")
    # --------------------------------------------------------
    # 9. Return updated graph state
    # --------------------------------------------------------

    return {
        "result": updated_result,
        "matches": updated_matches,
        "evidence": updated_evidence,
        "narrative": updated_narrative,
        "escalation_reason": None,

        **log_event(
            state,
            "rescore_with_reply",
            "RESCORED",
            {
                "confirmed_skills": confirmed_skills,
                "followup_evidence": followup_evidence,
                "followup_bonus": updated_result.get(
                    "followup_bonus",
                    0.0,
                ),
                "new_overall_score": updated_result.get(
                    "overall_score",
                ),
                "updated_matched_skills": matched_skills,
                "updated_missing_skills": missing_skills,
                "updated_skill_coverage": updated_matches.get(
                    "skill_coverage"
                ),
            },
        ),
    }