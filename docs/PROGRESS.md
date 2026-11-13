# Progress log

Newest entries at the bottom. Every session appends one entry: what was done,
check.py output (if applicable), and the next step.

---

## 2026-11-05 — Session 1: project setup
- Talked through what went wrong in an earlier session: the model was made by
  tracing/cutting outlines from photos instead of building it, it quietly kept
  doing that after being asked not to, and instructions got lost in very long
  sessions. This project's design (parametric model + numeric grader +
  unattended optimizer + human-owned grading) is the response to that.
- Created CLAUDE.md, docs/PLAN.md, docs/PRINCE_SPEC.md, this log.
- No real photos are in this environment yet.

## 2026-11-05 — Session 2: documentation only (owner said: build nothing yet)
- Owner confirmed the plan and asked for everything to be documented, then to
  **hold off on building** — they will give more info next session.
- Found **unlogged draft code** from an earlier session that was not recorded
  here or ticked in PLAN.md:
  - `prince/model.py` (237 lines: parameters, bounds, SDF of smooth-unioned
    ellipsoids), `prince/camera.py` (86 lines), `prince/render.py` (86 lines),
    empty `prince/__init__.py`.
  - `out/look_default.png`: renders of the **default parameters** from 6 angles
    plus silhouettes. This is a generic round rabbit shape, NOT fitted to any
    photo of Prince. Do not present it as Prince.
  - No tests exist for any of it. `config/`, `data/`, `tests/`, `tools/` are empty.
  - Status: **unreviewed**. Do not build on it until reviewed and tested; owner
    decides whether to keep it.
