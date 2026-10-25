"""Disagreement masking — detect HUD/cursor/particles via overlap comparison."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from screenstitch.pipeline.register import RegistrationResult

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLD = 30.0     # per-channel difference from median to count as outlier
DEFAULT_INLIER_FRAC = 0.5   # fraction of contributors that must agree
DEFAULT_MORPH_KERNEL = 5     # elliptical kernel size for morphological cleanup


# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------
@dataclass
class MaskResult:
    """Outputs of the disagreement-masking stage."""
    clean_masks: list[np.ndarray]   # per-image uint8 masks (255=world, 0=HUD/gap)
    consensus_map: np.ndarray       # canvas-sized bool: True where consensus exists
    contributor_count: np.ndarray   # canvas-sized int: how many images cover each pixel


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------
def compute_disagreement_masks(
    reg: RegistrationResult,
    *,
    threshold: float = DEFAULT_THRESHOLD,
    inlier_fraction: float = DEFAULT_INLIER_FRAC,
    morph_kernel_size: int = DEFAULT_MORPH_KERNEL,
) -> MaskResult:
    """
    For each canvas pixel with 2+ contributors, compare warped pixels against
    the per-pixel median.  Pixels that disagree with the consensus are flagged
    as HUD / UI / transient and masked out.

    Parameters
    ----------
    reg : RegistrationResult from the registration stage.
    threshold : max per-channel absolute difference from median to be "inlier".
    inlier_fraction : minimum fraction of contributors that must be inliers
                      for the position to count as "world".
    morph_kernel_size : kernel size for morphological close+open cleanup.

    Returns
    -------
    MaskResult with per-image clean masks, consensus map, and contributor counts.
    """
    n = len(reg.warped_images)
    h, w = reg.warped_images[0].shape[:2]
    log.info(
        "Disagreement masking: %d images, canvas %d×%d, t=%.1f, p=%.2f",
        n, w, h, threshold, inlier_fraction,
    )

    # Stack into (N, H, W, 3) float and (N, H, W) bool
    imgs = np.stack(reg.warped_images, axis=0).astype(np.float32)
    valid = np.stack(reg.warped_masks, axis=0) > 0  # (N, H, W)

    contributor_count = valid.sum(axis=0)  # (H, W) int

    # --- Compute per-pixel median of valid contributors ---
    # Use masked array so invalid pixels are excluded from the median.
    valid_3c = valid[..., np.newaxis]                          # (N,H,W,1)
    masked_imgs = np.ma.array(imgs, mask=~np.broadcast_to(valid_3c, imgs.shape))
    median = np.ma.median(masked_imgs, axis=0).filled(0.0)    # (H,W,3) float32

    # --- Per-image inlier test ---
    diff = np.abs(imgs - median[np.newaxis])         # (N,H,W,3)
    inlier = (diff < threshold).all(axis=-1) & valid  # (N,H,W) bool

    inlier_count = inlier.sum(axis=0)                 # (H,W)
    safe_count = np.maximum(contributor_count, 1)
    frac = inlier_count.astype(np.float32) / safe_count.astype(np.float32)

    # Position has consensus if >=2 contributors AND enough agree
    has_consensus = (contributor_count >= 2) & (frac >= inlier_fraction)

    # --- Build per-image output masks ---
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (morph_kernel_size, morph_kernel_size),
    )
    clean_masks: list[np.ndarray] = []

    for i in range(n):
        # In overlap zones: keep only inlier pixels where consensus exists
        mask_i = valid[i] & has_consensus & inlier[i]

        # Single-contributor pixels: no disagreement data → keep as-is
        mask_i |= (contributor_count == 1) & valid[i]

        mask_u8 = mask_i.astype(np.uint8) * 255

        # Morphological cleanup: close small holes, then open to remove specks
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_CLOSE, kernel)
        mask_u8 = cv2.morphologyEx(mask_u8, cv2.MORPH_OPEN, kernel)

        clean_masks.append(mask_u8)

    masked_pct = 100.0 * (1.0 - has_consensus.sum() / max(1, (contributor_count >= 2).sum()))
    log.info("Masked %.1f%% of overlap pixels as HUD/transient", masked_pct)

    return MaskResult(
        clean_masks=clean_masks,
        consensus_map=has_consensus,
        contributor_count=contributor_count,
    )
