# multicalcli - Codebase Guide

gcalcli를 대체하는 멀티 계정 Google Calendar CLI. 계정별 독립 OAuth 토큰으로 여러 Google 계정의 일정을 통합 조회/관리한다.

## Architecture Overview

```
CLI (click)  →  API (google-api-python-client)  →  Google Calendar API v3
    ↓                    ↑
 display (rich)    auth (google-auth-oauthlib)
    ↓                    ↑
 models          config (~/.config/multicalcli/)
```

**진입점:** `mcli` → `multicalcli.cli:main`

## File Map

| File | 역할 | 핵심 함수/클래스 |
|------|------|------------------|
| `cli.py` | Click CLI 명령어 그룹 | `main()`, `agenda()`, `week()`, `month()`, `quick()`, `add()`, `search()`, `delete()` |
| `api.py` | Google Calendar API 래퍼 | `get_all_events()`, `get_events()`, `list_calendars()`, `quick_add()`, `add_event()`, `delete_event()`, `search_events()` |
| `auth.py` | 계정별 OAuth 인증 | `authenticate()`, `load_credentials()`, `save_credentials()` |
| `config.py` | 설정 디렉토리/파일 관리 | `CONFIG_DIR`, `get_client_secret()`, `list_account_names()` |
| `models.py` | 데이터 모델 | `Calendar`, `Event` (dataclass) |
| `display.py` | Rich 터미널 출력 | `print_agenda()`, `print_week()`, `print_month()`, `print_calendars()` |
| `accounts.py` | 계정 CRUD 오케스트레이션 | `add_account()`, `remove_account()`, `list_accounts()` |

## Data Directory

```
~/.config/multicalcli/          # MCLI_CONFIG_DIR 환경변수로 변경 가능
├── config.json                 # default_account, display 설정
├── client_secret.json          # 글로벌 OAuth 클라이언트 (inha용)
└── accounts/
    ├── inha/
    │   └── token.json          # OAuth 토큰 (JSON, pickle 아님)
    └── lotte/
        ├── client_secret.json  # lotte 전용 OAuth 클라이언트
        └── token.json
```

- `get_client_secret(account_name)`: 계정별 `client_secret.json` 우선, 없으면 글로벌 fallback
- 토큰은 JSON 직렬화 (`token`, `refresh_token`, `token_uri`, `client_id`, `client_secret`, `scopes`)
- 만료 시 `load_credentials()`에서 자동 refresh

## Key Design Decisions

### 1. summaryOverride 우선
Google Calendar API의 `calendarList` 응답에는 `summary`(원래 이름)와 `summaryOverride`(사용자 변경 이름)가 있다. **`summaryOverride`가 있으면 우선 사용**하여 사용자가 Google Calendar 웹에서 변경한 이름이 그대로 표시된다.

### 2. 멀티 계정 병렬 조회
`get_all_events()`는 `ThreadPoolExecutor(max_workers=5)`로 여러 계정을 동시에 조회한 뒤 시간순 정렬한다.

### 3. KST 시간대
모든 이벤트 시간은 `dateutil.tz.gettz("Asia/Seoul")`로 KST 변환 후 표시. 종일 이벤트도 KST tzinfo를 부여하여 naive/aware datetime 비교 에러를 방지한다.

### 4. 필터링 체계
- `-a` / `--account`: 계정 단위 필터 (정확 매칭)
- `-c` / `--calendar`: 캘린더 이름 필터 (부분 문자열, 대소문자 무시, OR 조건)
- 캘린더 필터는 API 호출 **전에** 적용되어 불필요한 네트워크 요청을 줄인다

### 5. per-account client_secret
서로 다른 Google Cloud 프로젝트의 OAuth 클라이언트를 사용해야 할 때, 계정 디렉토리에 `client_secret.json`을 두면 해당 계정 인증에 사용된다.

## CLI Commands

```
mcli account add <name>        # OAuth 브라우저 인증
mcli account remove <name>     # 계정 삭제
mcli account list              # 등록된 계정 목록

mcli list [-a ACC] [-c CAL]           # 캘린더 목록
mcli agenda [start] [end] [-a] [-c]   # 일정 (기본 5일)
mcli week [weeks] [-a] [-c]           # 주간 그리드
mcli month [-a] [-c]                  # 월간 그리드
mcli search <text> [-a] [-c]          # 일정 검색

mcli quick <text> -a <account>        # 자연어 빠른 추가
mcli add -t <title> -w <when> -a <account>  # 상세 추가
mcli delete <text> -a <account>       # 일정 삭제
```

## Common Modification Patterns

### 새 CLI 명령어 추가
1. `cli.py`에 `@main.command()` 데코레이터로 함수 추가
2. `_resolve_accounts(account)` / `_require_account(account)`로 계정 처리
3. 읽기 작업: `calendar_filter` 파라미터 포함
4. 쓰기 작업: `_require_account()`로 계정 필수 지정

### 새 API 기능 추가
1. `api.py`에 함수 추가, `get_service(account_name)`으로 서비스 객체 획득
2. 시간 파싱 시 `_parse_event_time()` 재사용 (KST 자동 변환)
3. `Event` 모델 필드 추가 필요 시 `models.py` 수정

### 출력 형식 추가
1. `display.py`에 함수 추가
2. `_get_account_color(account_name)`으로 계정별 색상 할당
3. `rich` 라이브러리의 `Table`, `Panel`, `Text` 활용

## Dependencies

- `click` - CLI 프레임워크
- `google-api-python-client` - Google Calendar API
- `google-auth-oauthlib` - OAuth 인증 플로우
- `google-auth` - 토큰 관리/refresh
- `rich` - 터미널 UI (테이블, 색상, 그리드)
- `python-dateutil` - 날짜 파싱 + KST 시간대
- `parsedatetime` - 자연어 날짜 입력 ("내일", "다음주 월요일")

## Gotchas

- **Python 3.14 필수**: `requires-python = ">=3.14"`, `uv`로 관리
- **pickle 사용 금지**: 토큰은 반드시 JSON 직렬화 (디버깅/이식성)
- **`calendarList().get()` vs `calendars().get()`**: 전자는 사용자 뷰(summaryOverride 포함), 후자는 캘린더 원본 정보만 반환
- **access_role 필터**: `get_all_events()`는 `owner`/`writer`/`reader`만 조회, `freeBusyReader`는 제외
- **OAuth access denied**: Google Cloud 프로젝트에서 테스트 사용자 추가 필요 (테스트 모드일 때)
