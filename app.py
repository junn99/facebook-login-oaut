"""Main Streamlit application entry point."""

import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler

from src.database import init_db
from src.config import config

# Page configuration
st.set_page_config(
    page_title="Instagram Insights",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database on app start
init_db()

# Initialize session state
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "instagram_username" not in st.session_state:
    st.session_state.instagram_username = None
if "scheduler_started" not in st.session_state:
    st.session_state.scheduler_started = False


def start_background_scheduler():
    """Start APScheduler for background jobs."""
    if st.session_state.scheduler_started:
        return

    from jobs.collect_insights import run_collection
    from jobs.refresh_tokens import run_token_refresh

    scheduler = BackgroundScheduler()

    # Collect insights every 6 hours
    scheduler.add_job(run_collection, "interval", hours=6, id="collect_insights")

    # Refresh tokens daily
    scheduler.add_job(run_token_refresh, "interval", days=1, id="refresh_tokens")

    scheduler.start()
    st.session_state.scheduler_started = True


# Start scheduler (only in production)
if config.SUPABASE_URL:
    start_background_scheduler()


# Main page content
st.title("📊 Instagram Insights Dashboard")

# Check configuration
missing = config.validate()
if missing:
    st.error(f"⚠️ Missing configuration: {', '.join(missing)}")
    st.info("Please configure the required environment variables.")
    st.stop()

# Show login status
if st.session_state.user_id:
    st.success(f"✅ Logged in as @{st.session_state.instagram_username}")
    st.info("Navigate to **Dashboard** to view your insights.")
else:
    st.warning("Please log in with your Instagram Business account to get started.")
    st.info("Go to **Login** page in the sidebar to connect your account.")

# Quick stats section
st.markdown("---")
st.subheader("Quick Guide")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 1️⃣ Login")
    st.write("Connect your Instagram Business account via Facebook OAuth.")

with col2:
    st.markdown("### 2️⃣ Dashboard")
    st.write("View your engagement metrics, reach, and follower trends.")

with col3:
    st.markdown("### 3️⃣ Automatic Collection")
    st.write("Insights are collected automatically every 6 hours.")
