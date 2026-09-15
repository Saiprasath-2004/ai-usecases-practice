from pprint import pprint

from ats_agent.graph.nodes import extract_resume_profile
from ats_agent.ingestion.resume_parser import load_resume_text

resume_text = load_resume_text("input/resume.pdf")

state = {"resume_text": resume_text}

result = extract_resume_profile(state)

print("\n==============================")
print("RESUME PROFILE")
print("==============================")

pprint(result["resume_profile"], indent=4, width=80)
