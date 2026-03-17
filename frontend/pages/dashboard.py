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
           AI IMAGE STUDIO (Editor) — FIGMA UI
           Scoped + single .custom-card
           ───────────────────────────────────── */

        .custom-card {
            background: #ffffff;
            border-radius: 15px;
            border: 1px solid rgba(226, 232, 240, 0.95);
            box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
            padding: 16px 16px 14px 16px;
        }

        .studio-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .studio-title {
            font-size: 1.35rem;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.03em;
            margin: 0;
        }

        .studio-subtitle {
            margin: 0.15rem 0 0 0;
            font-size: 0.9rem;
            color: #64748b;
        }

        .studio-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: linear-gradient(135deg, rgba(79, 125, 242, 0.16), rgba(24, 184, 223, 0.14));
            border: 1px solid rgba(79, 125, 242, 0.22);
            color: #1d4ed8;
            font-size: 0.78rem;
            font-weight: 700;
            white-space: nowrap;
        }

        .card-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
        }

        .card-head-left {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .card-title {
            font-size: 0.9rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }

        .card-desc {
            font-size: 0.78rem;
            color: #64748b;
            margin: 0;
        }

        /* Uploader look */
        .st-key-studio_uploader_card [data-testid="stFileUploader"] section {
            border-radius: 14px;
            border: 1.5px dashed rgba(148, 163, 184, 0.6);
            background: #fbfdff;
        }

        /* Center images inside cards (fix use_container_width deprecation warning) */
        .studio-img-center [data-testid="stImage"] {
            display: flex;
            justify-content: center;
        }
        .studio-img-center img {
            max-width: 100%;
            height: auto;
            border-radius: 12px;
        }

        /* Style selector scroll area */
        .style-scroll {
            height: 520px;
            overflow-y: auto;
            padding-right: 6px;
        }
        .style-scroll::-webkit-scrollbar { width: 10px; }
        .style-scroll::-webkit-scrollbar-thumb {
            background: rgba(148, 163, 184, 0.55);
            border-radius: 999px;
            border: 3px solid rgba(255,255,255,0.9);
        }

        .style-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .style-card-wrap {
            position: relative;
        }

        /* Each style card is a Streamlit button (click target) */
        .st-key-style_grid .style-card-wrap button {
            width: 100% !important;
            border-radius: 14px !important;
            border: 1px solid rgba(226, 232, 240, 0.95) !important;
            background: #ffffff !important;
            box-shadow: 0 16px 40px rgba(15, 23, 42, 0.08) !important;
            padding: 0 !important;
            overflow: hidden !important;
            transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease !important;
            min-height: 240px !important;
        }
        .st-key-style_grid .style-card-wrap button:hover {
            transform: translateY(-2px) !important;
            border-color: rgba(79, 125, 242, 0.5) !important;
            box-shadow: 0 22px 50px rgba(15, 23, 42, 0.14) !important;
        }

        .style-card-overlay {
            pointer-events: none;
            position: absolute;
            inset: 0;
            display: flex;
            flex-direction: column;
        }

        .style-card-inner {
            padding: 12px 12px 11px 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            text-align: left;
        }

        .style-thumb {
            width: 100%;
            aspect-ratio: 16 / 10;
            border-radius: 12px;
            border: 1px solid rgba(226, 232, 240, 0.9);
            background: linear-gradient(135deg, #eef2ff, #f8fafc);
            overflow: hidden;
            position: relative;
        }
        .style-thumb img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }

        .popular-badge {
            position: absolute;
            left: 10px;
            top: 10px;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #ffffff;
            background: linear-gradient(135deg, #f97316, #ec4899);
            padding: 0.18rem 0.5rem;
            border-radius: 999px;
            box-shadow: 0 10px 22px rgba(236, 72, 153, 0.35);
        }

        .style-name {
            font-size: 0.92rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0;
        }
        .style-text {
            font-size: 0.78rem;
            color: #64748b;
            margin: 0;
            line-height: 1.45;
            min-height: 2.2em;
        }

        /* Selected state */
        .is-selected-style button {
            border-color: rgba(79, 125, 242, 0.9) !important;
            box-shadow: 0 22px 60px rgba(79, 125, 242, 0.22) !important;
        }

        /* Metric cards row under uploader */
        .metric-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 12px;
        }
        .metric-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #94a3b8;
            margin: 0;
        }
        .metric-value {
            font-size: 1.05rem;
            font-weight: 900;
            color: #0f172a;
            letter-spacing: -0.03em;
            margin: 0.25rem 0 0 0;
        }

        /* Transform button */
        .st-key-transform_ai_btn button {
            border: none !important;
            border-radius: 14px !important;
            background: linear-gradient(135deg, #4f7df2 0%, #18b8df 100%) !important;
            color: #ffffff !important;
            font-weight: 900 !important;
            min-height: 54px !important;
            box-shadow: 0 18px 44px rgba(79, 125, 242, 0.22) !important;
            transition: transform 160ms ease, box-shadow 160ms ease, filter 160ms ease !important;
        }
        .st-key-transform_ai_btn button:hover:enabled {
            transform: translateY(-1px) !important;
            box-shadow: 0 22px 52px rgba(79, 125, 242, 0.3) !important;
            filter: saturate(1.06) !important;
        }
        .st-key-transform_ai_btn button:disabled {
            background: #e5e7eb !important;
            color: #94a3b8 !important;
            box-shadow: none !important;
        }

        @keyframes fadeInUp {
            from { opacity:0; transform:translateY(8px); }
            to   { opacity:1; transform:translateY(0);   }
        }

        /* Responsive */
        @media(max-width: 900px) {
            .stat-row  { grid-template-columns: 1fr; }
            .rc-grid   { grid-template-columns: repeat(2, 1fr); }
            .style-grid { grid-template-columns: 1fr; }
            .metric-row { grid-template-columns: 1fr; }
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

# ─────────────────────────────────────────────
# AI IMAGE STUDIO — render_editor()
# (visual layer only; backend logic untouched)
# ─────────────────────────────────────────────

def render_editor() -> None:
    st.session_state.setdefault("last_time", None)

    st.markdown(
        """
        <style>
          /* Single block: studio cards + scroll grid */
          .custom-card{
            background:#fff;border-radius:15px;border:1px solid rgba(226,232,240,.95);
            box-shadow:0 18px 44px rgba(15,23,42,.08);padding:16px 16px 14px;
          }
          .studio-row{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;align-items:start;}
          .card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}
          .card-title{font-size:.9rem;font-weight:800;color:#0f172a;margin:0;}
          .card-desc{font-size:.78rem;color:#64748b;margin:0;}
          .pill{display:inline-flex;align-items:center;gap:.45rem;padding:.35rem .7rem;border-radius:999px;
            background:linear-gradient(135deg,rgba(79,125,242,.16),rgba(24,184,223,.14));
            border:1px solid rgba(79,125,242,.22);color:#1d4ed8;font-size:.78rem;font-weight:800;white-space:nowrap;}
          .studio-img-center [data-testid="stImage"]{display:flex;justify-content:center;}
          .studio-img-center img{max-width:100%;height:auto;border-radius:12px;}
          .style-scroll{height:520px;overflow-y:auto;padding-right:6px;}
          .style-scroll::-webkit-scrollbar{width:10px;}
          .style-scroll::-webkit-scrollbar-thumb{background:rgba(148,163,184,.55);border-radius:999px;border:3px solid rgba(255,255,255,.9);}
          .style-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}
          .style-card{border-radius:14px;padding:12px;border:1px solid rgba(226,232,240,.95);
            box-shadow:0 16px 40px rgba(15,23,42,.06);transition:transform 160ms ease,box-shadow 160ms ease,border-color 160ms ease;}
          .style-card:hover{transform:translateY(-2px);border-color:rgba(79,125,242,.45);box-shadow:0 22px 52px rgba(15,23,42,.12);}
          .style-card.selected{border:2px solid #4f7df2;}
          .style-name{font-size:.92rem;font-weight:900;color:#0f172a;margin:.35rem 0 .15rem 0;}
          .style-text{font-size:.78rem;color:#64748b;margin:0;line-height:1.45;min-height:2.2em;}
          .popular{display:inline-flex;align-items:center;gap:.35rem;font-size:.7rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase;
            color:#fff;background:linear-gradient(135deg,#f97316,#ec4899);padding:.18rem .5rem;border-radius:999px;
            box-shadow:0 10px 22px rgba(236,72,153,.25);}
          .metric-row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px;}
          .metric-label{font-size:.72rem;text-transform:uppercase;letter-spacing:.12em;color:#94a3b8;margin:0;}
          .metric-value{font-size:1.05rem;font-weight:900;color:#0f172a;letter-spacing:-.03em;margin:.25rem 0 0 0;}
          .st-key-transform_ai_btn button{
            border:none!important;border-radius:14px!important;background:linear-gradient(135deg,#4f7df2 0%,#18b8df 100%)!important;
            color:#fff!important;font-weight:900!important;min-height:54px!important;box-shadow:0 18px 44px rgba(79,125,242,.22)!important;
            transition:transform 160ms ease,box-shadow 160ms ease,filter 160ms ease!important;
          }
          .st-key-transform_ai_btn button:hover:enabled{transform:translateY(-1px)!important;box-shadow:0 22px 52px rgba(79,125,242,.3)!important;filter:saturate(1.06)!important;}
          .st-key-transform_ai_btn button:disabled{background:#e5e7eb!important;color:#94a3b8!important;box-shadow:none!important;}

          /* Selected border based on key prefix (Streamlit adds .st-key-<key>) */
          [class*="st-key-style_card__selected__"] .custom-card{border:2px solid #4f7df2;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    STYLE_CONFIG = {
        "classic_cartoon": {
            "label": "Classic Cartoon",
            "description": "Bold outlines with vibrant colors.",
            "icon_url": "put image url",
            "popular": True,
        },
        "sketch": {
            "label": "Sketch Art",
            "description": "Hand-drawn pencil technique.",
            "icon_url": "put image url",
            "popular": False,
        },
        "pencil_color": {
            "label": "Pencil Color",
            "description": "Soft color pencil texture blend.",
            "icon_url": "put image url",
            "popular": False,
        },
    }

    selected_style_key = cast(str, st.session_state.get("selected_style") or next(iter(STYLE_CONFIG.keys())))
    st.session_state.selected_style = selected_style_key
    style_items = list(STYLE_CONFIG.items())

    current_image_path = st.session_state.get("current_image_path")
    processed_image = st.session_state.get("processed_image")

    st.markdown(
        """
        <div class="studio-header">
          <div>
            <p class="studio-title">AI Image Studio</p>
            <p class="studio-subtitle">Transform photos into art instantly</p>
          </div>
          <div class="pill">⚡ Fast Processing</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        # Left workspace: 2 states (no upload -> uploader card; uploaded -> preview/result)
        st.markdown(
            """
            <div class="custom-card">
              <div class="card-head">
                <div>
                  <p class="card-title">Upload Image</p>
                  <p class="card-desc">Drag & drop your image (or browse)</p>
                </div>
              </div>
            """,
            unsafe_allow_html=True,
        )

        uploaded_file = None
        if not current_image_path:
            uploaded_file = st.file_uploader(
                "Upload image",
                type=["jpg", "jpeg", "png", "bmp"],
                help="Supported formats: JPG, JPEG, PNG, BMP. Max size: 10 MB.",
                key="studio_uploader",
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
                if (not current_image_path) or (file_hash != current_hash):
                    try:
                        saved_path = save_uploaded_image(uploaded_file)
                    except Exception as exc:
                        st.error(f"Failed to save image: {exc}")
                    else:
                        st.session_state.current_image_path = saved_path
                        st.session_state.current_image_hash = file_hash
                        st.session_state.processed_image = None
                        st.session_state.processed_style = None
                        st.session_state.last_time = None
                        current_image_path = saved_path
                        processed_image = None
                        st.rerun()

        # State 2: uploaded -> show workspace preview (result or side-by-side)
        if current_image_path:
            # Side-by-side when result exists, otherwise single original preview
            if processed_image is not None:
                try:
                    if processed_image.ndim == 2:
                        result_display = processed_image
                    else:
                        result_display = bgr_to_rgb(processed_image)
                except Exception:
                    result_display = None

                a, b = st.columns(2, gap="small")
                with a:
                    st.markdown('<div class="studio-img-center">', unsafe_allow_html=True)
                    st.image(current_image_path, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with b:
                    st.markdown('<div class="studio-img-center">', unsafe_allow_html=True)
                    if result_display is not None:
                        st.image(result_display, use_container_width=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="studio-img-center">', unsafe_allow_html=True)
                st.image(current_image_path, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)  # end custom-card

        # Bottom metrics (functional backend)
        last_time = st.session_state.get("last_time")
        processing_text = f"{float(last_time):.2f}s" if last_time is not None else "~—"

        quality_text = "—"
        if processed_image is not None:
            try:
                h, w = processed_image.shape[:2]
                png_bytes = encode_image_to_png(processed_image)
                kb = len(png_bytes) / 1024.0
                tier = "HD" if (w >= 1280 or h >= 720) else "SD"
                quality_text = f"{tier} • {w}x{h}px • {kb:.0f}KB"
            except Exception:
                quality_text = "—"

        styles_count = len(STYLE_CONFIG)  # style_dict keys count

        st.markdown(
            f"""
            <div class="metric-row">
              <div class="custom-card" style="padding:12px 14px;">
                <p class="metric-label">Processing Time</p>
                <p class="metric-value">{processing_text}</p>
              </div>
              <div class="custom-card" style="padding:12px 14px;">
                <p class="metric-label">Output Quality</p>
                <p class="metric-value">{quality_text}</p>
              </div>
              <div class="custom-card" style="padding:12px 14px;">
                <p class="metric-label">Style Options</p>
                <p class="metric-value">{styles_count}</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        # ── Build the full grid as a single HTML block ──────────────────────
        # This is the only reliable way to achieve display:grid in Streamlit;
        # injecting st.containers inside a CSS grid div breaks layout because
        # Streamlit wraps each widget in its own block-level div.

        cards_html_parts = []
        for idx, (style_key, cfg) in enumerate(style_items):
            is_selected = (style_key == selected_style_key)
            selected_class = "style-card-selected" if is_selected else ""
            popular_badge = (
                '<span class="style-popular-badge">POPULAR</span>'
                if cfg.get("popular") else ""
            )
            cards_html_parts.append(f"""
            <div class="style-card-wrap {selected_class}">
              {popular_badge}
              <img src="https://placehold.co/150x150?text=Style"
                   alt="{cfg['label']}" class="style-card-img" />
              <p class="style-card-name">{cfg['label']}</p>
              <p class="style-card-desc">{cfg['description']}</p>
            </div>
            """)

        cards_html = "\n".join(cards_html_parts)

        st.markdown(
            f"""
            <style>
              /* ── Right panel wrapper ── */
              .right-panel-card {{
                background: #ffffff;
                border-radius: 15px;
                border: 1px solid rgba(226,232,240,0.95);
                box-shadow: 0 18px 44px rgba(15,23,42,0.08);
                padding: 16px 16px 14px 16px;
                box-sizing: border-box;
              }}
              .right-panel-title {{
                font-size: 0.9rem; font-weight: 800; color: #0f172a; margin: 0;
              }}
              .right-panel-desc {{
                font-size: 0.78rem; color: #64748b; margin: 0 0 12px 0;
              }}

              /* ── Scrollable fixed-height grid container ── */
              .style-grid-scroll {{
                height: 550px;
                overflow-y: auto;
                padding-right: 6px;
                box-sizing: border-box;
              }}
              .style-grid-scroll::-webkit-scrollbar {{ width: 8px; }}
              .style-grid-scroll::-webkit-scrollbar-thumb {{
                background: rgba(148,163,184,0.5);
                border-radius: 999px;
                border: 2px solid rgba(255,255,255,0.9);
              }}

              /* ── 2-column grid ── */
              .style-grid-inner {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 16px;
                box-sizing: border-box;
              }}

              /* ── Individual card ── */
              .style-card-wrap {{
                position: relative;
                background: #ffffff;
                border-radius: 12px;
                border: 1.5px solid rgba(226,232,240,0.95);
                box-shadow: 0 4px 16px rgba(15,23,42,0.07);
                padding: 14px;
                box-sizing: border-box;
                transition: box-shadow 160ms ease, transform 160ms ease;
                cursor: pointer;
              }}
              .style-card-wrap:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 28px rgba(15,23,42,0.13);
                border-color: rgba(79,125,242,0.4);
              }}
              .style-card-selected {{
                border: 2px solid #4f7df2 !important;
                box-shadow: 0 6px 24px rgba(79,125,242,0.22) !important;
              }}

              /* ── Thumbnail image ── */
              .style-card-img {{
                width: 100%;
                height: 90px;
                object-fit: cover;
                border-radius: 8px;
                display: block;
                margin-bottom: 10px;
                border: 1px solid rgba(226,232,240,0.8);
              }}

              /* ── Text ── */
              .style-card-name {{
                font-size: 0.88rem; font-weight: 800;
                color: #0f172a; margin: 0 0 4px 0;
              }}
              .style-card-desc {{
                font-size: 0.75rem; color: #64748b;
                margin: 0; line-height: 1.45;
              }}

              /* ── POPULAR badge ── */
              .style-popular-badge {{
                position: absolute;
                top: 10px; right: 10px;
                font-size: 0.62rem; font-weight: 800;
                letter-spacing: 0.09em; text-transform: uppercase;
                color: #ffffff;
                background: linear-gradient(135deg, #f97316, #ec4899);
                padding: 0.18rem 0.48rem;
                border-radius: 999px;
                box-shadow: 0 4px 12px rgba(236,72,153,0.35);
                pointer-events: none;
              }}
            </style>

            <div class="right-panel-card">
              <p class="right-panel-title">Choose Art Style</p>
              <p class="right-panel-desc">Select how you want to transform your image</p>
              <div class="style-grid-scroll">
                <div class="style-grid-inner">
                  {cards_html}
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Streamlit buttons for click handling (visually hidden) ─────────
        # Rendered outside the HTML block; use compact columns to approximate
        # the 2-column grid layout so vertical stacking stays minimal.
        st.markdown(
            "<p style='font-size:0.8rem;font-weight:700;color:#374151;margin:12px 0 6px 0;'>"
            "Select a style:</p>",
            unsafe_allow_html=True,
        )
        btn_cols = st.columns(len(style_items))
        for col, (style_key, cfg) in zip(btn_cols, style_items):
            is_selected = (style_key == selected_style_key)
            with col:
                if st.button(
                    ("✓ " if is_selected else "") + cfg["label"],
                    key=f"select_style_{style_key}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.selected_style = style_key
                    st.rerun()

    ready = bool(st.session_state.get("current_image_path")) and bool(st.session_state.get("selected_style"))
    transform_clicked = st.button(
        "🪄  Transform with AI  →",
        type="primary",
        use_container_width=True,
        key="transform_ai_btn",
        disabled=not ready,
    )

    if transform_clicked:
        image_path = st.session_state.get("current_image_path")
        style_key = cast(str, st.session_state.get("selected_style"))

        with st.spinner("Transforming..."):
            t_start = time.time()
            try:
                if style_key == "classic_cartoon":
                    processed = classic_cartoon(image_path, k=8, edge_thickness=2)
                    style_label = STYLE_CONFIG[style_key]["label"]
                elif style_key == "sketch":
                    processed = sketch_effect(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
                else:
                    processed = pencil_color_effect(image_path)
                    style_label = STYLE_CONFIG[style_key]["label"]
            except Exception as exc:
                st.error(f"Failed to process image: {exc}")
                st.session_state.processed_image = None
                st.session_state.processed_style = None
                st.session_state.processing_time = None
                st.session_state.output_quality = None
            else:
                t_end = time.time()
                st.session_state.last_time = round(t_end - t_start, 2)  # t_end - t_start
                st.session_state.processed_image = processed
                st.session_state.processed_style = style_label
                # output quality shown dynamically in metrics; keep state clean

                st.rerun()

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
    render_editor()

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
