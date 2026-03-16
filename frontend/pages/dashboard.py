import base64
import sys
import hashlib
import time
from pathlib import Path
from datetime import datetime
from typing import cast

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from database.db import get_connection
from frontend.user_profile import sync_user_profile_state, render_sidebar_profile
from backend.image_upload import get_image_metadata, save_uploaded_image, validate_image
from backend.image_processing import (
    bgr_to_rgb,
    classic_cartoon,
    encode_image_to_png,
    pencil_color_effect,
    read_image,
    sketch_effect,
)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _img_to_b64(path: str) -> str | None:
    try:
        p = Path(path)
        if not p.is_file():
            return None
        ext = p.suffix.lstrip(".").lower()
        mime = "image/png" if ext == "png" else f"image/{ext}"
        return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
    except Exception:
        return None


def _fmt_date(raw: str) -> str:
    try:
        dt = datetime.strptime(str(raw), "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(raw)


# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

def fetch_dashboard_data(user_id: int | None) -> tuple[dict, list[dict], dict]:
    metrics = {"images_processed": 0, "completed_payments": 0, "total_spent": 0.0}
    transactions: list[dict] = []
    profile = {
        "created_at": "N/A", "last_login": "N/A",
        "is_active": True, "account_locked": False, "failed_attempts": 0,
    }
    if not user_id:
        return metrics, transactions, profile
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM ImageHistory WHERE user_id=?", (user_id,))
            metrics["images_processed"] = c.fetchone()[0] or 0

            c.execute(
                "SELECT COALESCE(SUM(amount),0), COUNT(*) FROM Transactions "
                "WHERE user_id=? AND payment_status='Completed'", (user_id,)
            )
            total_spent, completed_count = c.fetchone()
            metrics["total_spent"] = float(total_spent or 0)
            metrics["completed_payments"] = completed_count or 0

            c.execute(
                "SELECT transaction_date, amount, payment_status, payment_method "
                "FROM Transactions WHERE user_id=? ORDER BY transaction_date DESC LIMIT 12",
                (user_id,)
            )
            transactions = [
                {"Date": r[0], "Amount (USD)": f"{float(r[1]):.2f}", "Status": r[2], "Method": r[3]}
                for r in c.fetchall()
            ]

            c.execute(
                "SELECT created_at, last_login, is_active, account_locked, failed_attempts "
                "FROM Users WHERE user_id=?", (user_id,)
            )
            row = c.fetchone()
            if row:
                profile = {
                    "created_at": row[0] or "N/A", "last_login": row[1] or "N/A",
                    "is_active": bool(row[2]), "account_locked": bool(row[3]),
                    "failed_attempts": row[4] or 0,
                }
    except Exception:
        pass
    return metrics, transactions, profile


def fetch_recent_creations(user_id: int | None, limit: int = 8) -> list[dict]:
    if not user_id:
        return []
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT processed_image_path, style_applied, processing_date "
                "FROM ImageHistory WHERE user_id=? ORDER BY processing_date DESC LIMIT ?",
                (user_id, limit)
            )
            return [
                {"processed_image_path": r[0], "style_applied": r[1], "processing_date": r[2]}
                for r in c.fetchall()
            ]
    except Exception:
        return []


# ─────────────────────────────────────────────
# STYLES  — aligned with homepage design language
# ─────────────────────────────────────────────

