from pathlib import Path

from ats_agent.graph.nodes import extract_job_description_requirements

jd_text = Path("data/jd.txt").read_text(encoding="utf-8")

state = {"jd_text": jd_text}

result = extract_job_description_requirements(state)

print("\n==============================")
print("JD REQUIREMENTS")
print("==============================")

print(result["jd_requirements"])
