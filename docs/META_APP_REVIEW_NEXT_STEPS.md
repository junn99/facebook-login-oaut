# Meta App Review: Next Steps Runbook (운영자 가이드)

이 문서는 최근 Meta App Review 대응 수정(리다이렉트/도메인/정책 페이지 등) 이후, **이제 운영자가 실제로 무엇을 해야 하는지**를 “실행 순서”로 정리한 런북입니다.

참고 문서:
- `docs/APP_REVIEW_CHECKLIST.md`
- `docs/PROJECT_GUIDE.md`

실제 배포 전에 꼭 확인:
- 이 문서의 기본 도메인은 현재 `facebook-login-oaut.streamlit.app`으로 맞춰져 있습니다.
- 제출 전 실제 운영 도메인과 다르면 반드시 전부 치환하세요.

빠른 치환 예시(실행 전 `APP_BASE_URL`을 실제 값으로 수정):

```bash
APP_BASE_URL="https://facebook-login-oaut.streamlit.app"
python3 - <<'PY'
import os
from pathlib import Path

targets = [
    Path("docs/META_APP_REVIEW_NEXT_STEPS.md"),
    Path("docs/APP_REVIEW_CHECKLIST.md"),
]

app_base_url = os.environ["APP_BASE_URL"].rstrip("/")

for path in targets:
    text = path.read_text(encoding="utf-8")
    text = text.replace("https://facebook-login-oaut.streamlit.app", app_base_url)
    path.write_text(text, encoding="utf-8")
    print(f"updated: {path}")
PY
```

---

## 1) 목적과 범위

목적:
- Meta App Review(권한 심사) 제출 전에, **배포/설정/재현 자료(스크린캐스트) 준비**를 빠짐없이 수행
- 심사관이 그대로 따라해도 재현 가능한 상태(공개 URL, OAuth 동작, 정책 URL 접근성)를 확보

범위:
- 운영 절차(콘솔 설정/배포 후 점검/스크린캐스트 촬영/제출/반려 대응)
- 코드 변경은 포함하지 않습니다.

비범위:
- `src/`, `pages/`, `tests/` 코드 수정
- 신규 기능/권한 추가, 아키텍처 변경

---

## 2) 시작 전 준비물

계정/권한:
- Meta Developer 계정(앱 소유자/관리자 권한)
- Facebook 테스트 계정 1개(심사용) + 실제로 연결된 Instagram Business 계정
- Instagram Business 계정이 Facebook Page에 연결되어 있어야 합니다(연결된 Page가 없으면 Login/Pages 흐름에서 막힐 수 있음).

배포 URL:
- Streamlit Cloud 배포 URL(예: `https://facebook-login-oaut.streamlit.app`)
- 아래 페이지 라우트가 존재해야 합니다:
  - `/Login`
  - `/Dashboard`
  - `/Live_Insights`
  - `/Privacy`
  - `/Data_Deletion`

시크릿/환경변수:
- `FB_APP_ID`
- `FB_APP_SECRET`
- `OAUTH_REDIRECT_URI` (예: `https://facebook-login-oaut.streamlit.app/Login`)
- Supabase 사용 시: `SUPABASE_URL`, `SUPABASE_KEY`
- 정책 페이지 연락처: `CONTACT_EMAIL` (배포 환경변수/Streamlit Secrets에 실제 연락처 메일 설정)

도구:
- 화면 녹화 툴(스크린캐스트 1개 영상으로 권한 사용 증명)
- (선택) 로컬 테스트용 브라우저 프로필(쿠키/세션 꼬임 방지)

---

## 3) 10분 사전 점검 (Quick Preflight Checklist)

아래는 “제출 직전 10분 점검”입니다. 각 항목은 **Pass/Fail 기준**이 있습니다.

1. 공개 정책 페이지 접근성
- 액션: 브라우저 시크릿 모드에서 아래 URL을 직접 열기
  - `https://facebook-login-oaut.streamlit.app/Privacy`
  - `https://facebook-login-oaut.streamlit.app/Data_Deletion`
- Pass: 로그인 없이 페이지가 즉시 렌더링됨(에러/빈 화면 없음)
- Fail: 환경변수 누락/런타임 에러/무한 로딩

2. OAuth 리다이렉트 URL 일치
- 액션: 배포 환경 변수 `OAUTH_REDIRECT_URI` 확인 + Meta 콘솔에 등록된 redirect URI 확인
- Pass: `OAUTH_REDIRECT_URI`와 Meta 콘솔의 등록 값이 **완전히 동일**(스킴/호스트/경로 `/Login` 포함)
- Fail: 한 글자라도 불일치(특히 `/Login` 누락, http/https 혼동, 도메인 오타)

