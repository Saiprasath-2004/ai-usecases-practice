# ATS Resume Evaluator

An evidence-based resume evaluation application built with LangGraph, FastAPI, and a recruiter dashboard frontend.

## Current project status

The current codebase is working for the tested backend core and the active frontend app:

- backend scoring, matching, persistence, and agent layer tests pass
- the frontend app compiles successfully with Vite
- the API is configured to allow requests from the Vite frontend

## Project layout

```text
src/ats_agent/
    api/          FastAPI routes and app entry point
    agent_layer/  decision, follow-up, review, actions, reporting
    domain/      SQLModel domain entities
    extraction/   Pydantic schemas for structured LLM output
    graph/        LangGraph state, nodes, and workflow builder
    ingestion/    Resume PDF and job-description readers
    llm/          Chat-model factory
    persistence/  database access
    scoring/      matching, normalization, and scores
frontend/       React + Vite recruiter console
examples/       manual LLM-driven workflows
input/          resume and sample files
data/           job-description input
tests/          deterministic unit tests
```

## Setup

```powershell
uv sync --extra dev
```

Create a `.env` file in the project root with at least:

```powershell
GROQ_API_KEY=your_key_here
```

## Run the backend

```powershell
Set-Location "C:\Users\User\Desktop\AI_usecase\Resume_validator"
$env:PYTHONPATH='.;src'
uv run uvicorn ats_agent.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API docs will be available at:

- http://localhost:8000/docs

The backend includes CORS support for the active frontend origin:

- http://localhost:5173
- http://127.0.0.1:5173

## Run the frontend

```powershell
Set-Location "C:\Users\User\Desktop\AI_usecase\Resume_validator\frontend"
npm install
npm run dev
```

Then open:

- http://localhost:5173

## Run the relevant tests

```powershell
Set-Location "C:\Users\User\Desktop\AI_usecase\Resume_validator"
$env:PYTHONPATH='.;src'
uv run python -m pytest tests/test_agent_layer.py tests/test_candidate_evaluation.py tests/test_embeddings.py tests/test_persistence.py
```

This is the currently verified working subset for the project.

## Notes

- The frontend is intentionally separate from the backend and talks to it through the configured Vite API base URL.
- Real LLM-based extraction still depends on a valid Groq key and live API access.
- A few broader integration tests remain outside this working baseline and can be addressed later if needed.
