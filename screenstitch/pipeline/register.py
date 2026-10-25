"""Registration — ORB feature detection → descriptor matching → homography → warp to shared canvas."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from screenstitch.utils import to_gray

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_ORB_FEATURES = 3000
MATCH_RATIO_THRESH = 0.75  # Lowe's ratio test
MIN_MATCH_COUNT = 10       # minimum good matches for homography
RANSAC_REPROJ_THRESH = 5.0


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------
@dataclass
class RegistrationResult:
    """Outputs of the registration stage."""
    warped_images: list[np.ndarray]          # warped BGR images (same canvas size)
    warped_masks: list[np.ndarray]           # binary masks showing valid pixels per image
    canvas_size: tuple[int, int]             # (width, height) of the shared canvas
    homographies: list[np.ndarray]           # 3×3 matrices (identity for reference image)
    names: list[str]                         # filenames, same order as above
    match_counts: list[int] = field(default_factory=list)  # good-match count per pair


# ---------------------------------------------------------------------------
# Feature detection & matching
# ---------------------------------------------------------------------------
def _detect_and_compute(
    image: np.ndarray,
    n_features: int = DEFAULT_ORB_FEATURES,
) -> tuple[list[cv2.KeyPoint], np.ndarray | None]:
    """Detect ORB keypoints and compute descriptors."""
    orb = cv2.ORB_create(nfeatures=n_features)
    gray = to_gray(image)
    kps, descs = orb.detectAndCompute(gray, None)
    return kps, descs


def _match_descriptors(
    descs_a: np.ndarray,
    descs_b: np.ndarray,
) -> list[cv2.DMatch]:
    """BFMatcher + Lowe's ratio test. Returns good matches."""
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    raw = bf.knnMatch(descs_a, descs_b, k=2)
    good = []
    for pair in raw:
        if len(pair) == 2:
            m, n = pair
            if m.distance < MATCH_RATIO_THRESH * n.distance:
                good.append(m)
    return good