def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

        /* ── Base ── */
        :root {
            --ink-900: #111111;
            --ink-700: #374151;
            --ink-500: #64748b;
            --border:  #e5e7eb;
            --radius:  1rem;
            --blue:    #4f7df2;
        }

        html, body, [class*="css"],
        [data-testid="stApp"],
        [data-testid="stAppViewContainer"],
        [data-testid="stAppViewContainer"] > .main,
        [data-testid="stMain"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        .stApp {
            font-family: "Manrope", "Segoe UI", sans-serif !important;
            background: #ffffff !important;
            background-color: #ffffff !important;
            color: var(--ink-700);
        }

        .block-container {
            padding-top: 2rem !important;
            padding-bottom: 3rem !important;
            max-width: 1140px !important;
        }

        /* ── Sidebar — minimal, like homepage ── */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid var(--border) !important;
        }
        [data-testid="stSidebar"] > div:first-child,
        [data-testid="stSidebarContent"] {
            background: #ffffff !important;
        }

        /* Hide Streamlit's auto-generated page navigation list */
        [data-testid="stSidebarNav"] { display: none !important; }

        /* Sidebar nav links (Streamlit's built-in pages nav) */
        [data-testid="stSidebarNav"] {
            background: transparent !important;
            padding-top: 0.5rem !important;
        }
        [data-testid="stSidebarNavItems"] {
            gap: 0.15rem !important;
        }
        [data-testid="stSidebarNavLink"] {
            border-radius: 0.8rem !important;
            color: #374151 !important;
            padding: 0.52rem 0.75rem !important;
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            background: transparent !important;
        }
        [data-testid="stSidebarNavLink"]:hover {
            background: #f1f5f9 !important;
            color: #0f172a !important;
        }
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background: #f1f5f9 !important;
            color: #0f172a !important;
        }

        /* Sidebar collapse button */
        button[data-testid="collapsedControl"] {
            background: #ffffff !important;
            border: 1px solid #dbe3ef !important;
            border-radius: 0.6rem !important;
            color: #374151 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        }
        button[data-testid="collapsedControl"] svg { fill: #374151 !important; }

        /* Sidebar custom nav buttons */
        [data-testid="stSidebar"] .stButton button {
            border: none !important;
            background: transparent !important;
            color: #374151 !important;
            font-weight: 600 !important;
            border-radius: 0.8rem !important;
            padding: 0.55rem 0.75rem !important;
            display: flex !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
            transition: all 0.2s ease !important;
            width: 100% !important;
        }
        [data-testid="stSidebar"] .stButton button p {
            font-size: 0.95rem !important;
            color: inherit !important;
        }
        [data-testid="stSidebar"] .stButton button:hover {
            background: #f1f5f9 !important;
            color: #0f172a !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
            transform: translateY(-1px) !important;
        }
        /* Active Streamlit Button (primary) */
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 14px rgba(79,125,242,.22) !important;
        }
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] p {
            color: #ffffff !important;
        }
        [data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 18px rgba(79,125,242,.28) !important;
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            color: #ffffff !important;
        }
        .sb-divider {
            height: 1px;
            background: var(--border);
            margin: 0.65rem 0.5rem;
        }
        /* Sidebar Profile */
        .sidebar-profile {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-top: 0.5rem;
            margin-bottom: 2rem;
        }
        .profile-avatar {
            width: 72px;
            height: 72px;
            border-radius: 50%;
            background: linear-gradient(135deg, #e0e7ff, #c7d2fe);
            color: #4f46e5;
            font-size: 2rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.8rem;
            box-shadow: 0 4px 14px rgba(0,0,0,0.05);
        }
        .profile-name {
            font-size: 1.05rem;
            font-weight: 700;
            color: #0f172a;
        }
        /* ── Page header ── */
        .dash-kicker {
            display: inline-block;
            background: #f4f4f5; color: #71717a;
            border: 1px solid #e4e4e7;
            border-radius: 999px;
            padding: 0.28rem 0.8rem;
            font-size: 0.68rem; letter-spacing: 0.1em;
            text-transform: uppercase; font-weight: 700;
            margin-bottom: 0.45rem;
        }
        .dash-title {
            margin: 0 0 0.35rem 0;
            font-size: clamp(1.85rem, 3vw, 2.55rem);
            font-weight: 800; color: #0f172a;
            letter-spacing: -0.03em; line-height: 1.05;
        }
        .dash-sub {
            color: var(--ink-500);
            font-size: 0.97rem; line-height: 1.55;
            margin-bottom: 1.6rem;
        }

        /* ── Stat cards ── */
        .stat-row {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-bottom: 2.6rem;
        }
        .stat-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.2rem 1.35rem 1.05rem 1.35rem;
            box-shadow: 0 1px 6px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            gap: 0.55rem;
        }
        .stat-card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .stat-icon {
            width: 2.5rem; height: 2.5rem;
            border-radius: 0.65rem;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.05rem; flex-shrink: 0;
        }
        .stat-icon-blue   { background: linear-gradient(135deg, #4361ee, #3a0ca3); }
        .stat-icon-purple { background: linear-gradient(135deg, #7209b7, #560bad); }
        .stat-icon-pink   { background: linear-gradient(135deg, #f72585, #b5179e); }
        .stat-badge {
            font-size: 0.73rem; font-weight: 700;
            border-radius: 999px; padding: 0.17rem 0.52rem;
        }
        .stat-badge-green { color: #15803d; background: #dcfce7; }
        .stat-badge-blue  { color: #1d4ed8; background: #dbeafe; }
        .stat-value {
            font-size: 1.95rem; font-weight: 800;
            color: #0f172a; line-height: 1;
            letter-spacing: -0.035em;
        }
        .stat-label {
            font-size: 0.85rem; color: var(--ink-500); font-weight: 500;
        }

        /* ── Recent Creations ── */
        .rc-header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            margin-bottom: 1.35rem;
        }
        .rc-title {
            font-size: 1.65rem; font-weight: 800;
            color: #0f172a; letter-spacing: -0.025em; line-height: 1.1;
            margin: 0 0 0.18rem 0;
        }
        .rc-sub  { color: var(--ink-500); font-size: 0.9rem; margin: 0; }
        .rc-view-all {
            font-size: 0.9rem; font-weight: 700;
            color: var(--blue) !important; text-decoration: none;
            padding-bottom: 0.2rem; white-space: nowrap;
        }
        .rc-view-all:hover { text-decoration: underline; }

        /* Card grid */
        .rc-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin-bottom: 0.6rem;
        }
        .rc-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: 0 1px 6px rgba(0,0,0,0.06);
            transition: box-shadow .18s ease, transform .18s ease;
            animation: fadeInUp .35s ease both;
        }
        .rc-card:hover {
            box-shadow: 0 6px 22px rgba(0,0,0,0.1);
            transform: translateY(-3px);
        }
        .rc-card-img {
            width: 100%; height: 200px;
            object-fit: cover; display: block;
        }
        .rc-card-img-fallback {
            width: 100%; height: 200px;
            background: linear-gradient(135deg, #f0f3f9, #e2e8f0);
            display: flex; align-items: center; justify-content: center;
            font-size: 2rem; color: #94a3b8;
        }
        .rc-card-body { padding: 0.8rem 0.95rem 0.65rem 0.95rem; }
        .rc-card-style {
            font-size: 0.95rem; font-weight: 700;
            color: #0f172a; margin: 0 0 0.14rem 0;
        }
        .rc-card-date { font-size: 0.78rem; color: var(--ink-500); margin: 0; }

        /* Empty state */
        .rc-empty {
            border: 2px dashed #e2e8f0;
            border-radius: 1.2rem;
            padding: 3.5rem 2rem;
            text-align: center;
            background: #fafbfd;
            margin-bottom: 1.2rem;
        }
        .rc-empty-icon  { font-size: 2.8rem; margin-bottom: 0.9rem; display: block; }
        .rc-empty-title { font-size: 1.15rem; font-weight: 800; color: #0f172a; margin: 0 0 0.45rem 0; }
        .rc-empty-text  { color: var(--ink-500); font-size: 0.9rem; line-height: 1.55; max-width: 340px; margin: 0 auto; }

        /* Divider */
        .dash-hr { border: none; border-top: 1px solid var(--border); margin: 1.8rem 0 1.5rem 0; }

        /* Panel sections */
        .panel-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 1.1rem 1.2rem;
            box-shadow: 0 1px 5px rgba(0,0,0,0.04);
        }

        /* Buttons — primary */
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            border: none !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            border-radius: 0.75rem !important;
            box-shadow: 0 4px 14px rgba(79,125,242,.22) !important;
            transition: transform .15s, box-shadow .15s !important;
        }
        button[data-testid="baseButton-primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 18px rgba(79,125,242,.28) !important;
        }

        /* Streamlit metric — hide (we use custom HTML) */
        [data-testid="stMetric"] { display: none !important; }

        /* ─────────────────────────────────────
           AI IMAGE STUDIO (Editor) LAYOUT
           ───────────────────────────────────── */

        .studio-shell {
            margin-top: 0.5rem;
            display: flex;
            flex-direction: column;
            gap: 1.4rem;
        }

        .studio-layout {
            display: grid;
            grid-template-columns: minmax(0, 1.5fr) minmax(0, 1.1fr);
            gap: 1.3rem;
            align-items: flex-start;
        }

        .studio-left,
        .studio-right {
            display: flex;
            flex-direction: column;
            gap: 0.9rem;
        }

        /* Upload / preview panel */
        .studio-panel {
            background: #ffffff;
            border-radius: 1.3rem;
            padding: 1.1rem 1.15rem 1.15rem 1.15rem;
            border: 1px solid #e5e7eb;
            box-shadow: 0 22px 60px rgba(15, 23, 42, 0.08);
        }

        .studio-panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.75rem;
        }

        .studio-panel-title {
            font-size: 0.95rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #9ca3af;
        }

        .studio-panel-kicker {
            font-size: 0.78rem;
            font-weight: 600;
            color: #4b5563;
        }

        /* File uploader */
        [data-testid="stFileUploader"] section {
            border-radius: 1.05rem;
            border: 1.5px dashed #d4d4d8;
            background: #fafbfd;
            box-shadow: 0 20px 40px rgba(148, 163, 184, 0.16);
        }

        /* Before / After wrapper */
        .studio-before-after {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 0.9rem;
        }

        .studio-preview-card {
            background: #f9fafb;
            border-radius: 1.1rem;
            padding: 0.6rem;
            border: 1px solid #e5e7eb;
            box-shadow: 0 16px 40px rgba(148, 163, 184, 0.2);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }

        .studio-preview-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 48px rgba(15, 23, 42, 0.22);
        }

        .studio-preview-label {
            font-size: 0.78rem;
            font-weight: 600;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #9ca3af;
            margin-bottom: 0.45rem;
        }

        .studio-preview-image {
            width: 100%;
            border-radius: 0.9rem;
            overflow: hidden;
        }

        /* Meta card (right of preview) */
        .meta-card {
            border-radius: 1.1rem;
            border: 1px solid #e5e7eb;
            background: radial-gradient(circle at top left, #eef2ff 0, #ffffff 45%);
            padding: 0.95rem 1rem;
            box-shadow: 0 18px 48px rgba(129, 140, 248, 0.18);
        }
        .meta-title {
            font-size: 0.9rem;
            font-weight: 700;
            color: #111827;
            margin-bottom: 0.6rem;
        }
        .meta-item {
            display: flex;
            justify-content: space-between;
            font-size: 0.82rem;
            padding: 0.18rem 0;
            color: #4b5563;
        }
        .meta-key   { font-weight: 600; }
        .meta-value { font-weight: 500; }

        /* Style cards — soft shadow grid */
        .style-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.75rem;
        }

        .style-card {
            position: relative;
            padding: 0.9rem 0.95rem;
            border-radius: 1.1rem;
            background: radial-gradient(circle at 0% 0%, #eef2ff 0, #ffffff 40%);
            border: 1px solid rgba(226, 232, 240, 0.9);
            box-shadow: 0 22px 60px rgba(15, 23, 42, 0.12);
            cursor: pointer;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
        }

        .style-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 26px 70px rgba(15, 23, 42, 0.18);
            border-color: #c7d2fe;
        }

        .style-card.is-selected {
            border-color: #4f46e5;
            box-shadow: 0 26px 80px rgba(79, 70, 229, 0.4);
        }

        .style-name {
            font-size: 0.98rem;
            font-weight: 700;
            color: #111827;
        }

        .style-description {
            font-size: 0.8rem;
            color: #6b7280;
            line-height: 1.5;
        }

        .style-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.2rem;
        }

        .style-tagline {
            font-size: 0.78rem;
            color: #4b5563;
            font-weight: 600;
        }

        .style-badge {
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 0.13rem 0.5rem;
            border-radius: 999px;
            background: linear-gradient(135deg, #f97316, #ec4899);
            color: #ffffff;
            box-shadow: 0 10px 26px rgba(236, 72, 153, 0.45);
        }

        .style-thumb {
            margin-top: 0.35rem;
            font-size: 0.74rem;
            font-weight: 600;
            color: #9ca3af;
        }

        /* Studio controls */
        .studio-controls {
            margin-top: 0.9rem;
            padding: 0.85rem 0.4rem 0 0.4rem;
            border-top: 1px dashed #e5e7eb;
        }

        /* Metrics row beneath workspace */
        .metric-row-studio {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.9rem;
        }

        .metric-card-studio {
            background: #ffffff;
            border-radius: 1.1rem;
            padding: 0.8rem 0.95rem 0.85rem 0.95rem;
            border: 1px solid #e5e7eb;
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
        }

        .metric-label {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #9ca3af;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            font-size: 1.15rem;
            font-weight: 800;
            color: #111827;
            letter-spacing: -0.03em;
        }

        .metric-caption {
            font-size: 0.78rem;
            color: #6b7280;
            margin-top: 0.12rem;
        }

        @keyframes fadeInUp {
            from { opacity:0; transform:translateY(8px); }
            to   { opacity:1; transform:translateY(0);   }
        }

        /* Responsive */
        @media(max-width: 900px) {
            .stat-row  { grid-template-columns: 1fr; }
            .rc-grid   { grid-template-columns: repeat(2, 1fr); }
            .studio-layout { grid-template-columns: 1fr; }
            .style-grid { grid-template-columns: 1fr; }
            .metric-row-studio { grid-template-columns: 1fr; }
            .rc-title  { font-size: 1.3rem; }
        }
        @media(max-width: 540px) {
            .rc-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Artify Dashboard",
    page_icon=":art:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_styles()

# Auth guard
if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.switch_page("app.py")
    st.stop()

sync_user_profile_state()

username = st.session_state.get("user_name") or st.session_state.get("username", "User")
email    = st.session_state.get("email", "Not available")
user_id  = st.session_state.get("user_id")

metrics, transactions, profile = fetch_dashboard_data(user_id)
recent_creations = fetch_recent_creations(user_id, limit=8)

# Initialize editor-related session state so it persists across sections
st.session_state.setdefault("current_image_path", None)
st.session_state.setdefault("current_image_hash", None)
st.session_state.setdefault("processed_image", None)
st.session_state.setdefault("processed_style", None)
st.session_state.setdefault("processing_time", None)
st.session_state.setdefault("current_style", None)
st.session_state.setdefault("selected_style", "classic_cartoon")
st.session_state.setdefault("output_quality", None)

# Determine active section from session BEFORE sidebar render
section = st.session_state.get("dash_section", "dashboard")

# ─────────────────────────────────────────────
# SIDEBAR — minimal, no logo, no workspace labels
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        """
        <style>
        /* Sidebar-only navigation styling (scoped) */
        [data-testid="stSidebar"] {
            background: #ffffff !important;
        }

        /* Make sidebar content a flex column so footer can stick bottom */
        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            display: flex !important;
            flex-direction: column !important;
            min-height: 100vh !important;
        }

        /* Navigation buttons base */
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 0.95rem !important;
            border: 1px solid #e6edf7 !important;
            background: #ffffff !important;
            box-shadow: 0 10px 22px rgba(148, 163, 184, 0.16) !important;
            color: #24324a !important;
            font-weight: 750 !important;
            text-align: left !important;
            justify-content: flex-start !important;
            gap: 0.65rem !important;
            padding: 0.72rem 0.85rem !important;
            min-height: 3.1rem !important;
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease !important;
        }

        [data-testid="stSidebar"] .stButton > button:hover {
            transform: translateY(-1px) !important;
            border-color: #cfe0ff !important;
            box-shadow: 0 14px 26px rgba(148, 163, 184, 0.20) !important;
        }

        /* Active state (Streamlit primary buttons) */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            border: none !important;
            background: linear-gradient(135deg, #4d7ff5 0%, #18b5df 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 16px 34px rgba(77, 127, 245, 0.28) !important;
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"] * {
            color: #ffffff !important;
        }

        /* Ensure button label text aligns left */
        [data-testid="stSidebar"] .stButton > button div,
        [data-testid="stSidebar"] .stButton > button p,
        [data-testid="stSidebar"] .stButton > button span {
            text-align: left !important;
        }

        /* Footer */
        [data-testid="stSidebar"] .st-key-sb_footer {
            margin-top: auto !important;
            padding-top: 0.75rem !important;
            padding-bottom: 0.75rem !important;
        }

        [data-testid="stSidebar"] hr.sb-hr {
            border: none !important;
            border-top: 1px solid #e6edf7 !important;
            margin: 0.75rem 0 0.9rem 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_sidebar_profile()

    # Navigation — SPA style, sections within dashboard
    nav = st.container(key="sb_nav")
    with nav:
        if st.button(
            "📊  Dashboard",
            use_container_width=True,
            type="primary" if section == "dashboard" else "secondary",
            key="sb_nav_dashboard",
        ):
            st.session_state["dash_section"] = "dashboard"
            st.rerun()

        if st.button(
            "🪄  Image Editor",
            use_container_width=True,
            type="primary" if section == "editor" else "secondary",
            key="sb_nav_editor",
        ):
            st.session_state["dash_section"] = "editor"
            st.rerun()

        if st.button(
            "🕒  My Images",
            use_container_width=True,
            type="primary" if section == "my_images" else "secondary",
            key="sb_nav_my_images",
        ):
            st.session_state["dash_section"] = "my_images"
            st.rerun()

        if st.button(
            "💳  Payments",
            use_container_width=True,
            type="primary" if section == "payments" else "secondary",
            key="sb_nav_payments",
        ):
            st.session_state["dash_section"] = "payments"
            st.rerun()

        if st.button(
            "👤  Profile",
            use_container_width=True,
            type="primary" if section == "profile" else "secondary",
            key="sb_nav_profile",
        ):
            st.session_state["dash_section"] = "profile"
            st.rerun()

    footer = st.container(key="sb_footer")
    with footer:
        st.markdown('<hr class="sb-hr" />', unsafe_allow_html=True)

        # Logout remains neutral and separated at the bottom
        if st.button("🚪  Log out", use_container_width=True, type="secondary", key="sb_logout"):
            st.session_state.clear()
            st.switch_page("app.py")
            st.stop()

# ─────────────────────────────────────────────
# MAIN — section-based view switching (Dashboard, Editor, My Images, Payments, Profile)
# ─────────────────────────────────────────────

if section == "dashboard":
    # Header
    
    st.markdown(f'<h1 class="dash-title">Welcome back, {username} 👋</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="dash-sub">Here\'s an overview of your AI artwork activity.</p>',
        unsafe_allow_html=True,
    )

    # ── Stat cards ──
    images_count = metrics["images_processed"]
    st.markdown(
        f"""
        <div class="stat-row">
          <div class="stat-card">
            <div class="stat-card-top">
              <div class="stat-icon stat-icon-blue">⚡</div>
              <span class="stat-badge stat-badge-green">↑ +12%</span>
            </div>
            <div class="stat-value">{images_count}</div>
            <div class="stat-label">Images Processed</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-top">
              <div class="stat-icon stat-icon-purple">🎨</div>
              <span class="stat-badge stat-badge-blue">New</span>
            </div>
            <div class="stat-value">3</div>
            <div class="stat-label">Available Styles</div>
          </div>
          <div class="stat-card">
            <div class="stat-card-top">
              <div class="stat-icon stat-icon-pink">⬇</div>
              <span class="stat-badge stat-badge-green">↑ +8%</span>
            </div>
            <div class="stat-value">{images_count}</div>
            <div class="stat-label">Total Downloads</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Recent Creations header ──
    st.markdown(
        """
        <div class="rc-header">
          <div>
            <p class="rc-title">Recent Creations</p>
            <p class="rc-sub">Your latest AI-generated artwork</p>
          </div>
          <a class="rc-view-all" href="#">View All →</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Cards or empty state ──
    if recent_creations:
        cards_html = '<div class="rc-grid">'
        download_data = []  # list of (img_bytes, filename, key)

        for idx, item in enumerate(recent_creations[:8]):
            img_path = item["processed_image_path"]
            style    = item["style_applied"]
            date_str = _fmt_date(item["processing_date"])
            b64      = _img_to_b64(img_path)

            if b64:
                img_html = f'<img class="rc-card-img" src="{b64}" alt="{style}">'
            else:
                img_html = '<div class="rc-card-img-fallback">🖼</div>'

            cards_html += f"""
            <div class="rc-card">
                {img_html}
                <div class="rc-card-body">
                    <p class="rc-card-style">{style}</p>
                    <p class="rc-card-date">{date_str}</p>
                </div>
            </div>
            """
            try:
                img_bytes = Path(img_path).read_bytes()
                fname = f"artify_{style.lower().replace(' ','_')}.png"
                download_data.append((img_bytes, fname, f"dl_{idx}"))
            except Exception:
                continue

        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        # Download buttons aligned to cards
        COLS = 4
        for row_start in range(0, len(recent_creations[:8]), COLS):
            chunk = download_data[row_start: row_start + COLS]
            cols  = st.columns(len(chunk))
            for col, (data, fname, key) in zip(cols, chunk):
                with col:
                    if data and fname and key:
                        st.download_button(
                            "⬇  Download", data=data,
                            file_name=fname, mime="image/png",
                            key=key, use_container_width=True,
                        )
    else:
        st.markdown(
            """
            <div class="rc-empty">
                <span class="rc-empty-icon">✨</span>
                <p class="rc-empty-title">No creations yet</p>
                <p class="rc-empty-text">
                    Start by creating your first cartoon in the Image Editor tab.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:.5rem'></div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# IMAGE EDITOR PANEL (in-dashboard workspace)
# ─────────────────────────────────────────────

elif section == "editor":
    st.markdown('<h1 class="dash-title">AI Image Studio</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="dash-sub">Upload once, explore multiple AI styles, and compare results side‑by‑side.</p>',
        unsafe_allow_html=True,
    )

    # Backend-driven style dictionary (labels & descriptions injected via f-strings)
    STYLE_CONFIG = {
        "classic_cartoon": {
            "label": "Classic Cartoon",
            "description": "Bold outlines and smooth shading for a studio cartoon look.",
            "tagline": "Great for avatars & branding",
            "popular": True,
            "preview_asset": "cartoon_style.png",
        },
        "sketch": {
            "label": "Sketch",
            "description": "High-contrast pencil sketch lines with expressive depth.",
            "tagline": "Perfect for concept art",
            "popular": False,
            "preview_asset": "sketch_style.png",
        },
        "pencil_color": {
            "label": "Pencil Color",
            "description": "Layered colored-pencil texture with soft gradients.",
            "tagline": "Ideal for posters & print",
            "popular": False,
            "preview_asset": "pencil_color.png",
        },
    }

    selected_style_key = cast(str, st.session_state.get("selected_style", "classic_cartoon"))

    studio = st.container()
    with studio:
        st.markdown('<div class="studio-shell">', unsafe_allow_html=True)

        # ── Top layout: left (upload/preview) / right (style selection) ──
        left_col, right_col = st.columns([1.45, 1], gap="large")

        # LEFT: uploader + preview / before-after
        with left_col:
            st.markdown(
                """
                <div class="studio-panel">
                    <div class="studio-panel-header">
                        <div>
                            <div class="studio-panel-title">Upload & Preview</div>
                            <div class="studio-panel-kicker">Drop an image to start</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            uploaded_file = st.file_uploader(
                "Upload image",
                type=["jpg", "jpeg", "png", "bmp"],
                help="Supported formats: JPG, JPEG, PNG, BMP. Max size: 10 MB.",
            )

            if uploaded_file is not None:
                try:
                    is_valid, validation_message = validate_image(uploaded_file, max_size_mb=10)
                except Exception as exc:
                    st.error(f"Could not validate file: {exc}")
                    is_valid = False
                    validation_message = ""

                if not is_valid:
                    if validation_message:
                        st.error(validation_message)
                else:
                    file_hash = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
                    current_hash = st.session_state.get("current_image_hash")
                    current_path = st.session_state.get("current_image_path")

                    if (not current_path) or (file_hash != current_hash):
                        try:
                            saved_path = save_uploaded_image(uploaded_file)
                        except Exception as exc:
                            st.error(f"Failed to save image: {exc}")
                        else:
                            st.session_state.current_image_path = saved_path
                            st.session_state.current_image_hash = file_hash
                            st.session_state.processed_image = None
                            st.session_state.processed_style = None
                            st.session_state.processing_time = None
                            st.session_state.current_style = None
                            st.session_state.output_quality = None

            current_image_path = st.session_state.get("current_image_path")
            processed_image = st.session_state.get("processed_image")
            processed_style = st.session_state.get("processed_style")
            processing_time = st.session_state.get("processing_time")

            if current_image_path:
                image_path_obj = Path(current_image_path)
                if not image_path_obj.exists():
                    st.warning("Saved image path no longer exists. Please upload again.")
                    st.session_state.current_image_path = None
                    st.session_state.current_image_hash = None
                    st.session_state.processed_image = None
                    st.session_state.processed_style = None
                    st.session_state.processing_time = None
                    st.session_state.output_quality = None
                else:
                    try:
                        metadata = get_image_metadata(current_image_path)
                    except Exception as exc:
                        st.error(f"Could not read image metadata: {exc}")
                        metadata = None

                    # Before / After layout inside left panel
                    try:
                        original_bgr = read_image(current_image_path)
                    except Exception as exc:
                        st.error(f"Could not read original image for display: {exc}")
                        original_display = None
                        processed_display = None
                    else:
                        original_display = bgr_to_rgb(original_bgr)
                        if processed_image is not None:
                            if processed_image.ndim == 2:
                                processed_display = processed_image
                            else:
                                processed_display = bgr_to_rgb(processed_image)
                        else:
                            processed_display = None

                    st.markdown(
                        '<div class="studio-before-after">',
                        unsafe_allow_html=True,
                    )
                    col_orig, col_proc = st.columns(2, gap="small")

                    with col_orig:
                        st.markdown(
                            '<div class="studio-preview-card"><div class="studio-preview-label">Original</div>',
                            unsafe_allow_html=True,
                        )
                        if original_display is not None:
                            st.image(original_display, use_column_width=True)
                        else:
                            st.image(current_image_path, use_column_width=True)
                        st.caption(str(image_path_obj))
                        st.markdown("</div>", unsafe_allow_html=True)

                    with col_proc:
                        label = f"{processed_style} Result" if processed_style else "Result"
                        st.markdown(
                            f'<div class="studio-preview-card"><div class="studio-preview-label">{label}</div>',
                            unsafe_allow_html=True,
                        )
                        if processed_display is not None:
                            st.image(processed_display, use_column_width=True)
                        else:
                            st.caption("Run a style on the left to see the result here.")
                        if processing_time is not None:
                            st.caption(f"Processing time: {processing_time:.2f} seconds")
                        st.markdown("</div>", unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)  # end studio-before-after

                    # Metadata card stays on left but visually acts like a right column in panel
                    if metadata:
                        st.markdown(
                            f"""
                            <div class="meta-card" style="margin-top:0.9rem;">
                                <div class="meta-title">Image Metadata</div>
                                <div class="meta-item"><span class="meta-key">Width</span><span class="meta-value">{metadata['width']} px</span></div>
                                <div class="meta-item"><span class="meta-key">Height</span><span class="meta-value">{metadata['height']} px</span></div>
                                <div class="meta-item"><span class="meta-key">Size</span><span class="meta-value">{metadata['file_size_mb']:.4f} MB</span></div>
                                <div class="meta-item"><span class="meta-key">Format</span><span class="meta-value">{metadata['format']}</span></div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    if st.button("Replace Image", type="primary", use_container_width=True):
                        st.session_state.current_image_path = None
                        st.session_state.current_image_hash = None
                        st.session_state.processed_image = None
                        st.session_state.processed_style = None
                        st.session_state.processing_time = None
                        st.session_state.current_style = None
                        st.session_state.output_quality = None
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)  # end studio-panel

        # RIGHT: style selection cards + controls
        with right_col:
            st.markdown(
                """
                <div class="studio-panel">
                    <div class="studio-panel-header">
                        <div>
                            <div class="studio-panel-title">Styles</div>
                            <div class="studio-panel-kicker">Tap a card to select</div>
                        </div>
                    </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown('<div class="style-grid">', unsafe_allow_html=True)

            # Render each style card as a soft-shadow button, updating st.session_state.selected_style
            for style_key, cfg in STYLE_CONFIG.items():
                is_selected = style_key == selected_style_key
                card_classes = "style-card is-selected" if is_selected else "style-card"
                label = cfg["label"]
                description = cfg["description"]
                tagline = cfg["tagline"]
                badge_html = (
                    '<span class="style-badge">Popular</span>' if cfg.get("popular") else ""
                )
                thumb = cfg["preview_asset"]

                card_html = f"""
                <div class="{card_classes}">
                    <div class="style-name">{label}</div>
                    <div class="style-description">{description}</div>
                    <div class="style-meta">
                        <span class="style-tagline">{tagline}</span>
                        {badge_html}
                    </div>
                    <div class="style-thumb">{thumb}</div>
                </div>
                """

                if st.button(
                    "",
                    key=f"style_card_btn_{style_key}",
                    use_container_width=True,
                ):
                    st.session_state.selected_style = style_key
                    st.session_state.current_style = STYLE_CONFIG[style_key]["label"]
                    st.rerun()

                st.markdown(card_html, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)  # end style-grid

            # Controls / sliders for selected style
            cartoon_k = None
            cartoon_thickness = None
            with st.container():
                st.markdown('<div class="studio-controls">', unsafe_allow_html=True)
                if selected_style_key == "classic_cartoon":
                    cartoon_k = st.slider("Number of Colors", 4, 16, 8)
                    cartoon_thickness = st.slider("Edge Thickness", 1, 5, 2)
                st.markdown("</div>", unsafe_allow_html=True)

            process_clicked = st.button("Run Selected Style", type="primary", use_container_width=True)

            # Trigger OpenCV / AI processing without modifying underlying functions
            if process_clicked:
                current_image_path = st.session_state.get("current_image_path")
                if not current_image_path:
                    st.warning("Upload an image on the left before processing.")
                else:
                    with st.spinner("Processing image..."):
                        start_time = time.perf_counter()
                        try:
                            if selected_style_key == "classic_cartoon":
                                processed = classic_cartoon(
                                    current_image_path,
                                    k=cartoon_k or 8,
                                    edge_thickness=cartoon_thickness or 2,
                                )
                                style_label = STYLE_CONFIG["classic_cartoon"]["label"]
                            elif selected_style_key == "sketch":
                                processed = sketch_effect(current_image_path)
                                style_label = STYLE_CONFIG["sketch"]["label"]
                            else:
                                processed = pencil_color_effect(current_image_path)
                                style_label = STYLE_CONFIG["pencil_color"]["label"]
                        except Exception as exc:
                            st.error(f"Failed to process image: {exc}")
                            st.session_state.processed_image = None
                            st.session_state.processed_style = None
                            st.session_state.processing_time = None
                            st.session_state.output_quality = None
                        else:
                            elapsed = time.perf_counter() - start_time
                            st.session_state.processed_image = processed
                            st.session_state.processed_style = style_label
                            st.session_state.processing_time = elapsed
                            st.session_state.current_style = style_label

                            # Compute simple output-quality metric (resolution + encoded size)
                            try:
                                download_bytes = encode_image_to_png(processed)
                                size_kb = len(download_bytes) / 1024.0
                                height, width = processed.shape[:2]
                                st.session_state.output_quality = (
                                    f"{width}×{height} px · {size_kb:.1f} KB"
                                )
                            except Exception:
                                st.session_state.output_quality = None

            st.markdown("</div>", unsafe_allow_html=True)  # end studio-panel

        st.markdown("</div>", unsafe_allow_html=True)  # end studio-shell

        # ── Bottom metrics row: Processing Time, Output Quality, Style Options ──
        processing_time_val = st.session_state.get("processing_time")
        output_quality_val = st.session_state.get("output_quality")
        selected_style_label = st.session_state.get("current_style") or STYLE_CONFIG[selected_style_key]["label"]
        styles_count = len(STYLE_CONFIG)

        processing_text = f"{processing_time_val:.2f} s" if processing_time_val is not None else "—"
        output_text = output_quality_val or "Resolution & size will appear here"
        styles_text = f"{styles_count} styles · {selected_style_label}"

        st.markdown(
            f"""
            <div class="metric-row-studio">
                <div class="metric-card-studio">
                    <div class="metric-label">Processing Time</div>
                    <div class="metric-value">{processing_text}</div>
                    <div class="metric-caption">Measured from AI start to finish.</div>
                </div>
                <div class="metric-card-studio">
                    <div class="metric-label">Output Quality</div>
                    <div class="metric-value">{output_text}</div>
                    <div class="metric-caption">Based on processed image resolution & size.</div>
                </div>
                <div class="metric-card-studio">
                    <div class="metric-label">Style Options</div>
                    <div class="metric-value">{styles_text}</div>
                    <div class="metric-caption">Choose any card on the right.</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────
# MY IMAGES PANEL
# ─────────────────────────────────────────────

elif section == "my_images":
    st.markdown('<h1 class="dash-title">My Images</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dash-sub">All your AI-generated artwork.</p>', unsafe_allow_html=True)

    if recent_creations:
        cards_html = '<div class="rc-grid">'
        download_data = []  # list of (img_bytes, filename, key)
        for idx, item in enumerate(recent_creations):
            img_path = item["processed_image_path"]
            style    = item["style_applied"]
            date_str = _fmt_date(item["processing_date"])
            b64      = _img_to_b64(img_path)

            if b64:
                img_html = f'<img class="rc-card-img" src="{b64}" alt="{style}">'
            else:
                img_html = '<div class="rc-card-img-fallback">🖼</div>'

            cards_html += f"""
            <div class="rc-card">
                {img_html}
                <div class="rc-card-body">
                    <p class="rc-card-style">{style}</p>
                    <p class="rc-card-date">{date_str}</p>
                </div>
            </div>
            """
            try:
                img_bytes = Path(img_path).read_bytes()
                fname = f"artify_{style.lower().replace(' ','_')}.png"
                download_data.append((img_bytes, fname, f"dl_idx_myimg_{idx}"))
            except Exception:
                continue

        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

        COLS = 4
        for row_start in range(0, len(recent_creations), COLS):
            chunk = download_data[row_start: row_start + COLS]
            cols  = st.columns(len(chunk))
            for col, (data, fname, key) in zip(cols, chunk):
                with col:
                    if data and fname and key:
                        st.download_button(
                            "⬇  Download", data=data,
                            file_name=fname, mime="image/png",
                            key=key, use_container_width=True,
                        )
    else:
        st.markdown(
            """
            <div class="rc-empty">
                <span class="rc-empty-icon">✨</span>
                <p class="rc-empty-title">No creations yet</p>
                <p class="rc-empty-text">Start by creating your first cartoon in the Image Editor.</p>
            </div>
            """, unsafe_allow_html=True
        )

# ─────────────────────────────────────────────
# PAYMENTS PANEL
# ─────────────────────────────────────────────

elif section == "payments":
    st.markdown('<h1 class="dash-title">Payment History</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dash-sub">All your completed and pending transactions.</p>', unsafe_allow_html=True)

    with st.container():
        if transactions:
            st.dataframe(transactions, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions yet. Completed payments will appear here.")

    if st.button("← Back to Dashboard", use_container_width=False):
        st.session_state["dash_section"] = "dashboard"
        st.rerun()

# ─────────────────────────────────────────────
# PROFILE PANEL
# ─────────────────────────────────────────────

elif section == "profile":
    st.markdown('<h1 class="dash-title">Profile Settings</h1>', unsafe_allow_html=True)
    st.markdown('<p class="dash-sub">Your account details and security information.</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            st.markdown("#### Account details")
            st.write(f"**Username:** {username}")
            st.write(f"**Email:** {email}")
            st.write(f"**Member since:** {profile['created_at']}")
            st.write(f"**Last login:** {profile['last_login']}")
    with c2:
        with st.container(border=True):
            st.markdown("#### Security")
            st.write(f"**Active:** {'Yes' if profile['is_active'] else 'No'}")
            st.write(f"**Locked:** {'Yes' if profile['account_locked'] else 'No'}")
            st.write(f"**Failed login attempts:** {profile['failed_attempts']}")

    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
    if st.button("← Back to Dashboard", use_container_width=False):
        st.session_state["dash_section"] = "dashboard"
        st.rerun()
