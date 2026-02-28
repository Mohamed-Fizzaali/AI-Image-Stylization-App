from __future__ import annotations

"""
Core image processing routines for the Artify AI application.

All OpenCV/NumPy based image transformations are defined here so that
the Streamlit UI layer can remain thin and focused on presentation.
"""

from pathlib import Path

import cv2
import numpy as np


def _ensure_odd_kernel_size(ksize: int, minimum: int = 3) -> int:
    """
    Ensure kernel size is a positive odd integer, at least `minimum`.

    Parameters
    ----------
    ksize:
        Requested kernel size.
    minimum:
        Smallest allowed odd kernel size.
    """
    if ksize < minimum:
        ksize = minimum
    if ksize % 2 == 0:
        ksize += 1
    return ksize


def read_image(image_path: str | Path, max_width: int = 1200) -> np.ndarray:
    """
    Read an image from disk using OpenCV and optionally resize.

    Parameters
    ----------
    image_path:
        Path to the image file.
    max_width:
        Maximum allowed width in pixels. Images wider than this
        are resized while preserving aspect ratio.

    Returns
    -------
    np.ndarray
        Loaded BGR image.

    Raises
    ------
    ValueError
        If the image cannot be read.
    """
    path = Path(image_path).expanduser().resolve()
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image from path: {path}")

    height, width = image.shape[:2]
    if width > max_width:
        scale = max_width / float(width)
        new_width = max_width
        new_height = int(round(height * scale))
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

    return image


def adaptive_edge_from_array(
    image: np.ndarray,
    blur_ksize: int = 5,
) -> np.ndarray:
    """
    Compute edges from a BGR image using adaptive thresholding.

    Parameters
    ----------
    image:
        Input BGR image.
    blur_ksize:
        Median blur kernel size (will be normalized to an odd value).

    Returns
    -------
    np.ndarray
        Single-channel edge map (binary).
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_ksize = _ensure_odd_kernel_size(blur_ksize)
    blurred = cv2.medianBlur(gray, blur_ksize)

    h, w = gray.shape
    block_size = max(9, (min(h, w) // 100) | 1)

    edges = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        block_size,
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
        Input BGR image.
    threshold1:
        Lower hysteresis threshold for Canny.
    threshold2:
        Upper hysteresis threshold for Canny.
    blur_ksize:
        Median blur kernel size (will be normalized to an odd value).

    Returns
    -------
    np.ndarray
        Single-channel edge map.
    """
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
    """
    if kernel_size < 1:
        kernel_size = 1
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    dilated = cv2.dilate(edges, kernel, iterations=1)
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
    return cv2.bilateralFilter(image, d, sigmaColor, sigmaSpace)


def color_quantization(image: np.ndarray, k: int = 8) -> np.ndarray:
    """
    Reduce the number of colors in an image using K-means clustering.

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
    if k <= 0:
        raise ValueError("k must be a positive integer for color quantization.")

    data = image.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)

    # Improve determinism of cluster initialization.
    np.random.seed(42)

    _compactness, labels, centers = cv2.kmeans(
        data,
        k,
        None,
        criteria,
        5,
        cv2.KMEANS_PP_CENTERS,
    )
    centers = np.uint8(centers)
    quantized_flat = centers[labels.flatten()]
    quantized = quantized_flat.reshape(image.shape)
    return quantized


def classic_cartoon(
    image_path: str | Path,
    k: int = 8,
    edge_thickness: int = 2,
) -> np.ndarray:
    """
    Generate a classic cartoon-style effect.

    Pipeline
    --------
    - Read image.
    - Apply bilateral filter.
    - Apply color quantization.
    - Compute adaptive edges.
    - Thicken edges.
    - Convert edges to 3-channel.
    - Combine edges with quantized image via bitwise AND.

    Returns
    -------
    np.ndarray
        Final cartoonized image in BGR color space.
    """
    base_image = read_image(image_path)

    smoothed = bilateral_filter(base_image)
    quantized = color_quantization(smoothed, k=k)

    # Compute edges from the smoothed image for cleaner outlines.
    edges = adaptive_edge_from_array(smoothed)
    thick_edges = thicken_edges(edges, kernel_size=edge_thickness)

    # Invert so edges become black on white background.
    inverted_edges = cv2.bitwise_not(thick_edges)
    edges_3c = cv2.cvtColor(inverted_edges, cv2.COLOR_GRAY2BGR)

    cartoon = cv2.bitwise_and(quantized, edges_3c)
    return cartoon


def _sketch_from_array(image: np.ndarray) -> np.ndarray:
    """
    Internal helper to produce a grayscale sketch from a BGR image.

    Parameters
    ----------
    image:
        Input BGR image.

    Returns
    -------
    np.ndarray
        Single-channel sketch image.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    inverted = cv2.bitwise_not(gray)
    blurred = cv2.GaussianBlur(inverted, (21, 21), sigmaX=0, sigmaY=0)

    inverted_blur = 255 - blurred
    sketch = cv2.divide(gray, inverted_blur, scale=256.0)
    return sketch


def sketch_effect(image_path: str | Path) -> np.ndarray:
    """
    Produce a grayscale pencil sketch effect from an image.

    Pipeline
    --------
    - Read image.
    - Convert to grayscale.
    - Invert grayscale values.
    - Apply Gaussian blur.
    - Apply color dodge blending between grayscale and blurred inverse.

    Returns
    -------
    np.ndarray
        Single-channel sketch image.
    """
    image = read_image(image_path)
    return _sketch_from_array(image)


def pencil_color_effect(image_path: str | Path) -> np.ndarray:
    """
    Create a colored pencil sketch effect.

    Pipeline
    --------
    - Generate grayscale sketch.
    - Convert original image to slightly desaturated color base.
    - Combine sketch intensities with the color base.

    Returns
    -------
    np.ndarray
        Final colored pencil effect image in BGR color space.
    """
    original = read_image(image_path)
    sketch = _sketch_from_array(original)

    # Slightly desaturate the original image.
    hsv = cv2.cvtColor(original, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)
    s *= 0.6
    s = np.clip(s, 0, 255)
    hsv_desat = cv2.merge((h, s, v))
    desaturated_bgr = cv2.cvtColor(hsv_desat.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # Use sketch as intensity mask over the desaturated color.
    sketch_norm = sketch.astype(np.float32) / 255.0
    sketch_3c = cv2.merge([sketch_norm, sketch_norm, sketch_norm])

    color_float = desaturated_bgr.astype(np.float32)
    combined = color_float * sketch_3c

    # Slight contrast boost for a more vibrant colored pencil look.
    combined = cv2.convertScaleAbs(combined, alpha=1.15, beta=10)
    return combined


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
        Input image (BGR color or single-channel grayscale).

    Returns
    -------
    bytes
        PNG-encoded image data.

    Raises
    ------
    ValueError
        If the image cannot be encoded.
    """
    if image.ndim == 2:
        to_encode = image
    elif image.ndim == 3 and image.shape[2] in (1, 3):
        to_encode = image
    else:
        raise ValueError("Unsupported image shape for PNG encoding.")

    success, buffer = cv2.imencode(".png", to_encode)
    if not success:
        raise ValueError("Failed to encode image as PNG.")
    return buffer.tobytes()

