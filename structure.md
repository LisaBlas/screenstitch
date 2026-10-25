# ScreenStitch — Project Structure

## What it does
Stitches overlapping gameplay screenshots into a seamless, HUD-free panorama using only real pixels (no AI inpainting). Python + OpenCV.

## Stack
Python 3.10+, OpenCV, NumPy, Pillow. Entry: `python -m screenstitch` or `screenstitch` CLI.

## Current status
Phase 1 (Core Pipeline). All 4 pipeline stages + CLI done. Fixtures/evaluation remaining.

## Tree
```
screenstitch/              # Package root
  __init__.py              # version only
  cli.py                   # CLI: full pipeline with --debug-dir, tunables, fallback
  __main__.py              # `python -m screenstitch` support
  utils.py                 # load_image, load_images, save_image, to_gray
  pipeline/
    __init__.py            # Re-exports: register, register_fallback, compute_disagreement_masks
    register.py            # Stage 1: ORB→BFMatcher→homography→warp to shared canvas
    mask.py                # Stage 2: Median-based disagreement masking (HUD detection)
    reconstruct.py         # Stage 3: median composite of clean pixels → ReconstructionResult
    blend.py               # Stage 4: multi-band Laplacian pyramid blending + optional Poisson

test_registration.py       # Synthetic scene → registration visual test
test_stitch.py             # Runs registration + naive composite on all test sets
test_hades.py              # Smoke test: registration + masking on hades screenshots
test_winter_burrow.py      # Smoke test: registration + masking on winter_burrow screenshots
tests/                     # Formal test dir (empty, fixtures/ has no files yet)

test_screenshots/          # Input pairs: {hades,winter_burrow}_{left,right}.png
test_output/               # Composites + debug artifacts from test_stitch.py
debug/                     # Debug artifacts from individual test scripts

build-plan.md              # Full 5-phase roadmap with task checkboxes
pyproject.toml             # Package config, deps: opencv-python, numpy, Pillow
```

## Pipeline flow
```
Images → register() → RegistrationResult → compute_disagreement_masks() → MaskResult → reconstruct() → blend() → output
```

### register() → RegistrationResult
- ORB features (3000/image) → BFMatcher + Lowe's ratio test → RANSAC homography
- Chains pairwise: img[i]→img[i-1]→...→img[0] coordinate space
- Warps all onto shared canvas, returns warped images + valid-pixel masks
- Fallback: `cv2.Stitcher_create(SCANS)`
- Key constants: `MATCH_RATIO_THRESH=0.75`, `MIN_MATCH_COUNT=10`, `RANSAC_REPROJ_THRESH=5.0`

### compute_disagreement_masks(reg) → MaskResult
- Stacks warped images, computes per-pixel median across valid contributors
- Flags pixels where `|pixel - median| > threshold` (per-channel) as HUD/transient
- Consensus requires ≥2 contributors + `inlier_fraction` agreement
- Single-contributor pixels kept as-is (no disagreement data)
- Morphological close+open cleanup
- Key defaults: `threshold=30.0`, `inlier_fraction=0.5`, `morph_kernel=5`

### reconstruct(reg, mask) → ReconstructionResult
- Stacks warped images, applies clean masks from disagreement stage
- Median composite across clean contributors (masked array, same pattern as masking stage)
- Single-contributor pixels pass through directly; zero-contributor pixels = gap (black, coverage_mask=0)
- Logs coverage % and gap % for diagnostics
- Key dataclass: `ReconstructionResult` with `canvas` (uint8 BGR) and `coverage_mask` (uint8)

### blend(reg, mask, recon) → BlendResult
- Distance-transform weights per clean mask (pixels further from edge → higher weight)
- Normalize weights to sum to 1, build Gaussian pyramids for weights
- Laplacian pyramids for each warped image, weighted blend at each frequency band
- Collapse blended pyramid → final canvas
- Optional `use_poisson=True` for seamlessClone refinement at seam zones
- Key defaults: `num_bands=5` (auto-clamped to image size)
- Key dataclass: `BlendResult` with `canvas` (uint8 BGR) and `coverage_mask` (uint8)

## Key dataclasses
- **RegistrationResult**: `warped_images`, `warped_masks`, `canvas_size`, `homographies`, `names`, `match_counts`
- **MaskResult**: `clean_masks` (per-image), `consensus_map`, `contributor_count`
- **ReconstructionResult**: `canvas` (uint8 BGR composite), `coverage_mask` (uint8, 255=covered, 0=gap)
- **BlendResult**: `canvas` (uint8 BGR blended), `coverage_mask` (uint8, 255=covered, 0=gap)

## Next steps
1. Build test fixtures suite (1.6)
2. Phase 2: FastAPI backend
