from pathlib import Path

from ats_agent.agent_layer.schemas import ResumeProfile


def test_resume_processing_returns_structured_profile(monkeypatch):
    from ats_agent.graph import nodes

    class FakeStructuredModel:
        def with_structured_output(self, _schema):
            return self

        def invoke(self, _prompt):
            return ResumeProfile(
                skills=[
                    {"name": "React", "variants": ["React.js", "ReactJS"]},
                    {"name": "Angular", "variants": ["AngularJS"]},
                ],
                keywords=["unit testing", "code reviews"],
                responsibilities=[
                    {
                        "name": "Develop responsive web applications",
                        "keywords": ["web applications", "responsive UI"],
                    }
                ],
                experience_years=5,
            )

    monkeypatch.setattr(nodes, "get_chat_model", lambda: FakeStructuredModel())

    loaded = nodes.load_resume_node({"resume_path": "input/resume.pdf"})
    result = nodes.extract_resume_profile(loaded)
    profile = result["resume_profile"]

    assert Path("input/resume.pdf").is_file()
    assert loaded["resume_text"]
    assert profile["skills"]
    assert profile["keywords"]
    assert profile["responsibilities"]
    assert profile["experience_years"] == 5
