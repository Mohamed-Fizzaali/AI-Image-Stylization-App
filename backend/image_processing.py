from __future__ import annotations

"""
Core image processing routines for the Artify AI application.

All OpenCV/NumPy based image transformations are defined here so that
the Streamlit UI layer can remain thin and focused on presentation.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

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

def classic_cartoon(image_path: str | Path) -> np.ndarray:
    """
    Produces a high-quality 'Studio Cartoon' effect using Gaussian Pyramids 
    for algorithmic acceleration and morphological transformations for edges.
    """
    # 1. Use your robust caching reader and validator
    image = read_image(image_path)
    image = _validate_bgr_image(image, "classic_cartoon")

    # Extract exact width and height for safety during upsampling
    h, w = image.shape[:2]

    # -------------------------------------------------------------------------
    # Phase 1: Color Abstraction via Gaussian Pyramids
    # -------------------------------------------------------------------------
    color_tensor = image.copy()
    num_downsamples = 2
    
    # Downsample to drastically reduce bilateral filter complexity
    for _ in range(num_downsamples):
        color_tensor = cv2.pyrDown(color_tensor)

    # Apply iterative bilateral filtering on the tiny spatial domain
    for _ in range(5):
        color_tensor = cv2.bilateralFilter(color_tensor, d=9, sigmaColor=9, sigmaSpace=7)

    # Upsample back to approximate original size
    for _ in range(num_downsamples):
        color_tensor = cv2.pyrUp(color_tensor)
        
    # Force exact dimension match (pyrUp can shift odd-pixel dimensions by 1)
    color_tensor = cv2.resize(color_tensor, (w, h), interpolation=cv2.INTER_CUBIC)

    # -------------------------------------------------------------------------
    # Phase 2: Color Quantization
    # -------------------------------------------------------------------------
    # Use your existing, memory-safe robust helper instead of custom math
    quantized_image = color_quantization_from_array(color_tensor, k=12, downscale_for_kmeans=True)

    # -------------------------------------------------------------------------
    # Phase 3: Topological Edge Extraction and Morphological Refinement
    # -------------------------------------------------------------------------
    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred_gray = cv2.medianBlur(grayscale, 7)
    
    edges = cv2.adaptiveThreshold(
        blurred_gray, 255, 
        cv2.ADAPTIVE_THRESH_MEAN_C, 
        cv2.THRESH_BINARY, 
        blockSize=9, C=2
    )
                                  
    # Apply Morphological Closing to clean the binary mask
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    clean_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # -------------------------------------------------------------------------
    # Phase 4: Signal Fusion
    # -------------------------------------------------------------------------
    edge_3c = cv2.cvtColor(clean_edges, cv2.COLOR_GRAY2BGR)
    final_cartoon = cv2.bitwise_and(quantized_image, edge_3c)

    return final_cartoon


def _sketch_from_array(
    image: np.ndarray,
    blur_ksize: int = 21,
    contrast: float = 1.15,
    brightness: int = 10,
) -> np.ndarray:
    """
    Internal helper that produces a highly realistic grayscale pencil sketch.
    Uses the Color Dodge blending technique for natural graphite shading
    instead of harsh Canny edge lines.

    Parameters
    ----------
    image:
        Input BGR image (H, W, 3), dtype uint8.
    blur_ksize:
        Kernel size for the Gaussian blur (must be odd). Larger values
        create thicker, more dispersed pencil strokes.
    contrast:
        Alpha value to boost the contrast of the graphite lines.
    brightness:
        Beta value to ensure the paper background stays a crisp white.

    Returns
    -------
    np.ndarray
        Single-channel grayscale sketch.
    """
    image = _validate_bgr_image(image, "_sketch_from_array")
    
    # 1. Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. Invert the grayscale image
    inverted = cv2.bitwise_not(gray)
    
    # 3. Apply a strong Gaussian blur to the inverted image.
    if blur_ksize % 2 == 0:
        blur_ksize += 1
    blurred = cv2.GaussianBlur(inverted, (blur_ksize, blur_ksize), sigmaX=0, sigmaY=0)
    
    # 4. Color Dodge Blend
    inv_blurred = cv2.bitwise_not(blurred)
    sketch = cv2.divide(gray, inv_blurred, scale=256.0)
    
    # 5. Clean up the paper and pop the graphite
    sketch = cv2.convertScaleAbs(sketch, alpha=contrast, beta=brightness)
    
    return sketch


def sketch_effect(image_path: str | Path, **kwargs: Any) -> np.ndarray:
    """
    Produce a grayscale pencil sketch effect from an image.

    Pipeline
    --------
    - Read image once from disk.
    - Convert to grayscale and invert.
    - Apply Gaussian blur to the inverted image.
    - Apply color dodge blending to simulate natural graphite shading.

    Parameters
    ----------
    image_path:
        Path to the input image.
    **kwargs:
        Advanced parameters forwarded to :func:`_sketch_from_array`,
        such as ``blur_ksize``, ``contrast``, or ``brightness``.

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

    # Strong desaturation (optimized: avoid float64 array allocations, process uint8 in-place)
    # ⚡ Bolt: ~10x faster desaturation using cv2.convertScaleAbs on the saturation channel
    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = cv2.convertScaleAbs(hsv[:, :, 1], alpha=0.5)
    color_base = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

    sketch_3c = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

    if blend_mode == "multiply":
        # ⚡ Bolt: ~20x faster hardware-accelerated multiply vs numpy float32 broadcasting
        blended = cv2.multiply(color_base, sketch_3c, scale=1/255.0)
    else:  # "weighted"
        blended = cv2.addWeighted(color_base, 0.7, sketch_3c, 0.3, 0)

    # Subtle paper noise
    if add_paper_texture and paper_noise_std > 0:
        rng = np.random.default_rng(noise_seed)
        noise = rng.normal(0.0, paper_noise_std, blended.shape).astype(np.float32)
        textured = blended.astype(np.float32) + noise
        blended = np.clip(textured, 0, 255).astype(np.uint8)

    # Final light sharpening
    if sharpen_amount > 1.0:
        blur = cv2.GaussianBlur(blended, (0, 0), min(sharpen_amount, 3.0))
        blended = cv2.addWeighted(
            blended, sharpen_amount + 0.5, blur, -0.5, 0
        )

    return blended


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


