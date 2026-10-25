# ScreenStitch — Project Context

## What This Is
A web app that stitches overlapping gameplay screenshots into a single seamless, UI-free panorama. Uses only real captured pixels — no AI generation/inpainting. Target audience: gamers showcasing builds (hideouts, bases, housing) on Reddit/social media or for print.

## Tech Stack
- **Language:** Python 3.10+
- **Core libs:** OpenCV (`opencv-python`), NumPy, Pillow
- **API (Phase 2):** FastAPI with background task processing
- **Frontend (Phase 3):** Vanilla HTML/JS served by FastAPI, dark-themed
- **Deployment target:** DigitalOcean VPS, Docker, Nginx + SSL

## Project Structure
```
screenstitch/
  __init__.py
  cli.py                  # CLI entry point: python -m screenstitch
  utils.py                # I/O helpers (image loading, saving, path handling)
  pipeline/
    __init__.py
    register.py           # Feature matching (ORB) + homography → warp to shared space
    mask.py               # Disagreement-based HUD/UI detection via overlap comparison
    reconstruct.py        # Composite clean (world-only) pixels into single image
    blend.py              # Multi-band / Poisson blending for seamless seams
tests/
  __init__.py
  fixtures/               # Sample screenshot sets for testing
```

## Pipeline Architecture (4 stages, sequential)
1. **Registration** — ORB feature detection → BFMatcher/FLANN → `cv2.findHomography` (RANSAC) → warp all images into shared canvas. Fallback: `cv2.Stitcher_create()`.
2. **Disagreement Masking** — For each pixel with 2+ contributors: compute median color, flag outliers (`|pixel - median| > threshold`). Outliers = HUD/cursor/particles. Clean up with morphological ops (dilate/erode). Tunables: `t` (difference threshold), `p` (inlier fraction).
3. **Reconstruction** — Composite using only unmasked (world) pixels. Where multiple clean sources overlap, use median value.
4. **Blending** — Laplacian pyramid multi-band blending for exposure matching. Feathered alpha at seam boundaries. Optional Poisson blending for stubborn seams.

## Key Design Decisions
- **ORB over SIFT/SURF** — Free, no patent issues, fast enough for this use case.
- **Disagreement masking over template matching** — Game-agnostic. No need for per-game HUD templates. Works by comparing what's consistent across overlapping frames.
- **No AI inpainting** — Core promise is "only real captured pixels." Gaps from HUD removal stay as gaps unless covered by another screenshot.
- **CLI first, web second** — Prove the pipeline works before building API/UI. All value is in the stitching quality.

## Conventions
- Entry point: `python -m screenstitch ./screenshots/ -o output.png`
- Debug mode: `--debug-dir ./debug/` saves intermediates (keypoints, matches, warps, masks, seam maps)
- Pipeline functions should be independently testable — each stage takes explicit inputs and returns explicit outputs (no global state)
- Prefer NumPy array operations over Python loops for performance

## Current Phase
Phase 1: Core Pipeline (Local CLI) — see `build-plan.md` for detailed step tracking.
