from datetime import date, time

from pydantic import BaseModel, Field, field_validator


class SchedulingIntent(BaseModel):

    preferred_date: date | None = None

    date_range_start: date | None = None

    date_range_end: date | None = None

    preferred_weekdays: list[int] = Field(
        default_factory=list
    )

    preferred_time_start: str | None = None

    preferred_time_end: str | None = None

    duration_minutes: int = 60

    flexibility: str = "flexible"

    @field_validator(
        "preferred_time_start",
        "preferred_time_end",
    )
    @classmethod
    def validate_time(cls, value: str | None) -> str | None:
        if value is None:
            return None

        try:
            time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                "Time must use HH:MM or HH:MM:SS format."
            ) from exc

        return value

    def get_time_start(self) -> time | None:
        if self.preferred_time_start is None:
            return None

        return time.fromisoformat(
            self.preferred_time_start
        )

    def get_time_end(self) -> time | None:
        if self.preferred_time_end is None:
            return None

        return time.fromisoformat(
            self.preferred_time_end
        )