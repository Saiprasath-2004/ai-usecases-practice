# ATS Resume Evaluator

An evidence-based resume evaluation application built with LangGraph, Chroma, and OpenRouter.

## Project layout

```text
src/ats_agent/
	extraction/   Pydantic schemas for structured LLM output
	graph/        LangGraph state, nodes, and workflow builder
	ingestion/    Resume PDF and job-description readers
	llm/          Chat-model factory
	rag/          Embeddings, chunking, and Chroma persistence
	scoring/      Matching, normalization, and weighted scoring
tests/          Deterministic unit tests
examples/       Manual workflows that call the LLM
data/           Job-description input
input/          Resume input
vectorstore/   Persisted Chroma data
```

## Setup

```powershell
uv sync --extra dev
```

Set `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` in `.env`, then run:

```powershell
uv run pytest
uv run ats-evaluate
```

The live extraction examples are intentionally separate from the unit test suite:

```powershell
$env:PYTHONPATH = "src"
python examples/extract_resume_profile.py
```
