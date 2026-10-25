# ScreenStitch — Build Plan

## Overview

Turn overlapping gameplay screenshots into a single seamless, UI-free panorama using only real captured pixels. Python/FastAPI backend with OpenCV, lightweight frontend.

---

## Phase 1: Core Pipeline (Local CLI)

**Goal:** Prove the stitching + HUD removal pipeline works end-to-end on local files before touching any web layer.

### 1.1 — Project scaffold ✅
- [x] Python project with `pyproject.toml`
- [x] Dependencies: `opencv-python`, `numpy`, `Pillow`
- [x] Folder structure created
- [x] All module files initialized

### 1.2 — Registration (feature matching → homography) ✅
- [x] ORB feature detection (free, no patent issues unlike SIFT)
- [x] BFMatcher for descriptor matching + Lowe's ratio test
- [x] `cv2.findHomography` with RANSAC to get transform matrices
- [x] Warp all images into a shared coordinate space
- [x] **Fallback:** `cv2.Stitcher_create()` for simpler cases
- [x] **Output:** `RegistrationResult` dataclass with warped images, masks, canvas size, homographies

### 1.3 — Disagreement masking ✅
- [x] For each canvas pixel, collect all contributing warped pixels
- [x] If fewer than 2 contributors → mark as "unknown" (gap); single-contributor pixels kept as-is
- [x] Compute robust consensus:
  - Use median color across contributors as reference (masked array for correctness)
  - Mark contributor as "inlier" if `|pixel - median| < t` (per-channel)
  - If inlier fraction `>= p` → world (keep)
  - Else → HUD/cursor/particles (mask out)
- [x] Tunables: `t` (difference threshold, default 30), `p` (inlier fraction, default 0.5)
- [x] Morphological ops (close + open with elliptical kernel) to clean up mask edges
- [x] **Output:** `MaskResult` dataclass with per-image binary masks, consensus map, contributor counts

### 1.4 — Reconstruction ✅
- [x] Composite canvas using only unmasked (world) pixels
- [x] Where multiple clean sources exist for the same pixel, use median value
- [x] **Output:** `ReconstructionResult` dataclass with composite canvas + coverage mask (gaps where HUD was removed)

### 1.5 — Blending ✅
- [x] Multi-band blending (Laplacian pyramid) for exposure matching
- [x] Feathered alpha at seam boundaries (distance-transform weighting)
- [x] Optional: Poisson blending for stubborn seams (`use_poisson=True`)
- [x] **Output:** `BlendResult` dataclass with blended canvas + coverage mask

### 1.6 — Fixtures & evaluation
- Curated fixture suite in `tests/fixtures/`:
  - 2 "easy" sets (high texture, strong overlaps)
  - 2 "hard" sets (repetitive textures, low overlap, motion/particles)
  - 1 "failure" set (no overlap) to validate error paths
- Running fixtures produces: final image, intermediate artifacts, basic report (timings, inlier count, mask coverage)

### 1.7 — CLI wrapper ✅
- [x] `python -m screenstitch ./screenshots/ -o output.png`
- [x] Accepts a folder of images, runs full pipeline, saves result
- [x] `--debug-dir ./debug/` flag saves intermediate artifacts:
  - Warped images + valid masks
  - Clean masks (per-image, from disagreement stage)
  - Consensus map + contributor count heatmap
  - Reconstruction (median composite) + coverage mask
  - Blended result
- [x] Tunables exposed: `--threshold`, `--inlier-fraction`, `--num-bands`, `--poisson`, `--no-blend`
- [x] Progress logging to stdout, `-v` for debug verbosity
- [x] Fallback to `cv2.Stitcher` if custom registration fails

**Milestone:** Feed 5-10 overlapping game screenshots in, get one clean panorama out.

---

## Phase 2: FastAPI Backend

**Goal:** Expose the pipeline as an HTTP API with async processing.

### 2.1 — API scaffold
- FastAPI app with CORS enabled
- Endpoints:
  - `POST /api/stitch` — upload images (multipart), returns job ID
  - `GET /api/status/{job_id}` — poll progress
  - `GET /api/result/{job_id}` — download final image
- Temp storage: OS-agnostic via configurable base dir (env var), defaults to `tempfile.gettempdir()`

