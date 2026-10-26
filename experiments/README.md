# Source-pixel stitching experiment

This replaces image generation for the next fidelity test. The user cannot hide
PoE2's UI or player. Fixed UI regions and a conservative central player/follower
region are excluded before feature matching and compositing. Missing coverage
stays transparent. Existing generated outputs and sources are preserved.

## Status

Executed on 2026-10-26 after dependency approval. Three runs and integrity checks
passed. Visual quality does not pass: affine is the best diagnostic, but seams,
duplicated figures and holes remain. See [review and comparison](../output/geometry/REVIEW.md).
V3 uses a tighter player/ring mask; peripheral followers are not fully masked.

## Run

The pinned dependencies are installed in `.venv` with user approval. To recreate
the environment, obtain installation approval as required by local policy:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r experiments/requirements.txt
.venv/bin/python experiments/compare_projections.py --output output/geometry/poe2-v4
.venv/bin/python experiments/verify_result.py output/geometry/poe2-v4
```

Choose a new output directory for each run; the script refuses to overwrite one.
Sources default to indices 3, 4, 5 in sorted filename order (market, well, market approach).
Use `--indices` to select another group with overlap against the first image.

Dependencies are established releases, not new releases:
[OpenCV 4.11.0.86 (2025-01-16)](https://pypi.org/project/opencv-python-headless/4.11.0.86/),
[NumPy 2.2.6 (2025-05-17)](https://pypi.org/project/numpy/2.2.6/).

## Comparison

- Flat canvas: integer translation, directly copied source pixels.
- Sphere: shared focal length selected from a bounded grid; rotations fitted
  from corresponding viewing rays. Uses nearest-neighbour sampling.
- Sphere with focal length equal to image width: a visibly curved comparison,
  to distinguish useful spherical geometry from the near-flat, long-focal limit.
- Affine fit: scale, shear and translation, rendered with nearest-neighbour sampling.

SIFT feature matches exclude masks. A robust homography filter rejects likely
mismatches. Models fit two thirds of accepted matches and report errors on the
remaining third. Focal selection minimizes the mean of the per-pair training
median errors. This prefilter uses all matches and favours the dominant plane;
it is not an independent geometry benchmark and does not establish alignment of
roofs, NPCs or vegetation. Review those separately at original resolution.

The spherical model assumes rotation about a fixed camera centre. This is a test
of that hypothesis, not a calibrated camera reconstruction. A best focal length
at the grid boundary is a warning against interpreting the fit as calibration.

The compositor selects one source per output pixel, favouring distance from
masked areas and image borders. It does not blend colours, brighten images,
inpaint holes, or invent details. Hard seams and duplicated moving objects can
remain. Nearest-neighbour sphere sampling can alias detail. The source map stores
0 for holes and 1-based selected input IDs for covered pixels.

## Review before acceptance

Inspect masks for UI/player/follower leakage, then compare preview and full PNG:
shared ground landmarks, tall structures, NPCs, seam cuts, and colour fidelity.
Check the JSON report for input hashes, versions, mask definitions, transforms,
held-out errors, canvas sizes and coverage. Transparent holes are expected when
all sources hide the same area. Do not call this a clean full-hideout result.
