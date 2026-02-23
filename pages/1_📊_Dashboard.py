"""Dashboard page for viewing Instagram insights."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.database import (
    init_db,
    get_user_by_id,
    get_insights,
    get_latest_insights,
    get_latest_audience_data,
    get_user_token,
)
from src.insights_collector import collect_insights_for_user, collect_audience_for_user
from src.permission_badge import show_permission_badge

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
init_db()

st.title("📊 인스타그램 인사이트 대시보드")

user_id = st.session_state.get("user_id")
if not user_id:
    st.warning(
        "로그인이 필요합니다. 로그인 페이지에서 인스타그램 계정을 먼저 연결해주세요."
    )
    st.stop()

selected_user = get_user_by_id(user_id)
if not selected_user:
    st.error("로그인된 사용자를 찾을 수 없습니다. 다시 로그인해주세요.")
    st.stop()
if selected_user.id is None:
    st.error("사용자 정보가 올바르지 않습니다. 다시 로그인해주세요.")
    st.stop()
selected_user_id = selected_user.id

# Date range selection
st.sidebar.markdown("---")
date_range = st.sidebar.selectbox(
    "기간", ["최근 7일", "최근 30일", "최근 90일"], index=0
)

days_map = {"최근 7일": 7, "최근 30일": 30, "최근 90일": 90}
days = days_map[date_range]
start_date = datetime.utcnow() - timedelta(days=days)

# Manual refresh button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 데이터 새로고침"):
    token = get_user_token(selected_user_id, "page")
    if token:
        with st.spinner("인사이트 수집 중..."):
            result = collect_insights_for_user(
                selected_user_id, selected_user.instagram_id, token.access_token
            )
            if result["success"]:
                st.sidebar.success(f"{result['insights_count']}개 지표 수집 완료!")
            else:
                st.sidebar.error(result["error"])

            audience_result = collect_audience_for_user(
                selected_user_id, selected_user.instagram_id, token.access_token
            )
            if audience_result["success"]:
                st.sidebar.success("오디언스 데이터 업데이트 완료!")
    else:
        st.sidebar.error("유효한 토큰이 없습니다. 다시 로그인해주세요.")

# Get data
insights = get_insights(selected_user_id, start_date=start_date)
latest = get_latest_insights(selected_user_id)
audience = get_latest_audience_data(selected_user_id)

# Auto-collect if no data exists (first login)
if not insights and not latest:
    token = get_user_token(selected_user_id, "page")
    if token:
        with st.spinner("첫 로그인 데이터를 수집하고 있습니다..."):
            result = collect_insights_for_user(
                selected_user_id, selected_user.instagram_id, token.access_token
            )
            if result["success"] and result["insights_count"] > 0:
                st.success(f"✅ {result['insights_count']}개 인사이트 수집 완료!")
            elif result["success"]:
                st.warning(
                    "인사이트 데이터가 아직 없습니다. 비즈니스 계정 활동 후 다시 시도하세요."
                )
            else:
                st.warning(f"인사이트 수집 실패: {result['error']}")

            audience_result = collect_audience_for_user(
                selected_user_id, selected_user.instagram_id, token.access_token
            )
            if audience_result["success"]:
                st.success("✅ 오디언스 데이터 수집 완료!")

        # Re-fetch data after collection
        insights = get_insights(selected_user_id, start_date=start_date)
        latest = get_latest_insights(selected_user_id)
        audience = get_latest_audience_data(selected_user_id)

# Summary metrics
st.subheader("📈 주요 지표")
show_permission_badge("instagram_manage_insights")
col1, col2, col3, col4 = st.columns(4)

with col1:
    value = latest.get("follower_count", None)
    st.metric("팔로워", f"{int(value.metric_value):,}" if value else "N/A")

with col2:
    value = latest.get("impressions", None)
    st.metric("노출", f"{int(value.metric_value):,}" if value else "N/A")

with col3:
    value = latest.get("reach", None)
    st.metric("도달", f"{int(value.metric_value):,}" if value else "N/A")

with col4:
    value = latest.get("profile_views", None)
    st.metric("프로필 조회", f"{int(value.metric_value):,}" if value else "N/A")

st.markdown("---")

# Trends chart
if insights:
    st.subheader("📊 시간별 추이")
    show_permission_badge("instagram_manage_insights")

    # Convert to DataFrame
    df = pd.DataFrame(
        [
            {"date": i.collected_at, "metric": i.metric_name, "value": i.metric_value}
            for i in insights
        ]
    )

    if not df.empty:
        # Metric selection
        available_metrics = df["metric"].unique().tolist()
        selected_metrics = st.multiselect(
            "표시할 지표 선택",
            available_metrics,
            default=available_metrics[:3]
            if len(available_metrics) > 3
            else available_metrics,
        )

        if selected_metrics:
            filtered_df = df[df["metric"].isin(selected_metrics)]

            fig = px.line(
                filtered_df,
                x="date",
                y="value",
                color="metric",
                title="시간별 지표 추이",
                labels={"date": "날짜", "value": "값", "metric": "지표"},
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info(
        "아직 인사이트 데이터가 없습니다. '데이터 새로고침' 버튼을 클릭하여 수집하세요."
    )

st.markdown("---")

# Audience demographics
st.subheader("👥 오디언스 인구통계")
show_permission_badge("instagram_manage_insights")
show_permission_badge("pages_read_engagement")

if audience:
    col1, col2 = st.columns(2)

    with col1:
        # Find city or country data
        for key in audience:
            if "city" in key.lower():
                data = audience[key]
                if data:
                    df = pd.DataFrame(list(data.items()), columns=["위치", "수"])
                    df = df.nlargest(10, "수")
                    fig = px.bar(df, x="위치", y="수", title="상위 도시")
                    st.plotly_chart(fig, use_container_width=True)
                break

    with col2:
        # Find country data
        for key in audience:
            if "country" in key.lower():
                data = audience[key]
                if data:
                    df = pd.DataFrame(list(data.items()), columns=["국가", "수"])
                    df = df.nlargest(10, "수")
                    fig = px.pie(df, names="국가", values="수", title="상위 국가")
                    st.plotly_chart(fig, use_container_width=True)
                break

    # Age/gender breakdown
    for key in audience:
        if "age" in key.lower() or "gender" in key.lower():
            data = audience[key]
            if data:
                df = pd.DataFrame(list(data.items()), columns=["인구통계", "수"])
                fig = px.bar(df, x="인구통계", y="수", title="연령 및 성별 분포")
                st.plotly_chart(fig, use_container_width=True)
            break
else:
    st.info(
        "아직 오디언스 데이터가 없습니다. '데이터 새로고침' 버튼을 클릭하여 수집하세요."
    )

# Permission usage summary (for Meta App Review)
st.markdown("---")
st.subheader("🔑 Permission Usage Summary")
st.caption(
    "This table shows how each requested permission is used in this application."
)

permission_data = [
    {
        "Permission": "instagram_basic",
        "Used In": "Profile Info, Account Setup",
        "API Endpoint": "GET /{ig-user-id}?fields=id,username,...",
    },
    {
        "Permission": "instagram_manage_insights",
        "Used In": "Dashboard Metrics, Trends, Live Insights",
        "API Endpoint": "GET /{ig-user-id}/insights",
    },
    {
        "Permission": "pages_show_list",
        "Used In": "Login (find linked Instagram account)",
        "API Endpoint": "GET /me/accounts",
    },
    {
        "Permission": "pages_read_engagement",
        "Used In": "Audience Demographics",
        "API Endpoint": "GET /{ig-user-id}/insights (audience metrics)",
    },
    {
        "Permission": "business_management",
        "Used In": "Login (Business Manager page discovery fallback)",
        "API Endpoint": "GET /me/businesses, GET /{business-id}/owned_pages",
    },
]
st.dataframe(pd.DataFrame(permission_data), use_container_width=True, hide_index=True)
