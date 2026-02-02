"""콘텐츠별 인사이트 페이지."""

import streamlit as st
from datetime import datetime

from src.database import init_db, get_all_users, get_user_token
from src.instagram_api import InstagramAPI

st.set_page_config(page_title="콘텐츠 인사이트", page_icon="📸", layout="wide")
init_db()

st.title("📸 콘텐츠 인사이트")

# Get users
users = get_all_users()

if not users:
    st.warning("연결된 계정이 없습니다. 로그인 페이지에서 계정을 연결하세요.")
    st.stop()

# User selection
user_options = {f"@{u.instagram_username}": u for u in users}
selected_username = st.sidebar.selectbox("계정 선택", list(user_options.keys()))
selected_user = user_options[selected_username]

# Get token
token = get_user_token(selected_user.id, "page")
if not token:
    st.error("유효한 토큰이 없습니다. 다시 로그인해주세요.")
    st.stop()

api = InstagramAPI(token.access_token, selected_user.instagram_id)

# Tabs for different content types
tab1, tab2, tab3 = st.tabs(["📷 게시물", "📖 스토리", "🎬 릴스"])

with tab1:
    st.subheader("📷 최근 게시물")

    with st.spinner("게시물 불러오는 중..."):
        try:
            media_list = api.get_media_list(limit=12)

            if not media_list:
                st.info("게시물이 없습니다.")
            else:
                # Display in grid
                cols = st.columns(3)
                for idx, media in enumerate(media_list):
                    with cols[idx % 3]:
                        # Media thumbnail
                        media_url = media.get("thumbnail_url") or media.get("media_url")
                        if media_url:
                            st.image(media_url, use_container_width=True)

                        # Media type badge
                        media_type = media.get("media_type", "")
                        type_emoji = {"IMAGE": "📷", "VIDEO": "🎥", "CAROUSEL_ALBUM": "🎠", "REELS": "🎬"}.get(media_type, "📷")

                        # Basic stats
                        likes = media.get("like_count", 0)
                        comments = media.get("comments_count", 0)
                        st.write(f"{type_emoji} ❤️ {likes:,}  💬 {comments:,}")

                        # Caption preview
                        caption = media.get("caption", "")[:50]
                        if caption:
                            st.caption(f"{caption}...")

                        # Detailed insights button
                        if st.button("상세 보기", key=f"detail_{media['id']}"):
                            with st.spinner("인사이트 불러오는 중..."):
                                insights = api.get_media_insights(media["id"], media_type)
                                if insights:
                                    st.markdown("**상세 인사이트:**")
                                    for metric, value in insights.items():
                                        label = {
                                            "impressions": "노출",
                                            "reach": "도달",
                                            "saved": "저장",
                                            "shares": "공유",
                                            "likes": "좋아요",
                                            "comments": "댓글",
                                            "video_views": "동영상 조회",
                                            "plays": "재생",
                                            "total_interactions": "총 상호작용",
                                        }.get(metric, metric)
                                        st.write(f"  • {label}: {value:,}")
                                else:
                                    st.info("인사이트 데이터가 없습니다.")

                        st.markdown("---")

        except Exception as e:
            st.error(f"오류 발생: {str(e)}")

with tab2:
    st.subheader("📖 현재 스토리")
    st.caption("스토리는 24시간 동안만 조회 가능합니다.")

    with st.spinner("스토리 불러오는 중..."):
        try:
            stories = api.get_stories()

            if not stories:
                st.info("현재 활성화된 스토리가 없습니다.")
            else:
                cols = st.columns(4)
                for idx, story in enumerate(stories):
                    with cols[idx % 4]:
                        media_url = story.get("media_url")
                        if media_url:
                            st.image(media_url, use_container_width=True)

                        # Time
                        timestamp = story.get("timestamp", "")
                        if timestamp:
                            st.caption(f"업로드: {timestamp[:10]}")

                        # Get insights
                        if st.button("인사이트", key=f"story_{story['id']}"):
                            insights = api.get_story_insights(story["id"])
                            if insights:
                                for metric, value in insights.items():
                                    label = {
                                        "impressions": "노출",
                                        "reach": "도달",
                                        "replies": "답장",
                                        "exits": "이탈",
                                        "taps_forward": "다음으로",
                                        "taps_back": "이전으로",
                                    }.get(metric, metric)
                                    st.write(f"  • {label}: {value:,}")
                            else:
                                st.info("인사이트 없음")

        except Exception as e:
            st.error(f"오류 발생: {str(e)}")

with tab3:
    st.subheader("🎬 릴스")

    with st.spinner("릴스 불러오는 중..."):
        try:
            # Filter for REELS only
            media_list = api.get_media_list(limit=25)
            reels = [m for m in media_list if m.get("media_type") == "REELS"]

            if not reels:
                st.info("릴스가 없습니다.")
            else:
                cols = st.columns(3)
                for idx, reel in enumerate(reels):
                    with cols[idx % 3]:
                        media_url = reel.get("thumbnail_url") or reel.get("media_url")
                        if media_url:
                            st.image(media_url, use_container_width=True)

                        likes = reel.get("like_count", 0)
                        comments = reel.get("comments_count", 0)
                        st.write(f"🎬 ❤️ {likes:,}  💬 {comments:,}")

                        caption = reel.get("caption", "")[:30]
                        if caption:
                            st.caption(f"{caption}...")

                        if st.button("상세 보기", key=f"reel_{reel['id']}"):
                            insights = api.get_media_insights(reel["id"], "REELS")
                            if insights:
                                st.markdown("**릴스 인사이트:**")
                                for metric, value in insights.items():
                                    label = {
                                        "plays": "재생",
                                        "reach": "도달",
                                        "saved": "저장",
                                        "shares": "공유",
                                        "likes": "좋아요",
                                        "comments": "댓글",
                                        "total_interactions": "총 상호작용",
                                    }.get(metric, metric)
                                    st.write(f"  • {label}: {value:,}")
                            else:
                                st.info("인사이트 없음")

                        st.markdown("---")

        except Exception as e:
            st.error(f"오류 발생: {str(e)}")

# Footer
st.markdown("---")
st.caption("💡 팁: 인사이트는 게시 후 일정 시간이 지나야 정확한 데이터가 수집됩니다.")
