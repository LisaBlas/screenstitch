# Screenshot compositing workflow

## Proven example

The user accepted `output/imagegen/poe2-hideout-v1.png`. Its JSON manifest preserves the exact tool arguments and input order. This proves a useful visual result for this pair, not reliable accuracy across all games or camera angles.

## Repeat the saved run

1. Read `output/imagegen/poe2-hideout-v1.json`. Verify its SHA-256 values if the source files may have changed.
2. Inspect both source screenshots with `view_image`, in the recorded order.
3. Use the built-in `image_gen.imagegen` tool. Resolve the manifest's relative input paths to absolute paths. Pass its `prompt`, `referenced_image_paths`, and `transparent_background: false` unchanged. Do not also pass `num_last_images_to_include`.
4. Save the result as a new version, such as `output/imagegen/poe2-hideout-v2.png`. Copy the tool's output into the repository; preserve the original inputs and accepted v1 result.
5. Save the exact prompt, ordered inputs, settings, checksums and review alongside the new result. Do not claim a specific underlying model or seed unless the tool exposes it.

The built-in tool needs no API key setup. If it is unavailable, stop and explain the limitation; use an API/CLI fallback only with user authorization. There is currently no standalone batch program.

## Apply to another screenshot set

Inspect every image before writing the prompt. Identify the overlap using stable landmarks: buildings, stalls, stairs, rocks and paths. Moving characters, effects and HUD elements are poor anchors.

Describe what each numbered image contributes and where it belongs relative to the others. Name shared landmarks and require each to appear only once. Ask for one continuous view that includes the visible areas from all sources.

Preserve layout, object placement, scale, textures and game rendering. Explicitly list the HUD elements to remove. For the accepted PoE2 run, the moving player and selection ring were removed, while stationary NPCs were retained once. Adapt that choice to the requested result.

Prefer observed source content for hidden regions. Limit invented content to small uncovered gaps. Avoid arbitrary new structures or decoration. The exact PoE2 prompt is the starting example, not a generic description to reuse unchanged for other scenes.

## Review each result

- Shared landmarks appear once and connect in the correct order.
- Unique areas from each source are present.
- Paths, doors, stairs and room connections keep their original relationships.
- Important objects have not moved, vanished or multiplied.
- HUD, text overlays and unwanted moving characters are gone.
- Seams, scale, lighting and textures are visually consistent.

Record visible errors and obtain user feedback before calling an output accepted. A plausible image can still contain incorrect geometry. If an iteration is needed, change one clear instruction and save a new version.

## Reproduction limits

Generation is nondeterministic. The saved inputs, prompt and settings reproduce the procedure, not identical output pixels. The first run used a tool-selected model whose exact version was not exposed. No geometric accuracy benchmark or automated fidelity test has been run.

## Larger screenshot sets

The built-in tool rejected a call with 16 `referenced_image_paths` on 2026-10-26: at most five paths are accepted per call. The [full-hideout experiment](../output/imagegen/poe2-full-test.md) used four overlapping sections followed by a merge and revision. This produced a broad overview but omitted a canopy corridor and retained repeated waypoint effects. Treat this as an experimental workaround, not a validated fidelity-preserving procedure. Save intermediate sections because they reveal details lost during merging. Requested output dimensions in prompt text are not guaranteed.
