# Meta App Review One-Page Card

운영자가 제출 직전에 **딱 한 장으로 확인**할 수 있는 요약 카드입니다.

---

## 0) 오늘 목표

- 목표: Meta 심사자가 앱에서 권한 사용 흐름을 재현할 수 있게 준비
- 기준: URL 접근 가능 + OAuth 정상 + 권한별 화면 증빙 + 스크린캐스트 확보

---

## 1) 5분 사전 점검

- [ ] 배포 URL 확인: `https://facebook-login-oaut.streamlit.app`
- [ ] `OAUTH_REDIRECT_URI`가 `https://facebook-login-oaut.streamlit.app/Login`와 완전 일치
- [ ] `CONTACT_EMAIL` 실제 메일로 설정
- [ ] 아래 명령 통과:

```bash
".venv/bin/python" -m compileall -q .
".venv/bin/python" -m pytest -q
```

Pass 기준:
- 두 명령 모두 에러 없이 종료

---

## 2) Meta 콘솔 필수값

### Settings -> Basic
- [ ] `App Domains`에 `facebook-login-oaut.streamlit.app`
- [ ] `Privacy Policy URL` = `https://facebook-login-oaut.streamlit.app/Privacy`
- [ ] `Data Deletion Instructions URL` = `https://facebook-login-oaut.streamlit.app/Data_Deletion`

### Facebook Login -> Settings
- [ ] `Valid OAuth Redirect URIs`에 `https://facebook-login-oaut.streamlit.app/Login`
- [ ] (로컬 필요 시) `http://localhost:8501/Login`

Pass 기준:
- 실제 브라우저에서 URL 열었을 때 접근 가능 + OAuth 리다이렉트 에러 없음

---

## 3) 심사 재현 플로우 (2~3분 영상)

1. `/Login` 접속 -> Facebook 로그인/권한 승인
2. `/Dashboard`에서 지표/차트/오디언스 섹션 표시
3. `/Live_Insights`에서 프로필/인사이트/오디언스/Pages 섹션 표시
4. `/Privacy`, `/Data_Deletion` 공개 접근 확인

필수 권한 매핑:
- `instagram_basic` -> `/Login`, `/Live_Insights`
- `instagram_manage_insights` -> `/Dashboard`, `/Live_Insights`
- `pages_show_list` -> `/Login`, `/Live_Insights`
- `pages_read_engagement` -> `/Dashboard`, `/Live_Insights`

Pass 기준:
- 영상 1개에서 위 흐름이 끊기지 않고 확인 가능

---

## 4) 즉시 중단해야 하는 Fail 신호

- `redirect_uri mismatch`
- `/Privacy` 또는 `/Data_Deletion` 로그인 요구/에러
- `/Login`에서 state 검증 반복 실패
- 권한 사용 근거 화면이 영상에 안 잡힘

조치:
- 제출 중단 -> 콘솔/환경변수/도메인 재확인 -> 다시 촬영

---

## 5) 제출 메시지 초간단 템플릿

```text
Hello Meta App Review Team,

We addressed the feedback and prepared reproducible evidence.

Public URLs:
- Privacy: https://facebook-login-oaut.streamlit.app/Privacy
- Data Deletion: https://facebook-login-oaut.streamlit.app/Data_Deletion

Repro steps:
1) Open https://facebook-login-oaut.streamlit.app/Login
2) Grant requested permissions
3) Verify permission usage in /Dashboard and /Live_Insights

Screencast: <insert_link>

Thank you.
```

---

## 6) 운영 메모

- 문서 내 URL이 실서비스 도메인과 일치하는지 최종 확인하기
- 상세 절차는 `docs/META_APP_REVIEW_NEXT_STEPS.md` 참고
- 최소 체크리스트는 `docs/APP_REVIEW_CHECKLIST.md` 참고
