# PoE2 source-pixel comparison — 2026-10-26

Status: experiment completed; no output accepted as a clean panorama.

[Comparison board](poe2-v3/comparison.jpg) · [Best diagnostic preview](poe2-v3/affine-preview.jpg) · [Full affine PNG](poe2-v3/affine.png) · [Sphere preview](poe2-v3/sphere-preview.jpg)

## What was tested

Three original screenshots: 004203 (market), 004209 (well), 004217 (market
approach), in that order. UI remains enabled in the game. Screenshots are masked
before matching and compositing. No generated content, exposure adjustment,
colour blending or hole filling is used. The well screenshot has a different
source size; images retain their original dimensions.

- `poe2-v1`: broad player/follower rectangle, integer translation and two spherical projections.
- `poe2-v2`: same masks, affine rendering added; focal search gives each pair equal weight instead of pooling all point errors into one median.
- `poe2-v3`: same models as v2, tighter central player/ring mask and a small speech-overlay mask. This restores substantial scenery but does not remove peripheral followers.

All versions are retained. Each directory contains original-resolution PNGs,
checkerboard previews, masks, source maps, a report and verification results.
Checkerboard indicates missing coverage; it is not part of the transparent PNG.

## Measured result (v3)

Held-out median matching error in source pixels:

| Model | Well → market | Approach → market |
|---|---:|---:|
| Integer translation | 6.30 | 19.02 |
| Affine (scale/shear/translation) | 0.90 | 1.15 |
| Fitted sphere | 6.58 | 93.64 |
| Sphere, focal length = image width | 12.55 | 106.37 |

These errors describe only matches retained by a homography prefilter. The
filter uses all candidate matches before the train/holdout split, so the
holdout is not independent of match selection. Matches cluster mainly on rocks;
see `matches-1.jpg` and `matches-2.jpg`. Low affine error does not validate the
whole scene, tall structures or faces. The spherical fit hits the upper focal
search bound (40,944 pixels), approaching a flat projection. This is evidence
against this particular pure-rotation spherical model for this set, not a proof
that all spherical or depth-aware approaches fail.

## Visual review

- Original texture and colour appearance are retained; no AI repainting occurs.
- Affine rendering joins the central rocks, food racks and red-headdress NPC more
  coherently than translation or sphere, but stretches outer scenery.
- Hard cuts remain in rocks, palms, tree branches, stalls and paths.
- Armoured figures near the trees/stalls are duplicated or cut by seams. Their
  movement/identity has not been resolved; do not claim all companions removed.
- The central player is masked. V3 has a remaining interior hole over the market
  approach, plus incomplete outer coverage from UI masks and image boundaries.
- Tighter masks remove much of the large empty area in v1/v2. Those earlier holes
  were partly over-masking, not proof that the scene was never captured.
- NPC details are copied from sources but geometric resampling/seam cuts can
  still distort them. Nearest-neighbour affine/sphere rendering can alias.

## Verification

Dependency consistency check passed. All three end-to-end runs completed.
`experiments/verify_result.py` passed for all versions: source hashes, output
sizes, alpha/source-map consistency and coverage counts. Every covered pixel in
each integer-translation output is checked against the selected original pixel,
including exclusion masks. This verifies colour preservation in that output,
not correct scene geometry or complete UI removal. Warped outputs have structural
checks only; no full per-pixel provenance check was run for them.

## Reproduction

V1 script: `experiments/compare_projections.py` at Git commit `30ac85a`.
V2/V3 script: the revision saved with this review; its SHA-256 is in each run's
`execution.json`. Each report embeds its exact mask configuration and input
hashes. To repeat an older mask configuration, copy that report's `masks` object
to `experiments/masks.json` in an isolated checkout, then run the command in
`execution.json` with a new output directory. Do not overwrite saved results.

## Next experiment

Use spatially distributed anchors and local transforms for ground, rocks and
raised structures, with seams routed around whole NPCs. Refine player/follower
masks per image. A short slow video pass could provide intermediate views and
fill the remaining hole while the UI stays enabled; it is optional and has not
been tested here. More inputs alone will not repair incorrect global geometry.
