from ats_agent.llm.client import get_chat_model
from ats_agent.graph.nodes import (
    load_resume_node,
    retrieve_job_description,
)
from ats_agent.graph.state import ATSState


def main():
    llm = get_chat_model()

    state: ATSState = {
        "resume_path": "input/resume.pdf"
    }

    # Same first two steps as the real LangGraph application
    state.update(load_resume_node(state))
    state.update(retrieve_job_description(state))

    prompt = f"""
You are an ATS information extraction system.

Extract the following from this job description:

1. skills
2. keywords
3. responsibilities
4. experience_min
5. experience_max

Return ONLY valid JSON.

Required JSON structure:

{{
  "skills": [
    {{
      "name": "string",
      "variants": ["string"]
    }}
  ],
  "keywords": ["string"],
  "responsibilities": ["string"],
  "experience_min": null,
  "experience_max": null
}}

JOB DESCRIPTION:
{state["jd_context"]}
"""

    response = llm.invoke(prompt)

    print("\n========== RAW RESPONSE ==========")
    print(response)

    print("\n========== CONTENT ==========")
    print(response.content)


if __name__ == "__main__":
    main()