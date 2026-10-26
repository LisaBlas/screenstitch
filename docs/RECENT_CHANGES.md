# Recent Changes

## 2026-10-25

- Moved the project instructions unchanged from `CLAUDE.md` to canonical `AGENTS.md`; `CLAUDE.md` now links to `AGENTS.md`. Verified the relative symlink and byte-for-byte content preservation.

- Pulled the PoE2 source screenshots from origin/main and saved a first built-in image-generation composite plus its prompt and visual review in `output/imagegen/`. Main landmarks join coherently, but detail changes remain; geometric fidelity is unverified.

- Switched origin from HTTPS to SSH after verifying GitHub authentication as `LisaBlas`; recorded the remote and push policy in `AGENTS.md`.

- Saved a repeatable image-model workflow and the accepted PoE2 run manifest (exact prompt, input order, settings and checksums). Replaced the obsolete project instructions and added a README. Removed the legacy OpenCV package, Python project configuration, tests, old game samples and roadmap; retained the PoE2 sources and accepted output unchanged.

## 2026-10-26

- Recorded the user's rejection of the full-hideout image-generation results. Prepared a source-pixel flat/sphere comparison with conservative UI/player masks, transparent missing areas, source maps and geometry metrics. Syntax check passed; execution and visual review are pending approval to install pinned OpenCV/NumPy dependencies. See `experiments/README.md`.

- Tested all 16 full-hideout screenshots through four overlapping generated sections, a merge and a revision. Saved all six images, exact prompts, ordered inputs, checksums, actual output dimensions and visual review. Recorded the five-image tool limit and remaining omissions/geometry drift; the full result is awaiting user review, not accepted. Updated source-set references after the upstream replacement of the earlier two screenshots.
