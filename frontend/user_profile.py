from __future__ import annotations

from html import escape

import streamlit as st


PROFILE_STATE_KEYS = ("user_name", "profile_image", "profile_picture", "login_method")


def set_user_profile_state(
    user_name: str | None = None,
    profile_image: str | None = None,
    login_method: str | None = None,
) -> None:
    """Persist lightweight profile data used across Streamlit pages."""
    clean_name = (user_name or "").strip() or None
    clean_image = (profile_image or "").strip() or None
    clean_method = (login_method or "").strip() or None

    st.session_state.user_name = clean_name
    st.session_state.profile_image = clean_image
    st.session_state.profile_picture = clean_image
    st.session_state.login_method = clean_method


def clear_user_profile_state() -> None:
    """Clear transient profile state on logout."""
    for key in PROFILE_STATE_KEYS:
        st.session_state[key] = None


def sync_user_profile_state() -> None:
    """Keep profile keys aligned with the current auth session."""
    is_authenticated = bool(
        st.session_state.get("logged_in") or st.session_state.get("authenticated")
    )
    if not is_authenticated:
        clear_user_profile_state()
        return

    user_name = (
        st.session_state.get("user_name") or st.session_state.get("username") or "User"
    )
    profile_image = (
        st.session_state.get("profile_image") or st.session_state.get("profile_picture")
    )

    st.session_state.user_name = user_name
    st.session_state.profile_image = profile_image
    st.session_state.profile_picture = profile_image
    st.session_state.login_method = st.session_state.get("login_method") or "local"


def render_sidebar_profile() -> None:
    """Render the sidebar profile card used across the app."""
    sync_user_profile_state()
    is_logged_in = st.session_state.get("is_logged_in", st.session_state.get("logged_in", False))

    if not is_logged_in:
        return

    user_name = st.session_state.get("user_name", "User")
    profile_image = st.session_state.get("profile_image")

    if not profile_image:
        safe_name = str(user_name).replace(" ", "+")
        profile_image = f"https://ui-avatars.com/api/?name={safe_name}&background=random&rounded=true"

    st.markdown(
        """
        <style>
        div[data-testid="stSidebarUserContent"] img, 
        .sidebar-avatar-img {
            width: 70px !important;
            height: 70px !important;
            border-radius: 50% !important;
            object-fit: cover !important;
            border: 2px solid #4f7df2;
            margin-left: auto;
            margin-right: auto;
            display: block;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.sidebar.container():
        st.markdown(
            f'''
            <div style="text-align: center; margin-bottom: 2rem; margin-top: 0.5rem;">
                <img src="{escape(profile_image, quote=True)}" class="sidebar-avatar-img" alt="Profile">
                <div style="margin-top: 0.8rem;">
                    <b>{escape(str(user_name))}</b>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )
