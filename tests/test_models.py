"""Tests for multicalcli.models."""

from datetime import datetime, timedelta, timezone

from multicalcli.models import Calendar, Event


class TestEvent:
    def _make_event(self, **kwargs) -> Event:
        defaults = {
            "id": "test-1",
            "summary": "Test Event",
            "start": datetime(2026, 3, 17, 10, 0, tzinfo=timezone.utc),
            "end": datetime(2026, 3, 17, 11, 0, tzinfo=timezone.utc),
            "account_name": "test",
            "calendar_id": "primary",
        }
        defaults.update(kwargs)
        return Event(**defaults)

    def test_duration_minutes(self):
        event = self._make_event()
        assert event.duration_minutes == 60

    def test_duration_minutes_30min(self):
        event = self._make_event(
            end=datetime(2026, 3, 17, 10, 30, tzinfo=timezone.utc),
        )
        assert event.duration_minutes == 30

    def test_is_multiday_false(self):
        event = self._make_event()
        assert event.is_multiday is False

    def test_is_multiday_true(self):
        event = self._make_event(
            end=datetime(2026, 3, 18, 11, 0, tzinfo=timezone.utc),
        )
        assert event.is_multiday is True

    def test_default_fields(self):
        event = self._make_event()
        assert event.location == ""
        assert event.all_day is False
        assert event.attendees == []
        assert event.calendar_name == ""

    def test_all_day_event(self):
        event = self._make_event(all_day=True)
        assert event.all_day is True


class TestCalendar:
    def test_creation(self):
        cal = Calendar(
            id="cal-1",
            summary="My Calendar",
            access_role="owner",
            account_name="test",
        )
        assert cal.summary == "My Calendar"
        assert cal.time_zone == ""
        assert cal.color_id == ""
