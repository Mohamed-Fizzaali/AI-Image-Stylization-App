from __future__ import annotations

"""
Core image processing routines for the Artify AI application.

All OpenCV/NumPy based image transformations are defined here so that
the Streamlit UI layer can remain thin and focused on presentation.
"""

from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

_READ_CACHE_MAX_SIZE: int = 8
_KMEANS_MAX_SAMPLE_SIZE: int = 400

_read_cache: Dict[str, np.ndarray] = {}
_read_cache_keys: List[str] = []


def _ensure_odd_kernel_size(ksize: int, minimum: int = 3) -> int:
    """
    Ensure kernel size is a positive odd integer, at least ``minimum``.

    Parameters
    ----------
    ksize:
        Requested kernel size.
    minimum:
        Smallest allowed odd kernel size.

    Returns
    -------
    int
        Normalized odd kernel size.
    """
    if ksize < minimum:
        ksize = minimum
    if ksize % 2 == 0:
        ksize += 1
    return ksize


def _validate_bgr_image(image: np.ndarray, func_name: str) -> np.ndarray:
    """
    Validate that ``image`` is a 3-channel uint8 BGR image.

    Parameters
    ----------
    image:
        Input array to validate.
    func_name:
        Name of the calling function for clearer error messages.

    Returns
    -------
    np.ndarray
        The validated image (same object).

    Raises
    ------
    ValueError
        If the input is not a 3-channel uint8 image.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError(f"{func_name} expects a NumPy array, got {type(image)!r}.")
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"{func_name} expects a BGR image with shape (H, W, 3), got {image.shape}."
        )
    if image.dtype != np.uint8:
        raise ValueError(
            f"{func_name} expects image dtype uint8, got {image.dtype}."
        )
    return image


def _validate_gray_image(image: np.ndarray, func_name: str) -> np.ndarray:
    """
    Validate that ``image`` is a single-channel uint8 grayscale image.

    Accepts either 2D arrays of shape (H, W) or 3D arrays of
    shape (H, W, 1) and returns a 2D view.

    Parameters
    ----------
    image:
        Input array to validate.
    func_name:
        Name of the calling function for clearer error messages.

    Returns
    -------
    np.ndarray
        2D grayscale view of the image.

    Raises
    ------
    ValueError
        If the input is not a compatible grayscale image.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError(f"{func_name} expects a NumPy array, got {type(image)!r}.")
    if image.ndim == 2:
        gray = image
    elif image.ndim == 3 and image.shape[2] == 1:
        gray = image[:, :, 0]
    else:
        raise ValueError(
            f"{func_name} expects a grayscale image with shape (H, W) or (H, W, 1), "
            f"got {image.shape}."
        )
    if gray.dtype != np.uint8:
        raise ValueError(
            f"{func_name} expects image dtype uint8, got {gray.dtype}."
        )
    return gray


def _build_read_cache_key(path_obj: Path, max_width: int) -> str:
    """
    Build a stable cache key for ``read_image``.

    Includes resolved path, effective resize width, and file mtime to avoid
    stale cache hits when the file is replaced in place.
    """
    try:
        mtime_ns = path_obj.stat().st_mtime_ns
    except OSError:
        mtime_ns = -1
    return f"{path_obj}|{max_width}|{mtime_ns}"


