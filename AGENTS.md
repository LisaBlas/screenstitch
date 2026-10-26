# ScreenStitch — Project Context

## Purpose

Combine overlapping gameplay screenshots into a continuous, HUD-free panorama while preserving source detail and colours. The first generated pair was accepted, but the user rejected the later full-hideout results for lost detail, blurred faces and brighter colours. Source-pixel flat, affine and spherical experiments have run; no clean panorama is accepted yet.

## Current workflow

- Read `experiments/README.md` for the current source-pixel experiment. `docs/WORKFLOW.md` records the earlier image-generation method.
- Inspect all source images before prompting. Identify shared landmarks and describe the spatial relationship between the views.
- Test flat, affine and spherical geometry with explicit masks using `experiments/compare_projections.py`. Dependencies are pinned in `experiments/requirements.txt` and installed in `.venv` with user approval. Ask before new dependency installations.
- The user cannot hide the UI or player in-game. Mask them in the source images, recover hidden areas from overlapping views where possible, and leave uncovered areas transparent.
- Preserve scene layout and important details; remove HUD and handle moving characters explicitly.
- Generation may alter details. Do not describe results as pixel-exact or geometrically verified without evidence.

## Files

- `README.md`: overview and accepted example.
- `poe2/`: current 16-image full-hideout source set. The first two-image source set is available in Git history at `82b38a6`.
- `output/imagegen/poe2-hideout-v1.png`: accepted first result.
- `output/imagegen/poe2-hideout-v1.md`: exact prompt and review.
- `output/imagegen/poe2-hideout-v1.json`: tool arguments, input order and checksums.
- `output/imagegen/poe2-full-test.md`: full-hideout experiment review; adjacent JSON records all six successful calls.
- `docs/WORKFLOW.md`: repeatable procedure and review criteria.
- `experiments/`: source-pixel comparison, mask configuration, integrity verification and reproduction instructions.
- `output/geometry/REVIEW.md`: three-image test results and limitations. Affine fits sampled landmarks best but distorts outer scenery; sphere does not solve the tested overlaps. Original-resolution PNGs, previews, masks, source maps and reports are retained in versioned directories.
- `output/geometry/LOCAL_REVIEW.md`: local-mesh and graph-cut seam trials. Flexible warps bend scenery; limited-stretch warps leave larger misalignments. Neither is a clear overall improvement. `experiments/local_stitch.py` implements the test, with exact final source-pixel verification and three numerical tests in `experiments/test_local_stitch.py`.
- `docs/RECENT_CHANGES.md`: recent repository changes.

## Conventions

- Preserve source screenshots and accepted outputs. Save iterations under new versioned filenames.
- Save each result with ordered input paths, checksums, settings, transforms or exact prompt, and review.
- Copy project outputs from the tool's generated-image directory into this repository.
- Tool-selected models and nondeterministic generation prevent a promise of identical reruns.
- The old OpenCV implementation and sample tests are recoverable from Git history at `82b38a6`; they are no longer the active method.
- `AGENTS.md` is canonical. `CLAUDE.md` must remain a relative symlink to it.

## Deploy facts

- Remote: `git@github.com:LisaBlas/screenstitch.git` (SSH).
- Push policy: push only when explicitly requested by the user.
- Deploy command: not established.
- Restart command: not established.
- Preview URL: not established.