3. App Domains 포함 여부
- 액션: Meta App Dashboard -> Settings -> Basic -> `App Domains`
- Pass: `facebook-login-oaut.streamlit.app` 포함(로컬 테스트 시 `localhost` 선택)
- Fail: 도메인 미등록

4. 핵심 라우트 존재 확인
- 액션: 배포 URL에서 직접 열기
  - `https://facebook-login-oaut.streamlit.app/Login`
  - `https://facebook-login-oaut.streamlit.app/Dashboard`
  - `https://facebook-login-oaut.streamlit.app/Live_Insights`
- Pass: `/Login`은 로그인 버튼이 보이고, 로그인 후 `/Dashboard`/`/Live_Insights`에서 데이터 섹션이 표시됨
- Fail: 404/빈 페이지/오류 메시지(권한/토큰/DB 설정 누락 가능)

5. 제출 전 로컬 정적 점검(옵션이지만 권장)
- 액션(레포 루트에서 실행):

```bash
".venv/bin/python" -m compileall -q .
".venv/bin/python" -m pytest -q
```

- Pass: 두 명령이 non-error로 종료
- Fail: import/문법/테스트 실패(배포 전 먼저 해결)

---

## 4) 배포 후 실제 확인 절차 (Public URLs + OAuth E2E)

목표는 “심사관이 그대로 재현 가능한 E2E 흐름”을 확보하는 것입니다.

1. 공개 URL 정상 동작(로그인 없이)
- 액션: `https://facebook-login-oaut.streamlit.app/Privacy` 와 `https://facebook-login-oaut.streamlit.app/Data_Deletion` 접속
- Pass/Fail: 3) 1번과 동일

2. OAuth 로그인 E2E
- 액션:
  1) `https://facebook-login-oaut.streamlit.app/Login` 접속
  2) 로그인 버튼 클릭 → Facebook OAuth로 이동
  3) 권한 승인 화면에서 5개 권한이 표시되는지 확인 후 승인
  4) `/Login`으로 돌아와 성공 메시지 확인
- Pass:
  - 승인 후 `/Login`에서 로그인 성공 안내가 보임
  - 로그인 후 `/Dashboard`로 이동해 차트/지표 섹션이 표시됨
  - 로그인 후 `/Live_Insights`에서 “실시간 API 호출 데모” 섹션들이 보임
- Fail:
  - redirect mismatch
  - state 검증 실패(invalid state)
  - 페이지/IG 비즈니스 계정 탐색 실패

3. 권한-기능 매핑 확인(심사 핵심)
- 액션: 아래 라우트에서 권한 증빙 UI가 실제로 보이는지 확인
  - `/Login`: `instagram_basic`, `pages_show_list`, `business_management`
  - `/Dashboard`: `instagram_manage_insights`, `pages_read_engagement`
  - `/Live_Insights`: 4개 권한 섹션(프로필/인사이트/오디언스/페이지 목록) + `/Login`의 BM fallback 동작 증빙
- Pass: 각 섹션에서 권한 사용이 화면상 드러남(배지/섹션 제목/표 등)
- Fail: 로그인은 되지만, 심사관이 “권한을 어디서 쓰는지” 확인하기 어려움

---

## 5) Meta 콘솔 설정값 체크

아래 값들은 `docs/APP_REVIEW_CHECKLIST.md` 기준으로 “심사 통과 최소 조건”입니다.

1. Settings -> Basic
- `App Domains`:
  - `facebook-login-oaut.streamlit.app`
  - (선택) `localhost` (로컬 테스트 시)
- `Privacy Policy URL`:
  - `https://facebook-login-oaut.streamlit.app/Privacy`
- `Data Deletion Instructions URL`:
  - `https://facebook-login-oaut.streamlit.app/Data_Deletion`

Pass/Fail 기준:
- Pass: 위 URL이 모두 실제로 접근 가능(브라우저에서 200 + 정상 렌더)
- Fail: URL 오타/비공개/리다이렉트 루프/로그인 필요

2. Facebook Login -> Settings
- `Valid OAuth Redirect URIs`:
  - `https://facebook-login-oaut.streamlit.app/Login`
  - (선택) `http://localhost:8501/Login` (로컬 테스트 시)

Pass/Fail 기준:
- Pass: 실제 로그인 시 리다이렉트 에러 없이 `/Login`으로 돌아옴
- Fail: “redirect_uri mismatch” 류의 오류

---

## 6) 스크린캐스트 촬영 스크립트 (minute-by-minute)

