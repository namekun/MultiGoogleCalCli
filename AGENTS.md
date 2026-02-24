# multicalcli - Codebase Guide

A multi-account Google Calendar CLI replacement for gcalcli. Uses per-account independent OAuth tokens to aggregate and manage events across multiple Google accounts.

## Architecture Overview

```
CLI (click)  →  API (google-api-python-client)  →  Google Calendar API v3
    ↓                    ↑
 display (rich)    auth (google-auth-oauthlib)
    ↓                    ↑
 models          config (~/.config/multicalcli/)
```

**Entry point:** `mcli` → `multicalcli.cli:main`

## File Map

| File | Role | Key Functions/Classes |
|------|------|----------------------|
| `cli.py` | Click CLI command group | `main()`, `agenda()`, `week()`, `month()`, `quick()`, `add()`, `search()`, `delete()` |
| `api.py` | Google Calendar API wrapper | `get_all_events()`, `get_events()`, `list_calendars()`, `quick_add()`, `add_event()`, `delete_event()`, `search_events()` |
| `auth.py` | Per-account OAuth authentication | `authenticate()`, `load_credentials()`, `save_credentials()` |
| `config.py` | Config directory/file management | `CONFIG_DIR`, `get_client_secret()`, `list_account_names()` |
| `models.py` | Data models | `Calendar`, `Event` (dataclass) |
| `display.py` | Rich terminal output | `print_agenda()`, `print_week()`, `print_month()`, `print_calendars()` |
| `accounts.py` | Account CRUD orchestration | `add_account()`, `remove_account()`, `list_accounts()` |

## Data Directory

```
~/.config/multicalcli/          # Configurable via MCLI_CONFIG_DIR env var
├── config.json                 # default_account, display settings
├── client_secret.json          # Global OAuth client
└── accounts/
    ├── work/
    │   └── token.json          # OAuth token (JSON, not pickle)
    └── personal/
        ├── client_secret.json  # Account-specific OAuth client
        └── token.json
```

- `get_client_secret(account_name)`: Prefers account-level `client_secret.json`, falls back to global
- Tokens are JSON-serialized (`token`, `refresh_token`, `token_uri`, `client_id`, `client_secret`, `scopes`)
- Expired tokens are automatically refreshed in `load_credentials()`

## Key Design Decisions

### 1. summaryOverride Priority
The Google Calendar API `calendarList` response includes both `summary` (original name) and `summaryOverride` (user-renamed). **`summaryOverride` takes priority when present**, so names changed by the user in Google Calendar web are displayed as-is.

### 2. Multi-Account Parallel Fetching
`get_all_events()` uses `ThreadPoolExecutor(max_workers=5)` to query multiple accounts concurrently, then sorts results chronologically.

### 3. KST Timezone
All event times are converted to KST via `dateutil.tz.gettz("Asia/Seoul")` before display. All-day events also receive KST tzinfo to prevent naive/aware datetime comparison errors.

### 4. Filtering System
- `-a` / `--account`: Account-level filter (exact match)
- `-c` / `--calendar`: Calendar name filter (substring, case-insensitive, OR condition)
- Calendar filters are applied **before** API calls to reduce unnecessary network requests

### 5. Per-Account client_secret
When different Google Cloud project OAuth clients are needed, placing a `client_secret.json` in the account directory makes it used for that account's authentication.

## CLI Commands

```
mcli account add <name>        # OAuth browser authentication
mcli account remove <name>     # Remove account
mcli account list              # List registered accounts

mcli list [-a ACC] [-c CAL]           # List calendars
mcli agenda [start] [end] [-a] [-c]   # Agenda view (default 5 days)
mcli week [weeks] [-a] [-c]           # Weekly grid view
mcli month [-a] [-c]                  # Monthly grid view
mcli search <text> [-a] [-c]          # Search events

mcli quick <text> -a <account>        # Natural language quick add
mcli add -t <title> -w <when> -a <account>  # Detailed add
mcli delete <text> -a <account>       # Delete event
```

## Common Modification Patterns

### Adding a New CLI Command
1. Add a function with `@main.command()` decorator in `cli.py`
2. Use `_resolve_accounts(account)` / `_require_account(account)` for account handling
3. Read operations: include `calendar_filter` parameter
4. Write operations: use `_require_account()` to require account specification

### Adding a New API Feature
1. Add a function in `api.py`, obtain service object via `get_service(account_name)`
2. Reuse `_parse_event_time()` for time parsing (automatic KST conversion)
3. Modify `models.py` if new `Event` model fields are needed

### Adding an Output Format
1. Add a function in `display.py`
2. Use `_get_account_color(account_name)` for per-account color assignment
3. Use `rich` library's `Table`, `Panel`, `Text` components

## Dependencies

- `click` - CLI framework
- `google-api-python-client` - Google Calendar API
- `google-auth-oauthlib` - OAuth authentication flow
- `google-auth` - Token management/refresh
- `rich` - Terminal UI (tables, colors, grids)
- `python-dateutil` - Date parsing + KST timezone
- `parsedatetime` - Natural language date input ("tomorrow", "next Monday")

## Gotchas

- **Python 3.14 required**: `requires-python = ">=3.14"`, managed with `uv`
- **No pickle**: Tokens must be JSON-serialized (for debuggability/portability)
- **`calendarList().get()` vs `calendars().get()`**: The former returns user view (includes summaryOverride), the latter returns only raw calendar info
- **access_role filter**: `get_all_events()` only queries `owner`/`writer`/`reader` roles, excludes `freeBusyReader`
- **OAuth access denied**: Test users must be added in the Google Cloud project (when in testing mode)
