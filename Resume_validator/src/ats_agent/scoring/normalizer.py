"""Canonicalize skill and keyword names before comparison."""


def normalize_skill(skill: str) -> str:
    """Return a lowercase canonical name for a skill or keyword."""
    skill = skill.lower().strip()

    aliases = {
        "react.js": "react",
        "reactjs": "react",
        "angular.js": "angular",
        "angularjs": "angular",
        "github": "git",
        "git hub": "git",
        "ci/cd": "cicd",
        "ci-cd": "cicd",
        "cicd": "cicd",
        "powerbi": "power bi",
        "power-bi": "power bi",
    }

    return aliases.get(skill, skill)