### 2.2 — Async job processing
- Background task via FastAPI `BackgroundTasks` (phase 2) or Celery/Redis (phase 3+)
- Job states: `queued → processing → done | failed`
- Store status in memory dict initially (swap to Redis later if needed)

### 2.3 — Input validation
- Max file count (e.g. 20 images)
- Max file size per image (e.g. 15 MB)
- Accepted formats: PNG, JPG, BMP
- Reject if < 2 images uploaded

### 2.4 — Output delivery
- Serve result as downloadable PNG
- Auto-cleanup: delete job files after 1 hour (background cron or TTL)

**Milestone:** `curl` or Postman can upload screenshots and download a stitched panorama.

---

## Phase 3: Frontend

**Goal:** Minimal, functional upload UI. No framework bloat.

### 3.1 — Static frontend
- Single HTML page served by FastAPI (`/static/`)
- Vanilla JS (or Alpine.js if interactivity gets complex)
- Components:
  - Drag-and-drop upload zone
  - Upload progress bar
  - Processing status indicator (polling `/api/status/`)
  - Download button when done
  - Error display

### 3.2 — UX flow
1. User drops/selects images
2. Upload starts, progress bar fills
3. "Processing..." state with stage indicators (registering → masking → blending)
4. Result preview thumbnail appears
5. Download full-res button

### 3.3 — Styling
- Clean, dark-themed (gamers are the audience)
- Mobile-friendly but desktop-first
- Minimal — the product is the output image, not the UI

**Milestone:** Full working web app — upload screenshots in browser, download panorama.

---

## Phase 4: Hardening & Polish

### 4.1 — Error handling
- Graceful failure when images don't overlap enough
- Meaningful error messages per failure mode (not enough features, no overlap, etc.)
- Fallback to partial stitch if some images fail registration

### 4.2 — Quality tuning
- Adjustable disagreement threshold (auto-calibrate based on image set)
- Handle edge cases: varying resolutions, slight exposure differences, different aspect ratios
- Test across multiple games (Path of Exile, Minecraft, Valheim, Final Fantasy XIV)

### 4.3 — Performance
- Resize images for feature matching, apply transforms at full res
- Limit memory usage for large sets (stream processing where possible)
- Add processing time estimates to status endpoint

### 4.4 — Output options
- Resolution selector (original, 2x downscale, web-optimized)
- Optional JPEG output with quality slider
- Metadata in output (source count, dimensions, processing time)

---

## Phase 5: Deployment & Revenue

### 5.1 — Deployment
- Dockerize (Python + FastAPI in single container)
- Deploy to VPS (DigitalOcean droplet — aligns with existing infra)
- Nginx reverse proxy + SSL via Let's Encrypt
- Rate limiting (IP-based, e.g. 10 stitches/hour for free tier)

### 5.2 — Monetization options
- **Free tier:** up to 5 images, watermark on output, standard resolution
- **Paid tier ($3-5/stitch or $10/mo sub):** unlimited images, no watermark, full resolution, priority processing
- Payment: Stripe Checkout (simplest integration)
- Optional: tip jar / "buy me a coffee" for early traction

### 5.3 — Growth
- Reddit posts in game-specific subs (r/pathofexile, r/valheim, r/ffxiv, r/minecraft)
- Demo gallery page showing before/after comparisons
- SEO landing page: "game screenshot panorama maker"

---

## Risk Flags

| Risk | Impact | Mitigation |
|------|--------|------------|
| ORB features fail on repetitive textures (e.g. stone walls) | Stitching breaks | Fall back to `cv2.Stitcher`, allow manual anchor points later |
| HUD disagreement threshold too aggressive/lenient | Artifacts in output | Auto-calibrate from overlap statistics, expose manual override |
| Large image sets blow memory | Server crash | Cap at 20 images, process at reduced resolution, stream compositing |
| Game-specific HUD layouts confuse masking | Inconsistent quality | The disagreement approach is game-agnostic by design — test broadly |
| Low initial traffic | No revenue | Keep hosting costs minimal (~$6/mo droplet), validate on Reddit first |

---

## Suggested Build Order

Start with **Phase 1** — the entire value proposition lives in the pipeline. If the stitching doesn't work well, nothing else matters. Get 1.2 (registration) working first since everything depends on it.

Estimated first working CLI: a few focused sessions.
Estimated MVP web app (through Phase 3): add a couple more after that.
