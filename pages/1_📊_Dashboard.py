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

st.title("📊 Instagram Insights Dashboard")

# Get all users
users = get_all_users()

if not users:
    st.warning("No accounts connected yet. Please go to the Login page to connect your Instagram Business account.")
    st.stop()

# User selection
user_options = {f"@{u.instagram_username}": u for u in users}
selected_username = st.sidebar.selectbox("Select Account", list(user_options.keys()))
selected_user = user_options[selected_username]

# Date range selection
st.sidebar.markdown("---")
date_range = st.sidebar.selectbox(
    "Time Range",
    ["Last 7 days", "Last 30 days", "Last 90 days"],
    index=0
)

days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
days = days_map[date_range]
start_date = datetime.utcnow() - timedelta(days=days)

# Manual refresh button
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data Now"):
    token = get_user_token(selected_user.id, "page")
    if token:
        with st.spinner("Collecting insights..."):
            result = collect_insights_for_user(
                selected_user.id, selected_user.instagram_id, token.access_token
            )
            if result["success"]:
                st.sidebar.success(f"Collected {result['insights_count']} metrics!")
            else:
                st.sidebar.error(result["error"])

            audience_result = collect_audience_for_user(
                selected_user.id, selected_user.instagram_id, token.access_token
            )
            if audience_result["success"]:
                st.sidebar.success(f"Updated audience data!")
    else:
        st.sidebar.error("No valid token found. Please re-login.")

# Get data
insights = get_insights(selected_user.id, start_date=start_date)
latest = get_latest_insights(selected_user.id)
audience = get_latest_audience_data(selected_user.id)

# Summary metrics
st.subheader("📈 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    value = latest.get("follower_count", None)
    st.metric("Followers", f"{int(value.metric_value):,}" if value else "N/A")

with col2:
    value = latest.get("impressions", None)
    st.metric("Impressions", f"{int(value.metric_value):,}" if value else "N/A")

with col3:
    value = latest.get("reach", None)
    st.metric("Reach", f"{int(value.metric_value):,}" if value else "N/A")

with col4:
    value = latest.get("profile_views", None)
    st.metric("Profile Views", f"{int(value.metric_value):,}" if value else "N/A")

st.markdown("---")

# Trends chart
if insights:
    st.subheader("📊 Trends Over Time")

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
            "Select metrics to display",
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
                title="Metrics Over Time",
                labels={"date": "Date", "value": "Value", "metric": "Metric"}
            )
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No insights data available yet. Click 'Refresh Data Now' to collect data.")

st.markdown("---")

# Audience demographics
st.subheader("👥 Audience Demographics")

if audience:
    col1, col2 = st.columns(2)

    with col1:
        # Find city or country data
        for key in audience:
            if "city" in key.lower():
                data = audience[key]
                if data:
                    df = pd.DataFrame(list(data.items()), columns=["Location", "Count"])
                    df = df.nlargest(10, "Count")
                    fig = px.bar(df, x="Location", y="Count", title="Top Cities")
                    st.plotly_chart(fig, use_container_width=True)
                break

    with col2:
        # Find country data
        for key in audience:
            if "country" in key.lower():
                data = audience[key]
                if data:
                    df = pd.DataFrame(list(data.items()), columns=["Country", "Count"])
                    df = df.nlargest(10, "Count")
                    fig = px.pie(df, names="Country", values="Count", title="Top Countries")
                    st.plotly_chart(fig, use_container_width=True)
                break

    # Age/gender breakdown
    for key in audience:
        if "age" in key.lower() or "gender" in key.lower():
            data = audience[key]
            if data:
                df = pd.DataFrame(list(data.items()), columns=["Demographic", "Count"])
                fig = px.bar(df, x="Demographic", y="Count", title="Age & Gender Distribution")
                st.plotly_chart(fig, use_container_width=True)
            break
else:
    st.info("No audience data available yet. Click 'Refresh Data Now' to collect data.")
