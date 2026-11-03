"""LangGraph node functions for the ATS evaluation pipeline."""

from pathlib import Path

from pydantic import ValidationError

from ats_agent.embeddings import get_embedding_model
from ats_agent.extraction.schemas import JDRequirements, ResumeProfile
from ats_agent.ingestion.resume_parser import load_resume_text
from ats_agent.llm.client import get_chat_model, parse_llm_json, extract_text_from_response
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
            "extract_job_description_requirements"
        )
    except Exception as exc:
        return {
            "jd_extraction_error": str(exc)
        }


def extract_resume_profile(state):
    """Extract structured candidate information from the resume."""

    def _extract():
        llm = get_chat_model()

        prompt = f"""
        Extract structured candidate information from the resume below.

        Return ONLY valid JSON matching this exact structure:

        {{
            "skills": [
                {{
                    "name": "canonical skill name",
                    "variants": ["genuine aliases or alternate written forms"]
                }}
            ],
            "keywords": ["important non-skill terms explicitly present in the resume"],
            "responsibilities": ["concrete work actions explicitly performed by the candidate"],
            "experience_years": number or null
        }}

        IMPORTANT:
        You are extracting information from the resume.
        Do not evaluate the candidate.
        Do not compare the resume with a job description.
        Do not invent information.

        Rules:

        SKILLS:
        - Extract concrete technologies, tools, frameworks, libraries, platforms,
          databases, programming languages, testing tools, development tools,
          CI/CD tools, and other concrete technical skills explicitly present.
        - Skills may appear in a skills section, work experience, internships,
          projects, or other technical sections.
        - Do not treat general methodologies, behaviors, responsibilities, or
          workplace practices as skills.
        - Do not infer one technology from another.
        - Do not treat related technologies as aliases.
        - React != React Native.
        - SQL != PostgreSQL.
        - AWS != Azure.
        - Angular != AngularJS.
        - Variants must be genuine aliases or alternate written forms supported
          by the resume.
        - Do not invent aliases or technologies.
        - Avoid duplicate skills.

        KEYWORDS:
        - Extract important non-skill terms that are explicitly present in the
          resume and useful for ATS matching.
        - Inspect the ENTIRE resume, especially work experience, internships,
          projects, and technical descriptions.
        - Keywords may include:
          methodologies, development practices, technical concepts, domain terms,
          engineering practices, collaboration practices, and other meaningful
          work-related terminology.
        - Examples include Agile, unit tests, code reviews, integration,
          production, REST APIs, collaboration, CI/CD, troubleshooting,
          responsive UI, etc., but ONLY include them when they are actually
          present or clearly stated in the resume.
        - Do not create synonyms or paraphrases.
        - Do not copy keywords from any external source.
        - Do not repeat a term if it is already represented as a concrete skill.
        - Do not include names, addresses, phone numbers, emails, companies,
          locations, dates, or generic resume formatting text.

        RESPONSIBILITIES:
        - Extract the actual work performed by the candidate.
        - Inspect ALL work experience, internships, projects, and professional
          activity descriptions.
        - Convert each explicit work activity into a concise responsibility
          statement while preserving the original meaning.
        - Examples of valid responsibility statements:
          "Developed frontend screens and components using JavaScript and HTML5."
          "Designed SQL Server schemas and queries."
          "Participated in Agile ceremonies and code reviews."
          "Integrated frontend applications with REST APIs."
          "Developed backend services using ASP.NET Web API."
        - Prefer concrete action statements beginning with verbs such as:
          developed, designed, implemented, built, integrated, tested,
          maintained, deployed, participated, reviewed, configured, supported.
        - Do NOT create responsibilities merely from the skills list.
        - Do NOT invent responsibilities that are not supported by the resume.
        - Do NOT return an empty responsibilities list if the resume contains
          explicit work or project descriptions.
        - Avoid duplicate or nearly duplicate responsibilities.

        EXPERIENCE:
        - Determine total professional experience from explicit employment,
          internship, or professional experience dates/statements in the resume.
        - Inspect work experience and internship entries carefully.
        - Calculate the duration from explicit dates when possible.
        - Combine non-overlapping professional periods.
        - Do not count academic coursework.
        - Do not count ordinary academic projects unless the resume explicitly
          identifies them as professional employment.
        - Do not infer experience from skills, responsibilities, or job titles.
        - Return the total experience in years as a number.
        - Use decimals when appropriate, for example 1.5 or 2.25.
        - Return null only when the resume genuinely does not provide enough
          information to determine professional experience.

        GENERAL:
        - Use [] only when the resume genuinely contains no supported values
          for that field.
        - Use null only when experience cannot be reliably determined.
        - Do not evaluate, score, rank, or match the candidate.
        - Return JSON only.
        - Do not return markdown.
        - Do not return explanations.

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

    from ats_agent.config import EXTRACTION_MAX_RETRIES
    from ats_agent.graph.retry import with_retries

    try:
        return with_retries(
            _extract,
            EXTRACTION_MAX_RETRIES,
            "extract_resume_profile"
        )
    except Exception as exc:
        return {
            "resume_extraction_error": str(exc)
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
