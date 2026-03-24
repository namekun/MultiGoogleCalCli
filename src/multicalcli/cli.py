"""CLI entry point for multicalcli."""

import calendar as cal_mod
from datetime import date, datetime, timedelta, timezone

import click
import parsedatetime
from rich.table import Table

from . import config
from .accounts import add_account, list_accounts, reauth_account, remove_account
from .api import add_event, delete_event, get_all_events, list_calendars, quick_add, search_events
from .display import console, print_agenda, print_calendars, print_month, print_week

# 자연어 날짜 파싱용 인스턴스 (모듈 로드 시 1회 생성)
_pdt_calendar = parsedatetime.Calendar()


def _parse_natural_date(text: str, source_time: datetime | None = None) -> datetime:
    """Parse natural language date string into a UTC datetime."""
    if source_time is None:
        source_time = datetime.now(timezone.utc)
    result, _ = _pdt_calendar.parseDT(text, sourceTime=source_time)
    return result.replace(tzinfo=timezone.utc)


def _resolve_accounts(account: str | None) -> list[str]:
    """Resolve account name(s) to use."""
    if account:
        names = config.list_account_names()
        if account not in names:
            console.print(f"[red]Error:[/red] Account '{account}' not found.")
            raise SystemExit(1)
        return [account]
    return config.list_account_names()


def _require_account(account: str | None) -> str:
    """Require a specific account for write operations."""
    if account:
        return account
    cfg = config.load_config()
    default = cfg.get("default_account")
    if default:
        return default
    console.print("[red]Error:[/red] Specify --account or set a default account.")
    raise SystemExit(1)


@click.group()
@click.version_option(package_name="multicalcli")
def main():
    """multicalcli - Multi-account Google Calendar CLI."""
    pass


# ── Account management ──────────────────────────────────────

@main.group()
def account():
    """Manage Google Calendar accounts."""
    pass


