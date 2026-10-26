# ScreenStitch — Project Context

## Purpose

Combine overlapping gameplay screenshots into a continuous, HUD-free panorama using the built-in image-generation tool. The user accepted the first PoE2 hideout result and selected this direct method for further work.

## Current workflow

- Read `docs/WORKFLOW.md` before generating a composite.
- Inspect all source images before prompting. Identify shared landmarks and describe the spatial relationship between the views.
- Use the imagegen skill and built-in image tool. No local Python pipeline, application server or dependencies are required.
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
- `docs/RECENT_CHANGES.md`: recent repository changes.

## Conventions

- Preserve source screenshots and accepted outputs. Save iterations under new versioned filenames.
- Save each result with its exact prompt, ordered input paths, tool settings and review.
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
