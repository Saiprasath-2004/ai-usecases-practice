# ATS Recruiter Frontend — Phase 1

React frontend for the existing FastAPI + LangGraph ATS backend. It is a direct client: no mock data, no
invented endpoints, no scoring or matching logic in the browser.

## Run

```bash
npm install
cp .env.example .env      # VITE_API_BASE_URL=http://localhost:8000
npm run dev               # http://localhost:5173
npm run build             # tsc -b && vite build
npm run lint
```

The backend must allow the dev origin (`FRONTEND_ORIGINS`, default `http://localhost:5173`).

## What Phase 1 changed

**Recruiter Review** (route stays `/human-review`) replaces "Human Review" everywhere: sidebar, page title,
breadcrumbs, dashboard/job-page links. Inside a candidate the decision area is titled **Recruiter's Decision**.
The page lists evaluated candidates needing a decision, with filters All / Needs Review / Shortlisted / Follow-up.

**Candidate page** (`/applications/:id`) is built around the decision, in this order: header → score + pipeline
status → recruiter actions → AI Evaluation Summary → Score Breakdown → Skills → Responsibilities → Experience →
Strengths → Areas to Clarify → Follow-up → Interview → Resume.

- Actions: **Schedule Interview** (primary), **Get More Details** (secondary), **Hold** / **Move to Review**
  (pipeline), **Reject** (destructive, confirmed). "Confirm Rejection" is not shown.
- Score is the visual anchor; component scores are points out of their weights (Skills 60, Experience 25,
  Responsibilities 10, Keywords 5) — see `SCORE_WEIGHTS` in `src/lib/format.ts`.
- Skills render as compact chips (matched vs needs clarification); responsibilities as wrapping list rows.
- **Areas to Clarify** lists missing skills/responsibilities and has "Ask candidate about these", which opens
  Get More Details pre-filled.
- The AI score is always labelled as evidence, never a decision. The review flow (AI evaluated → evidence shown →
  you review → you decide) is shown at the top of the page.

**Strengths bug fixed.** The API stores `strengths` and `gaps` as JSON objects shaped
`{ skills: [], keywords: [], responsibilities: [] }`. The old parser returned the object's keys, so the UI showed
"skills / keywords / responsibilities". `asList()` no longer returns object keys, and
`parseEvidenceGroups()` (in `src/lib/format.ts`) turns that shape into typed groups. Strengths are summarised from
the real matched data ("8 required skills matched"), with a clean empty state when there is none.

**Candidate counts.** Every page reads candidates through the same per-job query (`useJobApplications`) and the
same flattening (`src/lib/board.ts`), so Dashboard, Jobs and Job pages agree. A job whose candidates fail to
load shows an error with **Try again** instead of "0 candidates" / "Nothing evaluated yet"; the multi-job pages
keep their totals and show a "numbers may be incomplete" notice.

**Evaluation Results tab** shows the current snapshot per candidate: Candidate, Score, Evaluation Status,
Pipeline Stage, Experience, Skills, Action.

**Terminology.** Evaluation Status: Not Evaluated / Evaluating / Completed / Failed (API values Pending /
Running / Completed / Failed are mapped in `evaluationStatusLabel`). Pipeline Stage: Shortlisted / Needs Review /
On Hold / Rejected. Recruiter actions are kept separate from both.

**No implementation wording in the UI.** Error text goes through `src/lib/errors.ts`, which maps known server
messages to plain language and never shows raw exception text.

## How actions map to the API

| Action | Call |
|---|---|
| Schedule Interview | `POST /applications/{id}/review` with `decision: "Schedule Interview"` and the recruiter's free text in `comments` |
| Get More Details | `POST /applications/{id}/review` with `decision: "Get More Details"` |
| Hold | `POST /applications/{id}/hold` |
| Move to Review | `POST /applications/{id}/actions` with `MOVE_TO_REVIEW` (`/review` rejects that decision string) |
| Reject | `POST /applications/{id}/reject` |
| Record candidate reply | `POST /applications/{id}/followup-reply` |

## Known gaps in the API (shown to recruiters only as neutral empty states)

- The AI recommendation and narrative are only returned by `followup-reply`; elsewhere the AI Evaluation Summary
  shows counts derived from the stored evidence.
- No endpoint lists past evaluation runs, so only the current snapshot is shown.
- No endpoint lists interviews. Interviews scheduled from this app are remembered in the browser
  (`src/api/interviews.ts`); follow-up requests likewise (`src/api/followups.ts`). Replace these with real reads
  when the endpoints exist.
- `follow_up_status` is never written by the backend.
- Bulk evaluation has no progress endpoint; the job page polls until candidates settle.

## Layout

```
src/api/         one module per domain (jobs, applications, calendar, interviews, followups, …)
src/hooks/       useJobApplications (single source per job), useAllApplications (across jobs)
src/lib/         format (parsing, terminology, experience), board, errors
src/components/  evaluation/ (ScoreHero, ReviewFlow, EvaluationSections), review/, candidates/, calendar/, layout/
src/pages/       one file per route
```
