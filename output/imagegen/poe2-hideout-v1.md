# PoE2 hideout composite — first experiment

Generated with the built-in image_gen tool from the two screenshots in `poe2/`.

## Reproduction

The [run manifest](poe2-hideout-v1.json) preserves the exact prompt, ordered input paths, tool settings and SHA-256 checksums. See [the workflow](../../docs/WORKFLOW.md) for the procedure.

## Review

The user accepted this result as successful.

Visual inspection: one continuous scene with the shared banana stall, portal, statue and dock; HUD removed. Some paving and decoration details are changed. This is a generated composite, not a verified geometrically accurate stitch. No automated fidelity measurement was run.

## Prompt

Use case: compositing. Create one faithful continuous panorama by stitching these two screenshots of the SAME Path of Exile 2 hideout. This is a spatial reconstruction test, not a redesign or inspired artwork. Input 1 shows the northeastern area: market stalls at left, glowing blue-purple stone portal and red seated statue above it, shoreline rocks and wooden dock to right. Input 2 shows the southwestern extension: woodworking workbench and stacked crates at left-center, hanging rugs, same banana market stall toward upper center, same portal at upper right, foreground plants and ornamental arches lower right. Align the SAME banana stall, adjacent red stone paving, barrel, portal and shoreline rocks across both images; each shared structure must appear exactly ONCE. Extend input 2 toward upper right with the unique scene content of input 1. Preserve original isometric game rendering, exact architecture and relative spatial relationships, decorations, textures, sunlight and scale as faithfully as possible. Show the union of visible areas in a single coherent wide landscape image, no panels, no split screen, no seam. Remove all game HUD including minimap, health/mana globes, skill bars, status icons, overhead health bars, cursor, text and Windows activation overlay. Remove the moving player and their purple selection ring to avoid duplicate player positions; keep stationary NPCs only once in their correct locations. Do not add buildings, move stalls, multiply portals or invent decorative details. Use reference scene content for occluded regions wherever available, minimal plausible fill only for small uncovered holes. Highest fidelity to provided screenshots, crisp detailed game screenshot appearance. Output only the composed image.
