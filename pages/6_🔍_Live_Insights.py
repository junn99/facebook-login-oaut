"""Live Insights - Real-time API demonstration for Meta App Review."""
import streamlit as st
import pandas as pd

from src.database import init_db, get_all_users, get_user_token
from src.instagram_api import InstagramAPI, InstagramAPIError
from src.oauth import get_user_pages
from src.permission_badge import show_permission_badge

st.set_page_config(page_title="Live Insights", page_icon="🔍", layout="wide")
init_db()

st.title("🔍 실시간 인사이트 / Live Insights")
st.info("This page demonstrates live Instagram Graph API calls using the granted permissions.")

# User selection
users = get_all_users()
if not users:
    st.warning("연결된 계정이 없습니다. 로그인 페이지에서 인스타그램 비즈니스 계정을 연결해주세요.")
    st.stop()

user_options = {f"@{u.instagram_username}": u for u in users}
selected_username = st.sidebar.selectbox("계정 선택", list(user_options.keys()))
selected_user = user_options[selected_username]

page_token = get_user_token(selected_user.id, "page")
if not page_token:
    st.error("유효한 페이지 토큰이 없습니다. 다시 로그인해주세요.")
    st.stop()

api = InstagramAPI(page_token.access_token, selected_user.instagram_id)

st.markdown("---")

# Section 1: Profile Information (instagram_basic)
st.subheader("1. 프로필 정보 / Profile Information")
show_permission_badge("instagram_basic")
try:
    info = api.get_account_info()
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**사용자명 / Username:** @{info.get('username', 'N/A')}")
        st.write(f"**이름 / Name:** {info.get('name', 'N/A')}")
        st.write(f"**소개 / Biography:** {info.get('biography', 'N/A')}")
    with col2:
        st.metric("팔로워 / Followers", f"{info.get('followers_count', 0):,}")
        st.metric("팔로잉 / Following", f"{info.get('follows_count', 0):,}")
        st.metric("게시물 / Posts", f"{info.get('media_count', 0):,}")
    with st.expander("API Details"):
        st.code(f"GET /{selected_user.instagram_id}?fields=id,username,name,profile_picture_url,followers_count,follows_count,media_count,biography")
except InstagramAPIError as e:
    st.error(f"API Error: {e}")

st.markdown("---")

# Section 2: Business Insights (instagram_manage_insights)
st.subheader("2. 비즈니스 인사이트 / Business Insights")
show_permission_badge("instagram_manage_insights")
try:
    insights = api.get_insights(period="day")
    if insights:
        df = pd.DataFrame(insights)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("현재 사용 가능한 인사이트 데이터가 없습니다.")
    with st.expander("API Details"):
        st.code(f"GET /{selected_user.instagram_id}/insights?metric=impressions,reach,profile_views,follower_count&period=day&metric_type=total_value")
except InstagramAPIError as e:
    st.error(f"API Error: {e}")

st.markdown("---")

# Section 3: Audience Demographics (instagram_manage_insights + pages_read_engagement)
st.subheader("3. 오디언스 인구통계 / Audience Demographics")
show_permission_badge("instagram_manage_insights")
show_permission_badge("pages_read_engagement")
try:
    audience = api.get_audience_data()
    if audience:
        for key, data in audience.items():
            st.write(f"**{key}:**")
            if data:
                df = pd.DataFrame(list(data.items()), columns=["Category", "Count"])
                df = df.nlargest(10, "Count")
                st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("현재 사용 가능한 오디언스 데이터가 없습니다.")
    with st.expander("API Details"):
        st.code(f"GET /{selected_user.instagram_id}/insights?metric=follower_demographics&period=lifetime&metric_type=total_value")
except InstagramAPIError as e:
    st.error(f"API Error: {e}")

st.markdown("---")

# Section 4: Connected Facebook Pages (pages_show_list)
st.subheader("4. 연결된 Facebook 페이지 / Connected Facebook Pages")
show_permission_badge("pages_show_list")
user_token = get_user_token(selected_user.id, "user")
if user_token:
    try:
        pages = get_user_pages(user_token.access_token)
        if pages:
            page_data = []
            for page in pages:
                page_data.append({
                    "Page Name": page.get("name", "N/A"),
                    "Page ID": page.get("id", "N/A"),
                    "Has Instagram": "✅" if "instagram_business_account" in page else "❌",
                })
            st.dataframe(pd.DataFrame(page_data), use_container_width=True, hide_index=True)
        else:
            st.info("연결된 Facebook 페이지가 없습니다.")
        with st.expander("API Details"):
            st.code("GET /me/accounts?fields=id,name,access_token,instagram_business_account")
    except Exception as e:
        st.error(f"API Error: {e}")
else:
    st.warning("유효한 사용자 토큰이 없습니다.")
