# Plan — systematic, numbers-based fitting of Prince

**Current step:** classifying the anchor photo part by part, see
`docs/STRAND_PLAN.md`. This file is the overall pipeline that follows it.

## Core idea
Turn "make it look like him" into an optimization problem with an objective
score. Prince is described by ~30 numbers (a parametric model). For every
reference photo we know (or solve for) the camera. We render the model from
each camera, compare to the photo numerically, and let an optimizer adjust the
numbers. `check.py` decides when it's done.

Claude builds the machine; the machine runs unattended. No LLM judgment is in
the unattended loop.

## Components

| File | Job |
|---|---|
| `prince/model.py` | Parameters → signed distance field (SDF) of Prince; parameter bounds; 3D landmark positions; mesh export (marching cubes → OBJ/GLB). |
| `prince/camera.py` | Orbit camera: yaw, pitch, roll, distance, field of view, image-center offset. Projects 3D points, generates rays. |
| `prince/render.py` | Sphere-traces the SDF → soft silhouette image (smooth, so the optimizer gets a useful signal). |
| `prince/score.py` | Silhouette IoU (hard and soft) and landmark pixel error per view, plus plausibility penalties. **Grader code — human-owned.** |
| `optimize.py` | Unattended fitting loop with checkpoints. Optionally also refines non-anchor cameras. Writes `out/`. Notifies when done. |
| `check.py` | Loads the latest fit, prints per-view scores vs thresholds, exits 0 on pass / 1 on fail. **Human-owned.** |
| `report.py` | `out/report.html`: each photo beside the matching render with the overlay and scores. |
| `tools/make_synthetic.py` | Builds a fake "Prince" with known parameters + cameras, to test the whole pipeline end to end without real photos. |
| `tools/landmark_tool.py` | (Phase 2b) Click landmarks on photos → `data/landmarks.json`. |
| `tools/make_masks.py` | (Phase 2b) Produce silhouette masks from photos for *measurement only*. |

## Coordinate conventions
- Units: model units ≈ centimeters (absolute scale doesn't matter for fitting).
- x forward (toward nose), y to Prince's left, z up. Ground plane z = 0.
- Camera yaw 0° = looking at Prince's face from straight in front. Yaw 90° =
  viewing his left side. Pitch positive = camera above, looking down.

## Data layout (`data/` is human-owned)
- `data/photos/<name>.jpg` — reference photos (same pose only).
- `data/masks/<name>.png` — white = Prince, black = background.
- `data/landmarks.json` — `{photo_name: {landmark_name: [x_px, y_px], ...}}`.
  Landmark names: `eye_l, eye_r, nose, ear_tip_l, ear_tip_r, ear_base_l,
  ear_base_r, tail, foot_fl, foot_fr` (any subset per photo; only mark
  visible ones). l/r = Prince's left/right.
- `data/cameras.json` — initial camera guess per photo (yaw/pitch at minimum).
  The optimizer may refine non-anchor cameras within bounds.

## Scoring
Per view: hard IoU of silhouettes, and mean landmark error as a fraction of
image diagonal. Total loss = Σ_view weight × [(1 − softIoU) + λ·landmark_err]
+ plausibility penalties (ears smaller than head, feet mostly under body,
parameters inside bounds). Anchor view weight is highest.
Pass criteria live in `config/thresholds.json`.

## Phases & tasks

### Phase 1 — owner, as needed
- [x] Anchor photo: `data/photos/anchor_front.webp`.
- [ ] Owner adds other angles as they're needed (not all at once).
- [ ] Rough angle for each chosen photo (front / left / 3-4 left / top...).
- [ ] Click landmarks (with the landmark tool, once built).
- [ ] Approve masks.
- [ ] Approve thresholds.

### Phase 2 — Claude builds the pipeline (small sessions)
- [x] Docs: CLAUDE.md, PLAN, SPEC, PROGRESS.
- [~] `prince/model.py` + tests — **unreviewed draft exists, no tests** (see PROGRESS 2026-11-05 session 2)
- [~] `prince/camera.py` + `prince/render.py` + tests — **unreviewed draft exists, no tests**
- [ ] `prince/score.py` + tests
- [ ] Synthetic end-to-end test: recover known parameters from synthetic views.
- [ ] `optimize.py` with checkpoints, `check.py`, `report.py`
- [ ] Permission rules protecting the grader (`.claude/settings.json`)
- [ ] 2a: **part-by-part classification of the anchor photo** (`docs/STRAND_PLAN.md`) — CURRENT
- [ ] 2b: landmark tool, camera-guess file; soft measurement masks rendered from the classified parts
- [ ] 2c: whisker/wisp 3D strand builder + 1-px projection test

### Phase 3 — unattended run on real photos
- [ ] `python optimize.py` → `python check.py` → `python report.py`

### Phase 4 — only if stuck
- Bounded Claude session: read report, propose ONE structural model change,
  run tests + check, keep only if scores improve.

### Phase 5 — later
- Texture from photos, optional fur, rig for the Little Self.

## Layers (owner's decision, 2026-11-07)
Prince is built in separate layers so no layer can distort another:
1. **Body shape**: head + undercarriage + ears + peets, parametric, fitted to
   the classified parts (whiskers ignored, wisps excluded). Parts must sum to
   the measured outline; see PRINCE_SPEC "Parts" and STRAND_PLAN.
2. **Fur**: strand hair groomed per part (head: shorter/smoother;
   undercarriage: longer/fluffier). The groom must not push the outline outside
   what the body layer fitted, except where the photo shows fuzz.
3. **Whiskers & wisps**: reproduced *exactly* from the photo, added last.

### How the whisker & wisp layer is made exact
- Separating whiskers and wisps from the body: done strand by strand as
  sub-pixel curves per `docs/STRAND_PLAN.md`. (Automatic separation was tried
  three times and failed; see DECISIONS.md "Lessons".)
- Build each as a 3D curve rooted on the model's cheek/brow, with depth chosen
  so its projection through the **anchor camera lands on the traced pixels**.
  From the anchor view, they are then identical by construction.
- Test: projected strand vs traced centerline within ~1 px for every strand.
  Fails = not done.
- The traced strands are **frozen data** (`data/whiskers/`, human-owned). The
  optimizer never generates, moves, or "improves" them.
- Caveats: depth is only pinned down from the anchor view; other photos refine
  it if they show the whiskers. Whiskers lying over the fur inside the outline
  need separate careful tracing.

## Build checklist: things that must not be forgotten when he's built
Owner: some layers are soft or partly hidden and must still be rendered.
- **Intermediate fur** around his body (`data/strands/intermediate_fur.json`).
- **The tuft's fuzz**, the see-through haze of hair tips below the underfluff
  tuft's spikes (`data/strands/tuft_fuzz.json`), as soft semi-transparent tips
  whose opacity follows the photo's fur coverage.
- **Parts continue under what covers them** (METHOD §3b): the cream peet under
  the tuft's fur, ears and eyes under lashes and whiskers. Build the whole part,
  then lay the covering fur over it.
- **Whiskers, eyebrow whiskers and wisps**, each exactly as traced, added last.
- **The black hotot eye marks**, every pixel.

## Owner's goals for how this runs
- **Set it and forget it.** The owner has a real rabbit to look after and does
  not want to babysit sessions. Human input happens up front (Phase 1) and at
  the end (one report page). Everything between is scripts + the grader.
- **Long sessions are where things went wrong before.** Instructions got pushed
  far back over hours-long runs and were effectively ignored, even when kept in
  a doc. So: small, bounded sessions, and no LLM inside the unattended loop.
- **Short check-in steps alone didn't work either** (the earlier session did
  almost nothing between steps). The fix is concrete, numeric targets per
  session (e.g. "make test X pass", "raise side-view IoU from 0.88 to 0.93").

