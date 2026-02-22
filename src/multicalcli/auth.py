"""Per-account OAuth authentication management."""

import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from . import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _token_path(account_name: str) -> Path:
    return config.get_account_dir(account_name) / "token.json"


def save_credentials(account_name: str, creds: Credentials):
    """Save credentials as JSON for an account."""
    token_path = _token_path(account_name)
    token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    fd = os.open(str(token_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(data, indent=2).encode())
    finally:
        os.close(fd)


def load_credentials(account_name: str) -> Credentials | None:
    """Load credentials from JSON, auto-refresh if expired."""
    token_path = _token_path(account_name)
    if not token_path.exists():
        return None

    data = json.loads(token_path.read_text())
    creds = Credentials(
        token=data["token"],
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", SCOPES),
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials(account_name, creds)

    return creds


def authenticate(account_name: str) -> Credentials:
    """Run OAuth flow for a new account. Opens browser for login."""
    client_config = config.get_client_secret(account_name)
    if not client_config:
        raise FileNotFoundError(
            f"OAuth client secret not found.\n"
            f"Place client_secret.json in:\n"
            f"  Per-account: {config.get_account_dir(account_name)}/client_secret.json\n"
            f"  Or global:   {config.CLIENT_SECRET_FILE}"
        )

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    save_credentials(account_name, creds)
    return creds


def remove_credentials(account_name: str):
    """Remove all credential files for an account."""
    account_dir = config.get_account_dir(account_name)
    if account_dir.exists():
        import shutil
        shutil.rmtree(account_dir)
