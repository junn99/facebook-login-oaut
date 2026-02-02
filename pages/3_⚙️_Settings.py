"""Settings page for account management."""

import streamlit as st
from datetime import datetime

from src.database import (
    init_db,
    get_all_users,
    get_user_token,
    get_expiring_tokens,
)
from src.oauth import refresh_long_lived_token
from src.database import save_token

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")
init_db()

st.title("⚙️ Settings")

# Get all users
users = get_all_users()

if not users:
    st.warning("No accounts connected yet. Please go to the Login page first.")
    st.stop()

# Account management
st.subheader("📱 Connected Accounts")

for user in users:
    with st.expander(f"@{user.instagram_username}", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Instagram ID:** {user.instagram_id}")
            st.write(f"**Facebook Page ID:** {user.facebook_page_id}")
            st.write(f"**Connected:** {user.created_at.strftime('%Y-%m-%d') if user.created_at else 'N/A'}")

        with col2:
            # Token status
            user_token = get_user_token(user.id, "user")
            page_token = get_user_token(user.id, "page")

            if user_token and user_token.expires_at:
                days_left = (user_token.expires_at - datetime.utcnow()).days
                if days_left > 14:
                    st.success(f"✅ Token valid for {days_left} days")
                elif days_left > 0:
                    st.warning(f"⚠️ Token expires in {days_left} days")
                else:
                    st.error("❌ Token expired")
            else:
                st.info("Token status unknown")

            if page_token:
                st.success("✅ Page token active")
            else:
                st.error("❌ No page token")

        # Refresh token button
        if st.button(f"🔄 Refresh Token", key=f"refresh_{user.id}"):
            if user_token:
                try:
                    with st.spinner("Refreshing token..."):
                        new_token = refresh_long_lived_token(user_token.access_token)
                        save_token(
                            user_id=user.id,
                            token_type="user",
                            access_token=new_token["access_token"],
                            expires_at=new_token["expires_at"],
                        )
                    st.success(f"Token refreshed! New expiry: {new_token['expires_at'].strftime('%Y-%m-%d')}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to refresh: {str(e)}")
            else:
                st.error("No user token to refresh. Please log in again.")

st.markdown("---")

# Token expiration warnings
st.subheader("⏰ Token Status")

expiring = get_expiring_tokens(days=14)
if expiring:
    st.warning(f"⚠️ {len(expiring)} token(s) expiring within 14 days:")
    for user, token in expiring:
        days_left = (token.expires_at - datetime.utcnow()).days if token.expires_at else 0
        st.write(f"  • @{user.instagram_username}: {days_left} days left")
else:
    st.success("✅ All tokens are valid")

st.markdown("---")

# App info
st.subheader("ℹ️ About")
st.markdown("""
**Instagram Insights Dashboard**

This app collects and displays insights from your Instagram Business account:
- Engagement metrics (impressions, reach, profile views)
- Follower trends
- Audience demographics

**Data Collection:**
- Insights are collected automatically every 6 hours
- Tokens are refreshed automatically before expiration

**Privacy:**
- Your data is stored securely in a private database
- We only access business insights, not personal data
""")
