import hashlib
import sys
import time
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.image_upload import get_image_metadata, save_uploaded_image, validate_image
from backend.image_processing import (
    bgr_to_rgb,
    classic_cartoon,
    encode_image_to_png,
    pencil_color_effect,
    read_image,
    sketch_effect,
)

STYLE_OPTIONS = ["Classic Cartoon", "Sketch", "Pencil Color"]


class _SessionUploadFile:
    """Minimal uploaded-file shim for dashboard -> editor handoff."""

    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self._data = data

    def getbuffer(self):
        return memoryview(self._data)

    def getvalue(self) -> bytes:
        return self._data

    def read(self) -> bytes:
        return self._data

    def seek(self, _offset: int) -> None:
        return


def _load_dashboard_prefill() -> None:
    """
    Import an uploaded image passed from dashboard, if present.

    The dashboard stores a small payload in session state:
    ``dashboard_image_prefill = {name, bytes, style}``.
    """
    prefill = st.session_state.pop("dashboard_image_prefill", None)
    if not prefill:
        return

    style_hint = prefill.get("style")
    if isinstance(style_hint, str) and style_hint in STYLE_OPTIONS:
        st.session_state.style_select = style_hint

    raw_bytes = prefill.get("bytes")
    file_name = prefill.get("name") or "dashboard_upload.png"
    if not isinstance(raw_bytes, (bytes, bytearray)) or not raw_bytes:
        st.warning("Could not import the dashboard image. Please upload again.")
        return

    incoming_hash = hashlib.sha256(raw_bytes).hexdigest()
    current_hash = st.session_state.get("current_image_hash")
    current_path = st.session_state.get("current_image_path")
    if current_path and current_hash == incoming_hash and Path(current_path).exists():
        return

    dashboard_file = _SessionUploadFile(str(file_name), bytes(raw_bytes))
    try:
        is_valid, validation_message = validate_image(dashboard_file, max_size_mb=10)
    except Exception as exc:
        st.warning(f"Could not import dashboard image: {exc}")
        return

    if not is_valid:
        st.warning(validation_message or "Could not import dashboard image.")
        return

    try:
        saved_path = save_uploaded_image(dashboard_file)
    except Exception as exc:
        st.warning(f"Could not save dashboard image: {exc}")
        return

    st.session_state.current_image_path = saved_path
    st.session_state.current_image_hash = incoming_hash
    st.session_state.processed_image = None
    st.session_state.processed_style = None
    st.session_state.processing_time = None
    st.success("Image imported from dashboard.")


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap');

        :root {
            --bg-top: #ffffff;
            --bg-mid: #ffffff;
            --bg-bottom: #f7f7f8;
            --ink-900: #111111;
            --ink-700: #222222;
            --ink-500: #555555;
            --brand-800: #111111;
            --brand-500: #111111;
            --card-bg: #ffffff;
            --card-stroke: #e5e7eb;
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
                #ffffff;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"] {
            background: #ffffff !important;
        }

        [data-testid="stAppViewContainer"] > .main {
            background: #ffffff !important;
        }

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {
            max-width: 100%;
            overflow-x: hidden !important;
        }

        .stApp {
            background:
                #ffffff;
            background-attachment: scroll;
        }

        [data-testid="stSidebar"] {
            border-right: 1px solid #e5e7eb;
            background: #ffffff;
            color: var(--ink-700);
            backdrop-filter: none;
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

        button[data-testid="collapsedControl"] {
            background: #111111 !important;
            border: 1px solid #111111 !important;
            border-radius: 0.6rem !important;
            min-width: 2.3rem !important;
            min-height: 2.3rem !important;
        }

        button[data-testid="collapsedControl"] svg,
        [data-testid="stSidebarNav"] svg {
            fill: #ffffff !important;
            color: #ffffff !important;
        }

        [data-testid="stSidebarNav"] a {
            color: var(--ink-700) !important;
        }

        .block-container {
            padding-top: 2.1rem;
            padding-bottom: 2.2rem;
            max-width: 1180px;
        }

        .page-kicker {
            display: inline-block;
            background: #f7f7f8;
            color: #555555;
            border: 1px solid #e5e7eb;
            border-radius: 999px;
            padding: 0.34rem 0.84rem;
            font-size: 0.72rem;
            letter-spacing: 0.095em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.65rem;
        }

        .page-title {
            margin: 0.1rem 0 0.5rem 0;
            font-size: clamp(1.95rem, 3.1vw, 2.85rem);
            line-height: 1.05;
            letter-spacing: -0.025em;
            color: var(--ink-900);
            font-weight: 800;
            white-space: normal !important;
            word-break: break-word;
        }

        .page-sub {
            color: var(--ink-700);
            font-size: 1rem;
            line-height: 1.55;
            margin-bottom: 0.9rem;
        }

        .meta-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 1rem;
            padding: 1rem 1.05rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        .meta-title {
            color: var(--ink-900);
            font-size: 1.02rem;
            font-weight: 750;
            margin-bottom: 0.7rem;
        }

        .meta-item {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.52rem 0;
            border-bottom: 1px solid #e5e7eb;
            color: var(--ink-700);
            font-size: 0.92rem;
        }

        .meta-item:last-child {
            border-bottom: none;
        }

        .meta-key {
            color: var(--ink-500);
            font-weight: 600;
        }

        .meta-value {
            color: var(--ink-900);
            font-weight: 700;
            text-align: right;
        }

        [data-testid="stFileUploader"] section {
            border-radius: 0.95rem;
            border: 1px dashed #e5e7eb;
            background: #fafafa;
        }

        button[data-testid="baseButton-primary"] {
            background: #111111;
            border: 1px solid #111111;
            color: #ffffff;
            font-weight: 700;
            border-radius: 0.72rem;
            box-shadow: none;
        }

        [data-testid="stLogo"] img,
        [data-testid="stLogo"] svg {
            max-height: 4.1rem !important;
            width: auto !important;
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
            .page-title {
                font-size: clamp(1.35rem, 7.4vw, 1.72rem);
                line-height: 1.12;
                overflow-wrap: anywhere;
            }
            .page-sub {
                font-size: 0.88rem;
                overflow-wrap: anywhere;
            }
            .meta-card {
                padding: 0.78rem 0.82rem;
            }
            .meta-item {
                font-size: 0.84rem;
                gap: 0.45rem;
            }
            [data-testid="stLogo"] img,
            [data-testid="stLogo"] svg {
                max-height: 3rem !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


assets_dir = Path(__file__).resolve().parents[1] / "assets"
icon_png = assets_dir / "artify_logo.png"
logo_svg = assets_dir / "artify_logo.svg"
logo_asset = logo_svg if logo_svg.exists() else icon_png

st.set_page_config(
    page_title="Image Upload & Preview",
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

# Protect page: login required
if not st.session_state.get("logged_in", False):
    st.warning("Please login first.")
    st.switch_page("app.py")
    st.stop()

if "current_image_path" not in st.session_state:
    st.session_state.current_image_path = None
if "current_image_hash" not in st.session_state:
    st.session_state.current_image_hash = None
if "processed_image" not in st.session_state:
    st.session_state.processed_image = None
if "processed_style" not in st.session_state:
    st.session_state.processed_style = None
if "processing_time" not in st.session_state:
    st.session_state.processing_time = None

_load_dashboard_prefill()

with st.sidebar:
    st.markdown("### Image Tools")
    st.caption("Upload, review metadata, and replace current image.")
    st.markdown("---")
    if st.button("Back to dashboard", width="stretch"):
        st.switch_page("pages/dashboard.py")
        st.stop()
    if st.button("Back to home", width="stretch"):
        st.switch_page("app.py")
        st.stop()

st.markdown('<div class="page-kicker">IMAGE STUDIO</div>', unsafe_allow_html=True)
st.markdown('<h1 class="page-title">Image Upload & Preview</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="page-sub">Upload a supported file, validate it, and inspect image metadata before processing.</p>',
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
        # Prevent duplicate saves while the same upload remains selected in Streamlit.
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
                st.success("Image validated and saved successfully.")

current_image_path = st.session_state.get("current_image_path")

if current_image_path:
    image_path_obj = Path(current_image_path)
    if not image_path_obj.exists():
        st.warning("Saved image path no longer exists. Please upload again.")
        st.session_state.current_image_path = None
        st.session_state.current_image_hash = None
        st.session_state.processed_image = None
        st.session_state.processed_style = None
        st.session_state.processing_time = None
        st.stop()

    try:
        metadata = get_image_metadata(current_image_path)
    except Exception as exc:
        st.error(f"Could not read image metadata: {exc}")
        st.stop()

    image_col, meta_col = st.columns([1.55, 1], gap="large")

    with image_col:
        with st.container(border=True):
            st.subheader("Preview")
            st.image(current_image_path, width="stretch")
            st.caption(str(image_path_obj))

    with meta_col:
        st.markdown(
            f"""
            <div class="meta-card">
                <div class="meta-title">Image Metadata</div>
                <div class="meta-item"><span class="meta-key">Width</span><span class="meta-value">{metadata['width']} px</span></div>
                <div class="meta-item"><span class="meta-key">Height</span><span class="meta-value">{metadata['height']} px</span></div>
                <div class="meta-item"><span class="meta-key">Size</span><span class="meta-value">{metadata['file_size_mb']:.4f} MB</span></div>
                <div class="meta-item"><span class="meta-key">Format</span><span class="meta-value">{metadata['format']}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("")
        if st.button("Replace Image", type="primary", width="stretch"):
            st.session_state.current_image_path = None
            st.session_state.current_image_hash = None
            st.session_state.processed_image = None
            st.session_state.processed_style = None
            st.session_state.processing_time = None
            st.rerun()

    st.markdown("")
    st.markdown("### Stylization")

    selected_style = st.selectbox(
        "Choose a style",
        STYLE_OPTIONS,
        key="style_select",
    )

    cartoon_k = None
    cartoon_thickness = None
    if selected_style == "Classic Cartoon":
        cartoon_k = st.slider("Number of Colors", 4, 16, 8)
        cartoon_thickness = st.slider("Edge Thickness", 1, 5, 2)

    process_clicked = st.button("Process Image", type="primary", width="stretch")

    if process_clicked:
        with st.spinner("Processing image..."):
            start_time = time.perf_counter()
            try:
                if selected_style == "Classic Cartoon":
                    processed = classic_cartoon(
                        current_image_path,
                        k=cartoon_k or 8,
                        edge_thickness=cartoon_thickness or 2,
                    )
                elif selected_style == "Sketch":
                    processed = sketch_effect(current_image_path)
                else:
                    processed = pencil_color_effect(current_image_path)
            except Exception as exc:
                st.error(f"Failed to process image: {exc}")
                st.session_state.processed_image = None
                st.session_state.processed_style = None
                st.session_state.processing_time = None
            else:
                elapsed = time.perf_counter() - start_time
                st.session_state.processed_image = processed
                st.session_state.processed_style = selected_style
                st.session_state.processing_time = elapsed

    # Side-by-side comparison and download, if processing succeeded at least once.
    processed_image = st.session_state.get("processed_image")
    processed_style = st.session_state.get("processed_style")
    processing_time = st.session_state.get("processing_time")

    if processed_image is not None:
        try:
            original_bgr = read_image(current_image_path)
        except Exception as exc:
            st.error(f"Could not read original image for display: {exc}")
        else:
            if processed_image.ndim == 2:
                original_display = bgr_to_rgb(original_bgr)
                processed_display = processed_image
            else:
                original_display = bgr_to_rgb(original_bgr)
                processed_display = bgr_to_rgb(processed_image)

            display_width = 520

            col_orig, col_proc = st.columns(2, gap="large")
            with col_orig:
                st.subheader("Original")
                st.image(original_display, width=display_width)
            with col_proc:
                title = f"{processed_style} result" if processed_style else "Processed"
                st.subheader(title)
                st.image(processed_display, width=display_width)
                if processing_time is not None:
                    st.caption(f"Processing time: {processing_time:.2f} seconds")

            try:
                download_bytes = encode_image_to_png(processed_image)
            except Exception as exc:
                st.error(f"Could not prepare download: {exc}")
            else:
                st.download_button(
                    "Download processed image",
                    data=download_bytes,
                    file_name="artify_output.png",
                    mime="image/png",
                )

            st.markdown("")
            st.caption(
                "You can change the style above to apply another effect "
                "to the same image without uploading again."
            )
else:
    st.info("Upload an image to preview and view metadata.")
