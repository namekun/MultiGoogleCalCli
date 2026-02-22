"""Rich-based terminal display for calendar data."""

from datetime import datetime, timedelta, date
from itertools import groupby

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .models import Calendar, Event

console = Console()

ACCOUNT_COLORS = [
    "cyan", "magenta", "green", "yellow", "blue",
    "red", "bright_cyan", "bright_magenta", "bright_green", "bright_yellow",
]

_color_map: dict[str, str] = {}


def _get_account_color(account_name: str) -> str:
    if account_name not in _color_map:
        idx = len(_color_map) % len(ACCOUNT_COLORS)
        _color_map[account_name] = ACCOUNT_COLORS[idx]
    return _color_map[account_name]


def print_calendars(calendars: list[Calendar]):
    """Print calendar list grouped by account."""
    table = Table(title="Calendars")
    table.add_column("Account", style="cyan")
    table.add_column("Access", style="dim")
    table.add_column("Calendar", style="white")

    for cal in calendars:
        color = _get_account_color(cal.account_name)
        table.add_row(
            f"[{color}]{cal.account_name}[/{color}]",
            cal.access_role,
            cal.summary,
        )

    console.print(table)


def print_agenda(events: list[Event], military: bool = True):
    """Print events as an agenda grouped by date."""
    if not events:
        console.print("[dim]No events found.[/dim]")
        return

    time_fmt = "%H:%M" if military else "%I:%M %p"

    grouped = groupby(events, key=lambda e: e.start.date())

    for day, day_events in grouped:
        day_str = day.strftime("%a %Y-%m-%d")
        console.print(f"\n[bold yellow]{day_str}[/bold yellow]")
        console.print("[dim]" + "─" * 60 + "[/dim]")

        for event in day_events:
            color = _get_account_color(event.account_name)
            account_tag = f"[{color}][{event.account_name}][/{color}]"

            if event.all_day:
                time_str = "  All Day "
            else:
                start = event.start.strftime(time_fmt)
                end = event.end.strftime(time_fmt)
                time_str = f"{start}-{end}"

            summary = event.summary
            if event.status == "error":
                summary = f"[red]{summary}[/red]"

            location_str = ""
            if event.location:
                location_str = f" [dim]@ {event.location}[/dim]"

            console.print(
                f"  [dim]{time_str}[/dim]  {summary}"
                f"  {account_tag}{location_str}"
            )


def print_week(events: list[Event], weeks: int = 1, start_date: date | None = None, monday_start: bool = True):
    """Print a week calendar grid view."""
    if start_date is None:
        start_date = date.today()

    # Align to week start
    weekday = start_date.weekday()  # 0=Monday
    if monday_start:
        start_date = start_date - timedelta(days=weekday)
    else:
        # Sunday start
        start_date = start_date - timedelta(days=(weekday + 1) % 7)

    total_days = weeks * 7

    for week_offset in range(weeks):
        week_start = start_date + timedelta(days=week_offset * 7)

        table = Table(show_header=True, expand=True, padding=(0, 1))

        # Add day columns
        days = []
        for d in range(7):
            day = week_start + timedelta(days=d)
            days.append(day)
            header = day.strftime("%a %m/%d")
            is_today = day == date.today()
            style = "bold bright_white on blue" if is_today else "bold"
            table.add_column(header, style=style if is_today else None, ratio=1)

        # Collect events per day
        day_events: dict[date, list[Event]] = {d: [] for d in days}
        for event in events:
            event_date = event.start.date()
            if event_date in day_events:
                day_events[event_date].append(event)

        # Find max events in any day for this week
        max_events = max((len(v) for v in day_events.values()), default=0)
        max_events = max(max_events, 1)

        for row_idx in range(max_events):
            row = []
            for day in days:
                evts = day_events[day]
                if row_idx < len(evts):
                    evt = evts[row_idx]
                    color = _get_account_color(evt.account_name)
                    if evt.all_day:
                        text = f"[{color}]■[/{color}] {evt.summary[:12]}"
                    else:
                        t = evt.start.strftime("%H:%M")
                        text = f"[{color}]■[/{color}] {t} {evt.summary[:10]}"
                    row.append(text)
                else:
                    row.append("")
            table.add_row(*row)

        console.print(table)


def print_month(events: list[Event], start_date: date | None = None, monday_start: bool = True):
    """Print a month calendar grid view."""
    if start_date is None:
        start_date = date.today().replace(day=1)

    import calendar as cal_mod
    year, month = start_date.year, start_date.month

    title = start_date.strftime("%B %Y")
    console.print(f"\n[bold]{title}[/bold]")

    # Build event lookup
    event_by_day: dict[int, list[Event]] = {}
    for event in events:
        d = event.start.date()
        if d.year == year and d.month == month:
            event_by_day.setdefault(d.day, []).append(event)

    table = Table(show_header=True, expand=True, padding=(0, 1))

    if monday_start:
        headers = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        first_weekday = 0
    else:
        headers = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        first_weekday = 6

    for h in headers:
        table.add_column(h, justify="center", ratio=1)

    c = cal_mod.Calendar(firstweekday=first_weekday)
    weeks = c.monthdayscalendar(year, month)

    today = date.today()

    for week in weeks:
        row = []
        for day_num in week:
            if day_num == 0:
                row.append("")
                continue

            d = date(year, month, day_num)
            is_today = d == today

            cell_parts = []
            if is_today:
                cell_parts.append(f"[bold bright_white on blue]{day_num:2d}[/bold bright_white on blue]")
            else:
                cell_parts.append(f"[bold]{day_num:2d}[/bold]")

            day_evts = event_by_day.get(day_num, [])
            for evt in day_evts[:3]:
                color = _get_account_color(evt.account_name)
                cell_parts.append(f"[{color}]·[/{color}]{evt.summary[:6]}")

            if len(day_evts) > 3:
                cell_parts.append(f"[dim]+{len(day_evts)-3}[/dim]")

            row.append("\n".join(cell_parts))

        table.add_row(*row)

    console.print(table)
