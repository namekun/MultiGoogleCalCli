# mcli - Multi-account Google Calendar CLI

여러 Google 계정의 캘린더를 하나의 CLI에서 통합 조회/관리합니다.

## Quick Start

```bash
# 설치
pip install multicalcli
# 또는
pipx install multicalcli

# 계정 추가 (브라우저에서 Google 로그인)
mcli account add work

# 일정 확인
mcli agenda
```

## 설치

### pip / pipx

```bash
pip install multicalcli
```

### 소스에서 설치

```bash
git clone https://github.com/namkun/multicalcli.git
cd multicalcli
pip install .
```

## OAuth 설정 (최초 1회)

mcli를 사용하려면 Google Cloud에서 OAuth 클라이언트를 만들어야 합니다.

### 1. Google Cloud Console에서 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 새 프로젝트 생성 (또는 기존 프로젝트 선택)

### 2. Google Calendar API 활성화

1. **API 및 서비스** > **라이브러리**
2. "Google Calendar API" 검색 > **사용 설정**

### 3. OAuth 동의 화면 설정

1. **API 및 서비스** > **OAuth 동의 화면**
2. **외부** 선택 > 앱 이름 입력
3. 범위 추가: `https://www.googleapis.com/auth/calendar`
4. 테스트 사용자에 본인 이메일 추가

### 4. OAuth 클라이언트 ID 생성

1. **API 및 서비스** > **사용자 인증 정보**
2. **사용자 인증 정보 만들기** > **OAuth 클라이언트 ID**
3. 유형: **데스크톱 앱**
4. JSON 다운로드 > `client_secret.json`으로 저장

### 5. client_secret.json 배치

```bash
# 모든 계정에서 같은 OAuth 클라이언트를 쓸 경우
cp client_secret.json ~/.config/multicalcli/client_secret.json

# 계정별로 다른 OAuth 클라이언트를 쓸 경우
cp client_secret_work.json ~/.config/multicalcli/accounts/work/client_secret.json
cp client_secret_personal.json ~/.config/multicalcli/accounts/personal/client_secret.json
```

### 6. 계정 등록

```bash
mcli account add work      # 브라우저가 열리고 Google 로그인 진행
mcli account add personal  # 두 번째 계정도 추가
```

## 사용법

### 일정 조회

```bash
# 모든 계정 일정 통합 조회 (다음 5일)
mcli agenda

# 기간 지정
mcli agenda "2025-03-01" "2025-03-07"

# 주간 / 월간 뷰
mcli week
mcli month
```

### 필터링

```bash
# 특정 계정만
mcli agenda -a work

# 특정 캘린더만 (이름 부분 매칭)
mcli agenda -c "프로젝트"

# 여러 캘린더 동시 필터 (OR)
mcli agenda -c "업무" -c "미팅"

# 계정 + 캘린더 조합
mcli agenda -a work -c "팀"
```

### 일정 추가

```bash
# 자연어 빠른 추가
mcli quick -a work "내일 오후 3시 미팅"

# 상세 추가
mcli add -a work --title "주간회의" --when "월요일 10시" --duration 60
```

### 일정 검색 / 삭제

```bash
mcli search "미팅"
mcli delete "미팅" -a work
```

### 캘린더 / 계정 목록

```bash
mcli list              # 전체 캘린더 목록
mcli account list      # 등록된 계정 목록
```

## 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `MCLI_CONFIG_DIR` | 설정 디렉토리 경로 | `~/.config/multicalcli` |

## 특징

- 여러 Google 계정의 일정을 시간순으로 병합 표시
- 계정별 색상 자동 할당
- 캘린더 이름 기반 필터링 (부분 매칭, 대소문자 무시)
- 사용자가 Google Calendar에서 변경한 캘린더 이름 반영
- 시간대 자동 변환 (KST)
- 계정별 독립 OAuth 토큰 관리

## License

MIT