def read_image(
    image_path: str | Path,
    max_width: int = 1200,
    use_cache: bool = True,
) -> np.ndarray:
    """
    Read an image from disk using OpenCV and optionally resize.

    This function also maintains a tiny in-memory LRU cache of the most
    recently read images (up to ``_READ_CACHE_MAX_SIZE`` entries) keyed
    by resolved path + ``max_width`` + file mtime. Cached images are copied
    on return so callers can safely modify them in-place without affecting
    the cache.

    Parameters
    ----------
    image_path:
        Path to the image file.
    max_width:
        Maximum allowed width in pixels. Images wider than this
        are resized while preserving aspect ratio.
    use_cache:
        Whether to use the small in-memory read cache to avoid
        repeated disk I/O within a single session.

    Returns
    -------
    np.ndarray
        Loaded BGR image (uint8).

    Raises
    ------
    ValueError
        If the image cannot be read or if parameters are invalid.
    """
    if max_width <= 0:
        raise ValueError("max_width must be a positive integer.")

    path_obj = Path(image_path).expanduser().resolve()
    cache_key = _build_read_cache_key(path_obj, max_width)

    if use_cache and cache_key in _read_cache:
        return _read_cache[cache_key].copy()

    image = cv2.imread(str(path_obj), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image from path: {path_obj}")

    height, width = image.shape[:2]
    if width > max_width:
        scale = max_width / float(width)
        new_width = max_width
        new_height = int(round(height * scale))
        image = cv2.resize(
            image, (new_width, new_height), interpolation=cv2.INTER_AREA
        )

    if use_cache:
        cached = image.copy()
        _read_cache[cache_key] = cached
        if cache_key in _read_cache_keys:
            _read_cache_keys.remove(cache_key)
        _read_cache_keys.append(cache_key)
        if len(_read_cache_keys) > _READ_CACHE_MAX_SIZE:
            oldest_key = _read_cache_keys.pop(0)
            _read_cache.pop(oldest_key, None)

    return image


def adaptive_edge_from_array(
    image: np.ndarray,
    blur_ksize: int = 5,
    block_size: Optional[int] = None,
) -> np.ndarray:
    """
    Compute edges from a BGR image using adaptive thresholding.

    Parameters
    ----------
    image:
        Input BGR image (H, W, 3), dtype uint8, BGR order.
    blur_ksize:
        Median blur kernel size (will be normalized to an odd value).
    block_size:
        Optional adaptive threshold block size. If None, a dynamic
        value based on image size is used:
        ``block_size = max(9, (min(h, w) // 100) | 1)``.

    Returns
    -------
    np.ndarray
        Single-channel edge map (binary, uint8).

    Raises
    ------
    ValueError
        If the input image or parameters are invalid.
    """
    image = _validate_bgr_image(image, "adaptive_edge_from_array")
    if blur_ksize <= 0:
        raise ValueError("blur_ksize must be a positive integer.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_ksize = _ensure_odd_kernel_size(blur_ksize)
    blurred = cv2.medianBlur(gray, blur_ksize)

    h, w = gray.shape
    if block_size is None:
        block_size_eff = max(9, (min(h, w) // 100) | 1)
    else:
        if block_size <= 1:
            raise ValueError("block_size must be greater than 1.")
        block_size_eff = _ensure_odd_kernel_size(block_size, minimum=3)

    edges = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        block_size_eff,
        2,
    )
    return edges


def canny_edge_from_array(
    image: np.ndarray,
    threshold1: int = 100,
    threshold2: int = 200,
    blur_ksize: int = 5,
) -> np.ndarray:
    """
    Compute Canny edges from a BGR image.

    Parameters
    ----------
    image:
        Input BGR image (H, W, 3), dtype uint8, BGR order.
    threshold1:
        Lower hysteresis threshold for Canny (non-negative).
    threshold2:
        Upper hysteresis threshold for Canny (non-negative).
    blur_ksize:
        Median blur kernel size (will be normalized to an odd value).

    Returns
    -------
    np.ndarray
        Single-channel edge map (uint8).

    Raises
    ------
    ValueError
        If the input image or parameters are invalid.
    """
    image = _validate_bgr_image(image, "canny_edge_from_array")
    if threshold1 < 0 or threshold2 < 0:
        raise ValueError("Canny thresholds must be non-negative.")
    if blur_ksize <= 0:
        raise ValueError("blur_ksize must be a positive integer.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_ksize = _ensure_odd_kernel_size(blur_ksize)
    blurred = cv2.medianBlur(gray, blur_ksize)
    edges = cv2.Canny(blurred, threshold1, threshold2)
    return edges


def canny_edge_detection(
    image_path: str | Path,
    threshold1: int = 100,
    threshold2: int = 200,
    blur_ksize: int = 5,
) -> np.ndarray:
    """
    Run a Canny edge detector on an input image.

    Pipeline
    --------
    - Read image from disk.
    - Convert to grayscale.
    - Apply median blur.
    - Apply Canny edge detection.

    Returns
    -------
    np.ndarray
        Single-channel edge map.
    """
    image = read_image(image_path)
    return canny_edge_from_array(
        image,
        threshold1=threshold1,
        threshold2=threshold2,
        blur_ksize=blur_ksize,
    )


def adaptive_edge_detection(
    image_path: str | Path,
    blur_ksize: int = 5,
) -> np.ndarray:
    """
    Compute edges using adaptive thresholding.

    Pipeline
    --------
    - Read image from disk.
    - Convert to grayscale.
    - Apply median blur.
    - Apply adaptive thresholding to emphasize edges.

    Returns
    -------
    np.ndarray
        Single-channel edge map (binary).
    """
    image = read_image(image_path)
    return adaptive_edge_from_array(image, blur_ksize=blur_ksize)


def thicken_edges(edges: np.ndarray, kernel_size: int = 2) -> np.ndarray:
    """
    Thicken an edge map using morphological dilation.

    Parameters
    ----------
    edges:
        Single-channel edge image.
    kernel_size:
        Size of the square dilation kernel.

    Returns
    -------
    np.ndarray
        Dilated edge map.

    Raises
    ------
    ValueError
        If ``edges`` is not a valid single-channel edge image.
    """
    gray_edges = _validate_gray_image(edges, "thicken_edges")
    if kernel_size < 1:
        kernel_size = 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    dilated = cv2.dilate(gray_edges, kernel, iterations=1)
    return dilated


def bilateral_filter(
    image: np.ndarray,
    d: int = 9,
    sigmaColor: float = 75,
    sigmaSpace: float = 75,
) -> np.ndarray:
    """
    Apply a bilateral filter to smooth colors while preserving edges.

    Parameters
    ----------
    image:
        Input BGR image.
    d:
        Diameter of each pixel neighborhood.
    sigmaColor:
        Filter sigma in the color space.
    sigmaSpace:
        Filter sigma in the coordinate space.

    Returns
    -------
    np.ndarray
        Bilaterally filtered BGR image.
    """
    image = _validate_bgr_image(image, "bilateral_filter")
    if d <= 0:
        raise ValueError("d must be a positive integer.")
    return cv2.bilateralFilter(image, d, sigmaColor, sigmaSpace)


def color_quantization_from_array(
    image: np.ndarray,
    k: int = 8,
    downscale_for_kmeans: bool = True,
    sample_for_kmeans: bool = True,
    max_sample_size: int = _KMEANS_MAX_SAMPLE_SIZE,
) -> np.ndarray:
    """
    Reduce the number of colors in an image using K-means clustering.

    For performance on large images, a downscaled version can be used
    to compute cluster centers, which are then mapped back onto the
    full-resolution image in a single vectorized pass.

    Parameters
    ----------
    image:
        Input BGR image (H, W, 3), dtype uint8.
    k:
        Number of color clusters (k >= 1).
    downscale_for_kmeans:
        If True, resize the input to ensure ``max(H, W) <= max_sample_size``
        before running K-means.
    sample_for_kmeans:
        Additional flag to control downsampling; when set to False,
        K-means is run on the full-resolution image even if
        ``downscale_for_kmeans`` is True.
    max_sample_size:
        Maximum dimension (in pixels) used when downscaling for K-means.

    Returns
    -------
    np.ndarray
        Quantized BGR image with the same shape and dtype as the input.

    Raises
    ------
    ValueError
        If parameters are invalid or the input image is not a valid BGR image.
    """
    image = _validate_bgr_image(image, "color_quantization_from_array")
    if k <= 0:
        raise ValueError("k must be a positive integer for color quantization.")
    if max_sample_size <= 0:
        raise ValueError("max_sample_size must be a positive integer.")

    h, w = image.shape[:2]
    use_sampling = downscale_for_kmeans and sample_for_kmeans

    if use_sampling and max(h, w) > max_sample_size:
        scale = max_sample_size / float(max(h, w))
        new_w = int(round(w * scale))
        new_h = int(round(h * scale))
        sample_img = cv2.resize(
            image, (new_w, new_h), interpolation=cv2.INTER_AREA
        )
    else:
        sample_img = image

    data_sample = sample_img.reshape((-1, 3)).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)

    # Improve determinism of cluster initialization.
    np.random.seed(42)

    _compactness, _labels_sample, centers = cv2.kmeans(
        data_sample,
        k,
        None,
        criteria,
        8,
        cv2.KMEANS_PP_CENTERS,
    )

    centers = centers.astype(np.float32)

    # Assign every original pixel to the nearest center in a single pass.
    data_full = image.reshape((-1, 3)).astype(np.float32)
    diff = data_full[:, None, :] - centers[None, :, :]
    distances_sq = np.sum(diff * diff, axis=2)
    labels_full = np.argmin(distances_sq, axis=1)
    quantized_flat = centers[labels_full].astype(np.uint8)
    quantized = quantized_flat.reshape(image.shape)
    return quantized


def color_quantization(image: np.ndarray, k: int = 8) -> np.ndarray:
    """
    Backward-compatible wrapper around :func:`color_quantization_from_array`.

    Parameters
    ----------
    image:
        Input BGR image.
    k:
        Number of color clusters.

    Returns
    -------
    np.ndarray
        Quantized BGR image.
    """
    return color_quantization_from_array(
        image,
        k=k,
        downscale_for_kmeans=True,
        sample_for_kmeans=True,
    )

def classic_cartoon(
    image_path: str | Path,
    k: int = 8,
    edge_thickness: int = 2,
    bilateral_passes: int = 2,
    edge_method: str = "adaptive",
    quantize_downscale: bool = True,
    soft_edges: bool = True,
) -> np.ndarray:
    """
    Produce a full-color cartoon effect with bold black outlines.

    Pipeline
    --------
    1. Read the image once from disk.
    2. Apply several bilateral filter passes to strongly smooth colors.
    3. Quantize colors using K-means (optionally on a downscaled sample).
    4. Boost saturation and value slightly in HSV space.
    5. Compute edges from the smoothed image (adaptive or Canny).
    6. Thicken edges and apply morphological closing to close gaps.
    7. Invert edges so background is white and outlines are black.
    8. Optionally soften edges with a small Gaussian blur.
    9. Convert to 3-channel and blend with the quantized colors using
       ``cv2.bitwise_and`` so colors are preserved and outlines remain.

    Parameters
    ----------
    image_path:
        Path to the input image.
    k:
        Number of color clusters used for quantization.
    edge_thickness:
        Thickness of detected outlines (in pixels).
    bilateral_passes:
        Number of times to apply bilateral filtering for strong smoothing.
    edge_method:
        Edge detector to use: ``\"adaptive\"`` or ``\"canny\"``.
    quantize_downscale:
        Whether to downscale before running K-means for faster quantization.
    soft_edges:
        If True, apply a small Gaussian blur to inverted edges for
        a slightly softer, hand-drawn look.

    Returns
    -------
    np.ndarray
        BGR cartoon image (uint8).
    """
    if k <= 0:
        raise ValueError("k must be a positive integer for classic_cartoon.")
    if edge_thickness < 1:
        raise ValueError("edge_thickness must be at least 1.")
    if bilateral_passes < 1:
        bilateral_passes = 1
    if edge_method not in {"adaptive", "canny"}:
        raise ValueError('edge_method must be either "adaptive" or "canny".')

    image = read_image(image_path)
    image = _validate_bgr_image(image, "classic_cartoon")

    # 1-2. Strong smoothing
    smoothed = image.copy()
    for _ in range(bilateral_passes):
        smoothed = bilateral_filter(smoothed, d=9, sigmaColor=75, sigmaSpace=75)

    # 3. Color reduction via K-means on smoothed colors
    quantized = color_quantization_from_array(
        smoothed,
        k=k,
        downscale_for_kmeans=quantize_downscale,
        sample_for_kmeans=quantize_downscale,
    )

    # 4. Slight HSV boost before applying edges
    hsv = cv2.cvtColor(quantized, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)
    s *= 1.15  # modest saturation boost
    v *= 1.05  # slight value boost
    hsv = cv2.merge((h, np.clip(s, 0, 255), np.clip(v, 0, 255)))
    boosted = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 5. Edge extraction from smoothed image
    if edge_method == "adaptive":
        edges = adaptive_edge_from_array(smoothed, blur_ksize=5)
    else:  # "canny"
        edges = canny_edge_from_array(smoothed, threshold1=80, threshold2=180, blur_ksize=5)

    # 6. Thicken edges and apply morphological closing
    edges = thicken_edges(edges, edge_thickness)
    close_kernel_size = _ensure_odd_kernel_size(edge_thickness * 2 + 1)
    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (close_kernel_size, close_kernel_size)
    )
    edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, close_kernel)

    # 7-8. Invert and optionally soften edges
    edges_inv = cv2.bitwise_not(edges_closed)
    if soft_edges:
        edges_inv = cv2.GaussianBlur(edges_inv, (3, 3), 0)

    # 7-8-9. Convert to 3-channel and blend with colors
    edges_3c = cv2.cvtColor(edges_inv, cv2.COLOR_GRAY2BGR)
    cartoon = cv2.bitwise_and(boosted, edges_3c)

    return cartoon


def _sketch_from_array(
    image: np.ndarray,
    use_clahe: bool = True,
    canny_threshold1: int = 50,
    canny_threshold2: int = 150,
) -> np.ndarray:
    """
    Internal helper that produces a grayscale pencil sketch from a BGR image.

    Parameters
    ----------
    image:
        Input BGR image (H, W, 3), dtype uint8.
    use_clahe:
        If True, apply CLAHE to enhance local contrast before sketching.
    canny_threshold1:
        Lower Canny edge threshold.
    canny_threshold2:
        Upper Canny edge threshold.

    Returns
    -------
    np.ndarray
        Single-channel grayscale sketch.
    """
    image = _validate_bgr_image(image, "_sketch_from_array")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if use_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    # Smooth slightly
    gray_blur = cv2.GaussianBlur(gray, (5, 5), 0)

    # Strong edge extraction
    edges = cv2.Canny(gray_blur, canny_threshold1, canny_threshold2)

    # Invert edges
    edges_inv = cv2.bitwise_not(edges)

    # Dodge blending
    inverted = cv2.bitwise_not(gray_blur)
    blurred = cv2.GaussianBlur(inverted, (21, 21), 0)
    dodge = cv2.divide(gray_blur, 255 - blurred, scale=256)

    # Combine edges + dodge
    sketch = cv2.bitwise_and(dodge, edges_inv)

    # Increase clarity
    sketch = cv2.convertScaleAbs(sketch, alpha=1.6, beta=15)

    return sketch


def sketch_effect(image_path: str | Path, **kwargs: object) -> np.ndarray:
    """
    Produce a grayscale pencil sketch effect from an image.

    Pipeline
    --------
    - Read image once from disk.
    - Optionally apply CLAHE for local contrast.
    - Apply Gaussian blur and Canny edge detection.
    - Apply color dodge blending between grayscale and blurred inverse.

    Parameters
    ----------
    image_path:
        Path to the input image.
    **kwargs:
        Advanced parameters forwarded to :func:`_sketch_from_array`,
        such as ``use_clahe`` or Canny thresholds.

    Returns
    -------
    np.ndarray
        Single-channel sketch image.
    """
    image = read_image(image_path)
    sketch = _sketch_from_array(image, **kwargs)

    return sketch


def pencil_color_effect(
    image_path: str | Path,
    blend_mode: str = "weighted",
    use_clahe: bool = True,
    canny_threshold1: int = 50,
    canny_threshold2: int = 150,
    add_paper_texture: bool = True,
    paper_noise_std: float = 4.0,
    noise_seed: Optional[int] = None,
    sharpen_amount: float = 1.1,
) -> np.ndarray:
    """
    Produce a colored pencil-style effect from an image.

    Parameters
    ----------
    image_path:
        Path to the input image.
    blend_mode:
        How to blend the sketch with the color base. Either
        ``\"multiply\"`` or ``\"weighted\"`` (default).
    use_clahe:
        Whether to apply CLAHE in the underlying sketch generation.
    canny_threshold1:
        Lower Canny edge threshold for the sketch.
    canny_threshold2:
        Upper Canny edge threshold for the sketch.
    add_paper_texture:
        If True, inject subtle Gaussian noise to mimic paper texture.
    paper_noise_std:
        Standard deviation of the paper texture noise.
    noise_seed:
        Optional random seed for reproducible noise.
    sharpen_amount:
        Strength of final unsharp masking. Values slightly above 1.0
        (e.g., 1.1) provide gentle sharpening.

    Returns
    -------
    np.ndarray
        BGR pencil-color image (uint8).
    """
    if sharpen_amount < 0:
        raise ValueError("sharpen_amount must be non-negative.")
    if blend_mode not in {"multiply", "weighted"}:
        raise ValueError('blend_mode must be either "multiply" or "weighted".')

    original = read_image(image_path)
    original = _validate_bgr_image(original, "pencil_color_effect")
    sketch = _sketch_from_array(
        original,
        use_clahe=use_clahe,
        canny_threshold1=canny_threshold1,
        canny_threshold2=canny_threshold2,
    )

    # Strong desaturation
    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)
    s *= 0.5
    hsv = cv2.merge((h, np.clip(s, 0, 255), v))
    color_base = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    sketch_3c = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

    if blend_mode == "multiply":
        blended_float = (
            color_base.astype(np.float32) / 255.0
            * sketch_3c.astype(np.float32) / 255.0
        )
        blended = np.clip(blended_float * 255.0, 0, 255).astype(np.uint8)
    else:  # "weighted"
        blended = cv2.addWeighted(color_base, 0.7, sketch_3c, 0.3, 0)

    # Subtle paper noise
    if add_paper_texture and paper_noise_std > 0:
        rng = np.random.default_rng(noise_seed)
        noise = rng.normal(0.0, paper_noise_std, blended.shape).astype(np.float32)
        textured = blended.astype(np.float32) + noise
        blended = np.clip(textured, 0, 255).astype(np.uint8)

    # Final light sharpening
    if sharpen_amount > 0:
        blurred = cv2.GaussianBlur(blended, (0, 0), sigmaX=1.0)
        alpha = sharpen_amount
        beta = 1.0 - alpha
        final = cv2.addWeighted(blended, alpha, blurred, beta, 0)
    else:
        final = blended

    return final

