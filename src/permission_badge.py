"""Permission badge display helper for Meta App Review."""
import streamlit as st

PERMISSIONS = {
    "instagram_basic": {
        "label": "instagram_basic",
        "description": "Basic account info and profile data",
    },
    "instagram_manage_insights": {
        "label": "instagram_manage_insights",
        "description": "Account insights and analytics metrics",
    },
    "pages_show_list": {
        "label": "pages_show_list",
        "description": "List of Facebook Pages managed by user",
    },
    "pages_read_engagement": {
        "label": "pages_read_engagement",
        "description": "Page engagement and audience data",
    },
}


def show_permission_badge(permission_key: str) -> None:
    """Display a permission badge caption."""
    perm = PERMISSIONS.get(permission_key)
    if perm:
        st.caption(f"🔑 Permission: `{perm['label']}` -- {perm['description']}")