def _find_homography(
    kps_a: list[cv2.KeyPoint],
    kps_b: list[cv2.KeyPoint],
    matches: list[cv2.DMatch],
) -> Optional[np.ndarray]:
    """Compute homography A→B using RANSAC. Returns None if too few matches."""
    if len(matches) < MIN_MATCH_COUNT:
        log.warning("Only %d matches (need %d) — skipping pair", len(matches), MIN_MATCH_COUNT)
        return None
    pts_a = np.float32([kps_a[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    pts_b = np.float32([kps_b[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(pts_a, pts_b, cv2.RANSAC, RANSAC_REPROJ_THRESH)
    if H is None:
        log.warning("findHomography returned None")
        return None
    inliers = int(mask.sum()) if mask is not None else 0
    log.info("Homography: %d/%d inliers", inliers, len(matches))
    return H


# ---------------------------------------------------------------------------
# Canvas sizing & warping
# ---------------------------------------------------------------------------
def _compute_canvas_bounds(
    shapes: list[tuple[int, int]],
    homographies: list[np.ndarray],
) -> tuple[np.ndarray, tuple[int, int]]:
    """
    Given image shapes (h, w) and their homographies, compute the bounding box
    that contains all warped images. Returns (offset_matrix, (canvas_w, canvas_h)).
    """
    all_corners = []
    for (h, w), H in zip(shapes, homographies):
        corners = np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2)
        warped_corners = cv2.perspectiveTransform(corners, H)
        all_corners.append(warped_corners)

    all_corners = np.concatenate(all_corners, axis=0)
    x_min, y_min = all_corners.min(axis=0).ravel()
    x_max, y_max = all_corners.max(axis=0).ravel()

    # Translation matrix to shift everything into positive coordinates
    offset = np.eye(3, dtype=np.float64)
    offset[0, 2] = -x_min
    offset[1, 2] = -y_min

    canvas_w = int(np.ceil(x_max - x_min))
    canvas_h = int(np.ceil(y_max - y_min))
    return offset, (canvas_w, canvas_h)


def _warp_image(
    image: np.ndarray,
    H: np.ndarray,
    canvas_size: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Warp a single image onto the canvas. Returns (warped_bgr, valid_mask)."""
    w, h = canvas_size
    warped = cv2.warpPerspective(image, H, (w, h), flags=cv2.INTER_LINEAR)
    # Build a valid-pixel mask by warping a white image
    ones = np.ones(image.shape[:2], dtype=np.uint8) * 255
    mask = cv2.warpPerspective(ones, H, (w, h), flags=cv2.INTER_NEAREST)
    return warped, mask


# ---------------------------------------------------------------------------
# Chain homographies (incremental: img0→img1→img2…)
# ---------------------------------------------------------------------------
def _chain_pairwise(
    images: list[np.ndarray],
    n_features: int = DEFAULT_ORB_FEATURES,
) -> tuple[list[np.ndarray], list[int]]:
    """
    Compute pairwise homographies along the image sequence and chain them
    so every image maps to image-0's coordinate space.

    Returns (homographies, match_counts).
    """
    n = len(images)
    # Pre-compute features for all images
    features = [_detect_and_compute(img, n_features) for img in images]

    # H_cumulative[i] maps image i → image 0
    cumulative: list[np.ndarray] = [np.eye(3, dtype=np.float64)]
    match_counts: list[int] = []

    for i in range(1, n):
        kps_a, descs_a = features[i]
        kps_b, descs_b = features[i - 1]

        if descs_a is None or descs_b is None:
            raise RegistrationError(
                f"No descriptors for image pair ({i-1}, {i}). "
                "Images may lack texture."
            )

        matches = _match_descriptors(descs_a, descs_b)
        match_counts.append(len(matches))
        log.info("Pair %d→%d: %d good matches", i, i - 1, len(matches))

        H_local = _find_homography(kps_a, kps_b, matches)
        if H_local is None:
            raise RegistrationError(
                f"Could not compute homography for pair ({i-1}, {i}). "
                f"Only {len(matches)} matches found."
            )

        # Chain: img_i → img_{i-1} → … → img_0
        cumulative.append(cumulative[-1] @ H_local)

    return cumulative, match_counts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class RegistrationError(Exception):
    """Raised when registration fails (too few features, no overlap, etc.)."""


def register(
    images: list[np.ndarray],
    names: list[str] | None = None,
    *,
    n_features: int = DEFAULT_ORB_FEATURES,
) -> RegistrationResult:
    """
    Register a list of overlapping images into a shared canvas.

    Parameters
    ----------
    images : list of BGR numpy arrays
    names  : optional filenames (for diagnostics)
    n_features : ORB feature cap per image

    Returns
    -------
    RegistrationResult with warped images, masks, canvas size, homographies.

    Raises
    ------
    RegistrationError if registration fails for any pair.
    """
    if len(images) < 2:
        raise RegistrationError("Need at least 2 images to register")

    if names is None:
        names = [f"image_{i}" for i in range(len(images))]

    log.info("Registering %d images…", len(images))

    # 1. Pairwise chain homographies → all map to image-0 space
    homographies, match_counts = _chain_pairwise(images, n_features)

    # 2. Compute canvas bounds
    shapes = [(img.shape[0], img.shape[1]) for img in images]
    offset, canvas_size = _compute_canvas_bounds(shapes, homographies)

    # 3. Apply offset so all coordinates are positive
    adjusted = [offset @ H for H in homographies]

    # 4. Warp every image
    warped_images = []
    warped_masks = []
    for img, H in zip(images, adjusted):
        w_img, w_mask = _warp_image(img, H, canvas_size)
        warped_images.append(w_img)
        warped_masks.append(w_mask)

    log.info("Canvas size: %d × %d", canvas_size[0], canvas_size[1])

    return RegistrationResult(
        warped_images=warped_images,
        warped_masks=warped_masks,
        canvas_size=canvas_size,
        homographies=adjusted,
        names=names,
        match_counts=match_counts,
    )


def register_fallback(images: list[np.ndarray]) -> np.ndarray | None:
    """
    Fallback using OpenCV's built-in Stitcher.
    Returns the stitched image or None on failure.
    """
    stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
    status, result = stitcher.stitch(images)
    if status == cv2.Stitcher_OK:
        log.info("Fallback stitcher succeeded")
        return result
    log.warning("Fallback stitcher failed with status %d", status)
    return None
