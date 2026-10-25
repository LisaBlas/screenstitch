"""CLI entry point — run the full stitching pipeline on a folder of images."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from screenstitch.utils import load_images, save_image

log = logging.getLogger("screenstitch")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="screenstitch",
        description="Stitch overlapping gameplay screenshots into a seamless, HUD-free panorama.",
    )
    p.add_argument(
        "input",
        type=Path,
        help="Folder containing overlapping screenshots",
    )
    p.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("output.png"),
        help="Output path for the final panorama (default: output.png)",
    )
    p.add_argument(
        "--debug-dir",
        type=Path,
        default=None,
        help="Save intermediate artifacts (keypoints, warps, masks, seams) to this directory",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=30.0,
        help="Disagreement threshold — per-channel diff from median to flag as HUD (default: 30)",
    )
    p.add_argument(
        "--inlier-fraction",
        type=float,
        default=0.5,
        help="Min fraction of contributors that must agree for consensus (default: 0.5)",
    )
    p.add_argument(
        "--num-bands",
        type=int,
        default=5,
        help="Laplacian pyramid levels for multi-band blending (default: 5)",
    )
    p.add_argument(
        "--poisson",
        action="store_true",
        help="Enable Poisson blending refinement for stubborn seams",
    )
    p.add_argument(
        "--no-blend",
        action="store_true",
        help="Skip blending — output the median reconstruction only",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )
    return p


def _save_debug(debug_dir: Path, reg, mask_result, recon, blend_result):
    """Save intermediate artifacts when --debug-dir is specified."""
    debug_dir.mkdir(parents=True, exist_ok=True)

    # Warped images + valid masks
    for i, (img, vmask, name) in enumerate(
        zip(reg.warped_images, reg.warped_masks, reg.names)
    ):
        save_image(debug_dir / f"warped_{i}_{name}", img)
        save_image(debug_dir / f"valid_mask_{i}_{name}", vmask)

    # Clean masks from disagreement stage
    for i, (cmask, name) in enumerate(zip(mask_result.clean_masks, reg.names)):
        save_image(debug_dir / f"clean_mask_{i}_{name}", cmask)

    # Consensus + contributor count
    import numpy as np
    consensus_vis = (mask_result.consensus_map.astype(np.uint8) * 255)
    save_image(debug_dir / "consensus_map.png", consensus_vis)

    count_max = max(mask_result.contributor_count.max(), 1)
    count_vis = (mask_result.contributor_count.astype(np.float32) / count_max * 255).astype(np.uint8)
    save_image(debug_dir / "contributor_count.png", count_vis)

    # Reconstruction (median composite)
    save_image(debug_dir / "reconstruction.png", recon.canvas)
    save_image(debug_dir / "coverage_mask.png", recon.coverage_mask)

    # Blended result (if available)
    if blend_result is not None:
        save_image(debug_dir / "blended.png", blend_result.canvas)

    log.info("Debug artifacts saved to %s", debug_dir)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(name)s | %(message)s",
    )

    # --- Load images ---
    log.info("Loading images from %s", args.input)
    try:
        pairs = load_images(args.input)
    except (FileNotFoundError, NotADirectoryError) as e:
        log.error("%s", e)
        return 1

    names = [name for name, _ in pairs]
    images = [img for _, img in pairs]
    log.info("Loaded %d images: %s", len(images), ", ".join(names))

    if len(images) < 2:
        log.error("Need at least 2 images, got %d", len(images))
        return 1

    # --- Import pipeline stages (deferred to keep --help fast) ---
    from screenstitch.pipeline.register import register, register_fallback, RegistrationError
    from screenstitch.pipeline.mask import compute_disagreement_masks
    from screenstitch.pipeline.reconstruct import reconstruct
    from screenstitch.pipeline.blend import blend

    t0 = time.perf_counter()

    # --- Stage 1: Registration ---
    log.info("Stage 1/4: Registration")
    try:
        reg = register(images, names)
    except RegistrationError as e:
        log.warning("Registration failed: %s", e)
        log.info("Trying fallback stitcher...")
        result = register_fallback(images)
        if result is not None:
            save_image(args.output, result)
            log.info("Fallback result saved to %s", args.output)
            return 0
        log.error("Fallback stitcher also failed. Cannot stitch these images.")
        return 1

    log.info("Canvas: %d x %d, matches: %s", reg.canvas_size[0], reg.canvas_size[1], reg.match_counts)

    # --- Stage 2: Disagreement masking ---
    log.info("Stage 2/4: Disagreement masking")
    mask_result = compute_disagreement_masks(
        reg,
        threshold=args.threshold,
        inlier_fraction=args.inlier_fraction,
    )

    # --- Stage 3: Reconstruction ---
    log.info("Stage 3/4: Reconstruction")
    recon = reconstruct(reg, mask_result)

    # --- Stage 4: Blending ---
    blend_result = None
    if args.no_blend:
        log.info("Stage 4/4: Blending (skipped — --no-blend)")
        final = recon.canvas
    else:
        log.info("Stage 4/4: Blending")
        blend_result = blend(
            reg, mask_result, recon,
            num_bands=args.num_bands,
            use_poisson=args.poisson,
        )
        final = blend_result.canvas

    elapsed = time.perf_counter() - t0

    # --- Save output ---
    out_path = save_image(args.output, final)
    log.info("Panorama saved to %s (%.1fs)", out_path, elapsed)

    # --- Debug artifacts ---
    if args.debug_dir:
        _save_debug(args.debug_dir, reg, mask_result, recon, blend_result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