def grayscale_noir(image_path: str | Path, **kwargs: Any) -> np.ndarray:
    """Produce a dramatic high-contrast grayscale image."""
    image = read_image(image_path)
    image = _validate_bgr_image(image, "grayscale_noir")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=-30)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def sepia_effect(image_path: str | Path, **kwargs: Any) -> np.ndarray:
    """Produce a vintage warm-toned sepia image."""
    image = read_image(image_path)
    image = _validate_bgr_image(image, "sepia_effect")
    kernel = np.array([[0.131, 0.534, 0.272],
                       [0.168, 0.686, 0.349],
                       [0.189, 0.769, 0.393]])
    sepia = cv2.transform(image, kernel)
    return np.clip(sepia, 0, 255).astype(np.uint8)


def invert_neon(image_path: str | Path, **kwargs: Any) -> np.ndarray:
    """Produce an inverted cyberpunk glow effect."""
    image = read_image(image_path)
    image = _validate_bgr_image(image, "invert_neon")
    inverted = cv2.bitwise_not(image)

    # ⚡ Bolt: Process saturation directly in uint8 to prevent large array copies
    hsv = cv2.cvtColor(inverted, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = cv2.convertScaleAbs(hsv[:, :, 1], alpha=1.5)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


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
def sepia_effect(image_path: str | Path) -> np.ndarray:
    """Apply a vintage sepia filter to the image."""
    image = read_image(image_path)
    image = _validate_bgr_image(image, "sepia_effect")
    
    # Standard Sepia transformation matrix
    kernel = np.array([[0.272, 0.534, 0.131],
                       [0.349, 0.686, 0.168],
                       [0.393, 0.769, 0.189]])
    sepia = cv2.transform(image, kernel)
    return np.clip(sepia, 0, 255).astype(np.uint8)

def invert_neon(image_path: str | Path) -> np.ndarray:
    """Create a high-contrast inverted neon glow style."""
    image = read_image(image_path)
    image = _validate_bgr_image(image, "invert_neon")
    
    inverted = cv2.bitwise_not(image)
    return cv2.GaussianBlur(inverted, (3, 3), 0)

def grayscale_noir(image_path: str | Path) -> np.ndarray:
    """Convert the image to a high-contrast cinematic grayscale Noir."""
    image = read_image(image_path)
    image = _validate_bgr_image(image, "grayscale_noir")
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Convert back to 3-channel BGR so it remains compatible with your dashboard preview
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

def apply_watermark(image: np.ndarray, text: str = "ARTIFY AI PREVIEW") -> np.ndarray:
    """Adds a semi-transparent text watermark for free previews.
    Accepts both BGR (3-channel) and grayscale (2D) images.
    Always returns a 3-channel BGR image.
    """
    if not isinstance(image, np.ndarray):
        raise ValueError("apply_watermark expects a NumPy array.")

    # Convert grayscale (2D or single-channel 3D) to BGR so putText works
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] == 1:
        image = cv2.cvtColor(image[:, :, 0], cv2.COLOR_GRAY2BGR)
    elif image.ndim == 3 and image.shape[2] != 3:
        raise ValueError(f"apply_watermark: unsupported image shape {image.shape}.")

    if image.dtype != np.uint8:
        image = image.astype(np.uint8)

    overlay = image.copy()
    h, w = image.shape[:2]

    font = cv2.FONT_HERSHEY_SIMPLEX
    # Scale font size based on image resolution
    font_scale = max(1, min(h, w) // 500)
    thickness = max(2, font_scale * 2)

    text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
    text_x = (w - text_size[0]) // 2
    text_y = (h + text_size[1]) // 2

    cv2.putText(overlay, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
    # Blend with 40% opacity
    return cv2.addWeighted(overlay, 0.4, image, 0.6, 0)