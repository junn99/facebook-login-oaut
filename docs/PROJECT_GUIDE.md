# urlinsta - 프로젝트 가이드

> Instagram Insights Dashboard / Meta App Review 대비 전체 정리

---

## 1. 시스템 전체 흐름

### 1.1 아키텍처

```
┌──────────────┐     OAuth      ┌──────────────┐     Graph API     ┌──────────────┐
│   사용자      │ ──────────────► │   Facebook   │ ◄──────────────── │  Instagram   │
│  (브라우저)   │ ◄────token───── │   OAuth 2.0  │                   │  Business    │
└──────┬───────┘                 └──────────────┘                   └──────────────┘
       │                                                                    │
       │  Streamlit                                                         │
       ▼                                                                    │
┌──────────────┐     API 호출    ┌──────────────┐     인사이트 수집          │
│  Streamlit   │ ──────────────► │  Instagram   │ ◄────────────────────────┘
│  App (7페이지)│                 │  Graph API   │
└──────┬───────┘                 │  v22.0       │
       │                         └──────────────┘
       │  CRUD
       ▼
┌──────────────┐
│   Supabase   │  users, tokens, insights, audience_data, collection_log
│  (PostgreSQL)│
└──────────────┘
```

### 1.2 사용자 여정 (User Flow)

```
1. 사용자가 Login 페이지 방문
2. "Facebook으로 인스타그램 연결" 버튼 클릭
3. Facebook OAuth 화면으로 리다이렉트 (5개 권한 요청)
4. 사용자가 권한 승인
5. Facebook이 code + state와 함께 redirect_uri로 리다이렉트
6. 앱이 code를 short-lived token으로 교환
7. short-lived token을 long-lived token (60일)으로 교환
8. 사용자의 Facebook Pages → Instagram Business Account 탐색
9. 계정 정보 + 토큰을 Supabase에 저장
10. Dashboard로 이동 → 첫 로그인 시 인사이트 자동 수집
11. 이후 6시간마다 백그라운드 자동 수집
```

### 1.3 페이지 구성

| 페이지 | 파일 | 역할 |
|--------|------|------|
| Home | `app.py` | 앱 소개, 로그인 상태 표시 |
| Dashboard | `pages/1_📊_Dashboard.py` | 인사이트 차트, 지표, 오디언스 |
| Login | `pages/2_🔐_Login.py` | Facebook OAuth 로그인 |
| Settings | `pages/3_⚙️_Settings.py` | 계정 관리, 토큰 갱신 |
| Privacy | `pages/4_🔒_Privacy.py` | 개인정보 처리방침 (Meta 필수) |
| Data Deletion | `pages/5_🗑️_Data_Deletion.py` | 데이터 삭제 안내 (Meta 필수) |
| Live Insights | `pages/6_🔍_Live_Insights.py` | 실시간 API 호출 데모 (심사용) |

### 1.4 요청하는 Facebook/Instagram 권한 5개

| 권한 | 용도 | 사용 위치 |
|------|------|-----------|
| `instagram_basic` | 계정 기본 정보 (username, 팔로워 등) | Login, Dashboard, Live Insights |
| `instagram_manage_insights` | 인사이트 지표 (노출, 도달, 프로필 조회) | Dashboard, Live Insights |
| `pages_show_list` | Facebook 페이지 목록 조회 | Login (연결된 IG 계정 탐색), Live Insights |
| `pages_read_engagement` | 오디언스 인구통계 데이터 | Dashboard, Live Insights |
| `business_management` | Business Manager 하위 페이지 조회(폴백) | Login (BM fallback page discovery) |

참고:
- 일부 Business Manager 구성에서는 인사이트 접근 시 `ads_management` 또는 `ads_read` 권한이 추가로 요구될 수 있습니다(앱은 해당 오류를 안내 메시지로 표시).

---

## 2. 이번에 변경한 것 (6개 커밋)

### 커밋 내역

