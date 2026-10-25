"""Quick test: run registration on test screenshots and produce a naive composite."""

import logging
import sys
from pathlib import Path

import cv2
import numpy as np

from screenstitch.utils import load_images, save_image
from screenstitch.pipeline.register import register, register_fallback, RegistrationError

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
log = logging.getLogger("test_stitch")

# ── Config ──────────────────────────────────────────────────────────────
INPUT_DIR = Path("test_screenshots")
OUTPUT_DIR = Path("test_output")
OUTPUT_DIR.mkdir(exist_ok=True)


def naive_composite(warped_images: list[np.ndarray], warped_masks: list[np.ndarray]) -> np.ndarray:
    """Average all valid pixels. No masking or blending — just overlay."""
    h, w = warped_images[0].shape[:2]
    accum = np.zeros((h, w, 3), dtype=np.float64)
    count = np.zeros((h, w), dtype=np.float64)

    for img, mask in zip(warped_images, warped_masks):
        valid = mask > 0
        accum[valid] += img[valid].astype(np.float64)
        count[valid] += 1.0

    count_safe = np.maximum(count, 1.0)
    result = (accum / count_safe[:, :, None]).astype(np.uint8)
    return result


def draw_matches_debug(img_a, img_b, name_a, name_b, output_path):
    """Save a keypoint match visualization between two images."""
    orb = cv2.ORB_create(nfeatures=3000)
    gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
    kp_a, des_a = orb.detectAndCompute(gray_a, None)
    kp_b, des_b = orb.detectAndCompute(gray_b, None)

    if des_a is None or des_b is None:
        log.warning("No descriptors found — skipping match debug")
        return

    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    raw = bf.knnMatch(des_a, des_b, k=2)
    good = [m for m, n in raw if len([m, n]) == 2 and m.distance < 0.75 * n.distance]
    good = sorted(good, key=lambda x: x.distance)[:50]  # top 50

    vis = cv2.drawMatches(img_a, kp_a, img_b, kp_b, good, None,
                          flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    save_image(output_path, vis)
    log.info("Match debug (%s↔%s): %d good matches → %s", name_a, name_b, len(good), output_path)


def run_test(prefix: str, filenames: list[str]):
    """Run registration + naive composite for a set of images with a common prefix."""
    log.info("=" * 60)
    log.info("Testing: %s", prefix)
    log.info("=" * 60)

    # Load only the matching files
    images = []
    names = []
    for fn in filenames:
        path = INPUT_DIR / fn
        img = cv2.imread(str(path))
        if img is None:
            log.error("Failed to load: %s", path)
            return
        images.append(img)
        names.append(fn)
        log.info("Loaded %s — %dx%d", fn, img.shape[1], img.shape[0])

    # Debug: match visualization
    debug_dir = OUTPUT_DIR / f"{prefix}_debug"
    debug_dir.mkdir(exist_ok=True)
    draw_matches_debug(images[0], images[1], names[0], names[1],
                       debug_dir / "matches.png")

    # Registration
    try:
        result = register(images, names)
        log.info("Registration OK — canvas %d×%d, matches: %s",
                 result.canvas_size[0], result.canvas_size[1], result.match_counts)

        # Save warped images
        for i, (w_img, w_mask, name) in enumerate(
            zip(result.warped_images, result.warped_masks, result.names)
        ):
            save_image(debug_dir / f"warped_{i}_{name}", w_img)
            save_image(debug_dir / f"mask_{i}_{name}", w_mask)

        # Naive composite
        composite = naive_composite(result.warped_images, result.warped_masks)
        out_path = save_image(OUTPUT_DIR / f"{prefix}_composite.png", composite)
        log.info("Composite saved → %s", out_path)

    except RegistrationError as e:
        log.warning("Custom registration failed: %s", e)
        log.info("Trying fallback stitcher…")
        fallback = register_fallback(images)
        if fallback is not None:
            out_path = save_image(OUTPUT_DIR / f"{prefix}_fallback.png", fallback)
            log.info("Fallback result → %s", out_path)
        else:
            log.error("Fallback also failed for %s", prefix)


def main():
    # Discover test sets by prefix
    all_files = sorted(p.name for p in INPUT_DIR.iterdir() if p.suffix.lower() == ".png")
    log.info("Found files: %s", all_files)

    # Group by prefix (everything before _left/_right)
    from collections import defaultdict
    groups = defaultdict(list)
    for fn in all_files:
        stem = Path(fn).stem
        # Try to find a grouping prefix
        for suffix in ("_left", "_right", "_1", "_2", "_3", "_a", "_b"):
            if stem.endswith(suffix):
                prefix = stem[: -len(suffix)]
                groups[prefix].append(fn)
                break
        else:
            groups[stem].append(fn)

    for prefix, fns in groups.items():
        if len(fns) >= 2:
            run_test(prefix, fns)
        else:
            log.info("Skipping %s — only %d file(s)", prefix, len(fns))


if __name__ == "__main__":
    main()
