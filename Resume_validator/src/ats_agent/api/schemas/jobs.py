"""Pydantic schemas for job requisition API endpoints."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class JobRead(BaseModel):
    """Response schema for a job requisition."""

    id: int
    title: str
    department: str
    location: str
    employment_type: str
    job_description_text: str
    job_description_source: str
    required_skills: str
    evaluation_status: str

    model_config = ConfigDict(
        from_attributes=True
    )


class JobCreate(BaseModel):
    """Request schema for creating a job requisition."""

    title: str
    department: str
    location: str
    employment_type: str
    job_description_text: str
    job_description_source: str
    required_skills: Optional[str] = ""