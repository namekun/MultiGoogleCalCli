"""Data models for multicalcli."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Calendar:
    """Google Calendar 캘린더 메타데이터."""
    id: str                  # 캘린더 고유 ID (이메일 형태)
    summary: str             # 표시 이름 (summaryOverride 우선)
    access_role: str         # owner / writer / reader / freeBusyReader
    account_name: str        # 소속 계정 이름
    time_zone: str = ""
    color_id: str = ""


@dataclass
class Event:
    """Google Calendar 이벤트."""
    id: str
    summary: str             # 일정 제목
    start: datetime          # 시작 시간 (KST)
    end: datetime            # 종료 시간 (KST)
    account_name: str        # 소속 계정 이름
    calendar_id: str         # 소속 캘린더 ID
    calendar_name: str = ""  # 소속 캘린더 표시 이름
    location: str = ""
    description: str = ""
    all_day: bool = False    # 종일 이벤트 여부
    html_link: str = ""      # Google Calendar 웹 링크
    hangout_link: str = ""   # Google Meet 링크
    attendees: list[str] = field(default_factory=list)
    color_id: str = ""
    status: str = ""

    @property
    def duration_minutes(self) -> int:
        """일정 길이(분)."""
        return int((self.end - self.start).total_seconds() / 60)

    @property
    def is_multiday(self) -> bool:
        """여러 날에 걸친 일정인지 여부."""
        return self.start.date() != self.end.date()
