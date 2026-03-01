import base64
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
            --bg-top: #06101f;
            --bg-mid: #0a1b31;
            --bg-bottom: #102546;
            --ink-900: #eaf2ff;
            --ink-700: #c0cfe8;
            --ink-500: #8ea3c3;
            --brand-800: #0a4f66;
            --brand-700: #0f7ea1;
            --brand-500: #22d3ee;
            --accent-500: #fb923c;
            --card-bg: rgba(12, 24, 44, 0.8);
            --card-stroke: rgba(125, 162, 206, 0.24);
            --focus-ring: #7fe3ff;
        }

        html, body, .stApp {
            font-family: "Manrope", "Segoe UI", sans-serif;
            color: var(--ink-700);
            max-width: 100%;
            overflow-x: hidden !important;
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
            background: linear-gradient(180deg, rgba(5, 13, 31, 0.97) 0%, rgba(12, 28, 52, 0.95) 100%);
            color: var(--ink-700);
            backdrop-filter: blur(10px);
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

        .panel-card {
            background: linear-gradient(165deg, rgba(12, 28, 52, 0.88) 0%, rgba(8, 20, 40, 0.9) 100%);
            border: 1px solid rgba(92, 142, 198, 0.3);
            border-radius: 1.2rem;
            padding: 1.05rem;
            box-shadow: 0 14px 28px rgba(2, 8, 28, 0.34);
            animation: fadeInUp 380ms ease both;
            position: relative;
            overflow: hidden;
            margin-bottom: 0.9rem;
        }

        .panel-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, rgba(34, 211, 238, 0.85), rgba(59, 130, 246, 0.45), transparent);
        }

        .panel-title {
            margin: 0;
            color: var(--ink-900);
            font-size: 1.08rem;
            font-weight: 800;
            letter-spacing: -0.02em;
        }

        .panel-sub {
            margin: 0.25rem 0 0.8rem 0;
            color: var(--ink-500);
            font-size: 0.86rem;
            line-height: 1.38;
        }

        .st-key-auth_shell {
            background: linear-gradient(180deg, #ffffff 0%, #f6fbff 100%);
            border: 1px solid #d8e6ff;
            border-radius: 1.2rem;
            padding: 1rem 1rem 0.9rem 1rem;
            box-shadow: 0 16px 30px rgba(6, 23, 56, 0.2);
            animation: fadeInUp 380ms ease both;
            margin-bottom: 0.9rem;
        }

        .st-key-auth_shell .panel-title {
            color: #0a1f3f !important;
            font-size: 1.16rem;
        }

        .st-key-auth_shell .panel-sub {
            color: #4e6388 !important;
            margin-bottom: 0.58rem;
        }

        .st-key-auth_shell .auth-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin-bottom: 0.65rem;
        }

        .st-key-auth_shell .auth-chip {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            border: 1px solid #c7daf9;
            background: #f4f8ff;
            color: #2a4c7c;
            font-size: 0.72rem;
            font-weight: 650;
            padding: 0.2rem 0.6rem;
        }

        .st-key-auth_shell .auth-note {
            margin: 0.38rem 0 0 0;
            text-align: right;
            color: #5170a0 !important;
            font-size: 0.78rem;
        }

        .st-key-auth_shell label,
        .st-key-auth_shell p,
        .st-key-auth_shell .stCaptionContainer {
            color: #1b355f !important;
        }

        .st-key-auth_shell [data-testid="stTabs"] [role="tablist"] {
            gap: 0.35rem;
            margin-bottom: 0.42rem;
            background: #eaf2ff;
            border: 1px solid #d0e1fb;
            border-radius: 999px;
            padding: 0.2rem;
        }

        .st-key-auth_shell [data-testid="stTabs"] [role="tab"] {
            border-radius: 999px;
            border: 1px solid transparent;
            background: transparent;
            color: #1f4276;
            padding: 0.3rem 0.88rem;
        }

        .st-key-auth_shell [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #0e7490 0%, #22d3ee 100%);
            border-color: transparent;
            color: #03101f;
            font-weight: 700;
        }

        .st-key-auth_shell [data-testid="stTabs"] [data-baseweb="tab-panel"] {
            padding-top: 0.4rem;
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

        form {
            background: rgba(8, 19, 36, 0.72);
            border: 1px solid rgba(125, 162, 206, 0.24);
            border-radius: 1rem;
            padding: 0.85rem 0.85rem 0.55rem 0.85rem;
        }

        .st-key-auth_shell form {
            background: transparent;
            border: none;
            border-radius: 0;
            padding: 0;
        }

        /* Default dark inputs outside the auth shell */
        input[type="text"],
        input[type="password"],
        input[type="email"] {
            border-radius: 0.72rem;
            border: 1px solid rgba(125, 162, 206, 0.32);
            background: rgba(5, 13, 31, 0.74);
            color: var(--ink-900);
        }

        /* Streamlit wraps text/password fields; style wrapper only once to avoid double-layer boxes */
        .st-key-auth_shell [data-baseweb="input"] {
            border: 1px solid #c4d8f7 !important;
            border-radius: 0.72rem !important;
            background: #ffffff !important;
            box-shadow: none !important;
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
            color: #0d274f !important;
        }

        .st-key-auth_shell [data-testid="stCheckbox"] label p {
            font-size: 0.82rem;
        }

        .st-key-auth_shell [data-testid="stFormSubmitButton"] button {
            font-weight: 700;
            border-radius: 0.72rem;
            min-height: 2.58rem;
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
            border-color: rgba(34, 211, 238, 0.75);
            box-shadow: 0 0 0 1px rgba(34, 211, 238, 0.35);
        }

        .st-key-auth_shell [data-baseweb="input"]:focus-within {
            border-color: #67b5f6 !important;
            box-shadow: 0 0 0 1px rgba(41, 130, 210, 0.3) !important;
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
            margin: 0 0 0.62rem 0;
            white-space: normal !important;
            word-break: break-word;
            max-width: 16ch;
        }

        .hero-sub {
            color: var(--ink-700);
            font-size: 1.02rem;
            line-height: 1.45;
            margin-bottom: 0.82rem;
            max-width: 48ch;
        }

        .stat-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-bottom: 0.9rem;
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
            background: linear-gradient(165deg, rgba(12, 28, 52, 0.88) 0%, rgba(8, 20, 40, 0.9) 100%);
            border: 1px solid rgba(92, 142, 198, 0.3);
            border-radius: 1.2rem;
            padding: 1rem 1.05rem;
            backdrop-filter: blur(4px);
            box-shadow: 0 14px 28px rgba(2, 8, 28, 0.34);
            animation: fadeInUp 380ms ease both;
            position: relative;
            overflow: hidden;
        }

        .spotlight-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, rgba(34, 211, 238, 0.85), rgba(59, 130, 246, 0.45), transparent);
        }

        .spotlight-card h4 {
            margin: 0 0 0.35rem 0;
            color: var(--ink-900);
            font-size: 1rem;
        }

        .spotlight-card p {
            margin: 0;
            color: var(--ink-700);
            font-size: 0.88rem;
            line-height: 1.42;
        }

        .proof-card {
            background: linear-gradient(165deg, rgba(9, 22, 42, 0.86) 0%, rgba(7, 18, 36, 0.88) 100%);
            border: 1px solid rgba(92, 142, 198, 0.28);
            border-radius: 1rem;
            padding: 0.8rem;
            box-shadow: 0 12px 22px rgba(2, 8, 28, 0.3);
            animation: fadeInUp 440ms ease both;
        }

        .proof-image {
            width: 100%;
            aspect-ratio: 16 / 10;
            border-radius: 0.72rem;
            border: 1px solid rgba(125, 162, 206, 0.34);
            margin-bottom: 0.62rem;
        }

        .proof-img-tag {
            width: 100%;
            aspect-ratio: 16 / 10;
            object-fit: cover;
            border-radius: 0.72rem;
            border: 1px solid rgba(125, 162, 206, 0.34);
            margin-bottom: 0.62rem;
            display: block;
        }

        .proof-before {
            background:
                radial-gradient(circle at 35% 30%, rgba(160, 196, 255, 0.45), transparent 36%),
                linear-gradient(150deg, rgba(19, 35, 66, 1) 0%, rgba(10, 24, 46, 1) 100%);
        }

        .proof-after {
            background:
                radial-gradient(circle at 70% 24%, rgba(34, 211, 238, 0.42), transparent 34%),
                linear-gradient(150deg, rgba(18, 75, 104, 0.95) 0%, rgba(12, 42, 79, 0.98) 100%);
        }

        .proof-alt {
            background:
                radial-gradient(circle at 28% 68%, rgba(251, 146, 60, 0.38), transparent 36%),
                linear-gradient(140deg, rgba(74, 46, 108, 0.95) 0%, rgba(18, 33, 74, 0.98) 100%);
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

        .feature-card {
            background: linear-gradient(165deg, rgba(9, 22, 42, 0.86) 0%, rgba(7, 18, 36, 0.88) 100%);
            border: 1px solid rgba(92, 142, 198, 0.28);
            border-radius: 1.2rem;
            padding: 0.95rem 1rem;
            min-height: 112px;
            transition: transform 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
            box-shadow: 0 12px 22px rgba(2, 8, 28, 0.32);
            animation: fadeInUp 430ms ease both;
            position: relative;
            overflow: hidden;
        }

        .feature-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 3px;
            height: 100%;
            background: linear-gradient(180deg, rgba(34, 211, 238, 0.85), rgba(59, 130, 246, 0.4));
        }

        .feature-card:hover {
            transform: translateY(-3px);
            border-color: rgba(34, 211, 238, 0.48);
            box-shadow: 0 14px 28px rgba(2, 6, 23, 0.34);
        }

        .feature-card h4 {
            color: var(--ink-900);
            margin: 0 0 0.24rem 0;
            font-size: 1.1rem;
        }

        .feature-card p {
            color: var(--ink-700);
            margin: 0;
            font-size: 0.86rem;
            line-height: 1.4;
        }

        .section-title {
            margin-top: 0.3rem;
            margin-bottom: 0.65rem;
            color: var(--ink-900);
            font-size: 1.08rem;
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

        button[data-testid="baseButton-primary"]:active,
        button[data-testid="baseButton-secondary"]:active {
            transform: translateY(0);
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

        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation: none !important;
                transition: none !important;
                scroll-behavior: auto !important;
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
                font-size: 0.95rem;
                overflow-wrap: anywhere;
            }
            .hero-title {
                font-size: clamp(1.42rem, 6.2vw, 1.72rem);
                line-height: 1.14;
                overflow-wrap: anywhere;
            }
            .feature-card {
                min-height: auto;
            }
            .spotlight-card,
            .feature-card,
            .panel-card,
            .proof-card {
                padding: 0.72rem 0.75rem;
            }
            .st-key-auth_shell {
                padding: 0.75rem;
            }
            .spotlight-card p,
            .feature-card p,
            .proof-card p {
                overflow-wrap: anywhere;
                font-size: 0.88rem;
            }
            .stat-row {
                gap: 0.35rem;
            }
            .stat-chip {
                font-size: 0.76rem;
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


assets_dir = Path(__file__).resolve().parent / "assets"
icon_png = assets_dir / "artify_logo.png"
logo_svg = assets_dir / "artify_logo.svg"
logo_asset = logo_svg if logo_svg.exists() else icon_png


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

st.set_page_config(
    page_title="Artify AI",
    page_icon=str(icon_png) if icon_png.exists() else ":art:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_resource
def initialize_app() -> None:
    create_tables()


initialize_app()
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
    st.markdown('<div class="side-head">Workspace</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="side-sub">Navigation and account actions</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if st.session_state.logged_in:
        st.success(f"Signed in as {st.session_state.username}")
        if st.session_state.email:
            st.caption(st.session_state.email)

        if st.button("Open Dashboard", width="stretch", type="primary"):
            st.switch_page("pages/dashboard.py")

        if st.button("Log out", width="stretch"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.email = None
            st.session_state.user_id = None
            st.session_state.remember_me = False
            st.rerun()
    else:
        st.info("Log in or register to access your dashboard, save edits, and manage your workspace.")
        if st.button("Open dashboard", width="stretch"):
            st.warning("Please sign in from the main account panel first.")

left, right = st.columns([1.55, 1], gap="large")

with left:
    st.markdown('<div class="brand-kicker">AI CARTOONIZATION STUDIO</div>', unsafe_allow_html=True)
    st.markdown(
        '<h1 class="hero-title">Turn photos into crisp, studio-style cartoon visuals.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-sub">Upload, stylize, compare, and export in a clean flow built for creators and marketing teams.</p>',
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

    start_creating = st.button("Start Creating", type="primary", width="stretch")
    if start_creating:
        if st.session_state.logged_in:
            st.switch_page("pages/dashboard.py")
        else:
            st.warning("Please sign in from the account panel on the right to continue.")

    st.caption("Built for fast social posts, campaigns, and portfolio-ready outputs.")

with right:
    if st.session_state.logged_in:
        st.markdown(
            """
            <div class="panel-card">
                <p class="panel-title">Welcome back</p>
                <p class="panel-sub">You are signed in and ready to process new images.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.success(f"Signed in as {st.session_state.username}")
        if st.session_state.email:
            st.caption(st.session_state.email)
        if st.button("Go to Dashboard", width="stretch", type="primary"):
            st.switch_page("pages/dashboard.py")
    else:
        auth_card_container = st.container(key="auth_shell")
        with auth_card_container:
            st.markdown(
                """
                <p class="panel-title">Account</p>
                """,
                unsafe_allow_html=True,
            )
            login_tab, register_tab = st.tabs(["Log in", "Register"])

            with login_tab:
                with st.form("login_form"):
                    identifier = st.text_input(
                        "Email or username",
                        key="login_identifier",
                        placeholder="you@example.com or username",
                    )
                    password = st.text_input(
                        "Password",
                        type="password",
                        key="login_password",
                        placeholder="Enter your password",
                    )
                    remember_me = st.checkbox(
                        "Remember me on this device",
                        key="login_remember_me",
                    )
                    login_submit = st.form_submit_button(
                        "Sign in",
                        width="stretch",
                        type="primary",
                    )
                    st.caption("Forgot password? Recovery options are coming soon.")

                if login_submit:
                    result = login_user(identifier.strip(), password)
                    if result.get("success"):
                        st.session_state.logged_in = True
                        st.session_state.username = result.get("username")
                        st.session_state.email = result.get("email")
                        st.session_state.user_id = result.get("user_id")
                        st.session_state.remember_me = bool(remember_me)
                        st.rerun()
                    else:
                        st.error(result.get("message", "Login failed."))

            with register_tab:
                with st.form("register_form"):
                    reg_col1, reg_col2 = st.columns(2, gap="small")
                    with reg_col1:
                        reg_user = st.text_input(
                            "Username",
                            key="reg_username",
                            placeholder="e.g. alex.smith",
                        )
                    with reg_col2:
                        reg_email = st.text_input(
                            "Email",
                            key="reg_email",
                            placeholder="you@example.com",
                        )
                    reg_pass = st.text_input(
                        "Password",
                        type="password",
                        key="reg_password",
                        placeholder="Create a strong password",
                    )
                    reg_confirm = st.text_input(
                        "Confirm password",
                        type="password",
                        key="reg_confirm",
                        placeholder="Re-enter your password",
                    )
                    st.caption("Use at least 8 characters with uppercase, lowercase, number, and special symbol.")
                    agree_terms = st.checkbox("I agree to the Terms and Conditions", key="reg_terms")
                    register_submit = st.form_submit_button("Register", width="stretch", type="primary")

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
                            st.rerun()
                        else:
                            st.error(result.get("message", "Registration failed."))

    st.markdown(
        """
        <div class="spotlight-card">
            <h4>Quick flow</h4>
            <p>1. Upload image<br>2. Apply style preset<br>3. Compare and export final artwork</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="section-title">Style Preview</div>', unsafe_allow_html=True)
before_image = assets_dir / "before.jpeg"
cartoon_image = assets_dir / "cartoon_style.png"
pencil_color_image = assets_dir / "pencil_color.png"
sketch_image = assets_dir / "sketch_style.png"

preview_cards = [
    {
        "title": "Before",
        "description": "Original photo input ready for style transformation.",
        "path": before_image,
        "fallback_class": "proof-before",
    },
    {
        "title": "Cartoon Style",
        "description": "Soft-shaded look for social content and branding visuals.",
        "path": cartoon_image,
        "fallback_class": "proof-after",
    },
    {
        "title": "Pencil Colour Style",
        "description": "Color-rich pencil rendering with clean strokes.",
        "path": pencil_color_image,
        "fallback_class": "proof-alt",
    },
    {
        "title": "Sketch Style",
        "description": "Graphite-style outlines for classic sketch output.",
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
