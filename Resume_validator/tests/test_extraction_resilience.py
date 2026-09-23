import pytest
from unittest.mock import MagicMock
from ats_agent.graph.builder import build_graph
from ats_agent.config import EXTRACTION_MAX_RETRIES

def test_extraction_retry_and_error_state(monkeypatch):
    """
    Verify that extraction nodes retry on failure and finally
    set the error state in the graph.
    """
    # Mock LLM to always raise an exception
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError("LLM API Failure")

    def mock_get_model():
        return mock_llm

    monkeypatch.setattr("ats_agent.graph.nodes.get_chat_model", mock_get_model)

    # We need to mock the node function in builder.py before build_graph is called
    # because build_graph captures the function references.
    def mock_error_node(state):
        return state

    monkeypatch.setattr("ats_agent.graph.builder.unrecoverable_error_node", mock_error_node)

    graph = build_graph()

    # Run graph with minimal inputs
    state = {
        "resume_path": "input/resume_1.pdf",
        "jd_path": "data/jd.txt",
        "resume_text": "Dummy resume text",
        "jd_text": "Dummy JD text"
    }

    monkeypatch.setattr("ats_agent.graph.nodes.load_inputs_node", lambda s: {})

    result = graph.invoke(state)

    # Check that it tried EXTRACTION_MAX_RETRIES times per node
    assert mock_llm.invoke.call_count == EXTRACTION_MAX_RETRIES * 2

    # Check that error fields are set
    assert "jd_extraction_error" in result
    assert "resume_extraction_error" in result
    assert "LLM API Failure" in result["jd_extraction_error"]
    assert "LLM API Failure" in result["resume_extraction_error"]

def test_extraction_success_after_retry(monkeypatch):
    """Verify that extraction succeeds if a retry eventually works."""
    # Mock LLM to fail once then succeed
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = [
        RuntimeError("Temporary failure"),
        MagicMock(content='{"skills": [], "keywords": [], "responsibilities": [], "experience_min": 0, "experience_max": 0}')
    ]

    def mock_get_model():
        return mock_llm

    monkeypatch.setattr("ats_agent.graph.nodes.get_chat_model", mock_get_model)

    from ats_agent.graph.nodes import extract_job_description_requirements
    state = {
        "resume_text": "Dummy resume text",
        "jd_text": "Dummy JD text"
    }

    res = extract_job_description_requirements(state)

    assert "jd_requirements" in res
    assert "jd_extraction_error" not in res
    assert mock_llm.invoke.call_count == 2
