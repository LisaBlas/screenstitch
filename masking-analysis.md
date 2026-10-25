# Masking Stage — Failure Analysis

> **Date:** 2026-02-16
> **Test data:** `test_output/hades_debug/` (2 Hades screenshots, 2560×1440)
> **Pipeline version:** 0.1.0 (Phase 1 complete)

---

## 1. Observed Symptoms

| Symptom | Severity |
|---|---|
| Massive black holes in the blended output — world geometry deleted | **Critical** |
| HUD elements (health/mana bars, resource counters) survive into final output | **High** |
| HUD-less world areas (center of scene) incorrectly masked | **Critical** |
| Both clean masks are nearly identical (both images lose the same pixels) | Diagnostic clue |

## 2. Quantitative Evidence

Pixel difference statistics in the overlap zone (2 warped Hades screenshots):

```
Canvas:              2560 × 1440
Overlap zone:        3,682,401 px (99.9% of canvas)
Single-contributor:  0 px

Per-pixel max-channel diff (overlap zone):
  P50:  35        ← median pixel differs by 35/255
  P75:  64
  P90:  122
  P95:  188
  Mean: 51.5

% of overlap pixels exceeding threshold:
  t=30:  54.3%    ← CURRENT DEFAULT → masks over half the scene
  t=60:  27.3%
  t=100: 12.6%
```

**Key number:** At the default threshold of 30, **54.3% of all overlap pixels are flagged as outliers.** These are overwhelmingly world pixels, not HUD.

## 3. Root Cause Analysis

### 3.1 The Overlap Paradox

These two screenshots have **99.9% overlap with 0 single-contributor pixels.** The camera barely moved between captures. This creates the worst case for disagreement masking:

- **HUD is in screen-space** → after warping to world-space, HUD from both images lands at nearly the same canvas position (because the homography shift is tiny). HUD pixels are identical across frames → **pass consensus → survive.**
- **World has sub-pixel variation** → even though the homography aligns features globally, local pixel values differ due to interpolation, compression, and micro-exposure shifts → **fail consensus → masked.**

The masking logic is **working backwards**: keeping HUD and removing world.

### 3.2 The N=2 Median Problem

With only 2 contributors, `median(a, b) = (a + b) / 2`. Both images are equidistant from the median:

```
|a - median| = |a - (a+b)/2| = |a - b| / 2
|b - median| = |b - (a+b)/2| = |a - b| / 2
```

So either **both pass or both fail.** There is no scenario where one image is "inlier" and the other is "outlier" — which is exactly what we'd need to detect "this pixel is HUD in image A but world in image B."

The disagreement approach was designed assuming the median would represent the "true" world value and outliers would be HUD. **With N=2, this collapses.**

### 3.3 Why Pixel Diffs Are So Large

Even with near-perfect registration, several factors produce large per-pixel differences between warped images:

1. **Warping interpolation** — `cv2.warpPerspective` with `INTER_LINEAR` interpolates sub-pixel positions, smearing values differently per image.
2. **JPEG/PNG compression artifacts** — lossy encoding in the original screenshots introduces unique noise per frame.
3. **Game rendering variation** — Hades uses real-time rendering with dynamic lighting, particle effects, and animated elements (water, fire, foliage sway). Two frames captured even milliseconds apart can differ substantially.
4. **Hades' art style** — high-contrast, hand-painted textures with lots of fine detail. A 1-pixel shift in a dark textured area can produce a diff of 100+.
5. **Homography imprecision** — ORB features matched with RANSAC produce a global best-fit. Local deviations (especially in non-planar 2.5D isometric scenes) cause misalignment in areas far from matched keypoints.

### 3.4 Why the HUD Survives

The health bar, mana bar, resource counters, and "Activer Windows" watermark all:
- Exist in screen-space at fixed positions in both frames
- Map to nearly the same canvas position after warping (because the camera shift is tiny)
- Are pixel-identical across frames → per-channel diff ≈ 0 → pass consensus easily

The current algorithm interprets this as "world agreement." It has no concept of screen-space vs. world-space.

## 4. Flawed Assumptions in Current Design

| Assumption | Reality |
|---|---|
| HUD pixels will be outliers in world-space | HUD is consistent in screen-space; with small camera shifts, it lands in similar world-space positions and passes consensus |
| World pixels will agree after registration | Sub-pixel registration errors, interpolation, and rendering variation produce diffs of 30–100+ across the scene |
| N≥2 is sufficient for median-based consensus | N=2 makes median = mean; both images are symmetric around it, so outlier detection can't distinguish them |
| Per-channel L1 threshold is a good metric | Sensitive to noise, doesn't account for perceptual similarity. Dark textured areas produce huge L1 diffs from tiny spatial shifts |

## 5. Proposed Fix Directions

### 5A. Screen-Space HUD Detection (Pre-Warp) — **Recommended Primary**

Compare raw (un-warped) screenshots in screen-space. Find the camera translation between frames (a simple 2D shift, estimable from registration homographies). After compensating for the shift, pixels that remain identical are screen-fixed elements (HUD). Pixels that changed are world content that moved with the camera.

**Why this works:** It inverts the comparison coordinate space. In screen-space, HUD is the invariant and world is the variant — exactly what we want to mask.

**Steps:**
1. Estimate the screen-space camera shift from the homography (extract translation component).
2. Shift image B to align with image A in screen-space (reverse the camera pan).
3. Where shifted-B ≈ A (small diff), pixels are likely screen-fixed → mark as HUD.
4. Apply HUD mask to each raw image before warping.
5. Proceed with warping and reconstruction using pre-masked images.

### 5B. Relaxed World-Space Disagreement — **Supplementary**

Keep the current disagreement logic but with drastically different parameters as a secondary cleanup:
- Raise threshold to 80–120 (only catch gross mismatches like HUD over different world content)
- Use perceptual color space (LAB deltaE) instead of per-channel L1
- Lower `inlier_fraction` to 0.3 (more lenient consensus)

This would catch HUD in areas where it overlaps different world content (large camera shifts), which screen-space detection might miss.

### 5C. Fixed-Margin Screen-Space Mask — **Fallback**

As a simpler fallback: mask known HUD regions in screen-space using fixed margins (top/bottom 10%, left/right 5%). Game-specific but catches the most common HUD placements. Can be user-configurable.

## 6. Recommended Implementation Order

1. **5A** — Screen-space HUD detection as the new primary masking strategy
2. **5B** — Relax existing disagreement masking as a supplementary pass
3. **5C** — Optional user-configurable margin masks for stubborn HUD

## 7. Impact on Downstream Stages

- **Reconstruction (Stage 3):** No changes needed — it consumes `clean_masks` the same way regardless of how they're produced.
- **Blending (Stage 4):** Will benefit from more pixels being available; distance-weight feathering should work better with larger clean regions.
- **CLI:** New parameters needed for screen-space mask threshold + optional margin sizes.