@account.command("add")
@click.argument("name")
def account_add(name: str):
    """Add a new Google account. Opens browser for OAuth login."""
    client_secret = config.get_client_secret()
    if not client_secret:
        console.print(
            f"[red]Error:[/red] OAuth client secret not found.\n"
            f"Copy your client_secret.json to: {config.CLIENT_SECRET_FILE}"
        )
        raise SystemExit(1)

    console.print(f"Adding account [cyan]{name}[/cyan]...")
    console.print("Browser will open for Google login.")

    try:
        email = add_account(name)
        console.print(
            f"[green]Success![/green] Account [cyan]{name}[/cyan] "
            f"linked to [yellow]{email}[/yellow]"
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@account.command("remove")
@click.argument("name")
@click.confirmation_option(prompt="Are you sure you want to remove this account?")
def account_remove(name: str):
    """Remove a registered account."""
    try:
        remove_account(name)
        console.print(f"[green]Removed[/green] account [cyan]{name}[/cyan]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@account.command("reauth")
@click.argument("name")
def account_reauth(name: str):
    """Re-authenticate an existing account. Opens browser for OAuth login."""
    console.print(f"Re-authenticating account [cyan]{name}[/cyan]...")
    console.print("Browser will open for Google login.")

    try:
        email = reauth_account(name)
        console.print(
            f"[green]Success![/green] Account [cyan]{name}[/cyan] "
            f"re-authenticated as [yellow]{email}[/yellow]"
        )
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@account.command("list")
def account_list():
    """List all registered accounts."""
    accounts = list_accounts()
    if not accounts:
        console.print(
            "[dim]No accounts registered. "
            "Use [cyan]mcli account add <name>[/cyan] to add one.[/dim]"
        )
        return

    table = Table(title="Registered Accounts")
    table.add_column("Name", style="cyan")
    table.add_column("Default", style="green")

    for acc in accounts:
        default_mark = "*" if acc["default"] else ""
        table.add_row(acc["name"], default_mark)

    console.print(table)


# ── Calendar list ───────────────────────────────────────────

@main.command("list")
@click.option("-a", "--account", default=None, help="Filter by account name")
@click.option("-c", "--calendar", "calendar_filter", multiple=True, help="Filter by calendar name (substring match, repeatable)")
def calendar_list(account: str | None, calendar_filter: tuple[str, ...]):
    """List calendars from all accounts."""
    accounts = _resolve_accounts(account)
    all_cals = []
    for name in accounts:
        try:
            all_cals.extend(list_calendars(name))
        except Exception as e:
            console.print(f"[red]Error ({name}):[/red] {e}")

    # 캘린더 이름 부분 문자열 필터 (대소문자 무시, OR 조건)
    if calendar_filter:
        all_cals = [
            cal for cal in all_cals
            if any(f.lower() in cal.summary.lower() for f in calendar_filter)
        ]

    print_calendars(all_cals)


# ── Agenda ──────────────────────────────────────────────────

@main.command()
@click.argument("start", default=None, required=False)
@click.argument("end", default=None, required=False)
@click.option("-a", "--account", default=None, help="Filter by account name")
@click.option("-c", "--calendar", "calendar_filter", multiple=True, help="Filter by calendar name (substring match, repeatable)")
def agenda(start: str | None, end: str | None, account: str | None, calendar_filter: tuple[str, ...]):
    """Show upcoming events (default: next 5 days)."""
    now = datetime.now(timezone.utc)

    time_min = _parse_natural_date(start, now) if start else now
    time_max = _parse_natural_date(end, now) if end else time_min + timedelta(days=5)

    accounts = _resolve_accounts(account)
    cal_filter = list(calendar_filter) if calendar_filter else None
    events = get_all_events(accounts, time_min=time_min, time_max=time_max, calendar_filter=cal_filter)
    print_agenda(events)


# ── Week view ───────────────────────────────────────────────

@main.command()
@click.argument("weeks", default=1, type=int, required=False)
@click.option("-a", "--account", default=None, help="Filter by account name")
@click.option("-c", "--calendar", "calendar_filter", multiple=True, help="Filter by calendar name (substring match, repeatable)")
def week(weeks: int, account: str | None, calendar_filter: tuple[str, ...]):
    """Show weekly calendar grid."""
    now = datetime.now(timezone.utc)
    time_max = now + timedelta(weeks=weeks)

    accounts = _resolve_accounts(account)
    cal_filter = list(calendar_filter) if calendar_filter else None
    events = get_all_events(accounts, time_min=now, time_max=time_max, calendar_filter=cal_filter)
    print_week(events, weeks=weeks)


# ── Month view ──────────────────────────────────────────────

@main.command()
@click.option("-a", "--account", default=None, help="Filter by account name")
@click.option("-c", "--calendar", "calendar_filter", multiple=True, help="Filter by calendar name (substring match, repeatable)")
def month(account: str | None, calendar_filter: tuple[str, ...]):
    """Show monthly calendar grid."""
    today = date.today()
    _, last_day = cal_mod.monthrange(today.year, today.month)

    time_min = datetime(today.year, today.month, 1, tzinfo=timezone.utc)
    time_max = datetime(today.year, today.month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    accounts = _resolve_accounts(account)
    cal_filter = list(calendar_filter) if calendar_filter else None
    events = get_all_events(accounts, time_min=time_min, time_max=time_max, calendar_filter=cal_filter)
    print_month(events)


# ── Quick add ───────────────────────────────────────────────

@main.command()
@click.argument("text")
@click.option("-a", "--account", default=None, help="Account to add event to")
def quick(text: str, account: str | None):
    """Quick-add event using natural language."""
    name = _require_account(account)
    console.print(f"Adding to [cyan]{name}[/cyan]: {text}")

    try:
        event = quick_add(name, text)
        console.print(
            f"[green]Created:[/green] {event.summary}\n"
            f"  [dim]{event.start.strftime('%Y-%m-%d %H:%M')} - "
            f"{event.end.strftime('%H:%M')}[/dim]"
        )
        if event.html_link:
            console.print(f"  [dim]{event.html_link}[/dim]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ── Add event ───────────────────────────────────────────────

@main.command()
@click.option("--title", "-t", required=True, help="Event title")
@click.option("--when", "-w", required=True, help="Start time (natural language)")
@click.option("--duration", "-d", default=60, type=int, help="Duration in minutes")
@click.option("--end-time", default=None, help="End time (overrides duration)")
@click.option("--where", default="", help="Location")
@click.option("--description", default="", help="Description")
@click.option("--who", multiple=True, help="Attendee email (repeatable)")
@click.option("--allday", is_flag=True, help="All-day event")
@click.option("-a", "--account", default=None, help="Account to add event to")
def add(title, when, duration, end_time, where, description, who, allday, account):
    """Add a new event."""
    name = _require_account(account)
    now = datetime.now(timezone.utc)

    start = _parse_natural_date(when, now)
    end = _parse_natural_date(end_time, now) if end_time else start + timedelta(minutes=duration)

    try:
        event = add_event(
            name, title, start, end,
            location=where,
            description=description,
            attendees=list(who) if who else None,
            all_day=allday,
        )
        console.print(
            f"[green]Created:[/green] {event.summary}\n"
            f"  [dim]{event.start.strftime('%Y-%m-%d %H:%M')} - "
            f"{event.end.strftime('%H:%M')}[/dim]"
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ── Search ──────────────────────────────────────────────────

@main.command()
@click.argument("text")
@click.option("-a", "--account", default=None, help="Filter by account name")
@click.option("-c", "--calendar", "calendar_filter", multiple=True, help="Filter by calendar name (substring match, repeatable)")
def search(text: str, account: str | None, calendar_filter: tuple[str, ...]):
    """Search events across all accounts."""
    accounts = _resolve_accounts(account)
    cal_filter = list(calendar_filter) if calendar_filter else None
    events = search_events(text, account_names=accounts, calendar_filter=cal_filter)
    if not events:
        console.print(f"[dim]No events matching '{text}'[/dim]")
        return
    print_agenda(events)


# ── Delete ──────────────────────────────────────────────────

@main.command()
@click.argument("text")
@click.option("-a", "--account", default=None, help="Account to delete from")
def delete(text: str, account: str | None):
    """Search and delete an event."""
    name = _require_account(account)
    events = search_events(text, account_names=[name])

    if not events:
        console.print(f"[dim]No events matching '{text}'[/dim]")
        return

    # Show matches
    for i, evt in enumerate(events):
        console.print(
            f"  [{i+1}] {evt.start.strftime('%Y-%m-%d %H:%M')} "
            f"- {evt.summary} ({evt.calendar_name})"
        )

    choice = click.prompt("Delete which event? (number, or 0 to cancel)", type=int, default=0)
    if choice == 0 or choice > len(events):
        console.print("[dim]Cancelled.[/dim]")
        return

    evt = events[choice - 1]
    if click.confirm(f"Delete '{evt.summary}'?"):
        try:
            delete_event(name, evt.id, calendar_id=evt.calendar_id)
            console.print(f"[green]Deleted:[/green] {evt.summary}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise SystemExit(1)