## Decisions
- **2026-11-05: Performance and quality are no object.** Owner has a strong GPU.
  - Target: from the anchor camera, a render hard to tell apart from the anchor
    photo. Fur is ~80% of the work.
  - **There is ONE Prince (decided 2026-11-07).** No separate "hero" and
    "real-time" versions. One full-quality asset: fitted shape, real strand hair
    (full strand count), photo-derived texture, glossy eyes, whiskers.
  - That same asset is used everywhere: fitting/comparison renders (Blender
    Cycles on GPU, lighting matched to the anchor photo) and the Little Self's
    live digital space (a strand-hair-capable real-time renderer, e.g. Unreal
    Engine 5 Groom; engine choice still open).
  - **Only reduce quality if it actually runs badly**, measured (e.g. frame rate
    in the live space), not assumed. Even then, propose the smallest reduction
    and let the owner decide. Do not pre-emptively build a lighter version.
  - Optimizer budget can be large: more fur parameters, more render samples,
    overnight runs are fine. Fur stage scored with perceptual image metrics
    (e.g. LPIPS/SSIM) against the anchor photo from the anchor camera, on top of
    silhouette/landmark scores.
  - Heavy rendering runs on the **owner's machine**, not in the cloud container
    (no GPU there). Pipeline scripts must be runnable locally.

## Open questions for the owner
- Anchor photo: swap in a full-res original if one exists?
- For each new angle the owner adds: its rough angle and pose.
- Pass thresholds — proposed starting point: hard IoU ≥ 0.95 every view,
  landmark error ≤ 1.5% of image diagonal, anchor weighted 3×. Owner to approve.
- How to be notified when an unattended run finishes (push / email / other).
- Owner's OS, GPU model, and Blender version (and which engine the Little Self's live space will use, e.g. Unreal).
- Whether to keep, review, or restart the unlogged draft code in `prince/`.
  Note: the draft models Prince as body + separate head + ears + feet + tail;
  it must be reworked to the owner's head/undercarriage decomposition.

## Known risks
- **Pose mismatch:** photos of a loafing vs. sitting Prince are different shapes.
  Only fit one pose at a time.
- **Camera uncertainty:** casual photos have unknown angles. Mitigation: owner
  gives rough angles, optimizer refines non-anchor cameras within ±15°. COLMAP
  is an option if available.
- **Metric gaming:** an optimizer (or Claude) can score well with something
  implausible. Mitigations: bounds, symmetry built in, plausibility penalties,
  and the human-owned grader.
