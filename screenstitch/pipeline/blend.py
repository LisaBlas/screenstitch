"""Blending — multi-band (Laplacian pyramid) blending for seamless seams."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from screenstitch.pipeline.register import RegistrationResult
from screenstitch.pipeline.mask import MaskResult
from screenstitch.pipeline.reconstruct import ReconstructionResult

log = logging.getLogger(__name__)

DEFAULT_NUM_BANDS = 5


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------
@dataclass
class BlendResult:
    """Outputs of the blending stage."""
    canvas: np.ndarray        # BGR blended image (uint8)
    coverage_mask: np.ndarray  # uint8 mask: 255 where pixels exist, 0 = gap


# ---------------------------------------------------------------------------
# Weight computation
# ---------------------------------------------------------------------------
def _distance_weights(masks: list[np.ndarray]) -> list[np.ndarray]:
    """
    Compute per-image weight maps via distance transform.

    Pixels further from the mask boundary get higher weight,
    producing natural feathering at seam boundaries.
    """
    weights = []
    for m in masks:
        binary = (m > 0).astype(np.uint8)
        if binary.sum() == 0:
            weights.append(np.zeros_like(binary, dtype=np.float32))
            continue
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
        weights.append(dist.astype(np.float32))
    return weights


# ---------------------------------------------------------------------------
# Pyramid utilities
# ---------------------------------------------------------------------------
def _gaussian_pyramid(img: np.ndarray, levels: int) -> list[np.ndarray]:
    """Build a Gaussian pyramid (each level is half the resolution)."""
    current = img.astype(np.float32)
    pyramid = [current]
    for _ in range(levels):
        current = cv2.pyrDown(current)
        pyramid.append(current)
    return pyramid


def _laplacian_pyramid(img: np.ndarray, levels: int) -> list[np.ndarray]:
    """Build a Laplacian pyramid (band-pass filtered at each level)."""
    gauss = _gaussian_pyramid(img, levels)
    lap = []
    for i in range(levels):
        h, w = gauss[i].shape[:2]
        up = cv2.pyrUp(gauss[i + 1], dstsize=(w, h))
        lap.append(gauss[i] - up)
    lap.append(gauss[-1])  # low-pass residual
    return lap


def _collapse_pyramid(pyramid: list[np.ndarray]) -> np.ndarray:
    """Reconstruct an image from its Laplacian pyramid."""
    img = pyramid[-1]
    for i in range(len(pyramid) - 2, -1, -1):
        h, w = pyramid[i].shape[:2]
        img = cv2.pyrUp(img, dstsize=(w, h)) + pyramid[i]
    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def blend(
    reg: RegistrationResult,
    mask: MaskResult,
    recon: ReconstructionResult,
    *,
    num_bands: int = DEFAULT_NUM_BANDS,
    use_poisson: bool = False,
) -> BlendResult:
    """
    Multi-band blend warped images using Laplacian pyramids.

    Distance-from-edge weighting places seams where overlap is deepest.
    Blending at multiple frequency bands smooths exposure differences
    without ghosting fine detail.

    Parameters
    ----------
    reg : RegistrationResult from registration stage.
    mask : MaskResult from disagreement-masking stage.
    recon : ReconstructionResult from reconstruction stage (provides coverage mask).
    num_bands : number of Laplacian pyramid levels.
    use_poisson : if True, refine seam zones with Poisson blending.

    Returns
    -------
    BlendResult with blended canvas and coverage mask.
    """
    n = len(reg.warped_images)
    h, w = reg.warped_images[0].shape[:2]
    log.info("Blending: %d images, canvas %d×%d, %d bands", n, w, h, num_bands)

    # --- Distance-based weights per image (feathered from mask edges) ---
    raw_weights = _distance_weights(mask.clean_masks)

    # Normalize so weights sum to 1 at each pixel
    weight_sum = np.zeros((h, w), dtype=np.float32)
    for wt in raw_weights:
        weight_sum += wt
    weight_sum = np.maximum(weight_sum, 1e-6)
    norm_weights = [wt / weight_sum for wt in raw_weights]

    # --- Clamp pyramid depth to image dimensions ---
    min_dim = min(h, w)
    max_bands = max(1, int(np.log2(max(min_dim, 1))) - 1)
    num_bands = min(num_bands, max_bands)
    log.info("Pyramid levels: %d (max supported: %d)", num_bands, max_bands)

    # --- Build pyramids ---
    img_laps: list[list[np.ndarray]] = []
    wt_gauss: list[list[np.ndarray]] = []
    for i in range(n):
        img_f = reg.warped_images[i].astype(np.float32)
        img_laps.append(_laplacian_pyramid(img_f, num_bands))
        wt_gauss.append(_gaussian_pyramid(norm_weights[i], num_bands))

    # --- Weighted blend at each pyramid level ---
    blended_pyr: list[np.ndarray] = []
    for lev in range(num_bands + 1):
        acc = np.zeros_like(img_laps[0][lev])
        for i in range(n):
            wt = wt_gauss[i][lev]
            # Broadcast single-channel weight to match 3-channel image
            if acc.ndim == 3 and wt.ndim == 2:
                wt = wt[..., np.newaxis]
            acc += img_laps[i][lev] * wt
        blended_pyr.append(acc)

    # --- Collapse ---
    result = _collapse_pyramid(blended_pyr)
    canvas = np.clip(result, 0, 255).astype(np.uint8)

    # --- Optional Poisson refinement ---
    if use_poisson:
        canvas = _poisson_seam_refinement(canvas, reg, mask)

    # --- Apply coverage mask (gaps stay black) ---
    coverage = recon.coverage_mask.copy()
    canvas[coverage == 0] = 0

    covered_pct = 100.0 * (coverage > 0).sum() / max(1, h * w)
    log.info("Blend complete. Coverage: %.1f%%", covered_pct)

    return BlendResult(canvas=canvas, coverage_mask=coverage)


# ---------------------------------------------------------------------------
# Poisson refinement (optional)
# ---------------------------------------------------------------------------
def _poisson_seam_refinement(
    canvas: np.ndarray,
    reg: RegistrationResult,
    mask: MaskResult,
) -> np.ndarray:
    """
    Refine seam zones using cv2.seamlessClone (Poisson / gradient-domain blending).

    Iterates over images and clones each one's clean region onto the
    blended canvas, smoothing gradient discontinuities at seam edges.
    Falls back gracefully if seamlessClone rejects a region.
    """
    h, w = canvas.shape[:2]

    for i in range(len(reg.warped_images)):
        clean = mask.clean_masks[i]

        # Need a non-trivial clean region
        ys, xs = np.where(clean > 0)
        if len(ys) < 100:
            continue

        # Center of the clean region (seamlessClone requirement)
        cx = int(xs.mean())
        cy = int(ys.mean())
        cx = max(1, min(cx, w - 2))
        cy = max(1, min(cy, h - 2))

        try:
            canvas = cv2.seamlessClone(
                reg.warped_images[i], canvas, clean, (cx, cy), cv2.MIXED_CLONE,
            )
        except cv2.error:
            log.debug("Poisson blending skipped for image %d (seamlessClone failed)", i)

    return canvas
