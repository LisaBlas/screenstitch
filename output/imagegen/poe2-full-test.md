# Full hideout test — 2026-10-26

Status: rejected by user on 2026-10-26. Fidelity check does not pass.

User review: the result looks like an AI recreation, loses detail, blurs NPC
faces and brightens the original colour scheme. The next experiment uses
source pixels with masks and geometric alignment; see
[experiment instructions](../../experiments/README.md).

## Result

[Latest full view, v2](poe2-full-hideout-v2.png) · [First merge, v1](poe2-full-hideout-v1.png) · [Exact run manifest](poe2-full-test.json)

All 16 source screenshots at revision `b0b0ca9` were inspected. A direct 16-image call was rejected before generation because the built-in tool accepts at most five image paths. Four overlapping five-image sections were generated, then merged with one original screenshot as waypoint detail evidence. A second merge restored the omitted retreat. All six generated images are retained, along with exact prompts, ordered inputs, checksums and actual output dimensions in the manifest.

## Sections

- [East](poe2-full-east-v1.png): market, temple, dock; source images 1, 2, 3, 4, 6.
- [North](poe2-full-north-v1.png): well, grove, market, cliff path; sources 4, 5, 6, 10, 11.
- [West](poe2-full-west-v1.png): cooking/dining, canopy corridor, hut, western pavilion; sources 7, 8, 9, 11, 12.
- [Retreat](poe2-full-retreat-v1.png): western pavilion, furnished clearing, wooded coastal path; sources 12, 13, 14, 15, 16.

Source numbers refer to the manifest's ordered `original_inputs`. These groups cover all 16 inputs.

## Visual review

- HUD and moving player are removed.
- V2 includes the furnished retreat and wooded extension that v1 omitted.
- Market, well, dining/cooking area, dock and two distinct domed complexes remain recognisable.
- Waypoint glow is still repeated across multiple archways despite the correction prompt.
- The large rectangular cloth-canopy corridor visible in the west section is missing in the final composite.
- The final coastline reads as a compact island; the full outline and altered spacing are not established by the source screenshots.
- Fine details and distances drift across generations. Combining generated sections adds another opportunity for error.
- V2 is 2072 × 759 pixels. The requested large output was not guaranteed by the built-in tool; no upscaling was performed.

## Reproduction

Follow the run order and exact arguments in `poe2-full-test.json`, resolving paths against the repository root. Inspect each input before each call. Prompts also exist as adjacent `.prompt.txt` files. Preserve all existing versions and save reruns under new names. The direct 16-image prompt is retained only as the rejected attempt, not as an executable successful recipe.

These outputs demonstrate coverage and tool limits; they do not establish a reliable full-hideout reconstruction method. The earlier suggestion to correct generated defects locally is superseded by the user's request to try source-pixel stitching.
