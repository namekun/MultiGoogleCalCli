"""CLI entry point for multicalcli."""

from datetime import datetime, timedelta, timezone

import click
from rich.console import Console
from rich.table import Table

console = Console()


def _resolve_accounts(account: str | None) -> list[str]:
    """Resolve account name(s) to use."""
    from . import config
    if account:
        names = config.list_account_names()
        if account not in names:
            console.print(f"[red]Error:[/red] Account '{account}' not found.")
            raise SystemExit(1)
        return [account]
    return config.list_account_names()


def _require_account(account: str | None) -> str:
    """Require a specific account for write operations."""
    from . import config
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
    from .accounts import add_account
    from . import config

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
    from .accounts import remove_account

    try:
        remove_account(name)
        console.print(f"[green]Removed[/green] account [cyan]{name}[/cyan]")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


@account.command("list")
def account_list():
    """List all registered accounts."""
    from .accounts import list_accounts

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
    from .api import list_calendars
    from .display import print_calendars

    accounts = _resolve_accounts(account)
    all_cals = []
    for name in accounts:
        try:
            all_cals.extend(list_calendars(name))
        except Exception as e:
            console.print(f"[red]Error ({name}):[/red] {e}")

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
    from .api import get_all_events
    from .display import print_agenda
    import parsedatetime

    cal = parsedatetime.Calendar()
    now = datetime.now(timezone.utc)

    if start:
        result, _ = cal.parseDT(start, sourceTime=now)
        time_min = result.replace(tzinfo=timezone.utc)
    else:
        time_min = now

    if end:
        result, _ = cal.parseDT(end, sourceTime=now)
        time_max = result.replace(tzinfo=timezone.utc)
    else:
        time_max = time_min + timedelta(days=5)

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
    from datetime import date
    from .api import get_all_events
    from .display import print_week

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
    from datetime import date
    from .api import get_all_events
    from .display import print_month

    today = date.today()
    first = today.replace(day=1)
    import calendar as cal_mod
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
    from .api import quick_add

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
    from .api import add_event
    import parsedatetime

    name = _require_account(account)
    cal = parsedatetime.Calendar()
    now = datetime.now(timezone.utc)

    result, _ = cal.parseDT(when, sourceTime=now)
    start = result.replace(tzinfo=timezone.utc)

    if end_time:
        result, _ = cal.parseDT(end_time, sourceTime=now)
        end = result.replace(tzinfo=timezone.utc)
    else:
        end = start + timedelta(minutes=duration)

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
    from .api import search_events
    from .display import print_agenda

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
    from .api import search_events, delete_event

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
