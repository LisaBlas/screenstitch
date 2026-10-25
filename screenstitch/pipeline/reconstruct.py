"""Reconstruction — composite clean (world-only) pixels into a single image."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from screenstitch.pipeline.register import RegistrationResult
from screenstitch.pipeline.mask import MaskResult

log = logging.getLogger(__name__)


@dataclass
class ReconstructionResult:
    """Outputs of the reconstruction stage."""
    canvas: np.ndarray        # BGR composite image (uint8)
    coverage_mask: np.ndarray  # uint8 mask: 255 where at least one clean pixel exists, 0 = gap


def reconstruct(
    reg: RegistrationResult,
    mask: MaskResult,
) -> ReconstructionResult:
    """
    Composite warped images using only clean (unmasked) pixels.

    Where multiple clean sources exist for the same pixel, the median
    value is used to reduce noise and minor exposure differences.

    Gaps (pixels with zero clean contributors) remain black with
    coverage_mask=0 so downstream blending knows where data is missing.

    Parameters
    ----------
    reg : RegistrationResult from registration stage.
    mask : MaskResult from disagreement-masking stage.

    Returns
    -------
    ReconstructionResult with the composite canvas and a coverage mask.
    """
    n = len(reg.warped_images)
    h, w = reg.warped_images[0].shape[:2]
    log.info("Reconstruction: %d images, canvas %d×%d", n, w, h)

    # Stack warped images → (N, H, W, 3) float32
    imgs = np.stack(reg.warped_images, axis=0).astype(np.float32)  # (N, H, W, 3)

    # Stack clean masks → (N, H, W) bool
    clean = np.stack(mask.clean_masks, axis=0) > 0  # (N, H, W)

    # Count clean contributors per pixel
    clean_count = clean.sum(axis=0)  # (H, W)

    # --- Median composite via masked array ---
    clean_3c = clean[..., np.newaxis]  # (N, H, W, 1)
    masked_imgs = np.ma.array(
        imgs,
        mask=~np.broadcast_to(clean_3c, imgs.shape),
    )
    # Median across axis 0 (images), ignoring masked entries
    median_composite = np.ma.median(masked_imgs, axis=0).filled(0.0)  # (H, W, 3)
    canvas = median_composite.astype(np.uint8)

    # Coverage mask: any pixel with at least one clean contributor
    coverage = (clean_count > 0).astype(np.uint8) * 255

    covered_pct = 100.0 * coverage.astype(bool).sum() / max(1, h * w)
    gap_pct = 100.0 - covered_pct
    log.info("Coverage: %.1f%% of canvas, %.1f%% gaps", covered_pct, gap_pct)

    return ReconstructionResult(canvas=canvas, coverage_mask=coverage)
