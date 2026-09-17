from ats_agent.extraction.schemas import JDRequirements
from ats_agent.graph.nodes import retrieve_job_description
from ats_agent.ingestion.resume_parser import load_resume_text
from ats_agent.llm.client import get_chat_model


def build_jd_prompt(jd_context: str) -> str:
	return f"""
You are a structured job-description extraction system.

Your task is to convert the job description into structured
requirements.

JOB DESCRIPTION:

{jd_context}


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


def main() -> None:
	resume_text = load_resume_text("input/resume.pdf")
	jd_state = retrieve_job_description({"resume_text": resume_text})
	prompt = build_jd_prompt(jd_state["jd_context"])
	llm = get_chat_model()

	for run_number in range(1, 4):
		print(f"RUN {run_number}")

		print("RAW RESPONSE")
		raw_result = llm.invoke(prompt)
		print("# ==============================")
		print("RAW LLM RESPONSE")
		print(f"Type: {type(raw_result)}")
		print(raw_result)

		structured_llm = llm.with_structured_output(JDRequirements)
		structured_result = structured_llm.invoke(prompt)
		print("# ==============================")
		print("STRUCTURED LLM RESPONSE")
		print(f"Type: {type(structured_result)}")
		print(structured_result)


if __name__ == "__main__":
	main()
