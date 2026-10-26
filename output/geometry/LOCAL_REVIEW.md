# Local alignment trial — 2026-10-26

Status: two end-to-end runs completed. Neither is accepted as a clean panorama
or a clear overall improvement over the previous affine result.

[Side-by-side comparison](poe2-local-v2/comparison.jpg) ·
[Flexible local PNG](poe2-local-v1/local-seams.png) ·
[Limited-stretch local PNG](poe2-local-v2/local-seams.png)

## Method

Same original three screenshots and masks as `poe2-v3`. No new dependencies.
A wider SIFT search retains mutual descriptor matches; several successive
homography RANSAC clusters admit matches at different apparent scene depths.
These clusters are geometric hypotheses, not identified ground/roof/NPC layers.

A 20 × 12 inverse displacement grid fits two thirds of accepted matches, with
curvature regularization, weak pull toward the translation baseline, and robust
residual weighting. It maps each output location to an original source pixel.
No AI generation, colour adjustment or RGB blending is used.

Graph-cut seam selection runs at 35% resolution; masks are then restored to full
resolution and intersected with valid source masks. Valid pixels lost during
seam-mask resampling are recovered from the distance-based compositor. The
red-headdress NPC rectangle is forced to use the unchanged reference source.
This is one explicit manual object constraint, not automatic NPC segmentation.

V1 allows more local deformation. V2 damps the whole displacement field per
source until sampled local stretch is between 0.7 and 1.4. This bounds distortion
on a diagnostic lattice; it is not an exact mathematical guarantee everywhere.
A separate sampled determinant check rejects folds/collapse during rendering.

## Observed result

- Source colours and original texture samples remain intact. Both outputs pass
  full visible-pixel provenance checks, including exclusion masks.
- The protected NPC rectangle uses only original reference-image pixels.
- Flexible alignment joins more matched regions, but severely bends the market
  path and canopy. It is not an improvement in overall fidelity.
- Restricting stretch reduces the bending but restores large discontinuities
  near the tree, stalls and path. Split/duplicated peripheral figures remain.
- Seams do not repair incorrect geometry. Some mask-edge cuts are still straight
  because a different image is the only valid source there.
- Interior and outer transparent holes remain. These are gaps in this three-view
  masked experiment, not proof that all 16 screenshots lack coverage.
- Neither trial should replace `poe2-v3/affine.png` as an accepted result; that
  older image is also diagnostic and has unresolved distortion.

## Measurements

| Run | Well median / p90 error (px) | Approach median / p90 error (px) | Verified visible pixels |
|---|---:|---:|---:|
| Local v1 | 4.47 / 60.98 | 5.31 / 25.06 | 6,440,531 |
| Local v2 | 7.94 / 68.93 | 83.56 / 147.74 | 6,330,350 |

The local fit uses a wider set of matches than the old affine fit, so these
errors cannot be compared directly with the earlier affine scores. RANSAC
selection sees all points before the holdout split. These are diagnostic
residuals, not an independent geometry benchmark.

## Verification and reproduction

Both runs completed. `report.json` contains source checksums, masks, numerical
settings, sampled Jacobian results and exact source-pixel verification counts.
`verification.json` adds coverage/alpha checks and the NPC ownership assertion.
Saved `mesh-*.npz` files contain control nodes, accepted anchors and train masks.
Each directory retains the exact generating script and `execution.json` command.
Shared helpers come from `experiments/compare_projections.py` with their hash
recorded. Run saved snapshots with `PYTHONPATH=experiments` from the repo root,
and always use a new output directory.

Three numerical tests pass: unseen-point recovery from a smooth synthetic field
with outliers, coordinate interpolation, and reflection/stretch rejection.
The reflection test exposed that singular values alone accept mirrored fields.
The current script additionally checks positive determinant. Recomputing both
v2 grids after that fix produces identical saved grids; images were unaffected.
The bug and fix are recorded in the shared failure journal.

## Next evidence needed

Do not scale this smooth mesh to all screenshots on the strength of low matching
error. A better next diagnostic is explicit per-region correspondence and
separate treatment of depth boundaries. A short slow video pass across the same
market/well area could supply closer-spaced views to test that approach; the UI
and player can remain visible. Video is not established as a solution and does
not remove the need to handle moving figures and missing coverage.