| 커밋 | 내용 | 왜 |
|------|------|----|
| `f5fa247` | OAuth 스코프를 `email,public_profile` → Instagram 권한 세트로 변경, API v21→v22 | **이전 스코프로는 Instagram API 호출 자체가 불가능했음** |
| `8ec5e45` | Privacy Policy + Data Deletion 페이지 추가 | Meta App Review 필수 요구사항 |
| `ea991a2` | Permission badge 헬퍼 + 각 페이지에 배지 추가 | 심사관에게 각 기능이 어떤 권한을 사용하는지 표시 |
| `c9cc83e` | Login 플로우 재구성 + OAuth 에러 처리 강화 | Streamlit Cloud에서 state 유실 시 빈 화면 방지 |
| `2a991c0` | Dashboard 첫 로그인 자동 수집 + 권한 요약 테이블 | 심사 시 빈 대시보드 방지 |
| `ad9cb78` | Live Insights 페이지 추가 | 실시간 API 호출 데모로 권한 사용 증명 |

### 변경 파일 요약

**수정 (5개):**
- `src/oauth.py` — 스코프 변경 (1줄)
- `src/config.py` — API 버전 변경 (1줄)
- `pages/1_📊_Dashboard.py` — 자동 수집 + 배지 + 요약 테이블
- `pages/2_🔐_Login.py` — state 처리 수정 + 에러 처리 + 배지
- `pages/3_⚙️_Settings.py` — 배지 추가

**신규 (4개):**
- `src/permission_badge.py` — 배지 헬퍼
- `pages/4_🔒_Privacy.py` — 개인정보 처리방침
- `pages/5_🗑️_Data_Deletion.py` — 데이터 삭제 안내
- `pages/6_🔍_Live_Insights.py` — 실시간 API 데모

---

## 3. 검증 완료 항목

### 3.1 자동 검증 (로컬에서 실행 완료)

| 검증 항목 | 방법 | 결과 |
|-----------|------|------|
| Python 구문 검사 | `ast.parse()` 13개 파일 | ✅ 전체 통과 |
| 패키지 의존성 | 모든 페이지 AST import 추출 → `__import__()` | ✅ 전체 통과 |
| OAuth 스코프 정확성 | URL 파싱 후 scope 파라미터 비교 | ✅ 4개 정확히 일치 |
| 이전 스코프 제거 | email, public_profile 미포함 확인 | ✅ 완전 제거 |
| API 버전 | config.GRAPH_API_VERSION 확인 | ✅ v22.0 |
| 모듈 import | venv 환경에서 10개 모듈 import | ✅ 전체 성공 |
| Pydantic 모델 | User 객체 생성 테스트 | ✅ 정상 |
| InstagramAPI 인스턴스화 | 생성자 호출 테스트 | ✅ 정상 |
| State 검증 로직 | generate → validate → reject bogus | ✅ 정상 |
| Streamlit 앱 시작 | HTTP health check + 메인 페이지 200 | ✅ 정상 |
| 런타임 에러 | Streamlit 로그에서 error/exception 검색 | ✅ 없음 |

### 3.2 검증 못 한 항목 (배포 환경 필요)

| 항목 | 이유 | 언제 가능 |
|------|------|-----------|
| 실제 Facebook OAuth 로그인 | FB_APP_ID, FB_APP_SECRET 필요 | .env 설정 후 |
| Supabase DB 연결 | SUPABASE_URL, SUPABASE_KEY 필요 | .env 설정 후 |
| 인사이트 API 호출 | 실제 Instagram Business 계정 + 유효 토큰 필요 | 로그인 성공 후 |
| 오디언스 데이터 조회 | 동일 | 로그인 성공 후 |
| 토큰 갱신 | 기존 long-lived token 필요 | 최초 로그인 후 |
| 백그라운드 스케줄러 | Supabase 연결 시에만 시작 | 배포 후 |

---

## 4. 당신이 해야 할 일 (순서대로)

### Phase 1: 환경 설정 (로컬 or Streamlit Cloud)

#### 4.1 환경 변수 설정

`.env` 파일 생성 (`.env.example` 참고):

```bash
# Facebook App Credentials (developers.facebook.com에서 확인)
FB_APP_ID=실제_앱_ID
FB_APP_SECRET=실제_앱_시크릿

# OAuth Redirect URI (Streamlit Cloud URL + /Login)
OAUTH_REDIRECT_URI=https://your-app.streamlit.app/Login

# Supabase (supabase.com 대시보드에서 확인)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
```

**Streamlit Cloud 사용 시:** Settings → Secrets에 같은 값 입력

