"""LangGraph node functions for the ATS evaluation pipeline."""

from pathlib import Path

from pydantic import ValidationError

from ats_agent.embeddings import get_embedding_model
from ats_agent.extraction.schemas import JDRequirements, ResumeProfile
from ats_agent.ingestion.resume_parser import load_resume_text
from ats_agent.llm.client import get_chat_model, parse_llm_json
from ats_agent.scoring.matcher import match_requirements
from ats_agent.scoring.scorer import calculate_ats_score


def load_inputs_node(state):
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


def extract_job_description_requirements(state):
    """Extract structured requirements from the job description."""

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
    React != React Native.
    SQL != PostgreSQL.
    AWS != Azure.
    Angular != AngularJS.
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

    if hasattr(response, "content") and response.content:
        if isinstance(response.content, str):
            raw_content = response.content.strip()

        elif isinstance(response.content, list):
            raw_content = "".join(
                item.get("text", "")
                if isinstance(item, dict)
                else str(item)
                for item in response.content
            ).strip()

        else:
            raw_content = str(response.content).strip()

    else:
        raw_content = ""

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


def extract_resume_profile(state):
    """Extract structured candidate information from the resume."""

    llm = get_chat_model()

    prompt = f"""
    Extract candidate information from the resume below into a valid JSON object.

    Return ONLY valid JSON matching this exact structure:

    {{
        "skills": [
            {{
                "name": "canonical skill name",
                "variants": ["genuine aliases or alternate written forms"]
            }}
        ],
        "keywords": ["important terms explicitly present in the resume"],
        "responsibilities": ["actions explicitly performed by the candidate"],
        "experience_years": number or null
    }}

    Rules:

    - Use only information explicitly supported by the resume.

    SKILLS:
    - Skills must be concrete technologies, tools, frameworks, libraries,
    platforms, databases, programming languages, or development tools
    explicitly present in the resume.
    - Do not treat general methodologies, workplace behaviors, or generic
    practices as concrete technology skills.
    - Do not infer one technology from another.
    - Do not treat related technologies as aliases.
    React != React Native.
    SQL != PostgreSQL.
    AWS != Azure.
    Angular != AngularJS.
    - Canonicalize a skill only when the resume supports that identity.
    - Variants must be genuine aliases, abbreviations, or alternate written
    forms supported by the resume.
    - Do not invent aliases or technologies.
    - Avoid duplicate skills.

    KEYWORDS:
    - Keywords must be important non-skill terms that actually appear in
    the resume.
    - Keywords may include methodologies, practices, technical concepts,
    domain terminology, or other relevant terms.
    - Do not repeat a term in keywords if it is already represented as a
    concrete skill.
    - Do not create synonyms.
    - Do not include irrelevant personal information or generic resume text.

    RESPONSIBILITIES:
    - Responsibilities must describe actual actions explicitly performed
    by the candidate.
    - Responsibilities may come from work, internships, projects, or other
    explicitly described activities.
    - Do not create responsibilities from skills alone.
    - Keep the meaning of the candidate's actual work.
    - Avoid duplicate responsibilities.

    EXPERIENCE:
    - Calculate professional experience only from explicit dates or
    explicit statements in the resume.
    - Do not count academic coursework as professional experience.
    - Do not count projects as professional experience unless the resume
    explicitly identifies them as professional employment.
    - If professional experience cannot be determined reliably, use null.
    - Do not infer experience from skills, responsibilities, or job titles.

    GENERAL:
    - Use [] when a list has no supported values.
    - Use null when experience is unavailable.
    - Do not evaluate, score, rank, or match the candidate.
    - Return JSON only.
    - Do not return markdown.
    - Do not return explanations.

    RESUME:
    {state["resume_text"]}
    """

    response = llm.invoke(prompt)

    if hasattr(response, "content") and response.content:
        if isinstance(response.content, str):
            raw_content = response.content.strip()

        elif isinstance(response.content, list):
            raw_content = "".join(
                item.get("text", "")
                if isinstance(item, dict)
                else str(item)
                for item in response.content
            ).strip()

        else:
            raw_content = str(response.content).strip()

    else:
        raw_content = ""

    if not raw_content:
        raise RuntimeError(
            "Resume extraction returned an empty response."
        )

    data = parse_llm_json(raw_content)

    try:
        result = ResumeProfile.model_validate(data)

    except ValidationError as exc:
        raise RuntimeError(
            "Resume extraction JSON does not match "
            "ResumeProfile schema:\n"
            f"{exc}"
        ) from exc

    return {
        "resume_profile": result.model_dump()
    }


def match_requirements_node(state):
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


def calculate_ats_score_node(state):
    """Calculate the deterministic ATS score from matching results."""

    result = calculate_ats_score(
        jd_requirements=state["jd_requirements"],
        resume_profile=state["resume_profile"],
        matches=state["matches"],
    )

    return {
        "result": result
    }