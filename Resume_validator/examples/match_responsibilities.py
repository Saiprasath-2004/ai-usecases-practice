from ats_agent.ingestion.resume_parser import load_resume_text
from ats_agent.llm.client import get_chat_model
from ats_agent.scoring.matcher import match_responsibilities

resume_text = load_resume_text("input/resume.pdf")

responsibilities = [
    "Build front-end web applications",
    "Build back-end database structures",
    "Participate in code reviews",
    "Maintain production applications",
]


llm = get_chat_model()


result = match_responsibilities(
    responsibilities,
    resume_text,
    llm,
)


print("\n==============================")
print("RESPONSIBILITY MATCHING")
print("==============================")

print("Matched:", result["matched_responsibilities"])

print("Missing:", result["missing_responsibilities"])

print("\nEvidence:")

for item in result["responsibility_evidence"]:
    print("\nResponsibility:")
    print(item["responsibility"])

    print("Supported:")
    print(item["supported"])

    print("Evidence:")
    print(item["evidence"])
