"""Dashboard page for viewing Instagram insights."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.database import (
    init_db,
    get_all_users,
    get_insights,
    get_latest_insights,
    get_latest_audience_data,
    get_user_token,
)
from src.insights_collector import collect_insights_for_user, collect_audience_for_user

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
init_db()

st.title("📊 인스타그램 인사이트 대시보드")

# Get all users
users = get_all_users()

if not users:
    st.warning("연결된 계정이 없습니다. 로그인 페이지에서 인스타그램 비즈니스 계정을 연결해주세요.")
    st.stop()

# User selection
user_options = {f"@{u.instagram_username}": u for u in users}
selected_username = st.sidebar.selectbox("계정 선택", list(user_options.keys()))
selected_user = user_options[selected_username]

# Date range selection
st.sidebar.markdown("---")
date_range = st.sidebar.selectbox(
    "기간",
    ["최근 7일", "최근 30일", "최근 90일"],
    index=0
)

days_map = {"최근 7일": 7, "최근 30일": 30, "최근 90일": 90}
days = days_map[date_range]
start_date = datetime.utcnow() - timedelta(days=days)

# Manual refresh button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 데이터 새로고침"):
    token = get_user_token(selected_user.id, "page")
    if token:
        with st.spinner("인사이트 수집 중..."):
            result = collect_insights_for_user(
                selected_user.id, selected_user.instagram_id, token.access_token
            )
            if result["success"]:
                st.sidebar.success(f"{result['insights_count']}개 지표 수집 완료!")
            else:
                st.sidebar.error(result["error"])

            audience_result = collect_audience_for_user(
                selected_user.id, selected_user.instagram_id, token.access_token
            )
            if audience_result["success"]:
                st.sidebar.success("오디언스 데이터 업데이트 완료!")
    else:
        st.sidebar.error("유효한 토큰이 없습니다. 다시 로그인해주세요.")

# Get data
insights = get_insights(selected_user.id, start_date=start_date)
latest = get_latest_insights(selected_user.id)
audience = get_latest_audience_data(selected_user.id)

# Summary metrics
st.subheader("📈 주요 지표")
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

    # Convert to DataFrame
    df = pd.DataFrame([
        {
            "date": i.collected_at,
            "metric": i.metric_name,
            "value": i.metric_value
        }
        for i in insights
    ])

    if not df.empty:
        # Metric selection
        available_metrics = df["metric"].unique().tolist()
        selected_metrics = st.multiselect(
            "표시할 지표 선택",
            available_metrics,
            default=available_metrics[:3] if len(available_metrics) > 3 else available_metrics
        )

        if selected_metrics:
            filtered_df = df[df["metric"].isin(selected_metrics)]

            fig = px.line(
                filtered_df,
                x="date",
                y="value",
                color="metric",
                title="시간별 지표 추이",
                labels={"date": "날짜", "value": "값", "metric": "지표"}
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("아직 인사이트 데이터가 없습니다. '데이터 새로고침' 버튼을 클릭하여 수집하세요.")

st.markdown("---")

# Audience demographics
st.subheader("👥 오디언스 인구통계")

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
    st.info("아직 오디언스 데이터가 없습니다. '데이터 새로고침' 버튼을 클릭하여 수집하세요.")
