"""Account management operations."""

from . import auth, config


def add_account(name: str) -> str:
    """Add a new account via OAuth flow. Returns authenticated email."""
    account_dir = config.get_account_dir(name)
    if (account_dir / "token.json").exists():
        raise ValueError(f"Account '{name}' already exists. Remove it first.")

    creds = auth.authenticate(name)

    # Fetch the account email for display
    from googleapiclient.discovery import build
    service = build("calendar", "v3", credentials=creds)
    calendar = service.calendars().get(calendarId="primary").execute()
    email = calendar.get("id", "unknown")

    # Update global config if this is the first account
    cfg = config.load_config()
    if cfg["default_account"] is None:
        cfg["default_account"] = name
        config.save_config(cfg)

    return email


def remove_account(name: str):
    """Remove an account and its credentials."""
    if name not in config.list_account_names():
        raise ValueError(f"Account '{name}' not found.")

    auth.remove_credentials(name)

    # Update default if removed account was default
    cfg = config.load_config()
    if cfg["default_account"] == name:
        remaining = config.list_account_names()
        cfg["default_account"] = remaining[0] if remaining else None
        config.save_config(cfg)


def list_accounts() -> list[dict]:
    """List all registered accounts with details."""
    names = config.list_account_names()
    cfg = config.load_config()
    accounts = []
    for name in names:
        accounts.append({
            "name": name,
            "default": name == cfg.get("default_account"),
        })
    return accounts
