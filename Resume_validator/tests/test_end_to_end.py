from pathlib import Path

from ats_agent.extraction.schemas import (
    JDRequirements,
    ResponsibilityMatch,
    ResponsibilityMatchResult,
    ResumeProfile,
)


def test_end_to_end_workflow_returns_complete_evaluation(monkeypatch):
    from ats_agent.graph import builder, nodes

    class FakeStructuredModel:
        def __init__(self, schema):
            self.schema = schema

        def invoke(self, _prompt):
            if self.schema is JDRequirements:
                return JDRequirements(
                    skills=[
                        {"name": "React", "variants": ["React.js"]},
                        {"name": "Angular", "variants": ["AngularJS"]},
                    ],
                    keywords=["unit testing", "code reviews"],
                    responsibilities=[
                        {
                            "name": "Build front-end web applications",
                            "keywords": ["frontend", "web applications"],
                        }
                    ],
                    experience_min=4,
                    experience_max=6,
                )
            if self.schema is ResumeProfile:
                return ResumeProfile(
                    skills=[
                        {"name": "React.js", "variants": ["React"]},
                        {"name": "AngularJS", "variants": ["Angular"]},
                    ],
                    keywords=["unit testing", "code reviews"],
                    responsibilities=[
                        {
                            "name": "Develop responsive web applications",
                            "keywords": ["web applications"],
                        }
                    ],
                    experience_years=5,
                )
            return ResponsibilityMatchResult(
                matches=[
                    ResponsibilityMatch(
                        responsibility="Build front-end web applications",
                        supported=True,
                        evidence="Developed responsive web applications.",
                    )
                ]
            )

    class FakeLLM:
        def with_structured_output(self, schema):
            return FakeStructuredModel(schema)

    monkeypatch.setattr(nodes, "get_chat_model", lambda: FakeLLM())

    graph = builder.build_graph()
    state = graph.invoke(
        {
            "resume_path": "input/resume.pdf",
            "jd_path": "data/jd.txt",
        }
    )

    assert state["resume_text"]
    assert state["jd_text"] == Path("data/jd.txt").read_text(encoding="utf-8")
    assert state["jd_requirements"]["skills"]
    assert state["resume_profile"]["skills"]
    assert state["matches"]["matched_skills"]
    assert set(state["result"]) == {
        "overall_score",
        "skill_score",
        "experience_score",
        "keyword_score",
        "responsibility_score",
    }
