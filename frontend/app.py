import sys
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.auth import register_user
from backend.auth_login import login_user
from database.db import create_tables


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

        :root {
            --bg-top: #050d1e;
            --bg-mid: #09182d;
            --bg-bottom: #0f1f3a;
            --ink-900: #eaf2ff;
            --ink-700: #c0cfe8;
            --ink-500: #8ea3c3;
            --brand-800: #0d4f63;
            --brand-700: #0e7490;
            --brand-500: #22d3ee;
            --accent-500: #fb923c;
            --card-bg: rgba(12, 24, 44, 0.78);
            --card-stroke: rgba(125, 162, 206, 0.24);
        }

        html, body, [class*="css"] {
            font-family: "Manrope", "Segoe UI", sans-serif;
            color: var(--ink-700);
        }

        h1, h2, h3, h4, h5, h6 {
            color: var(--ink-900);
        }

        p, label, li, [data-testid="stMarkdownContainer"] {
            color: var(--ink-700);
        }

        html, body {
            background:
                radial-gradient(circle at -2% -8%, rgba(34, 211, 238, 0.22), transparent 34%),
                radial-gradient(circle at 103% 0%, rgba(251, 146, 60, 0.20), transparent 34%),
                radial-gradient(circle at 70% 105%, rgba(59, 130, 246, 0.18), transparent 40%),
                linear-gradient(160deg, var(--bg-top) 0%, var(--bg-mid) 46%, var(--bg-bottom) 100%) fixed;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            background: transparent !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            background: transparent !important;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {
            max-width: 100%;
            overflow-x: hidden !important;
        }

        .stApp {
            background:
                radial-gradient(circle at -2% -8%, rgba(34, 211, 238, 0.22), transparent 34%),
                radial-gradient(circle at 103% 0%, rgba(251, 146, 60, 0.20), transparent 34%),
                radial-gradient(circle at 70% 105%, rgba(59, 130, 246, 0.18), transparent 40%),
                linear-gradient(160deg, var(--bg-top) 0%, var(--bg-mid) 46%, var(--bg-bottom) 100%);
            background-attachment: fixed;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid rgba(125, 162, 206, 0.24);
            background: linear-gradient(180deg, rgba(5, 13, 31, 0.98) 0%, rgba(12, 28, 52, 0.96) 100%);
            color: var(--ink-700);
            backdrop-filter: blur(10px);
        }

        [data-testid="stSidebar"] * {
            color: var(--ink-700);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4,
        [data-testid="stSidebar"] h5,
        [data-testid="stSidebar"] h6 {
            color: var(--ink-900);
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] label p,
        [data-testid="stSidebar"] .stCaptionContainer {
            color: var(--ink-700) !important;
        }

        button[data-testid="collapsedControl"] {
            background: rgba(7, 16, 32, 0.85) !important;
            border: 1px solid rgba(125, 162, 206, 0.4) !important;
            border-radius: 0.6rem !important;
            min-width: 2.3rem !important;
            min-height: 2.3rem !important;
        }

        button[data-testid="collapsedControl"] svg,
        [data-testid="stSidebarNav"] svg {
            fill: var(--ink-900) !important;
            color: var(--ink-900) !important;
        }

        [data-testid="stSidebarNav"] a {
            color: var(--ink-700) !important;
        }

        .block-container {
            padding-top: 2.35rem;
            padding-bottom: 2.35rem;
            max-width: 1180px;
        }

        .side-head {
            font-size: 1.1rem;
            font-weight: 800;
            margin-bottom: 0.3rem;
            color: var(--ink-900);
            letter-spacing: -0.01em;
        }

        .side-sub {
            margin-bottom: 0.75rem;
            color: var(--ink-500);
            font-size: 0.84rem;
        }

        form[data-testid="stForm"] {
            background: rgba(8, 19, 36, 0.72);
            border: 1px solid rgba(125, 162, 206, 0.24);
            border-radius: 1rem;
            padding: 0.85rem 0.85rem 0.55rem 0.85rem;
        }

        [data-testid="stTextInput"] input {
            border-radius: 0.72rem;
            border: 1px solid rgba(125, 162, 206, 0.32);
            background: rgba(5, 13, 31, 0.74);
            color: var(--ink-900);
        }

        [data-testid="stTextInput"] input::placeholder {
            color: var(--ink-500);
        }

        [data-testid="stTextInput"] input:focus {
            border-color: rgba(34, 211, 238, 0.75);
            box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.35);
        }

        .brand-kicker {
            display: inline-block;
            background: rgba(14, 116, 144, 0.22);
            color: #8de9ff;
            border: 1px solid rgba(34, 211, 238, 0.35);
            border-radius: 999px;
            padding: 0.34rem 0.9rem;
            font-size: 0.72rem;
            letter-spacing: 0.095em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.7rem;
        }

        .hero-title {
            font-size: clamp(2.15rem, 3.8vw, 3.35rem);
            line-height: 1.02;
            font-weight: 800;
            color: var(--ink-900);
            letter-spacing: -0.03em;
            margin: 0 0 0.8rem 0;
            white-space: normal !important;
            word-break: break-word;
        }

        .hero-sub {
            color: var(--ink-700);
            font-size: 1.04rem;
            line-height: 1.65;
            margin-bottom: 1rem;
            max-width: 60ch;
        }

        .stat-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-bottom: 1rem;
        }

        .stat-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.28rem 0.62rem;
            border-radius: 999px;
            background: rgba(8, 20, 38, 0.74);
            border: 1px solid rgba(125, 162, 206, 0.34);
            color: var(--ink-700);
            font-size: 0.77rem;
            font-weight: 650;
        }

        .spotlight-card {
            background: var(--card-bg);
            border: 1px solid var(--card-stroke);
            border-radius: 1.05rem;
            padding: 1.1rem 1.15rem;
            backdrop-filter: blur(4px);
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
            animation: fadeInUp 380ms ease both;
        }

        .spotlight-card h4 {
            margin: 0 0 0.35rem 0;
            color: var(--ink-900);
            font-size: 1.06rem;
        }

        .spotlight-card p {
            margin: 0;
            color: var(--ink-700);
            font-size: 0.92rem;
            line-height: 1.5;
        }

        .feature-card {
            background: var(--card-bg);
            border: 1px solid var(--card-stroke);
            border-radius: 1.05rem;
            padding: 1.02rem 1.08rem;
            min-height: 125px;
            transition: transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04);
            animation: fadeInUp 430ms ease both;
        }

        .feature-card:hover {
            transform: translateY(-3px);
            border-color: rgba(34, 211, 238, 0.48);
            box-shadow: 0 14px 28px rgba(2, 6, 23, 0.34);
        }

        .feature-card h4 {
            color: var(--ink-900);
            margin: 0 0 0.28rem 0;
        }

        .feature-card p {
            color: var(--ink-700);
            margin: 0;
            font-size: 0.9rem;
            line-height: 1.45;
        }

        .section-title {
            margin-top: 0.3rem;
            margin-bottom: 0.8rem;
            color: var(--ink-900);
            font-size: 1.22rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #0e7490 0%, #22d3ee 100%);
            border: none;
            color: #03101f;
            font-weight: 700;
            border-radius: 0.72rem;
            box-shadow: 0 10px 22px rgba(34, 211, 238, 0.20);
        }

        button[data-testid="baseButton-primary"]:hover {
            filter: brightness(1.03);
            transform: translateY(-1px);
        }

        button[data-testid="baseButton-secondary"] {
            border-radius: 0.72rem;
            border: 1px solid rgba(125, 162, 206, 0.45);
            color: var(--ink-900);
            background: rgba(8, 20, 38, 0.66);
        }

        .stAlert {
            border-radius: 0.8rem;
            border: 1px solid rgba(125, 162, 206, 0.32);
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

        @media (max-width: 900px) {
            .block-container {
                padding-top: 0.85rem;
                padding-bottom: 1rem;
                padding-left: 0.7rem;
                padding-right: 0.7rem;
                max-width: 100% !important;
            }
            [data-testid="stSidebar"] {
                width: auto !important;
                min-width: 0 !important;
                max-width: 100vw !important;
            }
            [data-testid="stSidebar"][aria-expanded="true"] {
                width: min(88vw, 22rem) !important;
                min-width: min(88vw, 22rem) !important;
                max-width: min(88vw, 22rem) !important;
            }
            button[data-testid="collapsedControl"] {
                position: fixed !important;
                top: 0.56rem !important;
                left: 0.56rem !important;
                z-index: 1002 !important;
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
            .hero-sub {
                font-size: 0.88rem;
                overflow-wrap: anywhere;
            }
            .hero-title {
                font-size: clamp(1.35rem, 7.4vw, 1.72rem);
                line-height: 1.12;
                overflow-wrap: anywhere;
            }
            .feature-card {
                min-height: auto;
            }
            .spotlight-card,
            .feature-card {
                padding: 0.78rem 0.82rem;
            }
            .spotlight-card p,
            .feature-card p {
                overflow-wrap: anywhere;
                font-size: 0.86rem;
            }
            .stat-row {
                gap: 0.35rem;
            }
            .stat-chip {
                font-size: 0.69rem;
            }
            button[data-testid="baseButton-primary"],
            button[data-testid="baseButton-secondary"] {
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


create_tables()

assets_dir = Path(__file__).resolve().parent / "assets"
icon_png = assets_dir / "artify_logo.png"
logo_svg = assets_dir / "artify_logo.svg"
logo_asset = logo_svg if logo_svg.exists() else icon_png

st.set_page_config(
    page_title="Artify AI",
    page_icon=str(icon_png) if icon_png.exists() else ":art:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_styles()
if logo_asset.exists() and hasattr(st, "logo"):
    try:
        st.logo(str(logo_asset), size="large")
    except TypeError:
        st.logo(str(logo_asset))

defaults = {
    "logged_in": False,
    "username": None,
    "email": None,
    "user_id": None,
    "remember_me": False,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "flash_message" in st.session_state:
    st.success(st.session_state.flash_message)
    del st.session_state.flash_message

with st.sidebar:
    st.markdown('<div class="side-head">Account Center</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-sub">Secure sign-in and profile access</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if st.session_state.logged_in:
        st.success(f"Signed in as {st.session_state.username}")
        if st.session_state.email:
            st.caption(st.session_state.email)

        if st.button("Open Dashboard", use_container_width=True, type="primary"):
            st.switch_page("pages/dashboard.py")

        if st.button("Log out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.email = None
            st.session_state.user_id = None
            st.session_state.remember_me = False
            st.rerun()
    else:
        mode = st.radio(
            "Access",
            options=["Login", "Create account"],
            key="auth_mode",
            horizontal=True,
        )

        if mode == "Login":
            with st.form("login_form"):
                st.markdown("#### Welcome back")
                identifier = st.text_input("Email or username", key="login_identifier")
                password = st.text_input("Password", type="password", key="login_password")
                remember_me = st.checkbox("Remember Me", key="login_remember_me")
                login_submit = st.form_submit_button("Sign in", use_container_width=True)
            st.caption("Forgot Password? (Coming Soon)")

            if login_submit:
                result = login_user(identifier.strip(), password)
                if result.get("success"):
                    st.session_state.logged_in = True
                    st.session_state.username = result.get("username")
                    st.session_state.email = result.get("email")
                    st.session_state.user_id = result.get("user_id")
                    st.session_state.remember_me = bool(remember_me)
                    st.rerun()
                st.error(result.get("message", "Login failed."))

        else:
            with st.form("register_form"):
                st.markdown("#### Create your account")
                reg_user = st.text_input("Username", key="reg_username")
                reg_email = st.text_input("Email", key="reg_email")
                reg_pass = st.text_input("Password", type="password", key="reg_password")
                reg_confirm = st.text_input(
                    "Confirm password",
                    type="password",
                    key="reg_confirm",
                )
                

                agree_terms = st.checkbox("I agree to the Terms and Conditions", key="reg_terms")
                register_submit = st.form_submit_button("Create account", use_container_width=True)

            if register_submit:
                reg_user_clean = reg_user.strip()
                reg_email_clean = reg_email.strip()
                submit_errors = []

                if not (reg_user_clean and reg_email_clean and reg_pass and reg_confirm):
                    submit_errors.append("All fields are required.")
                if reg_pass and reg_confirm and reg_pass != reg_confirm:
                    submit_errors.append("Passwords do not match.")
                if not agree_terms:
                    submit_errors.append("You must agree to the Terms and Conditions.")

                if submit_errors:
                    st.error("Please fix the following:\n- " + "\n- ".join(submit_errors))
                else:
                    result = register_user(reg_user_clean, reg_email_clean, reg_pass)
                    if result.get("success"):
                        st.session_state.flash_message = "Account created. Please sign in."
                        st.session_state.auth_mode = "Login"
                        st.rerun()
                    else:
                        st.error(result.get("message", "Registration failed."))

left, right = st.columns([1.6, 1], gap="large")

with left:
    st.markdown('<div class="brand-kicker">AI CARTOONIZATION STUDIO</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="hero-title">Turn photos into crisp, studio-style cartoon visuals.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-sub">A clean workflow for creators: upload, stylize, preview, and export in minutes.</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="stat-row">
            <span class="stat-chip">One-click styles</span>
            <span class="stat-chip">HD exports</span>
            <span class="stat-chip">Private workspace</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        open_editor = st.button("Launch AI Editor", type="primary", use_container_width=True)
    with c2:
        open_dashboard = st.button("Open dashboard", use_container_width=True)

    if open_editor or open_dashboard:
        if st.session_state.logged_in:
            st.switch_page("pages/dashboard.py")
        else:
            st.warning("Please sign in from the sidebar to continue.")

    st.caption("Built for fast social and portfolio-ready outputs.")

with right:
    st.markdown(
        """
        <div class="spotlight-card">
            <h4>Quick flow</h4>
            <p>1. Upload image<br>2. Apply style preset<br>3. Export final artwork</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Highlights</div>', unsafe_allow_html=True)
f1, f2 = st.columns(2, gap="medium")
with f1:
    st.markdown(
        """
        <div class="feature-card">
            <h4>Consistent quality</h4>
            <p>Stable visual style for portraits, products, and campaigns.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with f2:
    st.markdown(
        """
        <div class="feature-card">
            <h4>Faster iterations</h4>
            <p>Test style directions quickly with less manual editing.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
