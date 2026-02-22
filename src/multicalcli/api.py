"""Google Calendar API wrapper with multi-account support."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

from dateutil import parser as dateutil_parser
from dateutil import tz

KST = tz.gettz("Asia/Seoul")
from googleapiclient.discovery import build

from . import config
from .auth import load_credentials
from .models import Calendar, Event

_service_cache: dict[str, object] = {}


def get_service(account_name: str):
    """Get or create a Calendar API service for an account."""
    if account_name in _service_cache:
        return _service_cache[account_name]

    creds = load_credentials(account_name)
    if not creds:
        raise ValueError(
            f"No credentials for account '{account_name}'. "
            f"Run: mcli account add {account_name}"
        )

    service = build("calendar", "v3", credentials=creds)
    _service_cache[account_name] = service
    return service


def list_calendars(account_name: str) -> list[Calendar]:
    """List all calendars for an account."""
    service = get_service(account_name)
    calendars = []
    page_token = None

    while True:
        result = (
            service.calendarList()
            .list(pageToken=page_token)
            .execute()
        )
        for item in result.get("items", []):
            display_name = item.get("summaryOverride") or item.get("summary", item["id"])
            calendars.append(Calendar(
                id=item["id"],
                summary=display_name,
                access_role=item.get("accessRole", ""),
                account_name=account_name,
                time_zone=item.get("timeZone", ""),
                color_id=item.get("colorId", ""),
            ))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return calendars


def _parse_event_time(time_obj: dict) -> tuple[datetime, bool]:
    """Parse a Google Calendar time object. Returns (datetime, is_all_day) in KST."""
    if "date" in time_obj:
        dt = datetime.strptime(time_obj["date"], "%Y-%m-%d")
        return dt.replace(tzinfo=KST), True
    dt = dateutil_parser.parse(time_obj["dateTime"])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST), False


def get_events(
    account_name: str,
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    query: str | None = None,
    calendar_id: str = "primary",
) -> list[Event]:
    """Get events from a specific calendar."""
    service = get_service(account_name)

    if time_min is None:
        time_min = datetime.now(timezone.utc)
    if time_max is None:
        time_max = time_min + timedelta(days=5)

    # Get calendar name for display (prefer user's override name)
    cal_name = calendar_id
    try:
        cal_entry = service.calendarList().get(calendarId=calendar_id).execute()
        cal_name = cal_entry.get("summaryOverride") or cal_entry.get("summary", calendar_id)
    except Exception:
        try:
            cal_info = service.calendars().get(calendarId=calendar_id).execute()
            cal_name = cal_info.get("summary", calendar_id)
        except Exception:
            pass

    events = []
    page_token = None

    while True:
        params = {
            "calendarId": calendar_id,
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": True,
            "orderBy": "startTime",
            "pageToken": page_token,
        }
        if query:
            params["q"] = query

        result = service.events().list(**params).execute()

        for item in result.get("items", []):
            if item.get("status") == "cancelled":
                continue

            start_time, all_day = _parse_event_time(item.get("start", {}))
            end_time, _ = _parse_event_time(item.get("end", {}))

            attendee_emails = [
                a.get("email", "")
                for a in item.get("attendees", [])
            ]

            events.append(Event(
                id=item["id"],
                summary=item.get("summary", "(No title)"),
                start=start_time,
                end=end_time,
                account_name=account_name,
                calendar_id=calendar_id,
                calendar_name=cal_name,
                location=item.get("location", ""),
                description=item.get("description", ""),
                all_day=all_day,
                html_link=item.get("htmlLink", ""),
                hangout_link=item.get("hangoutLink", ""),
                attendees=attendee_emails,
                color_id=item.get("colorId", ""),
                status=item.get("status", ""),
            ))

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return events


def get_all_events(
    account_names: list[str] | None = None,
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    query: str | None = None,
    calendar_filter: list[str] | None = None,
) -> list[Event]:
    """Get events from all accounts in parallel, merged and sorted.

    Args:
        calendar_filter: List of calendar name substrings to include.
            Only calendars whose summary contains any of these strings
            (case-insensitive) will be queried. None means all calendars.
    """
    if account_names is None:
        account_names = config.list_account_names()

    if not account_names:
        return []

    all_events: list[Event] = []

    def _match_calendar(cal: Calendar) -> bool:
        """Check if calendar matches the filter."""
        if not calendar_filter:
            return True
        cal_lower = cal.summary.lower()
        return any(f.lower() in cal_lower for f in calendar_filter)

    def _fetch_account(name: str) -> list[Event]:
        calendars = list_calendars(name)
        events = []
        for cal in calendars:
            if cal.access_role in ("owner", "writer", "reader") and _match_calendar(cal):
                events.extend(get_events(
                    name,
                    time_min=time_min,
                    time_max=time_max,
                    query=query,
                    calendar_id=cal.id,
                ))
        return events

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(_fetch_account, name): name
            for name in account_names
        }
        for future in as_completed(futures):
            try:
                all_events.extend(future.result())
            except Exception as e:
                account = futures[future]
                all_events.append(Event(
                    id="error",
                    summary=f"[Error: {account}] {e}",
                    start=datetime.now(timezone.utc),
                    end=datetime.now(timezone.utc),
                    account_name=account,
                    calendar_id="",
                    status="error",
                ))

    all_events.sort(key=lambda e: e.start)
    return all_events


def quick_add(account_name: str, text: str, calendar_id: str = "primary") -> Event:
    """Quick-add an event using natural language."""
    service = get_service(account_name)
    result = service.events().quickAdd(
        calendarId=calendar_id,
        text=text,
    ).execute()

    start_time, all_day = _parse_event_time(result.get("start", {}))
    end_time, _ = _parse_event_time(result.get("end", {}))

    return Event(
        id=result["id"],
        summary=result.get("summary", text),
        start=start_time,
        end=end_time,
        account_name=account_name,
        calendar_id=calendar_id,
        all_day=all_day,
        html_link=result.get("htmlLink", ""),
    )


def add_event(
    account_name: str,
    title: str,
    start: datetime,
    end: datetime,
    calendar_id: str = "primary",
    location: str = "",
    description: str = "",
    attendees: list[str] | None = None,
    all_day: bool = False,
) -> Event:
    """Add a detailed event."""
    service = get_service(account_name)

    body: dict = {
        "summary": title,
    }
    if all_day:
        body["start"] = {"date": start.strftime("%Y-%m-%d")}
        body["end"] = {"date": end.strftime("%Y-%m-%d")}
    else:
        body["start"] = {"dateTime": start.isoformat()}
        body["end"] = {"dateTime": end.isoformat()}

    if location:
        body["location"] = location
    if description:
        body["description"] = description
    if attendees:
        body["attendees"] = [{"email": e} for e in attendees]

    result = service.events().insert(
        calendarId=calendar_id,
        body=body,
    ).execute()

    return Event(
        id=result["id"],
        summary=result.get("summary", title),
        start=start,
        end=end,
        account_name=account_name,
        calendar_id=calendar_id,
        location=location,
        description=description,
        all_day=all_day,
        html_link=result.get("htmlLink", ""),
    )


def delete_event(account_name: str, event_id: str, calendar_id: str = "primary"):
    """Delete an event."""
    service = get_service(account_name)
    service.events().delete(
        calendarId=calendar_id,
        eventId=event_id,
    ).execute()


def search_events(
    text: str,
    account_names: list[str] | None = None,
    time_min: datetime | None = None,
    time_max: datetime | None = None,
    calendar_filter: list[str] | None = None,
) -> list[Event]:
    """Search events across all accounts."""
    if time_min is None:
        time_min = datetime.now(timezone.utc) - timedelta(days=30)
    if time_max is None:
        time_max = datetime.now(timezone.utc) + timedelta(days=365)

    return get_all_events(
        account_names=account_names,
        time_min=time_min,
        time_max=time_max,
        query=text,
        calendar_filter=calendar_filter,
    )