원칙:
- 끊김 없는 1개 영상(2~3분)을 목표로 하되, **권한별 증빙 포인트**를 빠짐없이 포함
- 화면에 권한 배지/섹션 제목이 보이도록 촬영

권한(5개):
- `instagram_basic`
- `instagram_manage_insights`
- `pages_show_list`
- `pages_read_engagement`
- `business_management`

### 0:00 - 0:20 (앱 공개 URL + 목적 소개)
1) 브라우저 주소창에 배포 URL을 보여줌(예: `https://facebook-login-oaut.streamlit.app`)
2) 사이드바에서 페이지 목록이 보이는 것을 잠깐 보여줌(심사관이 페이지 구조 인지)

Pass 기준:
- 앱이 즉시 로드되고 오류/경고 없이 렌더

### 0:20 - 1:00 (/Login OAuth 흐름)
1) `https://facebook-login-oaut.streamlit.app/Login` 이동
2) 로그인 버튼 클릭 → Facebook OAuth로 이동
3) 권한 승인 화면에서 5개 권한이 요청되는 것을 보여줌
4) 승인 후 `/Login`으로 돌아와 성공 메시지 + 계정 정보 표시를 보여줌

Pass 기준:
- 승인 후 `/Login`에서 성공 표시, 그리고 권한 배지가 확인됨

### 1:00 - 1:40 (/Dashboard 권한 사용 증빙)
1) `https://facebook-login-oaut.streamlit.app/Dashboard` 이동
2) 지표/차트/오디언스 섹션을 스크롤하며 보여줌
3) 해당 화면에서 필요한 권한이 무엇인지(배지/표기) 확인 가능하도록 보여줌

Pass 기준:
- 차트/지표 UI가 실제 데이터 또는 “데이터 없음” 안내로라도 정상 렌더

### 1:40 - 2:20 (/Live_Insights 실시간 API 호출 증빙)
1) `https://facebook-login-oaut.streamlit.app/Live_Insights` 이동
2) 다음 섹션을 순서대로 보여줌:
   - 프로필 정보 (`instagram_basic`)
   - 비즈니스 인사이트 (`instagram_manage_insights`)
   - 오디언스 인구통계 (`instagram_manage_insights` + `pages_read_engagement`)
   - 연결된 Pages (`pages_show_list`)
3) 가능하면 각 섹션의 “API Details” expander를 열어 호출 엔드포인트(증빙)를 잠깐 보여줌

Pass 기준:
- 각 섹션이 오류 없이 표시되며, 권한 사용 근거(배지/문구/API Details)가 영상에 포함

### 2:20 - 2:50 (정책 URL 증빙)
1) `https://facebook-login-oaut.streamlit.app/Privacy` 이동(로그인 없이 접근 가능함을 강조)
2) `https://facebook-login-oaut.streamlit.app/Data_Deletion` 이동

Pass 기준:
- 두 페이지 모두 로그인 없이 정상 렌더

---

## 7) 제출 전 최종 체크리스트 (Go/No-Go)

아래가 모두 체크되면 제출(Go), 하나라도 Fail이면 No-Go입니다.

- [ ] `https://facebook-login-oaut.streamlit.app/Privacy` 로그인 없이 접근 가능(Pass)
- [ ] `https://facebook-login-oaut.streamlit.app/Data_Deletion` 로그인 없이 접근 가능(Pass)
- [ ] Meta 콘솔 `App Domains`에 `facebook-login-oaut.streamlit.app` 포함(Pass)
- [ ] Meta 콘솔 `Valid OAuth Redirect URIs`에 `https://facebook-login-oaut.streamlit.app/Login` 등록(Pass)
- [ ] 앱 환경변수 `OAUTH_REDIRECT_URI`가 위 값과 완전 일치(Pass)
- [ ] `/Login` -> OAuth 승인 -> `/Login` 복귀가 성공(Pass)
- [ ] `/Dashboard`와 `/Live_Insights`에서 권한 사용 증빙이 영상에 담길 수준으로 명확(Pass)
- [ ] 스크린캐스트에 주소창(경로)이 보임(Pass)

---

## 8) 자주 막히는 이슈와 해결

1) redirect_uri mismatch
- 증상: Facebook OAuth에서 “redirect uri is not allowed” 류 에러
- 원인: Meta 콘솔 등록값 vs `OAUTH_REDIRECT_URI` vs 실제 배포 URL이 불일치
- 해결:
  - Meta 콘솔 `Valid OAuth Redirect URIs`에 `https://facebook-login-oaut.streamlit.app/Login` 정확히 추가
  - 앱 시크릿의 `OAUTH_REDIRECT_URI`를 같은 값으로 맞춤

Pass 기준:
- `/Login`에서 승인 후 정상 복귀

