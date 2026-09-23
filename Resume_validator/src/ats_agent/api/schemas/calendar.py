
from datetime import date, datetime, time

from pydantic import BaseModel, Field, model_validator


class AvailabilityCreate(BaseModel):
    recruiter_id: str
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    active: bool = True

    @model_validator(mode="after")
    def validate_times(self):
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time.")
        return self


class AvailabilityUpdate(BaseModel):
    start_time: time | None = None
    end_time: time | None = None
    active: bool | None = None


class CalendarBlockCreate(BaseModel):
    recruiter_id: str
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    reason: str | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.start_at >= self.end_at:
            raise ValueError("Block end must be after its start.")
        return self


class FullDayBlockCreate(BaseModel):
    recruiter_id: str
    target_date: date
    reason: str | None = None


class AvailabilityRead(BaseModel):
    id: int | None
    recruiter_id: str
    day_of_week: int
    start_time: time
    end_time: time
    active: bool


class CalendarBlockRead(BaseModel):
    id: int | None
    recruiter_id: str
    start_at: datetime
    end_at: datetime
    all_day: bool
    reason: str | None


class AvailableSlot(BaseModel):
    start: datetime
    end: datetime


class AvailableSlotsResponse(BaseModel):
    recruiter_id: str
    target_date: date
    duration_minutes: int
    slots: list[AvailableSlot]