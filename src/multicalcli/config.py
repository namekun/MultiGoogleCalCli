"""Configuration management for multicalcli."""

import json
import os
import re
from pathlib import Path

CONFIG_DIR = Path(
    os.environ.get("MCLI_CONFIG_DIR", str(Path.home() / ".config" / "multicalcli"))
).expanduser()
ACCOUNTS_DIR = CONFIG_DIR / "accounts"
CONFIG_FILE = CONFIG_DIR / "config.json"
CLIENT_SECRET_FILE = CONFIG_DIR / "client_secret.json"

DEFAULT_CONFIG = {
    "default_account": None,
    "display": {
        "military_time": True,
        "week_start_monday": True,
    },
}


def ensure_dirs():
    """Create config directories if they don't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)


def load_config() -> dict:
    """Load global config, creating defaults if needed."""
    ensure_dirs()
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    """Save global config to disk."""
    ensure_dirs()
    fd = os.open(str(CONFIG_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(config, indent=2, ensure_ascii=False).encode())
    finally:
        os.close(fd)


def validate_account_name(name: str) -> str:
    """Validate account name to prevent path traversal."""
    if not re.match(r'^[a-zA-Z0-9_\-]+$', name):
        raise ValueError(
            f"Invalid account name '{name}'. "
            "Use only letters, numbers, hyphens, and underscores."
        )
    return name


def get_account_dir(name: str) -> Path:
    """Get the directory for a specific account."""
    validate_account_name(name)
    result = (ACCOUNTS_DIR / name).resolve()
    if not str(result).startswith(str(ACCOUNTS_DIR.resolve())):
        raise ValueError(f"Invalid account name '{name}'.")
    return result


def get_client_secret(account_name: str | None = None) -> dict | None:
    """Load OAuth client secret. Per-account first, then global fallback."""
    if account_name:
        account_secret = get_account_dir(account_name) / "client_secret.json"
        if account_secret.exists():
            return json.loads(account_secret.read_text())
    if CLIENT_SECRET_FILE.exists():
        return json.loads(CLIENT_SECRET_FILE.read_text())
    return None


def list_account_names() -> list[str]:
    """List all registered account names."""
    ensure_dirs()
    return sorted(
        d.name for d in ACCOUNTS_DIR.iterdir()
        if d.is_dir() and (d / "token.json").exists()
    )
