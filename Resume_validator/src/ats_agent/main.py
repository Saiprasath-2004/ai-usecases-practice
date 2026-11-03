

"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ats_agent.api.routes import applications, jobs, calendar

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""

    yield


# ============================================================
# CORS
# ============================================================

default_origins = (
    "http://localhost:5173,"
    "http://127.0.0.1:5173"
)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        default_origins,
    ).split(",")
    if origin.strip()
]


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="ATS Recruiter Agent API",
    description=(
        "API for recruiter-driven ATS evaluation "
        "using LangGraph."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# Middleware
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# API Routers
# ============================================================

app.include_router(
    jobs.router
)
app.include_router(
    applications.router
)
app.include_router(calendar.router)

# ============================================================
# Health / Root
# ============================================================

@app.get("/")
def read_root():
    """Basic API health response."""

    return {
        "message": "ATS Recruiter Agent API is online.",
        "docs": "/docs",
    }


# ============================================================
# Development Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "ats_agent.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )