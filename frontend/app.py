import base64
import sys
from pathlib import Path


import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.auth import register_user
from backend.auth_login import login_user
from backend.auth_google import get_google_auth_url, process_google_callback, has_google_credentials, REDIRECT_URI
from database.db import create_tables
from frontend.user_profile import (
    sync_user_profile_state,
    set_user_profile_state,
    render_sidebar_profile,
    clear_user_profile_state,
)


# ---------------------------------------------------------------------------
# ASSET PATHS  (needed before set_page_config for the page icon)
# ---------------------------------------------------------------------------
assets_dir = Path(__file__).resolve().parent / "assets"
icon_png = assets_dir / "artify_logo.png"
logo_svg = assets_dir / "artify_logo.svg"
logo_asset = logo_svg if logo_svg.exists() else icon_png
before1_image = assets_dir / "before1.png"
after1_image = assets_dir / "after1.png"
before_image = assets_dir / "before.jpeg"
cartoon_image = assets_dir / "cartoon_style.png"
pencil_color_image = assets_dir / "pencil_color.png"
sketch_image = assets_dir / "sketch_style.png"

# ---------------------------------------------------------------------------
# PAGE CONFIG  — must be the VERY FIRST Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Artify AI",
    page_icon=str(icon_png) if icon_png.exists() else ":art:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# PRIMER CSS — injected as the very first st.markdown call so the browser
