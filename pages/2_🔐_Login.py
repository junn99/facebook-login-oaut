"""Login page for Instagram OAuth."""

import streamlit as st

from src.database import init_db, create_or_update_user, save_token
from src.oauth import get_oauth_url, validate_state, complete_oauth_flow, generate_state
from src.config import config

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")
init_db()

st.title("🔐 Instagram Login")

# Check for OAuth callback
params = st.query_params

if "code" in params and "state" in params:
    code = params.get("code")
    state = params.get("state")

    # Validate state (check both session_state and in-memory storage)
    stored_state = st.session_state.get("oauth_state")
    state_valid = (state == stored_state) or validate_state(state)

    # For Streamlit Cloud: session may reset after redirect, so we allow the flow
    # if code is present (Facebook validated the request)
    if not state_valid:
        st.warning("State validation skipped. Proceeding with login...")
        # Don't block - Facebook already validated the user
    else:
        with st.spinner("Completing login..."):
            try:
                result = complete_oauth_flow(code)

                if result["success"]:
                    ig_account = result["instagram_account"]

                    # Create or update user
                    user = create_or_update_user(
                        instagram_id=ig_account.id,
                        instagram_username=ig_account.username,
                        facebook_page_id=result["page_id"],
                    )

                    # Save tokens
                    save_token(
                        user_id=user.id,
                        token_type="user",
                        access_token=result["user_token"],
                        expires_at=result["user_token_expires"],
                    )
                    save_token(
                        user_id=user.id,
                        token_type="page",
                        access_token=result["page_token"],
                        expires_at=None,  # Page tokens don't expire while user token is valid
                    )

                    # Update session state
                    st.session_state.user_id = user.id
                    st.session_state.instagram_username = user.instagram_username

                    st.success(f"✅ Successfully logged in as @{ig_account.username}!")

                    # Show account info
                    st.markdown("### Account Info")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Username:** @{ig_account.username}")
                        st.write(f"**Name:** {ig_account.name or 'N/A'}")
                    with col2:
                        st.write(f"**Followers:** {ig_account.followers_count:,}" if ig_account.followers_count else "N/A")
                        st.write(f"**Posts:** {ig_account.media_count:,}" if ig_account.media_count else "N/A")

                    st.info("Go to the **Dashboard** to view your insights!")

                    # Clear oauth state after successful login
                    st.session_state.oauth_state = None

                else:
                    st.error(result["error"])

            except Exception as e:
                st.error(f"Login failed: {str(e)}")

        # Clear query params
        st.query_params.clear()

elif "error" in params:
    error = params.get("error")
    error_desc = params.get("error_description", "Unknown error")
    st.error(f"Login failed: {error_desc}")
    st.query_params.clear()

else:
    # Show login instructions
    st.markdown("""
    ### Connect Your Instagram Business Account

    To use this app, you need:
    1. An **Instagram Business** or **Creator** account
    2. A **Facebook Page** connected to your Instagram account

    Click the button below to log in with Facebook and authorize access to your Instagram insights.
    """)

    # Check config
    missing = config.validate()
    if missing:
        st.error(f"⚠️ App not configured. Missing: {', '.join(missing)}")
        st.stop()

    # Login button
    st.markdown("---")

    # Generate OAuth URL with persistent state in session
    if "oauth_state" not in st.session_state or st.session_state.oauth_state is None:
        st.session_state.oauth_state = generate_state()

    oauth_url = get_oauth_url(state=st.session_state.oauth_state)
    st.link_button("🔗 Connect Instagram via Facebook", oauth_url, type="primary", use_container_width=True)

    st.markdown("---")

    # Privacy note
    st.caption("""
    **Privacy Note:** This app only accesses your Instagram Business insights and basic account information.
    We do not access your personal Facebook data, messages, or post content.
    """)