2) invalid state / state 검증 실패
- 증상: `/Login`에서 “보안 검증(state) 실패” 경고 후 재시도 안내
- 원인: 리다이렉트 과정에서 state가 유실/오염되었거나, 다중 탭/쿠키/세션 꼬임
- 해결:
  - 시크릿 모드에서 단일 탭으로 재시도
  - 동일한 URL/도메인으로만 진행(중간에 http/https 섞지 않기)

Pass 기준:
- 재시도 시 정상 로그인 성공

3) No Instagram Business Account found / Pages 탐색 실패
- 증상: 로그인은 되지만 IG 비즈니스 계정 탐색 단계에서 실패
- 원인: IG가 Facebook Page에 연결되지 않았거나, 계정 유형이 비즈니스/프로페셔널이 아님, 또는 BM 권한 부족
- 해결:
  - Instagram 설정에서 Facebook Page 연결
  - 테스트 계정을 “비즈니스 계정”으로 준비
  - OAuth에서 `business_management` 동의 및 BM 내 페이지 권한 확인
  - 일부 BM 구성에서는 `ads_management`/`ads_read`가 추가로 필요할 수 있음

4) 데이터가 비어 보임
- 증상: `/Dashboard`/`/Live_Insights`에서 데이터가 없다/표시가 약함
- 원인: 신규 계정/활동 부족/권한 범위 문제/토큰 문제
- 해결:
  - 최소한 프로필 정보 섹션(`instagram_basic`)과 Pages 목록(`pages_show_list`)은 보이게 확보
  - 가능하면 실제 활동 있는 계정으로 촬영
  - Live Insights에서 “API Details”를 열어 호출 자체가 이뤄짐을 증빙

---

## 9) 제출 후 대응 (Rejection 대응 템플릿/재현자료 준비)

목표:
- 반려 사유를 “재현 가능한 증거”로 빠르게 해소(영상/URL/콘솔 스크린샷)

### 9.1 반려 대응 자료 패키지(추천)
- 배포 URL: `https://facebook-login-oaut.streamlit.app`
- 정책 URL 2개:
  - `https://facebook-login-oaut.streamlit.app/Privacy`
  - `https://facebook-login-oaut.streamlit.app/Data_Deletion`
- OAuth Redirect URI 등록 화면 스크린샷
- App Domains 등록 화면 스크린샷
- 2~3분 스크린캐스트(주소창 포함, 권한별 증빙 포함)
- 테스트 계정 정보(공유 범위는 내부 운영자만)

### 9.2 반려 대응 템플릿(강화 버전, 복붙용)

아래 템플릿은 “재현 불가”, “권한 사용 근거 부족”, “URL 접근 실패” 유형 반려 대응용입니다.

```text
Subject: Meta App Review Resubmission - Reproducible Evidence Attached

Hello Meta App Review Team,

Thank you for your feedback. We have addressed the reported issues and prepared reproducible verification evidence.

1) Public policy URLs (accessible without login)
- Privacy Policy: https://facebook-login-oaut.streamlit.app/Privacy
- Data Deletion Instructions: https://facebook-login-oaut.streamlit.app/Data_Deletion

2) OAuth reproduction flow
1. Open https://facebook-login-oaut.streamlit.app/Login
2. Click the Facebook login button and grant the requested permissions.
3. After redirect back to /Login, the connected Instagram Business account details are shown.

3) Permission usage proof in product
- /Dashboard: metrics/charts and audience section
- /Live_Insights: profile, insights, audience demographics, connected Pages

4) Console configuration verified
- App Domains includes: facebook-login-oaut.streamlit.app
- Valid OAuth Redirect URIs includes: https://facebook-login-oaut.streamlit.app/Login

5) Evidence package
- Updated screencast link: <insert_link>
- Optional screenshots: App Domains, Redirect URI settings, public URL access

Please let us know if any additional evidence is needed.

Best regards,
<App Owner Name>
```

제출 팁:
- 메일/설명에는 반드시 **실제 URL**을 넣고, placeholder(`your-app...`)를 남기지 마세요.
- 스크린캐스트 링크는 접근 가능한 권한으로 공유하세요(심사관이 볼 수 있어야 함).

Pass 기준:
- 반려 사유가 “URL 접근 불가/리다이렉트 불일치/권한 사용 증빙 부족” 유형이면 위 패키지로 재현/증빙이 가능

---

### 부록: 운영자가 자주 쓰는 링크/경로

- Login: `/Login`
- Dashboard: `/Dashboard`
- Live Insights: `/Live_Insights`
- Privacy: `/Privacy`
- Data Deletion: `/Data_Deletion`
