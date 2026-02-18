"""Privacy Policy page."""

import streamlit as st
from src.config import config

st.set_page_config(page_title="Privacy Policy", page_icon="🔒", layout="centered")

st.title("🔒 개인정보 처리방침 / Privacy Policy")
st.caption("최종 업데이트: 2026-02-11 / Last Updated: February 11, 2026")

st.markdown("---")

# Section 1: Data Collection
st.subheader("1. 수집하는 데이터 / Data We Collect")
st.markdown("""
본 앱은 Facebook OAuth를 통해 인스타그램 비즈니스 계정에 연결할 때 다음 데이터를 수집합니다:

This app collects the following data when you connect your Instagram Business account via Facebook OAuth:

**계정 정보 / Account Information:**
- 인스타그램 비즈니스 계정 ID / Instagram Business Account ID
- 인스타그램 사용자명 / Instagram Username
- 인스타그램 표시 이름 / Instagram Display Name
- 프로필 사진 URL / Profile Picture URL
- 팔로워 수 / Follower Count
- 게시물 수 / Media Count
- 연결된 Facebook 페이지 ID / Connected Facebook Page ID

**비즈니스 인사이트 데이터 / Business Insights Data:**
- 노출 수 (impressions) / Impressions
- 도달 수 (reach) / Reach
- 프로필 조회 수 (profile views) / Profile Views
- 팔로워 증감 추이 / Follower Count Trends

**오디언스 인구통계 / Audience Demographics:**
- 팔로워 도시 분포 / Follower City Distribution
- 팔로워 국가 분포 / Follower Country Distribution
- 팔로워 연령 및 성별 분포 / Follower Age and Gender Distribution

**인증 토큰 / Authentication Tokens:**
- Facebook 사용자 액세스 토큰 (비공개 데이터베이스에 저장) / Facebook User Access Token (stored in a private database)
- Facebook 페이지 액세스 토큰 (비공개 데이터베이스에 저장) / Facebook Page Access Token (stored in a private database)
""")

st.markdown("---")

# Section 2: How We Use Data
st.subheader("2. 데이터 사용 목적 / How We Use Your Data")
st.markdown("""
수집된 데이터는 **오직 다음 목적으로만** 사용됩니다:

Collected data is used **solely for the following purposes**:

- **인사이트 대시보드 표시** / Displaying your Instagram Business insights on the dashboard
- **시간별 지표 추이 차트 생성** / Generating time-series charts of your metrics
- **오디언스 인구통계 시각화** / Visualizing audience demographic breakdowns
- **토큰 관리 및 자동 갱신** / Managing and auto-refreshing authentication tokens

본 앱은 사용자의 개인 Facebook 데이터, 개인 메시지, 개인 게시물 내용에 접근하지 않습니다.

This app does NOT access your personal Facebook data, private messages, or personal post content.
""")

st.markdown("---")

# Section 3: Third-Party Sharing
st.subheader("3. 제3자 공유 / Third-Party Sharing")
st.markdown("""
**본 앱은 수집된 데이터를 제3자와 공유하지 않습니다.**

**We do NOT share your data with any third parties.**

- 데이터는 비공개 Supabase 데이터베이스에만 저장됩니다 / Data is stored only in a private Supabase database
- 광고 목적으로 데이터를 사용하지 않습니다 / Data is not used for advertising purposes
- 분석 서비스에 데이터를 전송하지 않습니다 / Data is not sent to analytics services
- 데이터를 판매하지 않습니다 / Data is never sold
""")

st.markdown("---")

# Section 4: Data Retention
st.subheader("4. 데이터 보존 기간 / Data Retention")
st.markdown("""
- **인사이트 데이터:** 수집일로부터 최대 **1년간** 보존됩니다 / Insights data is retained for up to **1 year** from collection date
- **계정 정보:** 계정 연결이 해제될 때까지 보존됩니다 / Account info is retained until the account is disconnected
- **인증 토큰:** 만료 시 자동으로 삭제됩니다 / Authentication tokens are automatically deleted upon expiration
""")

st.markdown("---")

# Section 5: Data Deletion
st.subheader("5. 데이터 삭제 / Data Deletion")
st.markdown(f"""
데이터 삭제를 요청할 수 있습니다:

You can request deletion of your data:

1. **Facebook 설정에서 앱 제거** / Remove the app from Facebook Settings
   - 자세한 방법은 [데이터 삭제 안내 페이지](/Data_Deletion)를 참고하세요
   - See the [Data Deletion Instructions page](/Data_Deletion) for detailed steps
2. **이메일로 삭제 요청** / Request deletion via email
   - {config.CONTACT_EMAIL} 로 삭제 요청을 보내주세요
   - Send a deletion request to {config.CONTACT_EMAIL}

삭제 요청은 **30일 이내**에 처리됩니다.

Deletion requests are processed within **30 days**.
""")

st.markdown("---")

# Section 6: Data Security
st.subheader("6. 데이터 보안 / Data Security")
st.markdown("""
- 모든 데이터는 HTTPS를 통해 전송됩니다 / All data is transmitted via HTTPS
- 액세스 토큰은 안전한 데이터베이스에 저장됩니다 / Access tokens are stored in a secure database
- OAuth 2.0 표준 인증 프로토콜을 사용합니다 / We use OAuth 2.0 standard authentication protocol
- CSRF 보호를 위한 state 파라미터를 사용합니다 / We use state parameters for CSRF protection
""")

st.markdown("---")

# Section 7: Contact
st.subheader("7. 연락처 / Contact Information")
st.markdown(f"""
개인정보 처리방침에 관한 문의:

For questions about this Privacy Policy:

 - **이메일 / Email:** {config.CONTACT_EMAIL}
""")

st.markdown("---")
st.caption(
    "본 개인정보 처리방침은 사전 고지 후 변경될 수 있습니다. / This privacy policy may be updated with prior notice."
)
