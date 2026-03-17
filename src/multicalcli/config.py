"""Configuration management for multicalcli."""

import json
import os
import re
from pathlib import Path

# 설정 디렉토리 경로 (MCLI_CONFIG_DIR 환경변수로 변경 가능)
CONFIG_DIR = Path(
    os.environ.get("MCLI_CONFIG_DIR", str(Path.home() / ".config" / "multicalcli"))
).expanduser()
ACCOUNTS_DIR = CONFIG_DIR / "accounts"
CONFIG_FILE = CONFIG_DIR / "config.json"
CLIENT_SECRET_FILE = CONFIG_DIR / "client_secret.json"  # 글로벌 OAuth 클라이언트 시크릿

DEFAULT_CONFIG = {
    "default_account": None,
    "display": {
        "military_time": True,      # 24시간제 표시
        "week_start_monday": True,   # 월요일 시작
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
    # 파일 권한 0o600: 소유자만 읽기/쓰기 (보안)
    fd = os.open(str(CONFIG_FILE), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, json.dumps(config, indent=2, ensure_ascii=False).encode())
    finally:
        os.close(fd)


def validate_account_name(name: str) -> str:
    """Validate account name to prevent path traversal."""
    # 경로 탐색 공격 방지: 영숫자, 하이픈, 언더스코어만 허용
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
    # resolve() 후 경로가 ACCOUNTS_DIR 밖이면 경로 탐색 공격으로 간주
    if not str(result).startswith(str(ACCOUNTS_DIR.resolve())):
        raise ValueError(f"Invalid account name '{name}'.")
    return result


def get_client_secret(account_name: str | None = None) -> dict | None:
    """Load OAuth client secret. Per-account first, then global fallback."""
    # 계정별 client_secret.json이 있으면 우선 사용 (서로 다른 GCP 프로젝트 지원)
    if account_name:
        account_secret = get_account_dir(account_name) / "client_secret.json"
        if account_secret.exists():
            return json.loads(account_secret.read_text())
    # 계정별 시크릿이 없으면 글로벌 시크릿으로 fallback
    if CLIENT_SECRET_FILE.exists():
        return json.loads(CLIENT_SECRET_FILE.read_text())
    return None


def list_account_names() -> list[str]:
    """List all registered account names."""
    ensure_dirs()
    # token.json이 있는 디렉토리만 유효한 계정으로 인식
    return sorted(
        d.name for d in ACCOUNTS_DIR.iterdir()
        if d.is_dir() and (d / "token.json").exists()
    )