- Updated PLAN.md (draft status, owner's goals, open questions) and
  PRINCE_SPEC.md (owner's framing; what "immutable anchor" really means).
- Git: repo initialized, nothing committed, no remote checked.
- **Next step:** read "Open questions for the owner" in PLAN.md and go through
  them with the owner. Then Phase 1 (photos) or review of the draft code,
  as the owner chooses. Build nothing without the owner's go-ahead.

## 2026-11-07 — Session 2 (cont.): anchor photo added
- At the owner's request, added the anchor front photo they shared in chat as
  `data/photos/anchor_front.webp`. It may be a recompressed copy; a
  full-resolution original would be better if the owner has one.
- Committed all docs + draft code locally. **No git remote yet**; the work only
  exists in the cloud container until pushed somewhere.
- Owner decision: **one Prince**, full quality, used everywhere. Only reduce
  quality if it measurably runs badly, and only with the owner's OK. PLAN.md
  "Decisions" updated.
- Corrected my earlier note: the anchor photo's background is pure white and
  Prince's fur is not, so his outline separates cleanly. (Owner pointed it out;
  verified by measuring pixel values.) Owner re-shared the same photo; it
  matches the stored copy apart from tiny compression differences, so no change.

## 2026-11-07 — Session 2 (cont.): parts and whisker layer
- Owner directed: split Prince into parts (head, undercarriage, ears, paws) so
  the outline can't be accidentally distorted; whiskers & wispy hairs kept
  exactly as they are, added meticulously as a final layer.
- Measured the anchor outline with whiskers removed (width profile in
  PRINCE_SPEC). Confirmed: no neck notch; widest at mouth/chin level;
  undercarriage fur measurably fluffier than head fur.
- Proved whiskers/wisps can be separated from the body outline (scratch only,
  owner hasn't reviewed it yet).
- PLAN: added "Layers" and exact whisker method. CLAUDE.md: narrow exception to
  rule 1 for the whisker/wisp layer only; whisker data is human-owned.
- Built nothing in the repo.
- **Correction:** I reported the whisker/wisp separation as working "on the
  first try". It didn't. The owner spotted that fluff under the feet and the
  bases of the wispy hairs were missed; zoomed crops confirmed it. Spec
  corrected, better method added to PLAN, and CLAUDE.md gains rule 6: inspect
  full-res zoomed crops before claiming visual work is right.

## 2026-11-07 — Session 2 (cont.): three-class attempts failed; strand plan proposed
- Owner asked for three classes: CORE (solidly him), FLUFF (gradient),
  WISPS (strands). Tried three automatic versions (scratch only):
  v1 disk-opening, v2 opacity + ridge filter, v3 opacity core + fluff
  envelope. All three labelled the **dark tufts hanging under the
  undercarriage** as solid body. Owner caught it. Cause: rule-based methods
  read "dark and dense" as "solid".
- Owner decided: classify strand by strand, done once, done right.
- Wrote docs/STRAND_PLAN.md (PROPOSED, awaiting owner review): tiled edge,
  ledger, golden-tile calibration, per-strand annotation, self-checks, owner
  review in batches, and a rule for handling flagged mistakes.
- Nothing has started. Next: owner reviews STRAND_PLAN.md and answers its
  open questions.
- Owner pointed out that pixel-by-pixel labels make his fur edge look pixelly.
  STRAND_PLAN updated: strands and the core boundary are sub-pixel smooth curves,
  edge pixels get soft fractional ownership, and pixels only appear when
  rendering (anti-aliased). Review overlays use outlines, not flat fills.
- Owner direction: (1) between the paws, judge where "he" ends and the hanging
  tuft begins; that's an *inferred* smooth body line, reviewed by the owner.
  (2) Don't flag the natural fuzz along his whole edge (e.g. ears); the core
  boundary must be gentle and smooth, making him less jagged, not more. Only
  distinct tufts and strands are split off. STRAND_PLAN updated.
- Owner direction: every part gets its own colour and its own step (head,
  undercarriage, ears, peets, fluff, wisps, whiskers). Whiskers over the face are
  coloured precisely but otherwise treated as nonexistent (weight 0) until
  last. The peets/undercarriage boundary follows a faint gray semicircular line
  the owner sees; Claude couldn't confidently see it between the peets, so
  asked the owner to mark it.

## 2026-11-07 — Session 2 (cont.): peet line approved; moved to the repo
- **Approved:** the peets/underfluff/body line, after 5 rounds of owner feedback.
  Saved to `data/lines/peet_line.json` with control points, smoothing and how it
  was reached; picture in `docs/images/peet_line_approved.png`. Reference used:
  the anchor photo only.
- Moved the project into the public repo `nafoas/RoundModel`, on a fresh branch
  `claude/little-prince` with no history from the old branch, which is abandoned.
- Owner decided: only the anchor photo comes across; they add new angles as
  needed. Use every photo in the branch, and say which ones you used.
- Wrote `docs/DECISIONS.md` (all decisions, reasons, lessons) and `README.md`;
  rewrote `CLAUDE.md`; brought STRAND_PLAN (now AGREED, current), PLAN and
  PRINCE_SPEC in line with every decision. Repo is public: noted in CLAUDE.md.
- Still unreviewed: draft code in `prince/` and `out/look_default.png`.
- **Next step:** STRAND_PLAN step 1 (tile the edge, ledger, count strands), then
  step 2, golden tiles with the owner. Open question: review depth per batch.

## 2026-11-07 — Session 3: STRAND_PLAN step 1 (tile the edge)
- Reference used: anchor photo only.
- Wrote `tools/edge_tiles.py` + `tests/test_edge_tiles.py` (4 tests pass).
- Result: 152 tiles (108 outline + 44 extension), ledger at
  `data/strands/ledger.json` (all `todo`), overview at
  `docs/images/edge_tiles_overview.png`. Coverage: 0 of 107,874 band pixels
  uncovered. Checked at zoom on every side.
- Job size: ~40-100 distinct wisps/whiskers (automatic count is rough: 95
  pieces ≥ 8 px). Face whiskers inside the outline still need their own tiles.
- **Next step:** step 2, golden tiles with the owner (tuft between the peets,
  peet undersides, a dense side fringe, the long wisps on the right, an ear edge,
  cheek whiskers). Open question: review depth after the first batch.
- Owner decision: they review **every** tile (not a sample). Recorded in
  STRAND_PLAN step 5 and DECISIONS.
- Owner decision: **each peet is its own part, like each ear** (left peet, right
  peet, and the underfluff tuft between them are separate). Recorded in
  STRAND_PLAN, DECISIONS, CLAUDE.md. Resolves the peet-underside question.
- Step 2 started: six golden tiles picked and shown to the owner
  (`docs/images/golden_tiles.png`) with proposed classifications and three
  questions. Tiles are now viewed at 4x with context (8x was too blurry).
  Waiting on the owner's answers before writing definitions.
- **Step 2 DONE.** Owner approved all six proposals, confirmed the long dark
  hairs at cheek/mouth height are whiskers and the thin hairs at the ears are
  eyebrow whiskers, and trusted the spike-vs-wisp rule. Written as "THE GUIDE"
  in STRAND_PLAN step 2; summary in DECISIONS.
- **Next step:** step 3, annotate tiles strand by strand against the guide,
  in batches of ~20, owner reviews every tile.

## 2026-11-07 — Session 4: STRAND_PLAN step 3, part 1 (body outline)
- Reference used: anchor photo only.
- Wrote `tools/body_outline.py` + `tests/test_body_outline.py` (5 tests pass).
  One smooth closed outline through his soft edge; gentle on his sides,
  faithful at the ears and peets (three versions tried; details in STRAND_PLAN).
- Batch 1 (T001-T020) self-checked at 4x with context; sheets in
  `docs/images/batch1_outline_1.png` and `_2.png`. Ledger `outline` field =
  self-checked for those tiles.
- Review moved to chat (no local web page).
- **Next:** owner reviews batch 1; open question about the corner at each eye.
- **Owner flagged:** the bend at the eye needs to be tighter; eyes and ears are
  sensitive. **Cause:** the eye corners were in the gentle-smoothing zone (only
  the ears and peets were faithful). **Fix:** a sensitive zone over the whole top
  of his head (both ears, both eyes), fitted as tightly as possible after removing
  thin strands. **Re-checked:** both eyes and both ears at 5-6x
  (`docs/images/sensitive_eyes_ears.png`). Tried a wider strand filter (r=6):
  it made the line hook into his right eye's area, so it was undone (r=4 kept).
  Remaining: a small bump above his right eye's lashes; asked the owner.
- Batch 1 sheets regenerated with the tightened outline.
- **Owner flagged:** a tiny bit of the black eye mark was cut off; be sub-pixel
  precise, pixel by pixel; the hotot eye marks make him, him. **Measured:** 12
  pixels (lum 98-114) of the tip of his right eye's mark (x 316-318, y 421-424)
  were outside. **Cause:** the strand filter treated the 4-px-tall mark tip as a
  strand. **Fix:** eye marks are protected and merged into the outline at 1/8-px
  precision with a 0.5 px margin. **Re-checked:** both eyes: 0 mark pixels
  outside (3,024 and 4,175 checked); pixel-grid views of both corners; lashes
  still outside. Test added (it caught corner-shaving, fixed). 6 tests pass.
- Owner: the bump above his right eye is a rogue wisp. Outline bridged past it
  (rows 368-401, owner-guided). First bridge had an 11 deg/2 px angle at its
  lower joint (directions were taken partly from the bumped stretch); fixed by
  measuring directions only outside the stretch (now max 6.8). Also made the
  closed outline evenly spaced all the way round. Eye marks still 0 px outside.
  The wisp is noted for the wisp step. Review images regenerated.

## 2026-11-07 — Session 4 (cont.): method documented
- Owner: sensitive areas (peets, underfluff/pelvis and stance, ears, later
  mouth, nose, whisker pads, plus the eyes) always get extreme precision and
  owner-guided handling where needed.
- Wrote `docs/METHOD.md`: the full working method and when to do what (gentle vs
  sensitive areas, the precision protocol, judgment lines, the guide,
  representation, viewing/checking, working with the owner, per-batch routine).
  CLAUDE.md and DECISIONS point to it.
- Batch 1 (T001-T020) outline: self-checked, sheets regenerated; **not yet
  approved by the owner.**
- **Next:** owner approves/corrects batch 1, then batch 2 (T021-T040: his left
  side down to his left peet, so the peet's sensitive edge is in it).
- **Batch 1 (T001-T020) outline: owner-approved.** Ledger updated. Owner: ears
  need pixel-perfect tweaks later, when each ear is worked on individually; the
  ears, peets, underfluff etc. get special care as separate units later (noted in
  METHOD §2 and STRAND_PLAN).
- **Next:** batch 2 (T021-T040), down his left side to his left peet (image right).

## 2026-11-07 — Session 5: working through the outline batches on my own
- Owner: keep going batch by batch, double-check and fidelity-check each, note
  questions for a bulk review, stop only if something is physically wrong.
  Agents per batch were considered and not used for the outline step (one
  shared curve; batches are review units); suggested for strand tracing later.
- **Found and fixed a half-pixel convention bug** (outline stored with pixel
  centres at whole numbers; everything else uses [col, col+1)). Test added.
  Eye marks still 0 px outside. Batch 1 sheets regenerated; noted as Q1 in
  `docs/OWNER_QUESTIONS.md`.
- Added `tools/review_batch.py` (sheets + measured fidelity: cut / bulge /
  smoothness / eye marks / peet line) with tests that it detects a shrunken or
  swollen outline. Batch 1: all clean.
- **Batch 2 (T021-T040): self-checked.** Found the line wiggling around fur
  tufts at T033-T038. **Cause:** the peet zone was "everything below row 1100",
  which includes the lower furry sides. **Fix:** the peet zone is now everything
  below the approved peet line. **Re-checked:** T031-T040 smooth; peet corner
  hand-off smooth; batch 1 unaffected (far above the line); the left side (same
  cause could apply) will be checked in batch 3/4. Fidelity: 0 cuts; small
  fringe-gap bulges only (T021-23, T028-29, max 5.3 px); eye marks 0 px out;
  peet line inside.
- **Batch 3 (T041-T060): self-checked.** Both peets and the tuft (sensitive).
  Fidelity: 0 cuts, 0 bulges, smoother everywhere; eye marks 0 px out; peet
  line inside. Peets' sides/bottoms followed; wisps below them outside. Checked
  the left-side notch (T059-T060) up close with the gentle/faithful curves and
  the peet line: the hook is the real notch where the peet line starts, outside
  his fur; kept (Q2). Tuft spike tips noted for the fluff step (Q3).

## 2026-11-08 — Session 5 (cont.): body line recalibration, paused for the owner
- **Owner flagged:** the line is consistently too far out; it should follow the
  edge of his body, and the intermediate fur between body and wisps gets its own
  colour. **Cause:** the side line was the 50% level of a blurred coverage map,
  which lands mid-fringe.
- Tried: edge of "solid body" (opening r=9). Measured with a new into-fringe check
  (`tools/review_batch.py`, tested): old line 9,159 px in the fringe over 61/80
  tiles; new 526 px. But it **cut in too far** (e.g. his right side T076-T080 and
  under his right eye, where it hooked inward). **Owner stopped it.**
- Committed: the into-fringe check + test, and the cut check counting only solid
  fur connected to him. NOT committed: the over-tight outline/sheets. Ledger
  T013-T060 reset to todo.
- **Next:** calibration sheet with candidate lines on ~4 spots; owner picks.
- **Owner, looking again:** the recalibrated line is right on his sides; only the
  eye areas cut in ("cutting around the outline of his eye, not his shape";
  "his eyes should already be done"). **Cause:** zone joining by nearest point
  jumped to the wrong part of the line under his right eye (rows 420-460, 14 px).
  **Fix:** approved top of head locked as `data/lines/approved_top_of_head.json`
  (rows < 520, 40 px hand-off; tool refuses a hand-off > 8 px). **Re-checked:**
  top of head within 0.25 px of approved everywhere; both eyes viewed
  (`docs/images/eyes_after_lock.png`); eye marks 0 px out; hand-off 6.2 deg/2 px
  (same as his sides). Test added (12 pass).
- **batch1 (T013-T020) outline: self-checked** on the recalibrated line. Fidelity: no cuts, no bulges, no into-fringe > 6 px, smoother everywhere; eye marks 0 px out; peet line inside.
- **batch2 (T021-T040) outline: self-checked** on the recalibrated line. Fidelity: flags: T030 into-fringe 7.0 px, T031 into-fringe 7.0 px; eye marks 0 px out; peet line inside.
- **batch3 (T041-T060) outline: self-checked** on the recalibrated line. Fidelity: no cuts, no bulges, no into-fringe > 6 px, smoother everywhere; eye marks 0 px out; peet line inside.
- **batch4 (T061-T080) outline: self-checked** on the recalibrated line. Fidelity: no cuts, no bulges, no into-fringe > 6 px, smoother everywhere; eye marks 0 px out; peet line inside.
- **batch5 (T081-T100) outline: self-checked** on the recalibrated line. Fidelity: no cuts, no bulges, no into-fringe > 6 px, smoother everywhere; eye marks 0 px out; peet line inside.
- **batch6 (T101-T108) outline: self-checked** on the recalibrated line. Fidelity: no cuts, no bulges, no into-fringe > 6 px, smoother everywhere; eye marks 0 px out; peet line inside.
- Into-fringe check now skips the eye boxes (the black eye skews coverage, so
  light cheek fur beside it read as fringe; verified by looking: photo values
  180-251, real fur). Line unchanged.
- **Body outline complete for review: T001-T012 approved, T013-T108
  self-checked.** 12 tests pass. **Next:** owner bulk review + questions
  (`docs/OWNER_QUESTIONS.md`, Q1-Q7); then the next part step (Q4).

## 2026-11-08 — Session 5 (cont.): intermediate fur, first pass
- Owner: proceed; intermediate fur first, then split peets and ears along
  the drawn lines; the T019-T020 bulge is his brow ridge (body).
- First outer-edge try (closing/opening envelope) was jagged and followed
  hair clusters; replaced by reach-from-body-line with along-edge averaging.
  Then long straight strands were dragging it out where whiskers fan out
  (T024-T030, T071-T076); fixed by removing them before measuring. Tests: 14 pass.
- **batch1 (T001-T020) intermediate fur: self-checked**, all tiles viewed. 0 tiles in the peet zone (not this class). Outer line smoother than the raw edge everywhere.
- **batch2 (T021-T040) intermediate fur: self-checked**, all tiles viewed. 0 tiles in the peet zone (not this class). Outer line smoother than the raw edge everywhere.
- **batch3 (T041-T060) intermediate fur: self-checked**, all tiles viewed. 19 tiles in the peet zone (not this class). Outer line smoother than the raw edge everywhere.
- **batch4 (T061-T080) intermediate fur: self-checked**, all tiles viewed. 0 tiles in the peet zone (not this class). Wide band (>22 px, checked by eye: long feathery fringe): T070, T071, T072, T073, T074. Outer line smoother than the raw edge everywhere.
- **batch5 (T081-T100) intermediate fur: self-checked**, all tiles viewed. 0 tiles in the peet zone (not this class). Outer line smoother than the raw edge everywhere.
- **batch6 (T101-T108) intermediate fur: self-checked**, all tiles viewed. 0 tiles in the peet zone (not this class). Outer line smoother than the raw edge everywhere.
- Owner: outer edge "in just a tiny bit" → density 0.21 (median ~1 px in; the
  biggest moves, up to 6.6 px, were at the lashes, which are reserved). Ears and
  lashes get their own separate precise step later: 34 tiles at the ears/eyes
  marked reserved in the ledger; 55 self-checked; 19 in the peet zone. Sheets
  regenerated.
- **Peets: dividing lines proposed** (cream peet | tuft | gray peet), from the
  approved peet line down to the body outline. Colour tracing failed (shadows:
  the tuft's on the cream peet, the gray peet's own corner); placed by shape,
  checked at 4x. Saved as PROPOSED; stopped for the owner (Q11) since peets are
  sensitive and these lines decide his stance.
- **Owner flagged:** peet dividers went straight down, cutting the round peets
  off (top connections fine). **Cause:** dividers drawn as near-straight
  splines through 3 points, ignoring the peets' shape. **Fix (v2):** each peet's
  known outline fitted with a rounded-box shape (median error ~1-2 px); the
  divider follows its tuft-side curvature between the kept endpoints. Tried and
  rejected on the way: free fit (curled back and cut the cream peet's bottom
  corner; gray barely bowed and cut its shadowed corner); fit anchored at both
  ends (cream bulged outside the body). **Checked:** both inside the body, smooth,
  never cut in more than v1 (cream +17 px, gray +8 px). Zoom:
  `docs/images/peet_dividers_zoom.png` (red = v1). Awaiting owner (Q12).
- Owner: gray divider fine; cream divider's connection to the purple line still
  cut off part of the peet. **Cause:** the junction (x 433) sat left of the
  peet's widest point (x 453), so the side leaned in toward the top and left a
  wedge of shoulder on the tuft side. **Fix (v3, cream only):** junction moved
  to x 450 on the peet line, shoulder rounded in, lower part unchanged; adds up
  to 10.5 px, cuts none, inside the body, smooth. The 6x zoom showed no sharp
  edge there (cream fades into blue), so it's a judgment line. Awaiting owner.

## 2026-11-09 — Session 5 (cont.): cream peet completed under the tuft fur
- Owner: bluish tuft fur covers part of the cream peet's edge, but the peet
  extends under it; make the whole peet and lay the fur over it later.
  **Cause of the repeated cut-off:** the divider tracked where the peet stops
  being visible. **Fix (v4):** fit the peet's whole visible edge (outer side,
  bottom, rising side up to x 465, peet line on top; median error 1.5 px) and
  complete it under the fur: widest x 464.5 (v3: 453). Starts at v3's junction,
  ends on the outline at the peet's visible side. Two kinks found and removed
  (forced jump at the top, snapped end); final max turn 2.9 deg/px, inside the
  body, never inside v3. New general rule in METHOD §3b; lesson 11 in DECISIONS.
- Owner: gray peet fine; move on. Peet dividers marked approved (gray v2,
  cream v4).
- **Peets split off** (`tools/split_peets.py`, test added, 15 tests pass):
  cream peet 18,826 px², tuft 5,097 px², gray peet 16,918 px²; exact tiling
  (0 gap, 0 overlap). The peet line didn't reach the refined outline at either
  notch; joined (cream: straight 9.8 px into the notch; gray: inferred curve down
  the peet's shadowed side, after a darkest-point trace followed single hairs and
  was discarded). Checked on tinted overlays at 2x and 4x. Added requirements.txt
  (shapely is new).
- **Next:** owner review of the split (Q16); then the ears: propose where each
  ear meets his head, as their own precise step.
- Owner approved the peet split. **Ears: base lines proposed.** Groove filter
  (sigma 4-7) read column by column >10 px inside the outline. Discarded on the
  way: cheapest-path search (followed the dark rim around the ears, lesson 5);
  spline extrapolation past the measured crease (plunged down the head's side);
  straight inner extension (ran along the whole dip). Final: right ear follows
  its crease (median 1.1 px off it) from the dip's rising corner (572.6, 272.3)
  to the outer side (717.6, 307.9); left ear from its outer corner (376.5, 287.1)
  through its faint crease to its step bottom (512.9, 275.8). Ear areas 5,262
  and 7,171 px². Awaiting owner (Q17).
- Owner: ears pixel by pixel like the eyes (notches, kinks, the base on the
  left; asymmetry fine). Measured: the smooth ear line was 0.8 px (median),
  up to 2.7 px off the photo's exact edge and rounded off real notches. **Fix:**
  `tools/ear_edges.py`: exact 50% edge (no blur), whiskers removed, 2 whisker
  roots bridged, smoothing <= 0.25 px RMS (0.19 px median / 0.88 px max from the
  raw edge); spliced over the top of the head with 8 px blends (joints < 8.5 deg
  over 2 px). First splice end sat just under the ear-base hook and kinked; moved
  to where the exact edge meets the old line (0.2 px). Ear bases re-anchored on
  real notches; the left base's v1 "crease" was the ledge's rim, so it now
  mirrors the right ear's measured crease (inferred). Nothing else moved: peet
  parts within 0.1 px², eye marks 0 px out, top batches clean. Tests: 16 pass.
- Owner: both ear bases a tiny bit lower; ears include everything down to the
  flat part. **Measured** the flat part (brightness profile averaged along each
  base; slope map): v2 sat in the groove of the crease; flat begins ~12-16 px
  lower (right ear) and ~14 px lower (left). **v3:** lowered 12 px in the middle,
  cosine ease to 0 at the inner corners (already at the flat dip), outer ends slid
  12 px down the outline. Tried and dropped: nearest-point outer end (left line
  cupped), extending along the line (overshot 26 px onto the head's side).
  Ear areas recomputed. Awaiting owner (Q19).
- Owner: v3's 12 px was too far ("more like 3px"); and the base on the left side
  of the orange ear (image left) wasn't covered. **Cause of the 12 px:** I let a
  brightness measurement override "a tiny bit" (lesson 13, METHOD 8b). **Found the
  uncovered base:** below the hook the outline runs straight at a steady -29 deg
  to (351.5, 311.8), then curves as the head's side; that shaded flare is the
  ear's base, cut off by v2 and v3. **v4:** both bases v2 + 3 px (eased to 0 at
  the inner corners), right ear's outer end 3 px down the outline; orange ear's
  outer part sweeps down the flare to (351.5, 311.8) (first try had a knee and a
  dip from a forced depth; redone as one gentle curve, max 0.9 deg/2 px).

## 2026-11-11 — Session 6: orange ear base v5
- Owner: green ear fine (approved). Orange ear: right side down a tiny bit more,
  left side ~3 px more. **Cause on the right:** v4's 3 px drop eased in over the
  first 30% of the line, so near the inner notch it was only 0-1.6 px below v2.
  **v5:** v4 lowered 3 px along its whole length, eased in over 14 px at the notch
  (6 px gave a 27 deg kink, 10 px 14 deg; 14 px 7.9 deg, like the other joins),
  outer end slid 3 px further down the outline to (348.6, 313.8). Inside the body.
  Awaiting owner (Q21).
- Owner approved the ear bases. Added `tools/split_ears.py` (reproduces the
  approved ear parts to within 0.05 px²) → `data/strands/parts_ears.json`.
- **Fluff step: the underfluff tuft.** The smoothed outline cut across the
  tuft's hanging spikes (5-6 spikes, 5-10 px). `tools/tuft_edge.py` traces the
  exact edge between the peet dividers' bottom ends (0.16 px median from the raw
  edge); spliced into the outline. `splice_precise` now takes the short way
  between the ends (was "the higher way", only right for the top of the head).
  Checked: nothing else moved (<= 0.25 px), peet and ear parts unchanged
  (<= 0.06 px²), dividers still end on the outline (0.14 / 0.46 px), tuft +92 px²;
  the two joins (~20 deg vs 5 before) checked at 16x: real corners, not kinks.
  Faint haze below the spike tips left for the owner (Q22). 16 tests pass.
- Owner: the haze below the tuft is the tuft's fuzz, part of the tuft, not to be
  forgotten when building him. Added `tools/tuft_fuzz.py` → `data/strands/tuft_fuzz.json`:
  band from the tuft's spike edge to where coverage drops below 0.10 (three levels
  tried, middle kept), smoothed (no stair-steps), tapered to zero over 10 px at each
  divider end (first try had a vertical wall at the right end and a jag under the
  hook spike). ~620 px², median 3.9 px deep. Not added to the tuft's solid shape.
  Added a "Build checklist" to PLAN.md and guide #10 to METHOD.

## 2026-11-11 — Session 6 (cont.): wisps, region 1
- Owner approved the tuft fuzz; stressed pixel-by-pixel precision for the wisps.
- Inventory: 129 hair-like pieces outside the body, fur band and tuft fuzz.
- `tools/wisps.py` + `tests/test_wisps.py`: sub-pixel strand tracer (profile fits
  every 1 px; centre within 0.17 px on a known synthetic hair after removing the
  known pixel + sampling blur from width/opacity), crossing-aware seeds from the
  skeleton, duplicate removal, classification. 18 tests pass.
- Region 1 (his left side, ear to cheek): first pass had two real problems found
  by looking at contrast-stretched pixel views: a trace ran along a fringe EDGE
  and jumped to a neighbouring hair (false S-bend), because a step looked like a
  ridge. Fixed with a ridge check (lighter on both sides) and a sharp-turn split.
  Halo along the fur edge (pieces 2, 63) is refused by the tracer (not hair-shaped).
  Result: 5 wisps, 6 whiskers (provisional), 2 lash bits (reserved), 1 fringe tip.
  Saved to `data/strands/wisps.json`; stopped for owner calibration (Q24-Q26).
- Owner: judgment calls make sense; make sure everything gets a classification.
- **Wisp step run over all of him** (`tools/trace_wisps.py`, ~2 min): 63 wisps,
  21 whiskers (provisional), 6 lash bits, 6 fringe tips, 15 blobs, 81 refused
  (halo). Every wisp viewed on contrast-stretched pixel sheets (B1-B5): all on
  real hairs, centred, bases into the fringe. Fixes on the way: tuft fuzz now
  beats the fur band below the peet line ("peet & tuft fringe" for the rest);
  two long faint eyebrow whiskers had been labelled lashes (opacity 0.38 < 0.40)
  → very long straight hairs are whiskers at any opacity; the rogue wisp above
  his right eye had been labelled a lash and was split by a whisker crossing →
  owner-guided join, checked against the pre-bridge outline bump.
- **Accounting:** started at 756 unclassified px (a band of side-by-side
  whiskers in the left fan, hair bases/tips at junctions, a faint fringe halo);
  rules: touching a hair → that hair (recorded per hair); touching the fringe →
  its halo; near a hair (<= 20 px) → nearest. **Now 0 unclassified.**
- **Next:** owner bulk review of wisp sheets; then whiskers (incl. side-by-side
  whiskers in the left fan, crossings, and the 4 borderline wisps, Q27).
- Owner: whiskers are light; dark hairs are probably dark eye fur, not whiskers.
  Measured each traced hair's colour (unmixed from the white background): all
  ~140-210 of 255 (whiskers 142-206, the six borderline 141-196); the spread is
  mostly shadow (his left side) vs light (right side). My earlier "dark" meant
  opacity; corrected. The six stay wisps (no change). Colour cue + shadow caveat
  recorded for the whisker step (METHOD guide #13, lesson 13b).

## 2026-11-11 — Session 6 (cont.): whiskers, part 1 (outside the outline)
- `wisps.fit_multi/extend_whisker/retrace_whisker` (up to 3 side-by-side ridges,
  coasting through crossings), synthetic test (stays on its whisker 3 px from a
  neighbour, through a crossing); `tools/trace_whiskers.py`.
- Found the fan's thick line is 2-3 whiskers sharing a root (darkness doubles at
  B4-S12's tip, rises again at B4-S15's join). Fixes on the way: a join rule first
  joined a whisker's TIP (wrong) → root ends only; first shared fit put all three
  on one line (red halo, too wide) → fit exactly N whiskers with fixed widths;
  then lines swapped/crossed → fixed no-crossing order. Result: fan residual
  0.110 → 0.066 (S12), centres separated, no crossings, bends <= 7 deg.
- 2 fine hairs beside whiskers traced (wisps). Accounting: 0 unclassified.
- All 21 whiskers viewed (full length + root pixel zoom). Questions Q29-Q31.
- **Next:** whiskers part 2: the whiskers lying over his face inside the outline.

## 2026-11-11 — Session 6 (cont.): whiskers, part 2 (over his face)
- Photos used as references of him: `data/photos/anchor_front.webp` (the only one).
- Tried first: a step-by-step tracer from each whisker's root. It returned 0 points
  for every whisker; the cause was its "left the body" stop rule firing at the
  first step (root ends lie just outside the outline). Fixed, it then ran off each
  line where the whisker bends onto his cheek (lesson 15). Dropped it.
- Built `tools/face_whiskers.py`: whole-path search (dynamic programming over
  smooth arcs) on a local-contrast map; acceptance by running contrast with
  hysteresis (3.5 to accept, 2.5 to follow); change-point ends; per-px Gaussian
  fits on the photo + least-squares spline. Fixes on the way: one dark blob (his
  eye mark) pulled a path → per-point contrast capped, eye margin 50 px; paths
  ran along his outline's dark edge → the outline band (12 px) is off limits once
  past the entry; two whiskers ran onto one face line → the stronger keeps it.
  Synthetic tests (`tests/test_face_whiskers.py`): faint curved line on fur-like
  speckle, 0.15-0.25 px along the line, ends within ~2 px; plain fur gives nothing.
- Result: 7 face whiskers (5 continuations, B2-S02 linked by position, FW-01 face
  only), 5997 px marked WHISKER (weight 0) over the body; 7 whiskers with no
  visible face part; 8 fainter lines listed, not classified. Every line viewed at
  full resolution on the contrast-stretched photo with guides either side: each
  sits on its line. The lines are only 5-12 grey levels deep, about the size of
  the photo's compression blocks, so ends and the fainter lines are judgment.
- Tests: 24 passed. `check.py` does not exist yet (PLAN.md: not built), so no
  match is claimed.
- **Next:** owner review of face whiskers (Q32-Q35) and the earlier sheets; then
  the separate precise steps the owner listed (ears' pixel tweaks, lashes/eyes,
  whisker pads, mouth and nose), then the head/undercarriage split.

## 2026-11-13 — Session 6 (cont.): face whiskers, second pass (owner's review)
- Owner: "the inferred whiskers don't go for the full length, and you missed
  several whiskers along the way, but the method is solid".
- Photo used as reference of him: `data/photos/anchor_front.webp` (the only one).
- Causes found: (1) searches only started at his outline or known roots and the
  line had to be visible within 64 px of the outline; (2) a whisker's end was set
  where it fell to half its own typical strength; (3) lines found from inside his
  cheek were followed only the way the search went; (4) when one line was found
  twice, the better-scoring but shorter find won. Lesson 16.
- Fixes (tools/face_whiskers.py): cheek-wide starts (6 x 69 x 2 searches, joined
  through each start); end = change point against 1.17 x the local fur speckle
  (fur on his face only), calibrated on his forehead (plain fur, no whiskers);
  longest find kept; face-only names stable across runs; every face whisker runs
  outline -> nose; a linked whisker keeps its link when a longer find wins.
  Bugs fixed on the way: a zero-length path crashed the line measurement; the
  fur-speckle box took in the dark fur band (FW-01 collapsed to nothing).
- Result: 9 face whiskers (was 7): FW-02, FW-03 new; B4-S02 +23 px, FW-01 +17 px,
  others unchanged or a little longer; no whisker shorter than before. 7746 px
  marked WHISKER (weight 0). 13 faint lines numbered C01-C13 (not classified).
  New lines checked at 5-7x on the photo: each sits on its line.
- **Stopped on "full length" (rule 5).** Tried, on the traced ends: follow on
  while the 24 px running contrast >= 2.5 (0 px gained); let it bend faster (the
  bend was found, but it stays at fur level); follow the faintest evidence with
  no cost (wandered, crossed whiskers, overshot the pad); extend each whisker's
  own arc (curled away or crossed); test against side-by-side copies, and against
  identical searches started 12-30 px beside it (margins 0.01-0.16: noise). The
  continuations are visible to the eye but not separable from fur by these
  measures. Options for the owner in Q36.
- Tests: 24 passed. `check.py` does not exist yet (PLAN.md: not built), so no
  match is claimed.
- **Next:** owner's choice on Q36 (full length) and answers on C01-C13 (Q35).