def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
    """
    Convert a BGR image to RGB for display frameworks like Streamlit.

    Parameters
    ----------
    image:
        Input BGR image.

    Returns
    -------
    np.ndarray
        RGB image.
    """
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("bgr_to_rgb expects a 3-channel BGR image.")
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def encode_image_to_png(image: np.ndarray) -> bytes:
    """
    Encode an image as PNG bytes suitable for download.

    Parameters
    ----------
    image:
        Input image (BGR color or single-channel grayscale). Accepted
        shapes are (H, W), (H, W, 1), or (H, W, 3). The expected dtype
        is uint8; other dtypes will be converted to uint8.

    Returns
    -------
    bytes
        PNG-encoded image data.

    Raises
    ------
    ValueError
        If the image cannot be encoded or has an unsupported shape.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError(
            f"encode_image_to_png expects a NumPy array, got {type(image)!r}."
        )

    if image.ndim == 2:
        to_encode = image
    elif image.ndim == 3 and image.shape[2] == 1:
        to_encode = image[:, :, 0]
    elif image.ndim == 3 and image.shape[2] == 3:
        to_encode = image
    else:
        raise ValueError("Unsupported image shape for PNG encoding.")

    if to_encode.dtype != np.uint8:
        to_encode = to_encode.astype(np.uint8)

    success, buffer = cv2.imencode(".png", to_encode)
    if not success:
        raise ValueError("Failed to encode image as PNG.")
    return buffer.tobytes()


if __name__ == "__main__":
    """
    Small local test harness.

    To use this for manual verification, set ``sample_path`` below to
    point to an image on your system and run this module directly.
    """
    sample_path: Optional[Path] = None

    if sample_path is not None and sample_path.exists():
        src_path = sample_path
        cartoon_img = classic_cartoon(src_path)
        sketch_img = sketch_effect(src_path)
        pencil_img = pencil_color_effect(src_path)

        cv2.imwrite("debug_out_cartoon.png", cartoon_img)
        cv2.imwrite("debug_out_sketch.png", sketch_img)
        cv2.imwrite("debug_out_pencil_color.png", pencil_img)
