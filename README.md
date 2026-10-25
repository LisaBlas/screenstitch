# ScreenStitch

Combine overlapping game screenshots into one clean panorama with an image model.

The first accepted example combines two Path of Exile 2 hideout screenshots. The model removes the HUD and moving player, joins shared landmarks, and fills small gaps. It can change scene details; the result is not a pixel-exact reconstruction.

![PoE2 hideout composite](output/imagegen/poe2-hideout-v1.png)

## Repeat the method

Follow [docs/WORKFLOW.md](docs/WORKFLOW.md). No local application or Python dependencies are required for the current built-in image-tool workflow.

- [Source screenshots](poe2/)
- [Successful prompt and review](output/imagegen/poe2-hideout-v1.md)
- [Exact run arguments and checksums](output/imagegen/poe2-hideout-v1.json)

## Repository layout

- `poe2/`: original screenshots; preserve these files.
- `output/imagegen/`: saved results and their reproduction records.
- `docs/`: workflow and recent changes.
- `AGENTS.md`: instructions for future agents; `CLAUDE.md` links to it.

The former OpenCV pipeline, tests, sample screenshots and roadmap were removed after the successful image-model experiment. They remain available in Git history at commit `82b38a6`.