#### 4.2 Supabase 테이블 생성

Supabase SQL Editor에서 실행:

```sql
-- Users
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    instagram_id TEXT UNIQUE NOT NULL,
    instagram_username TEXT NOT NULL,
    facebook_page_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tokens
CREATE TABLE tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    token_type TEXT NOT NULL,  -- 'user' or 'page'
    access_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insights
CREATE TABLE insights (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    metric_name TEXT NOT NULL,
    metric_value FLOAT NOT NULL,
    period TEXT NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audience Data
CREATE TABLE audience_data (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    data_type TEXT NOT NULL,
    data_json TEXT NOT NULL,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);

-- Collection Log
CREATE TABLE collection_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    collection_type TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT,
    collected_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 4.3 플레이스홀더 교체

아래 두 파일에서 `[CONTACT_EMAIL]`을 실제 이메일로 변경:
- `pages/4_🔒_Privacy.py` (3곳)
- `pages/5_🗑️_Data_Deletion.py` (2곳)

```bash
# 검색
grep -rn "CONTACT_EMAIL" pages/
```

### Phase 2: 로컬 테스트

#### 4.4 앱 실행

```bash
cd /home/yeardream4/Celeblife/facebook-login-oaut
uv run streamlit run app.py
```

#### 4.5 전체 플로우 테스트

| 단계 | 확인 항목 | 예상 결과 |
|------|-----------|-----------|
| 1 | 앱 메인 페이지 열기 | "설정 누락" 메시지 없이 정상 표시 |
| 2 | Login 페이지 → "Facebook으로 연결" 클릭 | Facebook OAuth 화면으로 이동 |
| 3 | Facebook에서 권한 승인 | Login 페이지로 리다이렉트, 성공 메시지 |
| 4 | Dashboard 페이지 이동 | 자동으로 인사이트 수집 시작 |
| 5 | Dashboard에서 차트/지표 확인 | 데이터가 표시됨 (비즈니스 계정 활동이 있어야 함) |
| 6 | Live Insights 페이지 | 4개 섹션 모두 실시간 데이터 표시 |
| 7 | Settings 페이지 | 연결된 계정, 토큰 상태 표시 |
| 8 | Privacy 페이지 | 한영 이중언어 개인정보 처리방침 |
| 9 | Data Deletion 페이지 | 한영 이중언어 삭제 안내 |

### Phase 3: Meta App Review 설정

#### 4.6 Meta 개발자 콘솔 설정

[developers.facebook.com](https://developers.facebook.com) → 앱 → 설정 → 기본:

| 항목 | 값 |
|------|----|
| **Privacy Policy URL** | `https://your-app.streamlit.app/Privacy` |
| **Data Deletion Instructions URL** | `https://your-app.streamlit.app/Data_Deletion` |
| **앱 도메인** | `your-app.streamlit.app` |
| **사이트 URL** | `https://your-app.streamlit.app` |

#### 4.7 앱 모드 변경

- 개발 → **라이브** 모드로 전환
- "Use Cases" 탭에서 적절한 use case 선택

#### 4.8 App Review 제출

5개 권한을 각각 제출해야 합니다:

| 권한 | 제출 시 필요 |
|------|-------------|
| `instagram_basic` | 스크린캐스트: 로그인 → 프로필 정보 표시 |
| `instagram_manage_insights` | 스크린캐스트: Dashboard 지표 + Live Insights |
| `pages_show_list` | 스크린캐스트: 로그인 과정에서 페이지 목록 사용 |
| `pages_read_engagement` | 스크린캐스트: 오디언스 인구통계 데이터 |
| `business_management` | 스크린캐스트: BM 하위 페이지 탐색(로그인 fallback) |

### Phase 4: 스크린캐스트 촬영

Meta App Review에서 **각 권한별로 스크린캐스트가 필요합니다.**

#### 촬영 시나리오 (하나의 영상으로 가능)

