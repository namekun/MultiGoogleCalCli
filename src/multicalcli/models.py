"""Data models for multicalcli."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Calendar:
    id: str
    summary: str
    access_role: str
    account_name: str
    time_zone: str = ""
    color_id: str = ""


@dataclass
class Event:
    id: str
    summary: str
    start: datetime
    end: datetime
    account_name: str
    calendar_id: str
    calendar_name: str = ""
    location: str = ""
    description: str = ""
    all_day: bool = False
    html_link: str = ""
    hangout_link: str = ""
    attendees: list[str] = field(default_factory=list)
    color_id: str = ""
    status: str = ""

    @property
    def duration_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() / 60)

    @property
    def is_multiday(self) -> bool:
        return self.start.date() != self.end.date()
