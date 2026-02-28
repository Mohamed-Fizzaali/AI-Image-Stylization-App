from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, UnidentifiedImageError


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "BMP"}
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"


def _read_uploaded_bytes(uploaded_file) -> bytes:
    """Read uploaded bytes from Streamlit uploader or bytes-like object."""
    if uploaded_file is None:
        return b""

    if isinstance(uploaded_file, (bytes, bytearray)):
        return bytes(uploaded_file)

    if hasattr(uploaded_file, "getbuffer"):
        data = bytes(uploaded_file.getbuffer())
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return data

    if hasattr(uploaded_file, "read"):
        data = uploaded_file.read()
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        return data

    raise TypeError("Unsupported uploaded file type.")


def _get_extension(uploaded_file) -> str:
    file_name = getattr(uploaded_file, "name", "")
    return Path(file_name).suffix.lower()


def validate_image(uploaded_file, max_size_mb: int = 10) -> tuple[bool, str]:
    """Validate extension, size, and image integrity."""
    if uploaded_file is None:
        return False, "No file provided."

    extension = _get_extension(uploaded_file)
    if extension not in ALLOWED_EXTENSIONS:
        return False, "Unsupported file format. Allowed: JPG, JPEG, PNG, BMP."

    file_bytes = _read_uploaded_bytes(uploaded_file)
    if not file_bytes:
        return False, "Uploaded file is empty."

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, f"File too large. Maximum size is {max_size_mb} MB."

    try:
        with Image.open(BytesIO(file_bytes)) as img:
            image_format = (img.format or "").upper()
            img.verify()
    except (UnidentifiedImageError, OSError):
        return False, "Corrupted or invalid image file."

    if image_format not in ALLOWED_IMAGE_FORMATS:
        return False, "Unsupported image content. Allowed: JPG, JPEG, PNG, BMP."

    return True, "Image is valid."


def save_uploaded_image(uploaded_file) -> str:
    """
    Save a validated uploaded image to uploads/ with a UUID name.
    Raises ValueError for invalid/corrupted uploads.
    """
    is_valid, message = validate_image(uploaded_file, max_size_mb=10)
    if not is_valid:
        raise ValueError(message)

    file_bytes = _read_uploaded_bytes(uploaded_file)
    if not file_bytes:
        raise ValueError("No file data to save.")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    extension = _get_extension(uploaded_file)
    if extension not in ALLOWED_EXTENSIONS:
        extension = ".png"

    unique_filename = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / unique_filename
    try:
        file_path.write_bytes(file_bytes)
    except OSError as exc:
        raise OSError(f"Failed to save uploaded image: {exc}") from exc

    return str(file_path.resolve())


def get_image_metadata(file_path: str) -> dict:
    """Return width, height, size (MB), and format for an image path."""
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")

    try:
        with Image.open(path) as img:
            img.load()
            width, height = img.size
            image_format = (img.format or path.suffix.lstrip(".")).upper()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Cannot read metadata from a corrupted image file.") from exc

    file_size_mb = path.stat().st_size / (1024 * 1024)

    return {
        "width": width,
        "height": height,
        "file_size_mb": round(file_size_mb, 4),
        "format": image_format,
    }
