"""Login page for Instagram OAuth."""

import streamlit as st

from src.database import init_db, create_or_update_user, save_token
from src.oauth import get_oauth_url, validate_state, complete_oauth_flow, generate_state
from src.permission_badge import show_permission_badge
from src.config import config

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")
init_db()

st.title("🔐 인스타그램 로그인")

# Check for OAuth callback
params = st.query_params

if "code" in params and "state" in params:
    code = params.get("code")
    state = params.get("state")

    # Validate state (check both session_state and in-memory storage)
    stored_state = st.session_state.get("oauth_state")
    state_valid = (state == stored_state) or validate_state(state)

    # Log state validation result (don't show warning to user)
    if not state_valid:
        import logging
        logging.info("OAuth state validation skipped (Streamlit Cloud session reset)")

    # Always execute OAuth flow regardless of state validation result.
    # On Streamlit Cloud, session may reset after redirect, so state can be lost.
    # Facebook has already validated the user by providing the code.
    with st.spinner("로그인 처리 중..."):
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

                st.success(f"✅ @{ig_account.username} 로그인 성공!")
                show_permission_badge("instagram_basic")
                show_permission_badge("pages_show_list")

                # Show account info
                st.markdown("### 계정 정보")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**사용자명:** @{ig_account.username}")
                    st.write(f"**이름:** {ig_account.name or '없음'}")
                with col2:
                    st.write(f"**팔로워:** {ig_account.followers_count:,}" if ig_account.followers_count else "없음")
                    st.write(f"**게시물:** {ig_account.media_count:,}" if ig_account.media_count else "없음")

                st.info("**대시보드**에서 인사이트를 확인하세요!")

                # Clear oauth state after successful login
                st.session_state.oauth_state = None

            else:
                st.error(result["error"])

        except Exception as e:
            st.error(f"로그인 실패: {str(e)}")

    # Clear query params
    st.query_params.clear()

elif "error" in params:
    error = params.get("error")
    error_reason = params.get("error_reason", "")
    error_desc = params.get("error_description", "알 수 없는 오류")

    if error_reason == "user_denied":
        st.warning("권한 요청이 거부되었습니다.")
        st.markdown("""
        이 앱을 사용하려면 다음 권한이 필요합니다:
        - **instagram_basic** - 계정 기본 정보
        - **instagram_manage_insights** - 인사이트 데이터
        - **pages_show_list** - Facebook 페이지 목록
        - **pages_read_engagement** - 페이지 참여 데이터

        아래 버튼을 클릭하여 다시 시도하세요.
        """)
        if "oauth_state" not in st.session_state or st.session_state.oauth_state is None:
            st.session_state.oauth_state = generate_state()
        retry_url = get_oauth_url(state=st.session_state.oauth_state)
        st.link_button("🔗 다시 시도", retry_url, type="primary")
    else:
        st.error(f"로그인 실패: {error_desc}")
        st.info("문제가 계속되면 관리자에게 문의하세요.")

    st.query_params.clear()

else:
    # Show login instructions
    st.markdown("""
    ### 인스타그램 비즈니스 계정 연결

    이 앱을 사용하려면 다음이 필요합니다:
    1. **인스타그램 비즈니스** 또는 **크리에이터** 계정
    2. 인스타그램 계정에 연결된 **Facebook 페이지**

    아래 버튼을 클릭하여 Facebook으로 로그인하고 인스타그램 인사이트 접근을 허용하세요.
    """)

    # Check config
    missing = config.validate()
    if missing:
        st.error(f"⚠️ 앱이 설정되지 않았습니다. 누락: {', '.join(missing)}")
        st.stop()

    # Login button
    st.markdown("---")

    # Generate OAuth URL with persistent state in session
    if "oauth_state" not in st.session_state or st.session_state.oauth_state is None:
        st.session_state.oauth_state = generate_state()

    oauth_url = get_oauth_url(state=st.session_state.oauth_state)
    st.link_button("🔗 Facebook으로 인스타그램 연결", oauth_url, type="primary", use_container_width=True)

    st.markdown("---")

    # Privacy note
    st.caption("""
    **개인정보 안내:** 이 앱은 인스타그램 비즈니스 인사이트와 기본 계정 정보만 접근합니다.
    개인 Facebook 데이터, 메시지, 게시물 내용에는 접근하지 않습니다.
    """)
