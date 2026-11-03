from pydantic import BaseModel, Field
from typing import List, Optional
from ats_agent.domain.models import PipelineStage

class JobRead(BaseModel):
    id: int
    title: str
    department: str
    location: str
    employment_type: str
    job_description_text: str
    job_description_source: str
    evaluation_status: str

    class Config:
        from_attributes = True

class JobCreate(BaseModel):
    title: str
    department: str
    location: str
    employment_type: str
    job_description_text: str
    job_description_source: str
    required_skills: Optional[str] = ""
