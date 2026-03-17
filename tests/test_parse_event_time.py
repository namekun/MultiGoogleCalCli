"""Tests for multicalcli.api._parse_event_time."""

from datetime import datetime, timezone

from dateutil import tz

from multicalcli.api import _parse_event_time, KST


class TestParseEventTime:
    def test_all_day_event(self):
        dt, is_all_day = _parse_event_time({"date": "2026-03-17"})
        assert is_all_day is True
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 17
        assert dt.tzinfo == KST

    def test_datetime_with_timezone(self):
        dt, is_all_day = _parse_event_time(
            {"dateTime": "2026-03-17T10:00:00+09:00"}
        )
        assert is_all_day is False
        assert dt.tzinfo is not None
        # Should be converted to KST
        assert dt.hour == 10

    def test_datetime_utc(self):
        dt, is_all_day = _parse_event_time(
            {"dateTime": "2026-03-17T01:00:00Z"}
        )
        assert is_all_day is False
        # UTC 01:00 -> KST 10:00
        assert dt.hour == 10

    def test_datetime_without_timezone_assumes_utc(self):
        dt, is_all_day = _parse_event_time(
            {"dateTime": "2026-03-17T01:00:00"}
        )
        assert is_all_day is False
        # No tz -> assumed UTC -> KST 10:00
        assert dt.hour == 10
