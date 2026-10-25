"""Quick smoke test: registration + disagreement masking on winter_burrow screenshots."""

import logging
import sys
from pathlib import Path

import cv2
import numpy as np

from screenstitch.utils import load_image, save_image
from screenstitch.pipeline import register, compute_disagreement_masks

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

SCREENSHOTS = Path("test_screenshots")
DEBUG_DIR = Path("debug/winter_burrow")
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# Load
left = load_image(SCREENSHOTS / "winter_burrow_left.png")
right = load_image(SCREENSHOTS / "winter_burrow_right.png")
names = ["winter_burrow_left.png", "winter_burrow_right.png"]
print(f"Loaded: {left.shape}, {right.shape}")

# 1. Registration
print("\n--- Registration ---")
reg = register([left, right], names)
print(f"Canvas size: {reg.canvas_size}")
print(f"Match counts: {reg.match_counts}")

for i, name in enumerate(reg.names):
    save_image(DEBUG_DIR / f"warped_{name}", reg.warped_images[i])
    save_image(DEBUG_DIR / f"warped_mask_{name}", reg.warped_masks[i])
print(f"Saved warped images + masks to {DEBUG_DIR}/")

# 2. Disagreement masking
print("\n--- Disagreement Masking ---")
mask_result = compute_disagreement_masks(reg)

for i, name in enumerate(reg.names):
    save_image(DEBUG_DIR / f"clean_mask_{name}", mask_result.clean_masks[i])

# Save contributor count heatmap
count_vis = (mask_result.contributor_count.astype(np.float32) / max(1, mask_result.contributor_count.max()) * 255).astype(np.uint8)
count_vis = cv2.applyColorMap(count_vis, cv2.COLORMAP_VIRIDIS)
save_image(DEBUG_DIR / "contributor_count.png", count_vis)

# Save consensus map
consensus_vis = (mask_result.consensus_map.astype(np.uint8)) * 255
save_image(DEBUG_DIR / "consensus_map.png", consensus_vis)

# Stats
total_overlap = (mask_result.contributor_count >= 2).sum()
consensus_pixels = mask_result.consensus_map.sum()
print(f"Overlap pixels: {total_overlap:,}")
print(f"Consensus pixels: {consensus_pixels:,} ({100*consensus_pixels/max(1,total_overlap):.1f}% of overlap)")
for i, name in enumerate(reg.names):
    clean = (mask_result.clean_masks[i] > 0).sum()
    valid = (reg.warped_masks[i] > 0).sum()
    print(f"  {name}: {clean:,}/{valid:,} pixels clean ({100*clean/max(1,valid):.1f}%)")

print(f"\nAll debug artifacts saved to {DEBUG_DIR}/")
