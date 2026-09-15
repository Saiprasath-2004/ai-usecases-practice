"""LangGraph node functions for the ATS evaluation pipeline."""

from langchain_chroma import Chroma
from pydantic import BaseModel, Field

from ats_agent.extraction.schemas import JDRequirements, ResumeProfile
from ats_agent.ingestion.resume_parser import load_resume_text
from ats_agent.llm.client import get_chat_model
from ats_agent.rag.embeddings import get_embedding_model
from ats_agent.rag.vectorstore import (
    COLLECTION_NAME,
    PERSIST_DIRECTORY,
    remove_duplicate_documents,
)


class ATSResult(BaseModel):
    overall_score: int = Field(ge=0, le=100)

    skill_score: int = Field(ge=0, le=40)
    experience_score: int = Field(ge=0, le=25)
    keyword_score: int = Field(ge=0, le=15)
    responsibility_score: int = Field(ge=0, le=20)

    matching_skills: list[str]
    missing_skills: list[str]

    matching_keywords: list[str]
    missing_keywords: list[str]

    strengths: list[str]
    weaknesses: list[str]

    recommendations: list[str]


def retrieve_job_description(state):
    """Retrieve the job-description context most relevant to the resume."""
    embeddings = get_embedding_model()

    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIRECTORY,
    )

    remove_duplicate_documents(vector_store)

    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(state["resume_text"])
    jd_context = "\n\n".join(doc.page_content for doc in docs)

    return {"jd_context": jd_context}


def analyze_resume(state):
    """Generate an evidence-based preliminary analysis of the candidate."""
    llm = get_chat_model()

    prompt = f"""
        You are an ATS scoring engine.

        Evaluate the candidate against the provided job description.

        JOB DESCRIPTION:
        {state["jd_context"]}

        RESUME:
        {state["resume_text"]}

        Calculate the ATS score using these exact maximum weights:

        - Technical skills: 40 points
        - Relevant experience: 25 points
        - Keywords: 15 points
        - Responsibilities: 20 points

        The overall score MUST equal:

        skill_score
        + experience_score
        + keyword_score
        + responsibility_score

        Therefore the maximum overall score is 100.

        Be evidence-based.

        Do not invent skills, experience, education, or projects.

        Only award points based on evidence found in the resume.

        Return the structured ATS evaluation.
    """

    response = llm.invoke(prompt)

    return {"analysis": response.content}


def calculate_ats(state):
    """Generate and validate the final structured ATS evaluation."""
    llm = get_chat_model()

    structured_llm = llm.with_structured_output(
        ATSResult,
        method="json_schema",
    )

    prompt = f"""
        You are an ATS scoring engine.

        Evaluate the candidate against the provided job description.

        JOB DESCRIPTION:
        {state["jd_context"]}

        RESUME:
        {state["resume_text"]}

        PREVIOUS ANALYSIS:
        {state.get("analysis", "")}

        Calculate an ATS score from 0 to 100.

        Use these weights:

        - Technical skills: 40%
        - Relevant experience: 25%
        - Keywords: 15%
        - Responsibilities: 20%

        Be evidence-based.

        Do not invent skills, experience, education, or projects.

        Return the structured ATS evaluation.
        """

    result = structured_llm.invoke(prompt)

    if result is None:
        raise ValueError(
            "The configured OpenRouter model did not return structured ATS output. "
            "Choose a model that supports JSON Schema structured responses."
        )

    return {"result": result.model_dump()}


def load_resume_node(state):
    """Load resume text into graph state for downstream nodes."""

    resume_text = load_resume_text(state["resume_path"])

    return {"resume_text": resume_text}


def extract_job_description_requirements(state):
    """Extract structured requirements from retrieved job-description text."""

    llm = get_chat_model()

    structured_llm = llm.with_structured_output(JDRequirements)

    prompt = f"""
You are a structured job-description extraction system.

Your task is to convert the job description into structured
requirements.

JOB DESCRIPTION:

{state["jd_context"]}


IMPORTANT OUTPUT RULE:

The output MUST follow the provided JDRequirements schema.

The responsibilities field MUST contain objects.

Each responsibility object MUST have:

- name: a concise canonical description of the responsibility
- keywords: important concepts that represent that responsibility

DO NOT return responsibilities as plain strings.


SKILLS:

Extract technical skills explicitly required or strongly
expected.

For every skill provide:

- name: canonical/common skill name
- variants: genuine aliases, abbreviations, or equivalent
  written forms

Only include genuine aliases.

Do not merge distinct technologies.

Examples:

React.js:

name = "React"

variants = ["React", "React.js", "ReactJS"]

Amazon Web Services:

name = "AWS"

variants = ["AWS", "Amazon Web Services"]


DO NOT merge:

Java and JavaScript
React and React Native
SQL and PostgreSQL
AWS and Azure


KEYWORDS:

Extract important technical and job-related keywords.


RESPONSIBILITIES:

Convert each major responsibility into an object.

Example source text:

"Design and build front-end web structures to support
enterprise applications."

Expected structure:

{{
    "name": "Build front-end web applications",
    "keywords": [
        "frontend",
        "web applications",
        "enterprise applications"
    ]
}}


Another example:

"Participate in code reviews with peers and managers."

Expected structure:

{{
    "name": "Participate in code reviews",
    "keywords": [
        "code reviews",
        "peer review"
    ]
}}


EXPERIENCE:

Extract minimum and maximum required years when explicitly
stated.

Do not invent experience requirements.


GENERAL RULES:

- Do not invent requirements.
- Do not evaluate candidates.
- Do not calculate scores.
- Do not rank candidates.
- Do not merge unrelated technologies.
- Use only information supported by the job description.

Return only the structured JDRequirements object.
"""

    result = structured_llm.invoke(prompt)

    return {"jd_requirements": result.model_dump()}


def extract_resume_profile(state):
    """Extract structured skills, keywords, responsibilities, and experience."""

    llm = get_chat_model()

    structured_llm = llm.with_structured_output(ResumeProfile)

    prompt = f"""
You are a resume information extraction system.

Extract structured information from the candidate resume.

RESUME:
{state["resume_text"]}

Rules:

1. Extract technical skills explicitly mentioned in the resume.
2. For every skill provide:
   - canonical/common name
   - alternative names, abbreviations, or equivalent written forms
3. Only normalize genuine aliases or equivalent names.
4. Do NOT merge related but distinct technologies.

Examples:

React.js → React
ReactJS → React

AWS → AWS
Amazon Web Services → AWS

Do NOT treat these as the same:

Java ≠ JavaScript
React ≠ React Native
SQL ≠ PostgreSQL
AWS ≠ Azure

5. Extract important technical/job-related keywords.
6. Extract responsibilities the candidate has actually performed.
7. Estimate total professional experience in years only when supported by dates or explicit experience statements.
8. Do not count internships, academic projects, or unrelated experience as professional experience unless the resume clearly identifies them as professional experience.
9. Do not invent skills or experience.
10. Do not infer a skill simply because another related skill is present.
11. Only use information explicitly supported by the resume.

Return only the structured result.
"""

    result = structured_llm.invoke(prompt)

    return {"resume_profile": result.model_dump()}
