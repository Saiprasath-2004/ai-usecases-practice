from ats_agent.extraction.schemas import JDRequirements


def test_job_description_processing_returns_structured_requirements(monkeypatch):
    from ats_agent.graph import nodes

    class FakeStructuredModel:
        def with_structured_output(self, _schema):
            return self

        def invoke(self, _prompt):
            return JDRequirements(
                skills=[
                    {"name": "React", "variants": ["React.js"]},
                    {"name": "Angular", "variants": ["AngularJS"]},
                    {"name": "Jenkins", "variants": ["Jenkins CI"]},
                ],
                keywords=["unit testing", "enterprise applications"],
                responsibilities=[
                    {
                        "name": "Build front-end web applications",
                        "keywords": ["frontend", "web applications"],
                    }
                ],
                experience_min=4,
                experience_max=6,
            )

    monkeypatch.setattr(nodes, "get_chat_model", lambda: FakeStructuredModel())

    result = nodes.extract_job_description_requirements(
        {"jd_text": "React Angular Jenkins. Experience 4-6 years."}
    )
    requirements = result["jd_requirements"]

    assert requirements["skills"]
    assert requirements["keywords"]
    assert requirements["responsibilities"]
    assert requirements["experience_min"] == 4
    assert requirements["experience_max"] == 6
    assert requirements["skills"][0]["variants"] == ["React.js"]
