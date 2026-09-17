from ats_agent.extraction.schemas import ResponsibilityMatch, ResponsibilityMatchResult
from ats_agent.scoring.matcher import match_requirements
from ats_agent.scoring.scorer import calculate_ats_score


class FakeResponsibilityModel:
    def __init__(self, result):
        self.result = result

    def invoke(self, _prompt):
        return self.result


class FakeLLM:
    def __init__(self, responsibility_result):
        self.responsibility_result = responsibility_result

    def with_structured_output(self, _schema):
        return FakeResponsibilityModel(self.responsibility_result)


def test_candidate_evaluation_matches_and_scores_realistic_candidate():
    jd_requirements = {
        "skills": [
            {"name": "React", "variants": ["React.js", "ReactJS"]},
            {"name": "Angular", "variants": ["AngularJS"]},
            {"name": "Jenkins", "variants": ["Jenkins CI"]},
        ],
        "keywords": ["unit testing", "code reviews", "enterprise applications"],
        "responsibilities": [
            {
                "name": "Build front-end web applications",
                "keywords": ["frontend", "web applications"],
            },
            {
                "name": "Participate in code reviews",
                "keywords": ["code reviews", "peer review"],
            },
            {
                "name": "Maintain production applications",
                "keywords": ["production support", "troubleshooting"],
            },
        ],
        "experience_min": 4,
        "experience_max": 6,
    }
    resume_profile = {
        "skills": [
            {"name": "React.js", "variants": ["React", "ReactJS"]},
            {"name": "AngularJS", "variants": ["Angular"]},
        ],
        "keywords": ["unit testing", "code reviews"],
        "responsibilities": [
            {
                "name": "Develop responsive web applications",
                "keywords": ["web applications", "responsive UI"],
            },
            {
                "name": "Review code with development teams",
                "keywords": ["code review", "peer review"],
            },
        ],
        "experience_years": 5,
    }
    responsibility_result = ResponsibilityMatchResult(
        matches=[
            ResponsibilityMatch(
                responsibility="Build front-end web applications",
                supported=True,
                evidence="Developed responsive web applications.",
            ),
            ResponsibilityMatch(
                responsibility="Participate in code reviews",
                supported=True,
                evidence="Reviewed code with development teams.",
            ),
            ResponsibilityMatch(
                responsibility="Maintain production applications",
                supported=False,
                evidence="",
            ),
        ]
    )

    matches = match_requirements(
        jd_requirements=jd_requirements,
        resume_profile=resume_profile,
        llm=FakeLLM(responsibility_result),
    )
    result = calculate_ats_score(
        jd_requirements=jd_requirements,
        resume_profile=resume_profile,
        matches=matches,
    )

    assert matches["matched_skills"] == ["React", "Angular"]
    assert matches["missing_skills"] == ["Jenkins"]
    assert matches["matched_keywords"] == ["code reviews", "unit testing"]
    assert matches["missing_keywords"] == ["enterprise applications"]
    assert matches["matched_responsibilities"] == [
        "Build front-end web applications",
        "Participate in code reviews",
    ]
    assert matches["missing_responsibilities"] == ["Maintain production applications"]
    assert matches["responsibility_evidence"][0]["evidence"]
    assert matches["experience_match"] is True
    assert matches["experience_status"] == "meets_requirement"
    assert result == {
        "skill_score": 27,
        "experience_score": 25,
        "keyword_score": 10,
        "responsibility_score": 13,
        "overall_score": 75,
    }


def test_candidate_evaluation_reports_below_minimum_and_unknown_experience():
    jd_requirements = {
        "skills": [],
        "keywords": [],
        "responsibilities": [],
        "experience_min": 4,
        "experience_max": 6,
    }
    responsibility_result = ResponsibilityMatchResult(matches=[])
    llm = FakeLLM(responsibility_result)

    below_minimum = match_requirements(
        jd_requirements=jd_requirements,
        resume_profile={"experience_years": 3},
        llm=llm,
    )
    unknown = match_requirements(
        jd_requirements=jd_requirements,
        resume_profile={"experience_years": None},
        llm=llm,
    )

    assert below_minimum["experience_match"] is False
    assert below_minimum["experience_status"] == "below_minimum"
    assert unknown["experience_match"] is False
    assert unknown["experience_status"] == "unknown"
