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
    """Render the sidebar profile card used on the landing page."""
    sync_user_profile_state()

    if not st.session_state.get("authenticated"):
        st.markdown(
            """
            <div class="sidebar-profile-card">
                <div class="sidebar-profile-avatar">A</div>
                <div class="sidebar-profile-name">Artify AI</div>
                <div class="sidebar-profile-meta">Sign in to save your creations</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    user_name = str(st.session_state.get("user_name") or "User").strip() or "User"
    profile_image = st.session_state.get("profile_image")
    login_method = st.session_state.get("login_method") or "local"
    meta_label = "Signed in with Google" if login_method == "google" else "Signed in"
    initials = "".join(part[:1] for part in user_name.split()[:2]).upper() or "U"

    if profile_image:
        avatar_html = (
            f'<img class="sidebar-profile-image" src="{escape(profile_image, quote=True)}" '
            f'alt="{escape(user_name, quote=True)}">'
        )
    else:
        avatar_html = f'<div class="sidebar-profile-avatar">{escape(initials)}</div>'

    st.markdown(
        f"""
        <div class="sidebar-profile-card">
            {avatar_html}
            <div class="sidebar-profile-name">{escape(user_name)}</div>
            <div class="sidebar-profile-meta">{escape(meta_label)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