# sets a white background and fades the app in smoothly, eliminating the
# "flash of old/default UI" before apply_styles() finishes executing.
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* 1. Lock the background to white IMMEDIATELY so there is no colour flash */
    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"] {
        background: #ffffff !important;
        background-color: #ffffff !important;
    }

    /* 2. Start hidden; JS below will trigger the fade-in once Streamlit
          has finished mounting the real content tree */
    .stApp {
        opacity: 0;
        transition: opacity 280ms ease;
    }
    </style>
    <script>
    (function () {
        // Poll until Streamlit's main content block is present, then reveal.
        var attempts = 0;
        function reveal() {
            attempts++;
            var app = document.querySelector('.stApp');
            if (app) {
                app.style.opacity = '1';
            } else if (attempts < 60) {
                requestAnimationFrame(reveal);
            }
        }
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', reveal);
        } else {
            reveal();
        }
    })();
    </script>
    """,
    unsafe_allow_html=True,
)


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

        /* GLOBAL */
        :root {
            --bg-top: #ffffff;
            --bg-mid: #ffffff;
            --bg-bottom: #f7f7f8;
            --ink-900: #111111;
            --ink-700: #222222;
            --ink-500: #555555;
            --brand-800: #111111;
            --brand-700: #111111;
            --brand-500: #111111;
            --accent-500: #555555;
            --card-bg: #ffffff;
            --card-stroke: #e5e7eb;
            --focus-ring: #111111;
        }

        html, body, .stApp {
            font-family: "Manrope", "Segoe UI", sans-serif;
            color: var(--ink-700);
            max-width: 100%;
            overflow-x: hidden !important;
        }

        html, body {
            background: #ffffff;
        }

        .stApp {
            background: #ffffff !important;
            background-attachment: scroll;
        }


        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stBottomBlockContainer"],
        [data-testid="stFormSubmitButton"] {
            background: transparent !important;
            background-color: transparent !important;
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--ink-900);
        }

        p, label, li, [data-testid="stMarkdownContainer"] {
            color: var(--ink-700);
        }

        .block-container {
            padding-top: 2.35rem;
            padding-bottom: 2.35rem;
            max-width: 1180px;
        }

        .stAlert {
            border-radius: 0.8rem;
            border: 1px solid #e5e7eb;
        }

        [data-testid="stLogo"] img,
        [data-testid="stLogo"] svg {
            max-height: 4.2rem !important;
            width: auto !important;
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
                scroll-behavior: auto !important;
            }
        }

        /* HEADER */
        [data-testid="stHeader"] {
            background: rgba(255, 255, 255, 0.92) !important;
            border-bottom: 1px solid rgba(229, 231, 235, 0.85) !important;
            box-shadow: none !important;
        }

        [data-testid="stToolbar"] {
            background: transparent !important;
        }

        [data-testid="stDecoration"] {
            background: transparent !important;
        }

        .st-key-hero_showcase_shell {
            position: relative;
            padding: clamp(0.6rem, 1.2vw, 1.1rem) 0 2.2rem 0;
        }

        .st-key-hero_showcase_shell > div {
            position: relative;
        }

        .st-key-hero_showcase_shell > div::before {
            content: "";
            position: absolute;
            right: 4%;
            top: 2%;
            width: 18rem;
            height: 18rem;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(77, 127, 245, 0.14) 0%, rgba(77, 127, 245, 0) 72%);
            filter: blur(10px);
            pointer-events: none;
            z-index: 0;
        }

        .st-key-hero_showcase_shell > div > div {
            position: relative;
            z-index: 1;
        }

        .artify-hero-copy {
            max-width: 36rem;
            padding-top: clamp(0.6rem, 2vw, 2.3rem);
        }

        .artify-hero-title {
            margin: 0;
            font-size: clamp(3rem, 6vw, 5.2rem);
            line-height: 0.98;
            font-weight: 800;
            letter-spacing: -0.055em;
            color: #1f2937;
        }

        .artify-hero-gradient,
        .artify-hero-accent {
            background: linear-gradient(135deg, #4f7df2 0%, #1ab6df 100%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            -webkit-text-fill-color: transparent;
        }

        .artify-hero-desc {
            margin: 1.6rem 0 0 0;
            max-width: 32rem;
            color: #5b667a;
            font-size: 1.08rem;
            line-height: 1.7;
        }

        /* SIDEBAR */
        [data-testid="stSidebar"] {
            border-right: 1px solid #e5e7eb !important;
            background: #ffffff !important;
            color: var(--ink-700);
            backdrop-filter: none;
            padding-top: 0.35rem !important;
        }

        [data-testid="stSidebarNav"] {
            display: none !important;
            background: transparent !important;
            padding-top: 0.35rem !important;
        }

        [data-testid="stSidebarNavItems"] {
            gap: 0.2rem !important;
            padding-top: 0.15rem !important;
        }

        [data-testid="stSidebarNavLink"] {
            background: transparent !important;
            border-radius: 0.9rem !important;
            color: #334155 !important;
            padding: 0.55rem 0.75rem !important;
        }

        [data-testid="stSidebarNavLink"]:hover,
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background: #f8fafc !important;
            color: #0f172a !important;
        }

        [data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebarContent"] {
            background: #ffffff !important;
        }

        button[data-testid="collapsedControl"] {
            background: #ffffff !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 0.6rem !important;
            min-width: 2.3rem !important;
            min-height: 2.3rem !important;
            box-shadow: 0 8px 18px rgba(148, 163, 184, 0.16) !important;
            /* BUG FIX 3: color must be set so the SVG icon inherits currentColor */
            color: #24324a !important;
        }

        button[data-testid="collapsedControl"] svg,
        [data-testid="stSidebarNav"] svg {
            fill: #24324a !important;
            color: #24324a !important;
            stroke: #24324a !important;
        }

        /* Ensure the icon span/path inside the collapsed control is visible */
        button[data-testid="collapsedControl"] span,
        button[data-testid="collapsedControl"] path {
            fill: #24324a !important;
            stroke: #24324a !important;
            color: #24324a !important;
        }

        [data-testid="stSidebarNav"] a {
            color: var(--ink-700) !important;
        }

        /* AUTH MODAL */
        .st-key-auth_shell {
            max-width: 33rem;
            margin: 0 auto;
            background: linear-gradient(180deg, #ffffff 0%, #fcfdff 100%);
            border: 1px solid #edf2f7;
            border-radius: 1.9rem;
            padding: 1.25rem 1.35rem 1.3rem 1.35rem;
            box-shadow: 0 30px 80px rgba(59, 130, 246, 0.14);
            animation: fadeInUp 380ms ease both;
        }

        .st-key-auth_shell label,
        .st-key-auth_shell p,
        .st-key-auth_shell .stCaptionContainer {
            color: var(--ink-700) !important;
        }

        .auth-shell-head {
            text-align: center;
            margin-bottom: 1.1rem;
        }

        .auth-title {
            margin: 0;
            color: #24324a;
            font-size: clamp(2rem, 4vw, 2.45rem);
            line-height: 1.02;
            letter-spacing: -0.04em;
            font-weight: 800;
        }

        .auth-subtitle {
            margin: 0.72rem 0 0 0;
            color: #64748b;
            font-size: 0.99rem;
            line-height: 1.55;
        }

        .auth-social-stack {
            display: grid;
            gap: 0.72rem;
            margin: 1.15rem 0 1.1rem 0;
        }

        .auth-social-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.72rem;
            min-height: 3.35rem;
            border-radius: 1rem;
            border: 1px solid #dbe3ef;
            background: #ffffff;
            color: #24324a;
            font-size: 0.97rem;
            font-weight: 700;
            box-shadow: 0 8px 18px rgba(148, 163, 184, 0.12);
            transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
        }

        .auth-social-btn:hover {
            transform: translateY(-1px);
            border-color: #c7d6f4;
            box-shadow: 0 12px 24px rgba(148, 163, 184, 0.18);
        }

        .auth-social-icon {
            width: 1.6rem;
            height: 1.6rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            font-size: 0.92rem;
            font-weight: 800;
            line-height: 1;
        }

        .auth-social-icon.google {
            color: #4285f4;
        }

        .auth-divider {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin: 1rem 0 1.2rem 0;
            color: #64748b;
            font-size: 0.9rem;
            font-weight: 600;
        }

        .auth-divider::before,
        .auth-divider::after {
            content: "";
            flex: 1;
            height: 1px;
            background: #dbe3ef;
        }

        .auth-text-link,
        .auth-bottom-note {
            margin: 0;
            color: #64748b;
            font-size: 0.92rem;
            line-height: 1.55;
        }

        .auth-text-link {
            text-align: right;
            font-weight: 700;
            color: #2563eb;
        }

        .auth-bottom-note {
            margin-top: 1rem;
            text-align: center;
        }

        .auth-close-note {
            margin: 0.85rem 0 0 0;
            text-align: center;
            color: #94a3b8;
            font-size: 0.82rem;
        }

        /* FIX: Keep Streamlit modal structure intact */
        div[data-testid="stDialog"] div[role="dialog"] {
            background: #ffffff !important;
            border-radius: 1.6rem !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 30px 80px rgba(0,0,0,0.15) !important;
        }

        div[data-testid="stDialog"] [data-testid="stDialogContent"] {
            background: transparent !important;
        }

        /* INPUTS */
        input[type="text"],
        input[type="password"],
        input[type="email"] {
            border-radius: 0.72rem;
            border: 1px solid #e5e7eb;
            background: #ffffff;
            color: var(--ink-900);
        }

        /* Streamlit wraps text/password fields; style wrapper only once to avoid double-layer boxes */
        .st-key-auth_shell [data-baseweb="input"] {
            min-height: 3.3rem;
            border: 1px solid #dbe3ef !important;
            border-radius: 1rem !important;
            background: #ffffff !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9) !important;
        }

        .st-key-auth_shell [data-baseweb="input"] > div {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        .st-key-auth_shell input[type="text"],
        .st-key-auth_shell input[type="password"],
        .st-key-auth_shell input[type="email"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: #111827 !important;
            font-size: 0.96rem !important;
        }

        .st-key-auth_shell [data-testid="stCheckbox"] label p {
            font-size: 0.84rem;
            line-height: 1.5;
            color: #374151 !important;
        }

        .st-key-auth_shell [data-testid="stCheckbox"] input[type="checkbox"] {
            accent-color: #4f7df2 !important;
        }

        .st-key-auth_shell [data-testid="stCheckbox"] [data-baseweb="checkbox"] > div:first-of-type {
            border-color: #cbd5e1 !important;
            background: #ffffff !important;
        }

        .st-key-auth_shell [data-testid="stCheckbox"] [data-baseweb="checkbox"] input:checked + div {
            border-color: #4f7df2 !important;
            background: #4f7df2 !important;
        }

        .st-key-auth_shell [data-testid="stCheckbox"] [data-baseweb="checkbox"] input:checked + div svg {
            stroke: #ffffff !important;
            fill: #ffffff !important;
            color: #ffffff !important;
        }

        input[type="text"]::placeholder,
        input[type="password"]::placeholder,
        input[type="email"]::placeholder {
            color: var(--ink-500);
        }

        input[type="text"]:focus-visible,
        input[type="password"]:focus-visible,
        input[type="email"]:focus-visible,
        textarea:focus-visible,
        button:focus-visible,
        a:focus-visible {
            outline: 2px solid var(--focus-ring) !important;
            outline-offset: 2px !important;
            box-shadow: none !important;
        }

        input[type="text"]:focus,
        input[type="password"]:focus,
        input[type="email"]:focus {
            border-color: #111111;
            box-shadow: 0 0 0 1px rgba(17, 17, 17, 0.12);
        }

        .st-key-auth_shell [data-baseweb="input"]:focus-within {
            border-color: #9db6ff !important;
            box-shadow: 0 0 0 4px rgba(77, 127, 245, 0.12) !important;
        }

        /* BUTTONS */
        .st-key-auth_shell [data-testid="stFormSubmitButton"] button,
        .st-key-auth_shell [class*="st-key-auth_submit_button_"] button {
            font-weight: 800;
            border-radius: 1rem !important;
            min-height: 3.3rem;
            border: none !important;
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 16px 30px rgba(59, 130, 246, 0.18) !important;
            transition: transform 180ms ease, box-shadow 180ms ease;
        }

        .st-key-auth_shell [data-testid="stFormSubmitButton"] button p,
        .st-key-auth_shell [data-testid="stFormSubmitButton"] button span,
        .st-key-auth_shell [class*="st-key-auth_submit_button_"] button p,
        .st-key-auth_shell [class*="st-key-auth_submit_button_"] button span {
            color: #ffffff !important;
        }

        .st-key-auth_shell [data-testid="stFormSubmitButton"] button:hover,
        .st-key-auth_shell [class*="st-key-auth_submit_button_"] button:hover {
            transform: translateY(-1px);
            box-shadow: 0 18px 34px rgba(59, 130, 246, 0.22) !important;
        }


        .st-key-hero_cta_button {
            max-width: 19rem;
            margin-top: 2rem;
        }

        .st-key-hero_cta_button button {
            min-height: 4rem;
            border: none !important;
            border-radius: 999px !important;
            background: linear-gradient(90deg, #4d7ff5 0%, #18b5df 100%) !important;
            color: #ffffff !important;
            font-size: 1.12rem !important;
            font-weight: 800 !important;
            box-shadow: 0 18px 42px rgba(77, 127, 245, 0.25) !important;
            transition: transform 180ms ease, box-shadow 180ms ease !important;
        }

        .st-key-hero_cta_button button:hover {
            transform: scale(1.04);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.18) !important;
        }

        /* CARDS */
        .artify-preview-card {
            text-align: center;
        }

        .artify-preview-card.is-stylized {
            margin-top: 2.7rem;
        }

        .artify-preview-frame {
            padding: 0.42rem;
            border-radius: 2rem;
            background: #ffffff;
            box-shadow: 0 20px 52px rgba(148, 163, 184, 0.2);
            transition: transform 220ms ease, box-shadow 220ms ease;
            will-change: transform, box-shadow;
        }

        .artify-preview-frame.original {
            border: 3px solid rgba(255, 227, 190, 0.96);
        }

        .artify-preview-frame.stylized {
            border: 3px solid rgba(201, 229, 255, 0.98);
        }

        .artify-preview-image,
        .artify-preview-placeholder {
            width: 100%;
            aspect-ratio: 4 / 5;
            display: block;
            border-radius: 1.55rem;
            object-fit: cover;
            background: #f4f5f7;
        }

        .artify-preview-image.is-stylized {
            filter: saturate(1.18) contrast(1.06) brightness(1.02);
        }

        .artify-preview-image {
            transition: transform 220ms ease;
            will-change: transform;
        }

        .artify-preview-frame:hover {
            transform: scale(1.05);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
        }

        .artify-preview-frame:hover .artify-preview-image {
            transform: scale(1.05);
        }

        .artify-preview-placeholder {
            border: 1px solid #e5e7eb;
            background: linear-gradient(145deg, #eef2f7, #f8fafc);
        }

        .artify-preview-chip {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-top: 1rem;
            padding: 0.72rem 1.35rem;
            border-radius: 999px;
            background: #ffffff;
            color: #5b667a;
            font-size: 0.98rem;
            font-weight: 700;
            box-shadow: 0 10px 24px rgba(148, 163, 184, 0.18);
        }

        .artify-preview-chip.stylized {
            background: linear-gradient(90deg, #4d7ff5 0%, #18b5df 100%);
            color: #ffffff;
        }

        .proof-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 1rem;
            padding: 0.8rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            animation: fadeInUp 440ms ease both;
        }

        .proof-image {
            width: 100%;
            aspect-ratio: 16 / 10;
            border-radius: 0.72rem;
            border: 1px solid #e5e7eb;
            margin-bottom: 0.62rem;
        }

        .proof-img-tag {
            width: 100%;
            aspect-ratio: 16 / 10;
            object-fit: cover;
            border-radius: 0.72rem;
            border: 1px solid #e5e7eb;
            margin-bottom: 0.62rem;
            display: block;
        }

        .proof-before,
        .proof-after,
        .proof-alt {
            background: #f7f7f8;
        }

        .proof-card h4 {
            margin: 0 0 0.2rem 0;
            font-size: 0.98rem;
            color: var(--ink-900);
        }

        .proof-card p {
            margin: 0;
            font-size: 0.84rem;
            color: var(--ink-700);
            line-height: 1.38;
        }

        .how-works-intro {
            text-align: center;
            margin: 0 auto 1.9rem auto;
            max-width: 46rem;
        }

        .how-works-title {
            margin: 0;
            color: #1f2937;
            font-size: clamp(2.1rem, 4.6vw, 3.45rem);
            line-height: 1.02;
            letter-spacing: -0.045em;
            font-weight: 800;
        }

        .how-works-sub {
            margin: 0.9rem auto 0 auto;
            color: #66758c;
            font-size: 1.06rem;
            line-height: 1.65;
            max-width: 42rem;
        }

        .how-works-card {
            position: relative;
            height: 100%;
            min-height: 18.7rem;
            padding: 2rem 1.4rem 1.6rem 1.4rem;
            border-radius: 1.7rem;
            border: 1px solid #eef2f7;
            background: linear-gradient(180deg, #ffffff 0%, #ffffff 68%, #fbfcff 100%);
            box-shadow: 0 22px 48px rgba(148, 163, 184, 0.14);
            transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
            overflow: hidden;
        }

        .how-works-card:hover {
            transform: translateY(-8px);
            border-color: #dce6fb;
            box-shadow: 0 30px 62px rgba(148, 163, 184, 0.22);
        }

        .how-works-card::after {
            content: "";
            position: absolute;
            inset: auto 1.4rem 0.95rem 1.4rem;
            height: 0.3rem;
            border-radius: 999px;
            background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(226, 232, 240, 0.8), rgba(255, 255, 255, 0));
            pointer-events: none;
        }

        .how-works-icon {
            width: 5.05rem;
            height: 5.05rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 1.35rem;
            color: #ffffff;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1.6rem;
            box-shadow: 0 16px 34px rgba(148, 163, 184, 0.2);
        }

        .how-works-icon.upload {
            background: linear-gradient(135deg, #4f84f5 0%, #5ca2ff 100%);
        }

        .how-works-icon.stylize {
            background: linear-gradient(135deg, #18b8df 0%, #34c6e2 100%);
        }

        .how-works-icon.preview {
            background: linear-gradient(135deg, #f255a5 0%, #ea5a9b 100%);
        }

        .how-works-icon.save {
            background: linear-gradient(135deg, #8b5cf6 0%, #9a6df7 100%);
        }

        .how-works-card-title {
            margin: 0 0 0.9rem 0;
            color: #163055;
            font-size: 1.02rem;
            line-height: 1.2;
            font-weight: 800;
        }

        .how-works-card-desc {
            margin: 0;
            color: #5d6c83;
            font-size: 0.94rem;
            line-height: 1.7;
            max-width: 16rem;
        }

        .section-title {
            margin-top: 0.3rem;
            margin-bottom: 0.65rem;
            color: var(--ink-900);
            font-size: 1.08rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        /* TABS — fix: no CSS existed for these; Streamlit's dark-theme defaults were winning */
        [data-testid="stTabs"] {
            background: transparent !important;
        }

        [data-testid="stTabs"] [data-baseweb="tab-list"] {
            background: transparent !important;
            border-bottom: 2px solid #e5e7eb;
        }

        [data-testid="stTabs"] button[role="tab"] {
            background: transparent !important;
            color: #64748b !important;
            border: none !important;
            border-radius: 0 !important;
            font-weight: 600;
            font-size: 0.95rem;
        }

        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: #111111 !important;
            border-bottom: 2px solid #111111 !important;
            background: transparent !important;
        }

        [data-testid="stTabs"] button[role="tab"]:hover {
            background: #f8fafc !important;
            color: #111111 !important;
        }

        [data-testid="stTabContent"] {
            background: transparent !important;
        }

        /* AUTH SHELL plain st.button() "Sign In" / "Register" fake-tab buttons */
        .st-key-auth_shell [data-testid="baseButton-secondary"],
        .st-key-auth_shell [data-testid="baseButton-secondary"] button {
            background: #f1f5f9 !important;
            color: #334155 !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 0.85rem !important;
        }

        .st-key-auth_shell [data-testid="baseButton-secondary"] button:hover {
            background: #e8edf5 !important;
            border-color: #b9caf0 !important;
            color: #111111 !important;
        }

        /* GLOBAL BUTTON RESET — prevent background-clip inheritance from
           creating black artifacts on any button element */
        button {
            background-clip: border-box !important;
            -webkit-background-clip: border-box !important;
        }

        .block-container button[data-testid="baseButton-primary"]:active,
        .block-container button[data-testid="baseButton-secondary"]:active {
            transform: translateY(0);
        }

        /* MOBILE */
        @media (max-width: 900px) {
            .block-container {
                padding-top: 0.85rem;
                padding-bottom: 1rem;
                padding-left: 0.7rem;
                padding-right: 0.7rem;
                max-width: 100% !important;
            }
            .block-container [data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
                gap: 0.65rem !important;
            }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
            }
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 0 !important;
            }
            .block-container [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 0 !important;
            }
            .artify-hero-copy {
                max-width: none;
                padding-top: 0.25rem;
                text-align: center;
            }
            .artify-hero-title {
                font-size: clamp(2.2rem, 11vw, 3.4rem);
            }
            .artify-hero-desc {
                max-width: none;
                margin-top: 1.05rem;
                font-size: 0.98rem;
            }
            .st-key-hero_showcase_shell {
                padding-bottom: 1.5rem;
            }
            .st-key-hero_cta_button {
                max-width: none;
                margin-top: 1.4rem;
            }
            .st-key-hero_cta_button button {
                min-height: 3.35rem;
                font-size: 1rem !important;
            }
            .artify-preview-card.is-stylized {
                margin-top: 1rem;
            }
            .how-works-intro {
                margin-bottom: 1.2rem;
            }
            .how-works-title {
                font-size: clamp(1.9rem, 9vw, 2.6rem);
            }
            .how-works-sub {
                margin-top: 0.65rem;
                font-size: 0.96rem;
            }
            .how-works-card {
                min-height: auto;
                padding: 1.3rem 1.05rem 1.15rem 1.05rem;
                border-radius: 1.3rem;
            }
            .how-works-icon {
                width: 4.2rem;
                height: 4.2rem;
                border-radius: 1.1rem;
                font-size: 1.7rem;
                margin-bottom: 1.1rem;
            }
            .how-works-card-title {
                margin-bottom: 0.7rem;
            }
            .how-works-card-desc {
                max-width: none;
                font-size: 0.9rem;
                line-height: 1.6;
            }
            .proof-card {
                padding: 0.72rem 0.75rem;
            }
            .st-key-auth_shell {
                padding: 1rem 0.95rem 1rem 0.95rem;
                border-radius: 1.45rem;
            }
            .auth-title {
                font-size: clamp(1.8rem, 8vw, 2.1rem);
            }
            .auth-subtitle {
                font-size: 0.93rem;
            }
            .auth-social-btn {
                min-height: 3.05rem;
                font-size: 0.92rem;
            }
            .auth-social-icon {
                width: 1.45rem;
                height: 1.45rem;
                font-size: 0.84rem;
            }
            .st-key-auth_shell [data-baseweb="input"] {
                min-height: 3.05rem;
            }
            .st-key-auth_shell [data-testid="stFormSubmitButton"] button {
                min-height: 3.1rem;
            }
            .proof-card p {
                overflow-wrap: anywhere;
                font-size: 0.88rem;
            }
            .block-container button[data-testid="baseButton-primary"],
            .block-container button[data-testid="baseButton-secondary"] {
                min-height: 2.65rem;
            }
            [data-testid="stLogo"] img,
            [data-testid="stLogo"] svg {
                max-height: 3.1rem !important;
            }
            .section-title {
                font-size: 1.05rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def image_data_uri(path: Path):
    if not path.exists():
        return None
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    else:
        mime = "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def render_auth_forms() -> None:

    if "auth_page" not in st.session_state:
        st.session_state.auth_page = "login"

    def set_auth_page(page: str):
        st.session_state.auth_page = page
        st.rerun()

    def render_auth_intro(title, subtitle, google_text, divider_text):
        has_creds = has_google_credentials()
        
        btn_html = ""
        if has_creds:
            google_url, state = get_google_auth_url(REDIRECT_URI)
            st.session_state.oauth_state = state
            btn_html = f"""
                <div class="auth-social-stack">
                    <a href="{google_url}" target="_self" style="text-decoration: none; display: block;">
                        <div class="auth-social-btn">
                            <span class="auth-social-icon google">G</span>
                            <span>{google_text}</span>
                        </div>
                    </a>
                </div>
                <div class="auth-divider"><span>{divider_text}</span></div>
            """
        else:
            btn_html = f"""
                <div class="auth-divider"><span>{divider_text}</span></div>
            """

        st.markdown(
            f"""
            <div class="auth-shell-head">
                <h2 class="auth-title">{title}</h2>
                <p class="auth-subtitle">{subtitle}</p>
            </div>
            {btn_html}
            """,
            unsafe_allow_html=True,
        )

    def render_password_input(label, key, placeholder, visibility_key):
        return st.text_input(
            label,
            type="password",
            key=key,
            placeholder=placeholder,
        )

    # Fake tabs (same layout visually)
    tab1, tab2 = st.columns(2)

    with tab1:
        if st.button("Sign In", use_container_width=True):
            set_auth_page("login")

    with tab2:
        if st.button("Register", use_container_width=True):
            set_auth_page("register")

    # ---------------- LOGIN ---------------- #

    if st.session_state.auth_page == "login":

        render_auth_intro(
            "Welcome Back",
            "Sign in to continue to AI Stylizer",
            "Continue with Google",
            "Or continue with email",
        )

        identifier = st.text_input(
            "Email address",
            key="login_identifier",
            placeholder="you@example.com",
        )

        password = render_password_input(
            "Password",
            "login_password",
            "Enter your password",
            "show_login_password",
        )

        remember_col, forgot_col = st.columns([1,1])

        with remember_col:
            remember_me = st.checkbox(
                "Remember me",
                key="login_remember_me",
            )

        with forgot_col:
            st.markdown(
                '<p class="auth-text-link">Forgot password?</p>',
                unsafe_allow_html=True,
            )

        login_submit = st.button(
            "Sign In",
            key="auth_submit_button_login",
            use_container_width=True,
            type="primary",
        )

        col1, col2 = st.columns([3,2])

        with col1:
            st.markdown(
                '<p class="auth-bottom-note">Don&#39;t have an account?</p>',
                unsafe_allow_html=True,
            )

        with col2:
            if st.button("Sign up for free", key="switch_to_register", type="tertiary"):
                set_auth_page("register")

        if login_submit:

            result = login_user(identifier.strip(), password)

            if result.get("success"):

                st.session_state.logged_in = True
                st.session_state.authenticated = True
                st.session_state.is_logged_in = True
                st.session_state.username = result.get("username")
                st.session_state.user_name = result.get("username")
                st.session_state.profile_image = None
                st.session_state.email = result.get("email")
                st.session_state.user_id = result.get("user_id")
                set_user_profile_state(
                    user_name=result.get("username"),
                    profile_image=None,
                    login_method="local",
                )
                st.session_state.remember_me = bool(remember_me)
                st.session_state.auth_modal_open = False

                st.rerun()

            else:
                st.error(result.get("message", "Login failed."))

    # ---------------- REGISTER ---------------- #

    if st.session_state.auth_page == "register":

        render_auth_intro(
            "Create Account",
            "Start transforming your photos with AI",
            "Sign up with Google",
            "Or sign up with email",
        )

        reg_user = st.text_input(
            "Full name",
            key="reg_username",
            placeholder="John Doe",
        )

        reg_email = st.text_input(
            "Email address",
            key="reg_email",
            placeholder="you@example.com",
        )

        reg_pass = render_password_input(
            "Password",
            "reg_password",
            "Create a strong password",
            "show_reg_password",
        )

        reg_confirm = render_password_input(
            "Confirm password",
            "reg_confirm",
            "Re-enter your password",
            "show_reg_confirm_password",
        )

        agree_terms = st.checkbox(
            "I agree to the Terms of Service and Privacy Policy",
            key="reg_terms",
        )

        register_submit = st.button(
            "Create Account",
            key="auth_submit_button_register",
            use_container_width=True,
            type="primary",
        )

        col1, col2 = st.columns([3,2])

        with col1:
            st.markdown(
                '<p class="auth-bottom-note">Already have an account?</p>',
                unsafe_allow_html=True,
            )

        with col2:
            if st.button("Sign in", key="switch_to_login", type="tertiary"):
                set_auth_page("login")

        if register_submit:

            reg_user_clean = reg_user.strip()
            reg_email_clean = reg_email.strip()

            submit_errors = []

            if not (reg_user_clean and reg_email_clean and reg_pass and reg_confirm):
                submit_errors.append("All fields are required.")

            if reg_pass != reg_confirm:
                submit_errors.append("Passwords do not match.")

            if not agree_terms:
                submit_errors.append("You must agree to the Terms of Service and Privacy Policy.")

            if submit_errors:
                st.error("Please fix the following:\n- " + "\n- ".join(submit_errors))

            else:

                result = register_user(reg_user_clean, reg_email_clean, reg_pass)

                if result.get("success"):

                    st.session_state.flash_message = "Account created. Please sign in."
                    set_auth_page("login")

                else:
                    st.error(result.get("message", "Registration failed."))



def close_auth_modal() -> None:
    st.session_state.auth_modal_open = False


if hasattr(st, "dialog"):

    @st.dialog("Sign In / Register", on_dismiss=close_auth_modal)
    def open_auth_modal() -> None:
        auth_card_container = st.container(key="auth_shell")
        with auth_card_container:
            render_auth_forms()

else:

    def open_auth_modal() -> None:
        auth_card_container = st.container(key="auth_shell")
        with auth_card_container:
            render_auth_forms()
            st.markdown(
                '<p class="auth-close-note">Close this panel by reloading or navigating.</p>',
                unsafe_allow_html=True,
            )

@st.cache_resource
def initialize_app() -> None:
    create_tables()


initialize_app()
apply_styles()
# After apply_styles() runs the full theme is in place — unlock opacity in
# case the primer JS fired before .stApp existed (rare but possible on slow tabs).
st.markdown(
    "<style>.stApp { opacity: 1 !important; }</style>",
    unsafe_allow_html=True,
)

defaults = {
    "logged_in": False,
    "authenticated": False,
    "username": None,
    "user_name": None,
    "email": None,
    "user_id": None,
    "profile_picture": None,
    "profile_image": None,
    "login_method": None,
    "remember_me": False,
    "auth_modal_open": False,
    "auth_tabs": "Sign In",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

auth_state = bool(st.session_state.get("logged_in") or st.session_state.get("authenticated"))
st.session_state.logged_in = auth_state
st.session_state.authenticated = auth_state
sync_user_profile_state()

# ==========================================
# GOOGLE OAUTH CALLBACK HANDLING
# ==========================================
if "code" in st.query_params:
    auth_code = st.query_params.get("code")
    st.query_params.clear()  # Clear URL code param
    
    with st.spinner("Authenticating with Google..."):
        oauth_state = st.session_state.get("oauth_state")
        result = process_google_callback(auth_code, state=oauth_state, redirect_uri=REDIRECT_URI)
        
        if result.get("success"):
            st.session_state.logged_in = True
            st.session_state.authenticated = True
            st.session_state.is_logged_in = True
            st.session_state.username = result.get("username")
            st.session_state.user_name = result.get("name") or result.get("username")
            st.session_state.profile_image = result.get("profile_picture")
            st.session_state.email = result.get("email")
            st.session_state.user_id = result.get("user_id")
            set_user_profile_state(
                user_name=result.get("name") or result.get("username"),
                profile_image=result.get("profile_picture"),
                login_method="google",
            )
                
            st.session_state.auth_modal_open = False
            st.success("Successfully signed in with Google!")
            st.rerun()
        else:
            st.error(result.get("message", "Google login failed."))

if "flash_message" in st.session_state:
    st.success(st.session_state.flash_message)
    del st.session_state.flash_message

with st.sidebar:
    request_auth_modal = bool(st.session_state.get("auth_modal_open"))
    
    if not has_google_credentials():
        st.error("OAuth Credentials missing. See README.md for setup.")
        
    render_sidebar_profile()

    if st.session_state.authenticated:
        if st.button("Open Dashboard", use_container_width=True, type="primary"):
            st.switch_page("pages/dashboard.py")

        if st.button("Log out", use_container_width=True):
            clear_user_profile_state()
            st.session_state.logged_in = False
            st.session_state.authenticated = False
            st.session_state.email = None
            st.session_state.user_id = None
            st.session_state.remember_me = False
            st.session_state.auth_modal_open = False
            st.rerun()
    else:
        if st.button("Sign In / Register", use_container_width=True, type="primary"):
            st.session_state.auth_modal_open = True
            request_auth_modal = True

before_uri = image_data_uri(before1_image)
after_uri = image_data_uri(after1_image)
original_image_block = (
    f'<img src="{before_uri}" alt="Original photo" class="artify-preview-image">'
    if before_uri
    else '<div class="artify-preview-placeholder"></div>'
)
stylized_image_block = (
    f'<img src="{after_uri}" alt="Stylized photo" class="artify-preview-image is-stylized">'
    if after_uri
    else '<div class="artify-preview-placeholder"></div>'
)

hero_showcase_shell = st.container(key="hero_showcase_shell")
with hero_showcase_shell:
    hero_copy_col, hero_preview_col = st.columns([1.08, 1], gap="large")

    with hero_copy_col:
        st.markdown(
            """
            <div class="artify-hero-copy">
                <h1 class="artify-hero-title">
                    Transform Your<br>
                    Photos into <span class="artify-hero-gradient">Art</span> in<br>
                    <span class="artify-hero-accent">Seconds</span>
                </h1>
                <p class="artify-hero-desc">
                    Turn everyday photos into stunning cartoon illustrations with
                    our AI-powered platform. Built with Python and OpenCV for
                    professional-quality results.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        hero_cta_button = st.container(key="hero_cta_button")
        with hero_cta_button:
            start_creating = st.button(
                "Get Started Now →",
                type="primary",
                use_container_width=True,
                key="hero_get_started",
            )
            if start_creating:
                if st.session_state["authenticated"]:
                    st.switch_page("pages/dashboard.py")
                else:
                    st.session_state.auth_modal_open = True
                    request_auth_modal = True

    with hero_preview_col:
        preview_original_col, preview_stylized_col = st.columns(2, gap="medium")

        with preview_original_col:
            st.markdown(
                f"""
                <div class="artify-preview-card">
                    <div class="artify-preview-frame original">
                        {original_image_block}
                    </div>
                    <div class="artify-preview-chip">Original</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with preview_stylized_col:
            st.markdown(
                f"""
                <div class="artify-preview-card is-stylized">
                    <div class="artify-preview-frame stylized">
                        {stylized_image_block}
                    </div>
                    <div class="artify-preview-chip stylized">Stylized</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

if request_auth_modal:
    open_auth_modal()

st.markdown("<div style='height: 2.2rem;'></div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="how-works-intro">
        <h2 class="how-works-title">How It Works</h2>
        <p class="how-works-sub">
            Four simple steps to transform your photos into beautiful artwork
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

how_step_1, how_step_2, how_step_3, how_step_4 = st.columns(4, gap="medium")
with how_step_1:
    st.markdown(
        """
        <div class="how-works-card">
            <div class="how-works-icon upload">&#128228;</div>
            <h3 class="how-works-card-title">Upload</h3>
            <p class="how-works-card-desc">
                Select any photo from your device to begin the transformation process.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with how_step_2:
    st.markdown(
        """
        <div class="how-works-card">
            <div class="how-works-icon stylize">&#10024;</div>
            <h3 class="how-works-card-title">Stylize</h3>
            <p class="how-works-card-desc">
                AI processes your image using advanced neural networks instantly.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with how_step_3:
    st.markdown(
        """
        <div class="how-works-card">
            <div class="how-works-icon preview">&#128065;</div>
            <h3 class="how-works-card-title">Preview</h3>
            <p class="how-works-card-desc">
                Compare side-by-side results and adjust settings to perfection.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with how_step_4:
    st.markdown(
        """
        <div class="how-works-card">
            <div class="how-works-icon save">&#11015;</div>
            <h3 class="how-works-card-title">Save</h3>
            <p class="how-works-card-desc">
                Download your transformed images in high-quality formats.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Explore styles</div>', unsafe_allow_html=True)

preview_cards = [

    {
        "title": "Studio Cartoon",
        "description": "Soft-shaded, bold outlines designed for modern branding.",
        "path": cartoon_image,
        "fallback_class": "proof-after",
    },
    {
        "title": "Colored Pencil",
        "description": "Rich, textured strokes with natural tonal depth.",
        "path": pencil_color_image,
        "fallback_class": "proof-alt",
    },
    {
        "title": "Graphite Sketch",
        "description": "Classic monochrome lines for timeless illustration.",
        "path": sketch_image,
        "fallback_class": "proof-before",
    },
]

preview_columns = st.columns(len(preview_cards), gap="medium")
for column, card in zip(preview_columns, preview_cards):
    with column:
        uri = image_data_uri(card["path"])
        if uri:
            image_block = f'<img src="{uri}" alt="{card["title"]}" class="proof-img-tag">'
        else:
            image_block = f'<div class="proof-image {card["fallback_class"]}"></div>'
        st.markdown(
            f"""
            <div class="proof-card">
                {image_block}
                <h4>{card["title"]}</h4>
                <p>{card["description"]}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