```
1. 앱 메인 페이지 보여주기
2. Login 페이지 → "Facebook으로 연결" 클릭
3. Facebook 권한 승인 화면 (5개 권한 표시됨) → 승인
4. 로그인 성공 화면 (계정 정보 표시)
5. Dashboard → 주요 지표 (팔로워, 노출, 도달, 프로필 조회)
6. Dashboard → 시간별 추이 차트
7. Dashboard → 오디언스 인구통계
8. Live Insights → 프로필 정보 (instagram_basic)
9. Live Insights → 비즈니스 인사이트 (instagram_manage_insights)
10. Live Insights → 오디언스 데이터 (pages_read_engagement)
11. Live Insights → 연결된 Pages (pages_show_list)
12. Privacy Policy 페이지
13. Data Deletion 페이지
```

**팁:**
- 각 섹션의 "Permission: `instagram_basic`" 배지가 화면에 보이도록
- Live Insights의 "API Details" expander를 열어서 호출 엔드포인트 보여주기
- 2~3분 영상이 적당

---

## 5. 트러블슈팅

### OAuth 로그인 실패

| 증상 | 원인 | 해결 |
|------|------|------|
| "앱이 설정되지 않았습니다" | 환경변수 누락 | `.env` 또는 Streamlit Secrets 확인 |
| Facebook 화면에서 에러 | `OAUTH_REDIRECT_URI` 불일치 | Meta 콘솔의 "Valid OAuth Redirect URIs"에 정확한 URL 등록 |
| "No Instagram Business Account found" | Instagram이 Facebook 페이지에 연결 안 됨 또는 BM 페이지 조회 권한 부족 | Instagram 설정 → 페이지 연결 + `business_management` 권한 동의 여부 확인 |
| 인사이트 데이터 없음 | 비즈니스 계정 활동 부족 | 게시물 올리고 하루 뒤 재시도 |

### Streamlit Cloud 배포

| 증상 | 원인 | 해결 |
|------|------|------|
| "ModuleNotFoundError" | 의존성 미설치 | `pyproject.toml`의 dependencies 확인 |
| DB 연결 실패 | Secrets 미설정 | Streamlit Cloud → Settings → Secrets |
| OAuth 리다이렉트 실패 | URL 불일치 | `OAUTH_REDIRECT_URI`를 Cloud URL로 변경 |

---

## 6. 프로젝트 구조

```
facebook-login-oaut/
├── app.py                          # 메인 앱 (홈페이지 + 스케줄러)
├── pyproject.toml                  # 의존성 정의 (uv 사용)
├── .env.example                    # 환경변수 템플릿
├── .streamlit/
│   └── config.toml                 # Streamlit 테마/서버 설정
├── src/
│   ├── config.py                   # 환경변수 → Config 클래스
│   ├── models.py                   # Pydantic 모델 (User, Token, Insight 등)
│   ├── oauth.py                    # Facebook OAuth 전체 플로우
│   ├── database.py                 # Supabase CRUD 함수
│   ├── instagram_api.py            # Instagram Graph API 클라이언트
│   ├── insights_collector.py       # 인사이트 수집 로직
│   ├── rate_limiter.py             # API 요청 제한
│   └── permission_badge.py         # 권한 배지 표시 헬퍼
├── pages/
│   ├── 1_📊_Dashboard.py           # 인사이트 대시보드
│   ├── 2_🔐_Login.py              # OAuth 로그인
│   ├── 3_⚙️_Settings.py           # 계정/토큰 관리
│   ├── 4_🔒_Privacy.py            # 개인정보 처리방침
│   ├── 5_🗑️_Data_Deletion.py     # 데이터 삭제 안내
│   └── 6_🔍_Live_Insights.py      # 실시간 API 데모
├── jobs/
│   ├── collect_insights.py         # 정기 인사이트 수집 job
│   └── refresh_tokens.py           # 정기 토큰 갱신 job
└── docs/
    └── PROJECT_GUIDE.md            # 이 문서
```

---

## 7. 기술 스택

| 영역 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | Streamlit | >= 1.31.0 |
| 데이터베이스 | Supabase (PostgreSQL) | - |
| API | Facebook/Instagram Graph API | v22.0 |
| 데이터 시각화 | Plotly + Pandas | >= 5.18.0 / >= 2.1.0 |
| 모델 | Pydantic | >= 2.5.0 |
| HTTP | Requests + Tenacity (재시도) | >= 2.31.0 / >= 8.2.0 |
| 스케줄러 | APScheduler | >= 3.10.0 |
| 패키지 관리 | uv | - |
| Python | CPython | >= 3.11 |
