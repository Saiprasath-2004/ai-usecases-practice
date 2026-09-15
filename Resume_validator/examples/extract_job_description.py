from ats_agent.graph.nodes import extract_job_description_requirements
from ats_agent.ingestion.job_description import load_job_description

document = load_job_description("data/jd.txt")

state = {"jd_context": document.page_content}

result = extract_job_description_requirements(state)

print("\n==============================")
print("JD REQUIREMENTS")
print("==============================")

print(result["jd_requirements"])
