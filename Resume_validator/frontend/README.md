# Recruiter Console — frontend

A job-centric recruiter dashboard for the ATS agent: browse open jobs, run bulk
evaluation, work an applicant pipeline board (Shortlisted / Needs Review / On
Hold / Rejected), open a candidate's evaluation detail, and act on it. A
"Quick evaluate" page keeps the original single-resume flow (`POST
/candidates`) working as a standalone utility.

## Setup

```bash
npm install
cp .env.example .env   # adjust VITE_API_BASE_URL if needed
npm run dev
```

Requires the FastAPI backend (`ats_agent.api.main:app`) running, by default at
`http://localhost:8000`.

## Before this will work: two backend changes are needed

The frontend was built against the routes and schemas exactly as they exist in
`src/ats_agent/api/` today. Two gaps on the backend side will block or limit it:

**1. CORS is not enabled.** `api/main.py` has no `CORSMiddleware`, so the
browser will block every request from `http://localhost:5173`. Add:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**2. `ApplicationRead` doesn't expose evaluation evidence.** The `Application`
table already stores `score_breakdown`, `matched_skills`, `missing_skills`,
`strengths`, `gaps`, `responsibilities_matched`, `responsibilities_missing`,
`experience_result`, and `recruiter_comments`, but
`api/schemas/applications.py`'s `ApplicationRead` only returns a handful of
top-level fields, so `GET /applications/{id}` can't show the reasoning behind
a score. The application detail panel reads all of these fields defensively
and shows a note when they're missing — add them to `ApplicationRead` to light
it up:

```python
class ApplicationRead(BaseModel):
    application_id: str
    candidate_name: str
    candidate_email: str
    pipeline_stage: PipelineStage
    overall_score: Optional[float] = None
    evaluation_status: EvaluationStatus
    evaluation_verdict: Optional[str] = None
    resume_path: str
    score_breakdown: Optional[str] = None
    matched_skills: Optional[str] = None
    missing_skills: Optional[str] = None
    strengths: Optional[str] = None
    gaps: Optional[str] = None
    responsibilities_matched: Optional[str] = None
    responsibilities_missing: Optional[str] = None
    experience_result: Optional[str] = None
    recruiter_comments: Optional[str] = None

    class Config:
        from_attributes = True
```

Neither change was made in this delivery since it was scoped to the frontend
— but without them the dashboard will either fail every request (CORS) or
show empty evidence sections (schema).

## What's intentionally not here

- **Create job / apply to job.** There's no `POST /jobs` or "create
  application" endpoint on the backend, so there's no UI for either — jobs
  and applications still need to be seeded directly in the database.
- **Real interview scheduling and follow-up delivery.** The corresponding
  routes (`/applications/{id}/interview-slots`, `/interview`,
  `/follow-up/approve`, `/follow-up/reply`) are backend stubs that return a
  placeholder response. The detail panel calls them and shows whatever they
  return, so the UI is ready the moment they're implemented for real.

## Structure

```
src/
  api/            axios calls, one file per backend router
  components/     shared UI (AppShell, ApplicationDetailPanel, Primitives, Toast)
  pages/          JobsListPage, JobDetailPage, QuickEvaluatePage
  types/          TypeScript mirrors of the backend Pydantic/SQLModel schemas
  lib/format.ts   safe parsing for the JSON-encoded-string fields on Application
```
