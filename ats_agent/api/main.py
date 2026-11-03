"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ats_agent.api.routes import applications, candidates, jobs
from ats_agent.persistence.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reuses the single canonical seeding implementation in routes/jobs.py
    # instead of duplicating the same logic here.
    db = Database()
    with db.get_session() as session:
        jobs.create_default_job_if_missing(session)
    yield


# Local-dev default: allow any origin (the bundled static frontend has no
# build step and may be served from any local port, or opened via file://).
# Set FRONTEND_ORIGINS to a comma-separated list of real origins in
# production and this will lock down automatically.
frontend_origins_env = os.getenv("FRONTEND_ORIGINS", "").strip()
allowed_origins = [o.strip() for o in frontend_origins_env.split(",") if o.strip()]
allow_all_origins = not allowed_origins

app = FastAPI(
    title="ATS Recruiter Agent API",
    description="API for automating resume evaluations with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else allowed_origins,
    allow_credentials=not allow_all_origins,  # can't combine "*" with credentials
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(candidates.router)
app.include_router(jobs.router)
app.include_router(applications.router)


@app.get("/")
def read_root():
    return {"message": "ATS Recruiter Agent API is online. Visit /docs for Swagger UI."}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
