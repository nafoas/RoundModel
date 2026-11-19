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

## 2026-11-13 — Session 6 (cont.): face whiskers, third pass (the line view)
- Owner: "recalibrate the views you're using to try and increase the contrast? Use
  a different method of highlighting them ... I don't wanna leave a single whisker
  unaccounted for." Photo used: `data/photos/anchor_front.webp` (the only one).
- Measured on the 9 traced face whiskers vs the fur beside them: colour channels
  and colour differences do not help (whiskers differ from fur only in
  brightness). Long thin line filters do: 12 scales tried, best 2 px across x 14 px
  along (whisker/fur 2.3 vs ~1.3); restricting to the whisker direction field
  (smoothed from traced whiskers) removes fur streaks crossing them.
- New `tools/whisker_lineview.py` (part 2b, run by face_whiskers.py): the same
  whole-path search in the line view; extensions of traced whiskers; new
  candidates with a side-by-side test and photo fits; one-by-one verdicts (judgment
  calls, in the tool). Test `tests/test_whisker_lineview.py` (finds a faint curved
  whisker, ignores a darker streak crossing the whisker directions).
- Result: 12 face whiskers (was 9), 14044 px WHISKER (weight 0); 6 whiskers longer
  (B5-S17 +125 px); FW-04/05/06 new (= the old faint lines C01/C04/C05, found
  independently); inferred links mostly replaced by seen lines. Earlier parts moved
  median 0.02-0.15 px (up to 1.7 px only at the old, least certain ends). All new
  and extended lines viewed at 3-6x on the photo: each sits on its line.
  7 candidates L01-L07 for the owner (Q35). Lesson 17.
- Tests: 25 passed. `check.py` does not exist yet (PLAN.md: not built), so no
  match is claimed.
- **Next:** owner review (Q32-Q37), especially L01-L07 and any whisker still missing.

## 2026-11-14 — Session 6 (cont.): face whiskers, fourth pass (rigour, colour/contrast)
- Owner: L01-L07 are all whiskers (then: L05 and similar grey areas go to a new class,
  "uncertain: owner sorts manually"); "a lot of them are missing segments ... be more
  rigorous ... look for fainter traces ... try other combinations of color and contrast".
  Photo used: `data/photos/anchor_front.webp` (the only one).
- Colour/contrast tested on every known face whisker vs fur (19 views + best RGB mix):
  colour carries no whisker signal; contrast evened out (12 px) + a longer filter is
  best on the faintest parts; combined view adopted (AUC 0.969 on the faintest quarter).
- New `tools/whisker_fulllength.py` (part 2c) + `tests/test_whisker_fulllength.py`.
  Fixes found on the way: extension pieces were attached without checking they continue
  the whisker's direction (B5-S17 folded back on itself; FW-10 turned sharply) → direction
  and bend checks (also in part 2b); sweep pieces had skipped the side-by-side test →
  same test for all; the test's bar (0.5) and the follow's cost (1.5) were hand-set and
  both too loose (fur passed 10%; 87 px overshoot in a synthetic test) → calibrated on
  plain fur (bar 0.94 = fur's 95th pct; cost 2.5). Lesson 18.
- Result: 18 face whiskers, 18194 px WHISKER (weight 0); confirmed extensions +16/+14/+32
  px. 13 grey areas for the owner (L05, L08-L19), bold cyan on the sheets. A container
  restart killed one run; rerun from the caches, data from the killed run not used.
- Tests: 27 passed. `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner sorts L05, L08-L19 (Q35); any whisker still missing (a rough mark is enough).

## 2026-11-14 — Session 6 (cont.): review sheets for the grey areas
- Owner: "help me discern these by showing a few views of each of them, both with this
  view and his base image". Photo used: `data/photos/anchor_front.webp` (the only one).
- New `tools/candidate_sheets.py`: one sheet per uncertain candidate (L05, L08-L19) +
  one PDF (`docs/images/candidates/`). Each: locator, photo as it is, photo with brightness
  stretched in true colour, contrast evened out, line view; unmarked + marked; test result;
  my read (not a decision). All 13 sheets looked at; reads in the tool (READS).
- Fixes found on the way: (1) the stretched-photo panel first invented colour (channels
  stretched separately, then together); now brightness only, true colour added back.
  (2) Lines on their own had been scored with an older side-by-side test that counted
  neighbouring whiskers as "beside" (L11 between B2-S08/B2-S16); every candidate is now
  re-tested the same way; a candidate with no fair comparison is "untestable", not a
  number. Rechecked: L09 +1.52, L10 +1.19 beat the fur bar; L17 +0.89, L19 +0.85
  just under; L11 untestable; L05 +1.81 (edge of the fur band, which the test also
  rewards). Whiskers unchanged (18, 18194 px). Lesson 19.
- Tests: 27 passed. `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner sorts L05, L08-L19 with the sheets (Q35).

## 2026-11-14 — Session 6 (cont.): the owner's whisker rule; is this all of them?
- Owner: all the grey areas are whiskers; continuations are part of the same whisker; the
  rule: whiskers come from his whisker pads, point to them, and are straight; faint ones are
  never boosted and never forgotten. Photo used: `data/photos/anchor_front.webp`.
- Applied: L05, L08-L11 -> FW-13..FW-17; L12-L19 joined (matched by where the piece is, not
  by name). Bugs on the way: whisker names shifted between runs (an owner-confirmed piece
  missed its whisker) -> names now stable against the saved data; FW-12's joined piece
  wandered into a dark fur patch (S-bend) -> every owner-joined whisker refitted as one
  gentle arc (photo fits 0.7-1.5 px from the arcs; FW-12 2.7 px).
- 23 face whiskers, 27891 px WHISKER (weight 0), no grey areas left.
- New `tools/whisker_pads.py` (completeness by the rule): pads at (504, 695) and (661, 702);
  a scan of every straight line pointing into a pad finds no untraced line at the normal
  level (the one hit on the left is B5-S17's own arc), 3 + 1 at a fainter level, where
  control lines through the same fur find 20 + 8, so nothing stands out from fur. What is
  still open is parts, not whole whiskers: roots into the pads (Q36), and outside/face parts
  that line up but aren't joined (Q38).
- Tests: 27 passed. `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner on Q36 (roots into the pads) and Q38 (joins); then the separate precise
  steps (ears' tweaks, lashes/eyes, whisker pads, mouth and nose).

## 2026-11-14 — Session 6 (cont.): every whisker pad to tip
- Owner: examine the junctions individually (the pictures are hard to read); whiskers don't just
  cut off; trace them to the pads now. Photo used: `data/photos/anchor_front.webp` (the only one).
- Junctions measured one by one (`docs/WHISKER_MAP.md` has every decision and its numbers): one
  arc through both pieces (0.1-0.8 px = same whisker; 2-10 px = not), darkness (a stretch carrying
  two whiskers reads ~2x), direction. New links: FW-03 = B2-S20 + the 'loose' B2-S29 (0.28 px
  across a 45 px invisible stretch); FW-07 = B4-S13 (0.09 px); FW-04's tip = B4-S06; FW-16 =
  W-F01; B4-S01 shares B4-S02's face line; FW-02 shares B5-S17's root stretch (2.8x dark);
  FW-13 shares B2-S02's root stretch (flagged).
- Pads: nose, philtrum and mouth measured from the photo; working pad outline = upper lip under
  each nostril wing, raised to where 90% of the whiskers point (the first, unraised outline made
  most paths funnel into one corner: whiskers point a little above the wing end).
- New `tools/whisker_chains.py` (+ `tests/test_whisker_chains.py`): 28 pad whiskers, each one line
  pad to tip, inferred stretches labelled; inferred paths keep each whisker's own bend (26 of 28
  reach the pad on their own bend); FW-13 and FW-14 flagged (would need more bend than any whisker).
  Bugs on the way: 4 px sampling of pad points made a 15 px reach look like a sharp bend
  (FW-15: 147 px detour) -> follow its own bend to the exact crossing first; a seen end already at
  the pad got a 176 px loop (B5-S17) -> nothing inferred at the pad; sheets cropped B2-S29 off.
  Regression found by diffing runs: the arc refit ran before following ends (FW-12 lost 80 px)
  and renamed FW-12 -> refit last, names follow the owner's L-numbers. Lesson 20.
- Tests: 31 passed. `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner review (Q37-Q41); then the separate precise steps (whisker pads, mouth and nose,
  ears' tweaks, lashes/eyes).

## 2026-11-14 — Session 6 (cont.): his pads are the whole raised muzzle
- Owner: the pad outline was too narrow; it should encircle the whole raised "mouf" area from the
  mouth up to the nose; that whole area has whiskers. Photo used: `data/photos/anchor_front.webp`.
- Looked at the muzzle as a shape: shading at bulge scale (6-40 px) shows the raised area and the
  crease where it turns away. Traced it as one closed ring (rays from the middle of the philtrum,
  stays in the shading dip, changes radius smoothly, never through the nose), smoothed to a
  sub-pixel curve; split at the philtrum into the two pads. Synthetic test (follows a crease at
  r 150 to within 4 px median, encloses the nose).
- Whiskers re-traced to it: 25 of 28 reach their pad on their own bend; inferred to-pad stretches
  much shorter; FW-14's doubt resolved (reaches the muzzle in 44 px); FW-13 still flagged.
  Lesson 21. Pads picture: `docs/images/whiskers_full/pads.png`.
- Tests: 32 passed. `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner review of the pads (Q39) and the whiskers (Q37, Q40, Q41).

## 2026-11-14 — Session 6 (cont.): pads, third try (follow his mouth around and up)
- Owner: the muzzle outline still didn't follow his pads; then (stopping a colour-saturation
  attempt): "Just follow the edges of his mouth around and up ... look at the big perspective."
- Looked at his whole face at normal size. New outline (`whisker_chains.measure_muzzle`): the lip
  line traced from the middle of his mouth outward until it fades into fur (to x 405 and 709),
  round each side and up to the nostril wing tips, along the bottom of his nose; one smooth
  sub-pixel curve; split at the philtrum. Test: synthetic lip line followed to median < 1.5 px.
- Whiskers re-traced: 19 of 28 reach a pad on their own bend; the upper whiskers bunch at the
  nostril-wing corner (question Q39); FW-13, FW-14 flagged. Lesson 22.
- Tests: 32 passed. `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner review of the pads (Q39) and whiskers (Q37, Q40, Q41).

## 2026-11-14 — Session 6 (cont.): whiskers, final cleanup
- Owner: the pad outline is "pretty good"; overview of everything left, clean up, find whiskers that
  are one, show what's uncertain, then move on. Photo used: `data/photos/anchor_front.webp` (the only one).
- Inventory: nothing unaccounted (21 outside pieces, 23 face parts, 4 reclassified outside pieces).
- Checks: no two whiskers' seen parts line up end to end; overlaps are filled-in roots converging near
  the pads, one crossing (FW-16 / B2-S02), and the declared shared lines.
- Fixes: FW-02 / FW-13 end at his outline instead of taking over B5-S17's / B2-S02's outside part
  (darkness tapers, no step; lesson 23); inferred roots may not cross his nose; sign bug in the inward
  continuation of whiskers with hidden face parts (lesson 24, test added); eyebrow whiskers completed to
  his brow; final status for faint lines C01-C13 (C03 fur; C06, C08, C12 for the owner); dead code removed;
  whisker_pads.py's points renamed "convergence_points" (not the pad outline).
- Result: 28 pad whiskers + 8 eyebrow whiskers, each continuous; 21 of 28 reach their pad on their own
  bend. Uncertain items on one page: `docs/images/whiskers_full/unsure.png`.
- Tests: 33 passed. Completeness scan rerun: no untraced line pointing into a pad stands out from fur (the one hit lies across B5-S17's own curve). `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner on Q37, Q40-Q42; then move on (owner's choice of next part).

## 2026-11-14 — Session 6 (cont.): owner's whisker answers applied
- Owner: C06, C08 not whiskers; the rest are; keep the non-whiskers as "Bnuy Perturbances" (BP); bends
  are fine (whiskers bend, less than fur); FW-14 may be two whiskers; didn't understand Q41.
- FW-14: the trace was S-shaped (level, then 25 deg steeper). Split where the two straight parts cross;
  the level part carries on past the joint on its own bend and beats the fur beside it (+1.31 at 80 px,
  measured with copies on the steeper line left out); the steeper part carried back shows nothing
  (-0.42) -> FW-14 (level) + FW-19 (steeper, sharing the outer stretch). A first follow slid onto the
  steeper line (the stronger line pulls a flexible search): measured straight / own-bend instead.
- C12 -> FW-18 (extended on its own bend while it beats the fur beside it). C03/C06/C08 -> BP-01..03.
- 30 pad whiskers + 8 eyebrow whiskers; 23 of 30 reach their pad on their own bend. Close-ups of the
  new and odd ones: `docs/images/whiskers_full/unsure.png`. Q41 re-asked in plain words.
- Tests: 34 passed. `check.py` does not exist yet (PLAN.md: not built); no match claimed.
- **Next:** owner on Q40 follow-up (FW-19) and Q41; then move on.

## 2026-11-14 — Session 6 (cont.): whiskers closed
- Owner: a whisker reaching the edge of his face goes past it, then "either goes backwards or stays with
  the fluff"; FW-19's curve is fine (a consistent curve a whisker could make).
- Checked the eight such whiskers: none carries on straight into the fringe (straight line no darker than
  the fringe beside it), which fits. Outer ends relabelled; build checklist (PLAN.md) updated, including
  the Bnuy Perturbances.
- **Whisker step done:** 30 pad whiskers + 8 eyebrow whiskers, continuous root to tip; BP-01..03 kept.
  Left to later steps: pad roots move with the pad step; eyebrow roots (B1-S07, B5-S06) with the eye step.
- **Next:** the owner picks the next part (open per plan: ears' pixel tweaks, lashes/eyes, whisker pads,
  mouth and nose, head/undercarriage split, then the 3D build).

## 2026-11-15 — Session 6 (cont.): body parts: Head / Intermediate Bnuy / Undercarriage
- Owner chose the head/undercarriage split next, in this session; then: three parts, not two. The head ends
  at "that dark line under his mouth that goes up through his cheeks diagonally to his edge"; the lower
  boundary (the fold under his chin) is the undercarriage's. Photo used: `data/photos/anchor_front.webp`.
- Looked at the whole body first (photo, evened shading, fur roughness, bulge-scale shading). Measured
  profiles: chin bulge y ~900-960, fold below it y ~1030-1050, fur roughness doubles below the fold.
- Head line: a "darkest curve to the outline" search hugged the shaded sides of his face (the darkest-path
  trap, rejected); a step tracer on bulge shading climbed at its slope limit (rejected). A view showing only
  creases slanting up and out from the mouth corners shows the cheek creases; followed from each corner.
  Two bugs on the way: the carried-on part copied a short flat stretch (went level), then a 5 px dip made
  the "diagonal" point downward (crossed the fold) -> seen part = from the lowest point near the corner to
  the highest point the crease reaches; carried on in that diagonal's direction.
- New `tools/body_parts.py` (+ `tests/test_body_parts.py`), proposal pictures `docs/images/body_parts/`.
  Owner review: Q43.
- **Next:** owner on Q43; then the head / intermediate / undercarriage become the approved parts.
- Owner: agrees with three parts (head slick and short, undercarriage thick and rough, intermediate the
  slow transition); move the middle of the head line down under his mouth (it split the lip in two), no
  bump up in the middle; nose, under-nose cheeks and pads all in the head. Done: one gentle line from just
  under each mouth corner (where the dark band under it fades halfway); pads clear it by >= 13 px. Brightness
  profiles show no sharp lower-lip edge; the line sits where the mouth's shadow levels out into chin fur.
- Owner: two small changes. (1) The cheek line "goes up just a tiny, tiny, tiny bit too high on his right
  side - ideally, mirror the line on the left on the right". Read as the picture's right (the higher one,
  meeting his edge at y 647 vs 667); stated to the owner to correct if meant the other way. The
  picture-right cheek line is now the picture-left one mirrored. First try (a plain mirror from the point
  under the right mouth corner) still met his edge 13 px higher (y 654): his face is tipped a few degrees
  in the anchor photo (right nostril wing 16 px, lip corner 22 px higher), so that start point is 28 px
  higher. Now that 28 px is taken up gently along the cheek and the shape is stretched across to his
  edge: both sides meet it at y 666.6. Labelled owner-guided; the legend says so (it was drawn solid
  under a legend saying solid = seen). (2) "His left peet": the undercarriage drifted into the grey peet.
  Cause: the region code used only the approved peet line, which stops at x 785, short of his edge, so
  910 px inside the approved peet parts (`data/strands/parts_peets.json`) were coloured undercarriage.
  Fix: the approved peet parts always count as peets & underfluff, and the peet line is carried on to his
  edge at both ends. Re-checked both peets: 0 px of head / intermediate / undercarriage inside either;
  318 px of peets & underfluff lie just beyond the parts (the carried-on line).
- Same cause, re-checked everywhere it could apply (every approved part against the new map): the
  approved ears (`data/strands/parts_ears.json`) were coloured head, 7878 + 7262 px, out of sight above
  the pictures' crop. Fixed the same way (approved parts win; ears now their own colour, green), plus a
  1 px sliver along the ears' sides (106 px inside his body outline but just outside the ear polygons,
  above the ear bases: the two approved outlines differ by a pixel there) given to the ear it touches.
  The tool now counts every approved part's pixels against the map and stops if any carry another label
  (all 0; recorded in `body_parts.json` checks) + a test for that check. The overview picture now shows
  his whole body, ears included. Pixels now: head 332228, intermediate bnuy 148776, undercarriage 100173,
  peets & underfluff 41248, ears 15256. Pads clear the head line by >= 15.3 px. Tests: 37 passed.
  Checked at full size: both cheek ends on one level guide (2x); both peets close up (photo beside tint,
  3x); both ears' edges pixel by pixel (6x). Photo used: `data/photos/anchor_front.webp`.
- Owner: two more changes, nothing else. (1) Under his mouth the line still rose to the picture's right:
  "keep that flat, and then connect it back to the diagonal, so that his head boundary is symmetrical".
  Now the whole head line is the picture-left half mirrored about one upright line (x 553.7, halfway
  between the two places it meets his edge at y 666.5), level under his mouth at y 895.9; the earlier
  tilt allowance is gone. Mirror mismatch <= 0.6 px; pads clear it by >= 21 px. (2) "Connecting his
  little ears with a tiny strip between them ... kinda like his peets" (owner has a reason, later): the
  top of his head between the ears, his outline's inner 4 px, ear to ear, coloured with the ears (300 px).
  Checked at full size (mouth 2x with axis and level guides; ears 4x, pixel edges). Pixels: head 338816,
  intermediate bnuy 141888, undercarriage 100173, peets & underfluff 41248, ears + strip 15556. Approved
  parts: 0 px leaked. Tests: 37 passed. Photo used: `data/photos/anchor_front.webp`.
- Owner: "just add the peets one to it, so we can have a fully mapped out image of his regions". The
  map now shows each approved peets-step part in its own colour: cream peet red, underfluff tuft teal,
  gray peet yellow (the peets picture's orange/purple/green are already head/undercarriage/ears here);
  grey is only the 318 px of fringe below the peet line beyond the parts. (That edit was interrupted
  by a misclick mid-run; it had been written in full, checked, then finished.)
- **Owner approved the three body parts** (Q43). Saved, frozen: `data/lines/body_parts_lines.json`
  (head line with its seen / inferred / owner-guided stretches, the fold, the ear strip). The tool now
  uses those lines exactly as saved and only compares its own recomputed lines with them (drift 0.01 px
  both); `data/strands/body_parts.json` status OWNER-APPROVED. Labels along the head line now follow
  position along it (they had flickered between seen and inferred where the smoothing strays a pixel).
  Pixels: head 338817, intermediate bnuy 141888, undercarriage 100172, ears + strip 15556, cream peet
  18825, underfluff tuft 5189, gray peet 16916, fringe 318 (1 px moved head/undercarriage: the saved
  points are rounded to 0.01 px). Approved parts: 0 px leaked. Tests: 37 passed. Checked at full size:
  whole map; peets at 2x with the photo above. Photo used: `data/photos/anchor_front.webp`.

## 2026-11-16 — Session 6 (cont.): every bit of him assigned
- Owner: "fix the remaining little grey areas, then once every little bit of him is assigned I can give
  proper advice". The grey (318 px below the peet line, outside the approved parts) was 10 pieces: one
  307 px wedge of dark side fur hanging down beside the gray peet's top-right corner, outside its approved
  edge -> undercarriage (it touches it); 9 single pixels between a peet part's edge and his outline (the
  same 1 px mismatch as at the ears) -> the part they touch (cream peet 7, underfluff tuft 1; one at the
  undercarriage junction -> undercarriage).
- Looking at full size found more of the same cause in another colour: 13 undercarriage pixels in a 1 px
  sliver between the peets and his outline (beside the cream peet, below the notch the peet line starts
  at) -> the peet part they touch (cream 12, gray 1).
- Whole-map check: inside his outline 0 px unassigned, 0 grey (the tool now stops if either is not 0);
  every colour is one piece, except 2 single pixels of underfluff tuft that are inside the approved tuft
  outline, at tips of its spiky lower edge thinner than a pixel. Approved parts: 0 px leaked.
- Pixels: head 338817, intermediate bnuy 141888, undercarriage 100467, ears + strip 15556, cream peet
  18846, underfluff tuft 5190, gray peet 16917. Tests: 37 passed. Checked at full size: the wedge and
  peet edges at 4x and the whole peet area at 2x (hard pixel edges, photo above).
  Photo used: `data/photos/anchor_front.webp`.
- One edit of mine reported success but never reached the file; caught because the result didn't change.
  Since then every edit is confirmed in the file and by its result.
- **Next:** the owner's advice, now that every bit of him is assigned.


## 2026-11-16 — Session 6 (cont.): 3D grounding, steps 1-3 (first pass)
- Owner: ground him in a real 3D space before any sculpting ("previous claude had nothing to anchor him
  in and I think that caused a ton of confusion"); the parts exist so every shape can be traced back
  between shots. The green strip joining his ears = the top of his head seen from above; the tuft between
  his peets = his belly. Logged in DECISIONS. Photo used: `data/photos/anchor_front.webp` (the only one).
- Checked first: one photo, no camera data (no EXIF), background removed (no floor/wall to measure).
- Step 1, the room: new `prince/space.py` (cm; floor y = 0; +X his left, +Y up, +Z his forward; origin on
  the floor under the front of his peets) and a pinhole camera (project, pixel -> ray, floor hits, orbit
  placement with the plan's yaw/pitch words). The unlogged draft `prince/camera.py` was reviewed and not
  used (orbit only, no lens model, no pixel -> ray). 8 tests pin every convention (his left shows on the
  picture's right, up is up, no mirroring, angles round-trip, pixel -> ray -> pixel exact); one caught a
  flipped cross product on the first run. PLAN's old axes (x forward, z up, from the draft) marked
  superseded. `docs/SPACE.md` defines the room.
- Step 2, landmarks (`tools/landmarks.py` -> `data/strands/landmarks.json`): 27, named by HIS side, each
  with part, picture position, how found, how sure, mirror partner, kind (fixed surface point or
  view-dependent). Eyes: an oval fitted to the eyeball's edge measured in 180 directions, robust to lashes
  and fur (his right eye 61% of directions kept, rms 0.68 px; his left 87%, 1.16 px); the top where the
  eyeball meets the lashes has no light-dark edge, so the centres are ±4 px and the eye step will draw the
  eyes properly. The eyes show as ovals (short/long 0.56 and 0.42): a depth clue for step 4. Found and
  fixed on the way: 3 false "peet marks" on his right peet (darker fur along its edge) -> marks must be
  well inside a peet; the gray peet's bottom point at its corner -> middle of its flat bottom; nostril
  wings ±3 px (their dark shape fades out). His left peet's two dark specks are kept as fixed marks.
- Step 3, rays (`tools/scene.py`): the anchor camera placed PROVISIONALLY from three named placeholders
  (26 mm-equivalent lens, his widest outline = 12 cm, nose seen 5 deg below level) -> 8.5 cm up, 15.1 cm
  in front, tipped 3.6 deg down (`data/cameras.json`). Every part as rays (`data/scene/anchor_rays.json`):
  his outline (1628 rays, by part, marked grazing), head line, fold, peet line, ear bases, every approved
  part's outline, every landmark; each ray lands back on its pixel to 0.006 px. Pictures
  `docs/images/space/room_behind.png`, `room_side.png`, `room_top.png` (rays end at one length, so no flat
  cut-out at their far end), and the room in 3D, interactive: `docs/space/room.html` (three.js r159, MIT,
  inlined; tested in headless Chromium: all four views and dragging, no errors; "Camera's view" puts the
  eye where the camera was and every ray shrinks to its pixel).
- Tests: 48 passed (11 new).
- **Next:** owner on Q44 (landmarks; the real numbers for the camera), then step 4 (camera from real
  numbers, how he faces from his symmetry), step 5 (depth lines).

## 2026-11-16 — Session 6 (cont.): the anchor camera, owner's memory; a wrong tilt stopped
- Owner on how the photo was taken: phone settings unknown, no more than six inches away, straight on, a
  touch below his eye level (looking level or very slightly up), background removed afterwards; he sat on
  a soft surface. (Shooting details kept general here: this repo is public.)
- I placed the camera from that with the aim point at the picture's centre: it came out tipped 12 deg
  down. The owner stopped it ("way too much of a down angle ... it is mostly just straight on").
  Cause: the picture was cropped, so its centre is not where the camera aimed (lesson 26); the lens guess
  had the same assumption. Nothing with the wrong tilt was committed: those files were restored to the
  last commit (the committed camera is still the earlier labelled placeholder).
- Kept: `prince/space.py` saves the camera's rotation to 10 decimals (8 left it 4e-9 from a pure
  rotation); the scene test's no-mirroring check allows 1e-7.
- Owner's method for step 4: fix the camera as it was (straight on, ~six inches, a touch below eye level),
  then determine how he is being looked at. Proposed: aim point at his eye height in the picture, lens as
  a range; his turn, tip and nod from his mirror pairs (eyes, nostrils, mouth and lip corners, ear bases,
  peets), head versus peets to tell his head tilting from the phone tilting; shown in the room for review.
- **Next:** owner's go-ahead on that, then step 4.

## 2026-11-16 — Session 6 (cont.): camera as the owner remembers it; how he is being looked at
- Owner: go ahead with the three things proposed (no step numbers: the owner read "step 4" as jumping
  ahead in the broader plan; it only meant these three). Photo used: `data/photos/anchor_front.webp`.
- 1. Camera fixed as remembered (`tools/scene.py`): level, tilted up 1 deg, 13 cm from his nose, his eyes
  0.5 cm above it, aimed at his face: aim point (548, 482) in the picture, not its centre (the picture
  was cropped, lesson 26). Lens: if a 26 mm-equivalent main camera, the smallest 3:4 frame centred on the
  aim point that holds the picture gives 1428 px: the shortest lens that fits (PROVISIONAL). Result:
  camera 6.5 cm above the surface, 12.8 cm in front; his nose 4.4 cm up; widest outline 7.5 cm at his
  nose's distance. Test updated to the owner's memory.
- 2. How he is being looked at (`tools/facing.py` -> `data/scene/facing.json`, `facing.png`): his
  left-right axis from 6 mirror pairs (the one direction in all six camera-pair planes). Head tipped
  5.2 deg, his left side up: solid (4.1-6.0 leaving any pair out; 4.7-5.6 with landmark wobble; 4.8-5.6
  across the owner's ranges). Head turned toward his left: pairs 9.0, eye ovals 5.5, nose right of the
  eyes' middle: direction solid; amount 5-9 deg, not firm (leaving one pair out: 1.6-15.6; mouth, lip
  corners and ear bases fit worst, misfit 2.2-3.6 deg vs eyes/nostrils 0.4). Body from the peets'
  lowest points (rough): 3.3 deg toward his right. Nod: needs depth, later. New test: a made-up head
  turned 7 / tipped 4 comes back exactly, with the right signs.
- 3. Shown in the room: still views rebuilt; the 3D page shows his head (blue) and body (red) directions.
  Found while checking the page at full size: its "Camera's view" and picture plane still assumed the
  camera aimed at the picture's centre (labels landed beside his eyes and ears) -> the page now uses the
  real aim point (off-centre lens); labels land on every feature, and the floor's horizon runs through
  his eyes, as a level camera at eye level should. Tested in headless Chromium: no errors.
- Tests: 49 passed.
- **Next:** owner review; his real size would fix the lens. Then depth lines (rough round shell).

## 2026-11-16 — Session 6 (cont.): his size from six inches
- Owner: "he was roughly 6 inches away from the camera ... you could use that to find his size"; check any
  measurement with "is this the size of a little fluffy rabbit?". Asked which step this was: the 3D
  grounding steps are now listed in `docs/SPACE.md` (1-4 done, 5 depth lines next, 6 new angles).
- Distance alone needs the lens (size = distance x how much of the view he fills, and how much of the
  view a pixel covers depends on the lens and the crop). Tabled his size for lenses from the shortest that
  fits (1428-1437 px) to 2x: only the shortest gives a little fluffy rabbit (12.4 x 10.6 cm at six
  inches); 1.15x already gives 10.3 x 9.2, 1.5x 7.3 x 7.1, 2x 5.2 x 5.4. So: distance 15.24 cm (six inches),
  lens = the shortest that fits (1437 px), no longer marked provisional. Camera 7.7 cm up, 15.0 cm in
  front; his size (rough): 12.3 cm wide, 10.5 cm to the top of his head, ear tips 11.3, eyes 8.2, nose
  5.1 (`his_size_estimate_cm`, new `size_estimate()` in `tools/scene.py`). How he faces is unchanged
  (tipped 5.1, turned 9.1 by the pairs). Docs: SPACE (steps list), DECISIONS (size check as a standing
  test), PRINCE_SPEC (his size), Q44, PLAN. Tests: 49 passed.
- **Next:** step 5 of the 3D grounding, depth lines, on the owner's go.

## 2026-11-16 — Session 6 (cont.): his size floor: an adult Netherland Dwarf
- Owner: 12.3 x 10.5 cm "would make him incredibly small. He's of a small breed, but he's not a juvenile.
  Go off of the measurements for a netherland dwarf as your floor". Looked up (web): adult Netherland Dwarf
  shoulder height 12.7-15.2 cm, length 19-23 cm, 0.9-1.1 kg, ears 5-6.4 cm (dimensions.com, Wikipedia; one
  outlier site's 33-50 cm length disagrees with the rest and was not used). No loafing height or width
  published -> floor: the top of his head >= 12.7 cm.
- At six inches only the camera's height on him and the lens change his size; the lens was already the
  shortest that fits, so the camera sits lower: the smallest drop below his eyes that reaches the floor is
  2.4 cm (between his eye and nose height; ~1.5 cm with a 24 mm lens). `tools/scene.py` now searches for
  it (`ND_FLOOR_TOP_OF_HEAD_CM`; the lens is passed through properly: a default bound at definition time
  had made a 24 mm comparison silently use 26 mm). Camera 7.4 cm up, 15.2 cm in front, lens 1237 px; his
  size (rough): 15.5 cm wide, 12.7 to the top of his head, ear tips 13.6, eyes 9.9, nose 6.0.
- How he faces, re-measured with this camera: head tipped 6.0 deg his left side up (5-7), turned 7.8 deg
  toward his left (eye ovals 5.7; direction solid, amount 5-9); body 3.5 deg toward his right (rough).
- The 3D page's text is now generated from the camera file (it had hand-typed old sizes). Tests: 49 passed.
- **Next:** owner review; then step 5 of the 3D grounding (depth lines) on the owner's go.

## 2026-11-16 — Session 6 (cont.): his size approved; what kind of rabbit he is
- Owner: "those numbers seem to fit him" (15.5 cm wide, 12.7 cm to the top of his head); no tape measure.
  Breed unknown, a dwarf: maybe half Dwarf Hotot, half Netherland Dwarf (or Hotot x Polish). Fluffier and
  rounder than a purebred Dwarf Hotot, less defined hotot eye rings, an even smoother face (the ridge
  between his eyes slopes gently down to his mouth), even less neck, even tinier ears. Recorded as identity
  features in PRINCE_SPEC and DECISIONS; camera file status: size approved.
- **Next:** step 5 of the 3D grounding (depth lines), on the owner's go.

## 2026-11-16 — Session 6 (cont.): he is him, no breed orthodoxy
- Owner: "I don't want you to adhere to breed orthodoxy for anything, or look up a breed and then adhere him
  to it ... just conceptualize him as him ... he is just a little round fluffy guy."
- Cause of the risk: when setting his size floor I had copied a breed's length, weight and ear length into
  the docs; the ear length (5-6.4 cm) is far longer than his tiny ears and could later have pulled him
  toward a breed. Re-checked every mention (docs, tools, tests, data): removed all breed details; the only
  outside number kept is the owner's floor on his overall size (top of his head >= 12.7 cm), named as such
  (`SIZE_FLOOR_TOP_OF_HEAD_CM`). PRINCE_SPEC "He is him" and DECISIONS rewritten to describe him, not a
  breed; METHOD item 24. Earlier PROGRESS entries are history and left as written.

## 2026-11-16 — Session 6 (cont.): step 5 of the 3D grounding, depth lines (first pass)
- Owner: "Begin." Photo used: `data/photos/anchor_front.webp`.
- Rule 1 kept: the shell (`prince/shell.py`) is parametric (two smoothly joined ellipsoids: body sitting
  into the surface, head with the measured turn/tip; 11 numbers) and his outline only measures it
  (`tools/depth_lines.py`: silhouette through the anchor camera vs his outline; ears, peets and tuft not
  scored; nose on the surface at six inches; head ends at his chin).
- Fit history (each looked at on the photo): 80% overlap with nonsense shapes -> cause: a traced hit read
  "on the edge" not "inside" (fixed: read 4 mm past the hit) and zero-start settings never moved (fixed:
  real first steps) -> 94% but a head egg running below the surface -> clip at the surface, head ends at
  his chin -> 91%, shell shifted sideways and unable to reach his chest's bottom -> body may sit into the
  surface (flat underside) -> **97.5%**, nose on the surface (0.03 mm), 4 starts agree. Lesson 27.
  Rough result: body 13.9 cm wide, top of his head 13.4 cm; the head/body join hit its tightest limit
  (0.5 cm): crisp, consistent with almost no neck. ASSUMED: as deep as wide (round).
- Lines: level rings every 1 cm, slices every 1 cm going back, midline, drawn through the anchor camera only
  where it can see them; the surface's 1 cm grid around him. From six inches the camera sees only the front
  ~5 cm of him (the 5 cm slice is at his outline). Views from his side, above, behind his shoulder, with his
  approved parts painted where the camera saw him (hatched grey where it could not); the shell and lines in
  the 3D page (rays now off by default).
- Bugs found on the way, each fixed with a test where it applies: integer start distance in the tracer;
  far views drew no lines (visibility traced only 60 cm); I misread the side view's highest point (checked:
  it is on top of his head, 5 cm behind his nose); an ellipsoid's exact centre read as surface (0/0).
- Tests: 54 passed.
- **Next:** owner review (Q45: how far back he goes; a side photo would measure it).

## 2026-11-16 — Session 6 (cont.): owner: the face is flat; two fixes; still flat in the middle
- Owner: "the resulting shape is very very flat ... you kept the actual part where depth was important flat,
  then just rounded out the back. Determining face depth ... from what we can see, is far more important."
- Cause: the shell was fitted to his outline only (lesson 28). Measured it: lighting the flat shell explains
  only 72% of his fur's brightness (corrected mask: only eyes, eye marks, mouth lines and his pink nose left
  out; his grey-blue chest kept, it had been wrongly dropped as "dark").
- Shell given its own head/body depths and a muzzle (`prince/shell.py`). Fit 1 (outline + shading + nose,
  eyes held out): squashed his body into a 4 cm slab, eye check worse (45/46 deg vs 56/65): not used.
  Fit 2 (outline + both eye directions + shading + nose, no part thinner than 0.9 of its width): outline
  97.3%, nose 0.8 mm, his right eye 55.9 vs 56.2 deg, his left 53.8 vs 64.9, shading 83% (vs 72% flat).
- Measured per feature (cm behind his nose, flat -> new): eyes 1.7-2.0 -> 2.4-2.6, top of head 2.6 -> 4.5;
  but nostril wings 0.3, mouth corners 0.0, chin 0.0, chest 0.2: **still flat in the middle**. Stopped
  (rule 5): from one straight-on photo how far back his chin and chest sit is not settled (a chest further
  back and bigger fits his outline as well; two equally good shading fits disagree about the light's
  direction). Pictures redrawn from fit 2 but not presented as right. Owner's call: Q46.

## 2026-11-16 — Session 6 (cont.): lights from his eyes; owner stopped the shell refits
- Owner: multiple lights (ceiling light, lamps); use albedo, shadows and the lights in his eyes; then: his eyes
  are clearly not flat, measure their actual angle instead of tuning the eye shape to fit the light.
- Done: each eye measured from its own outline as a bulging cap (`eye_geometry`): both the same shape (ball
  radius ~1.4x the opening), facing 62 and 71 deg from the camera. Its catchlight then shows a light per eye:
  two lights, both ~35 deg up, one on each side of him. Lit by those two fixed lights, the shell explains
  ~88% of his fur's brightness (one free light: 83%).
- Not fixed: the middle of his face is still flat (nostril wings, mouth, chin, chest within ~3 mm of his nose)
  in every refit. Cause: the shell's shape (two broad ellipsoids + a small muzzle) cannot make a nose that
  sticks out with the chin and chest set back, whatever it is fitted to. I kept refitting instead of saying
  so; owner: "stop, this is quite silly". `data/scene/shell.json` holds the last (two-light) refit; the
  pictures and 3D page are still from the previous (eye-direction) shell.
- **Next:** the owner's direction.

## 2026-11-16 — Session 6 (cont.): reading the light straight from his fur (owner: keep it simple)
- Owner: "You're making this too hard ... Look at the shading. Look at the albedo. Look at his little eyes.
  Then just narrow down where the light must be coming from." He is white all over, so his fur's brightness
  and colour are the light. Read directly (`docs/images/space/light_reading.png`; 4 x 4 grid over his fur):
  brightest and warmest at the top of his head and down his right side (197-198, red-blue +11); his left
  side's edge mildly warm; the middle of his face, his chest and belly darkest and bluest (109-124, -21 to
  -26).
- Lights: a warm main light above him on his right side (from the side: his face's middle, facing the camera,
  is not in it); a weaker warm light from his left; a dim cool fill lighting what faces the camera or faces
  down. His eyes agree: catchlights high in both eyes (lights above, ~35 deg up), each eye catching the light
  on its own side.
- For his shape: warm = his surface faces up or to a side; cool = faces the camera or down. The cool middle is
  narrow at his forehead and widens into his chest and belly: his front is round and curves under.
- **Next:** owner's call: read his face's depth directly from this (each spot's warm/cool and bright/dark
  says which way it faces; those directions add up into his shape).

## 2026-11-16 — Session 6 (cont.): one soft light, read from his outline (owner)
- Owner: navy blue blanket under him (some of the blue underneath); maybe one light at a shallow angle on his
  right, not two. Measured with no shape assumed: fur brightness (red, least touched by the blanket) just
  inside his outline vs the outline's facing direction: brightest facing up-and-toward-his-right (226),
  darkest facing down-toward-his-left (95, bluest, -13). One soft light from ~33 deg from straight up toward
  his right explains 94.3% (two lights 94.5%): one light. Eyes agree (catchlights high in both). The blue goes
  with the shade (facing down, toward the blanket). Front/back of the light: not from the outline; his face's
  dim middle says overhead and to his right, skimming across his face (owner: "very shallow angle").
- Bug found: the pink-nose filter (red - blue > 15) also dropped warm-lit fur on his right side, so earlier
  shading fits were missing part of his lit side; limit it to around his nose (not yet changed in
  tools/depth_lines.py: the shell refits are stopped).
- **Next:** owner's call: read his face's depth from his fur's brightness under this one light.

## 2026-11-16 — Session 6 (cont.): depth read from the light on his fur (NOT settled)
- `tools/depth_from_light.py`: light calibrated on his outline (one soft light, ~34 deg from straight up toward
  his right, explains 95% of his edge's brightness); depth read over his visible fur so each spot faces the way
  its brightness says; held by his nose at six inches, edge-on outline, smoothness on facing, a loose pull to
  the shell. A measurement, not the model.
- Run 1 overfit (smoothness effectively off; top of head 24 cm back; light solved as from behind): discarded.
- Runs 2-3: real depth in the middle at last (cm behind his nose: chin 1.7, chest 4.0, top of head 7.0; the
  flat shell had ~0, 0.2, 4.5). But lopsided: his right side reads nearer than his nose (right eye 0.75, left
  2.96), i.e. the light from his right is read as his face turning ~25 deg (pairs measured ~8). Holding his
  mirror pairs to the measured turn (run 3) did not fix it. Held-out eye check: fur around his eyes faces 76 /
  69 deg vs 56 / 65 from the ovals. **Not settled**; outputs `data/scene/depth_from_light.json`,
  `docs/images/space/light_depth*.png` are this run, kept for the record.
- Paused here: the owner is explaining why no extra angles of him are offered (the previous attempt).

## 2026-11-16 — Session 6 (cont.): depth approach scrapped (owner)
- Owner (after the reason no extra angles are offered: a rigid numbers method cannot cope with a rabbit that
  moves): "Literally everywhere. It's not a viable method." Shown what exists; then: "I dislike this. Scrap it,
  lemme think of another method."
- Removed (recoverable from git history, commit ac8e35a): `prince/shell.py`, `tools/depth_lines.py`,
  `tools/depth_from_light.py`, `tests/test_shell.py`, `data/scene/shell*.json`, `data/scene/depth_from_light.json`,
  `docs/images/space/depth_*.png`, `light_depth*.png`; the shell taken out of the 3D page. Docs marked scrapped
  (SPACE, PLAN, STRAND_PLAN, METHOD, Q45/Q46 closed, DECISIONS).
- Kept: room + camera (`prince/space.py`, `tools/scene.py`), his size (approved), landmarks, rays, his head's
  tilt/turn (`tools/facing.py`), the light read from his fur (`docs/images/space/light_reading.png`).
- **Next:** the owner's new method.

## 2026-11-16 — Session 6 (cont.): research: depth from one photo
- Owner: research the most objective way to discern depth from a 2D image; first, what is left (shown: the room,
  camera, size, landmarks, rays, his head's tilt/turn, the light from his fur; screenshots of the 3D room).
- Research written up in `docs/DEPTH_RESEARCH.md`: classic shape-from-shading is underconstrained on one photo
  (bas-relief ambiguity: exactly the flat / lopsided faces we got); the field now uses depth models learned
  from millions of real photos (Depth Pro, MoGe-2, Depth Anything 3; surface-direction models). Most
  objective available: several independent models, each put in the room through our camera and checked
  against what they were not told (his nose at six inches, his size, his outline, his head's tilt); agreement
  = measured, disagreement shown for the owner. Measurements only (rule 1). Feasible here on CPU (Hugging
  Face reachable; 4 cores, 15 GB memory).
- **Next:** owner's go to run the models.

## 2026-11-16 — Session 6 (cont.): visible depth from two models (owner's plan: invent nothing)
- Owner's plan: every area of him governed by exactly one photo (other areas from other photos later, no
  overlap); from this photo only what is visible; each ray cut at the measured distance; don't model him.
- `tools/visible_depth.py`: Depth Pro (Apple) and MoGe-2 (Microsoft) on the anchor photo, untouched; one distance
  per pixel of him (637,497 px); saved as `data/scene/visible_depth_<model>.png` (16-bit, 0.01 cm) + `.json`.
- Absolute distances are not trustworthy for this photo (no scale cues: background removed): his nose at 32 cm
  (Depth Pro, lens 2312 px) and 335 cm (MoGe-2, lens 1795 px); owner remembers ~15 cm. Cutting OUR camera's rays
  at a model's own distances would make him 29 cm (or 3 m) wide: each model's distances only fit its own lens.
- His SHAPE, scale-free (cm behind his nose / his width), agrees in the middle of his face: nostrils 0.02 / 0.02,
  chin 0.16 / 0.19, chest 0.29 / 0.29, eyes 0.36 / 0.27; both left-right symmetric. They differ toward his edges
  (widest edge 0.80 / 0.58, belly 0.74 / 0.47, top of head 1.25 / 0.59).
- Scaled to his approved width (15.5 cm), both models put the camera about 25-31 cm from his nose (Depth Pro 31.3,
  MoGe-2 25.0), not ~15 cm: they read weaker perspective than six inches would give. Owner's call.

## 2026-11-17 — Session 6 (cont.): each model's surface placed in the room with its own camera
- Owner, on the models' camera distance (25-30 cm, not six inches): "Maybe I misremembered. Either way I trust
  them." So each model is placed with ITS OWN camera (`tools/visible_depth.py`, now two steps: `--measure` runs
  the models; by default it only places them): its own lens and rays, straight on; one number per model so he
  is 15.5 cm wide (approved), shape untouched; up from the owner's memory (eyes 0.5 cm above the camera); the
  surface through his two peet bottoms, origin under their middle. Every point lies on its own pixel's ray
  (reprojection error ~1e-13 px). Nothing smoothed, filled, removed or merged.
- Caught before showing: (1) lesson 26 again inside the models (they assume the cropped picture's centre is
  straight ahead; "level" on that put the camera at his nose height): up now from the owner's memory (lesson
  29); (2) the new flat side/top chart was a mirror image (lesson 30), fixed; older pictures and the 3D page
  checked: they project through real cameras. (3) A sign slip in the tilt search (hit its limit), fixed.
- Results (cm): Depth Pro: camera 30.4 from his nose, 14.3 up; top of head 18.3, eyes 14.8, nose 11.0, ear tips
  19.7; peets 13.1 behind his nose. MoGe-2: camera 24.5, 12.9 up; top of head 16.7, eyes 13.4, nose 9.5, ear
  tips 18.0; peets 5.7 behind his nose. Peet bottoms level within 0.13 / 0.01 (free check). The cropped
  picture's centre is 5.6 / 7.1 deg below where the camera aimed (six-inch camera: 4.9).
- Seen from the side (`docs/images/space/visible_depth_side_top.png`): MoGe-2 looks like a rabbit sitting up;
  Depth Pro leans his face 13 cm out over his peets and pulls his outermost pixels far back (edge blend).
- **Open (Q47):** his approved width and height cannot both hold with the models' cameras (at 15.5 cm wide the
  top of his head is 16.7-18.3 cm, not 12.7). The 12.7 relied on the six-inch camera's assumption that his
  peets sit right under his face. Owner's call.
- 3D page (`docs/space/room.html`) rebuilt: each model with its own camera, his points coloured as the photo,
  his outermost 4 px on a toggle, camera's view per model (photo hidden), the six-inch camera kept, off by
  default. Tests: 56 passed (7 new, `tests/test_visible_depth.py`). check.py: does not exist (no match claimed).
- **Next:** the owner's answer to Q47 and their look at the two surfaces; then the next photo's areas.

## 2026-11-17 — Session 6 (cont.): the two models compared; MoGe-2 it is (owner)
- Owner: "compare them both. Personally, I think it is very obvious which one looks more like a rabbit."
- Overlaid in the same views (`docs/images/space/visible_depth_compare.png`, from `tools/visible_depth.py`),
  both 15.5 cm wide, cm behind his nose (MoGe-2 / Depth Pro): chin 2.6 / 2.2, chest 3.7 / 4.0 (agree);
  eyes 4.4-4.7 / 5.8-6.1, top of head 8.4 / 14.3, belly 6.1 / 10.3, peets 5.7 / 13.1, ear tip 10.0 / 17.5;
  lowest point -0.1 / -1.1 cm (4 px inside his outline), deepest seen 11.7 / 27.2 cm (edges: 12.3 / 43.7).
  MoGe-2 sits up like a rabbit; Depth Pro is a forward-leaning wedge. **MoGe-2 used from here on**; Depth Pro
  set aside (kept, off by default in the 3D page). Logged in DECISIONS; Q47 (b) answered, (a) open for MoGe-2.
- Tests: 56 passed. check.py: does not exist (no match claimed).
- **Next:** the owner's call on his size (Q47 a): 15.5 cm wide (top of head 16.7) or 12.7 tall (11.8 wide).

## 2026-11-17 — Session 6 (cont.): his size from the model (owner)
- Owner (Q47): "I agree with whatever the model says. If the model says so then I agree."
- MoGe-2 cannot tell his real size from this photo (alone: 2 m wide, 3.35 m away; no background), so his
  approved width stays the one size number; the rest is the model's: **15.5 cm wide, 16.7 cm to the top of his
  head, eyes 13.4, nose 9.5, ear tips 18.0; camera 24.5 cm from his nose, 12.9 cm up**. Above his adult floor
  (12.7). The six-inch camera's size numbers marked superseded (DECISIONS, SPACE, PRINCE_SPEC, PLAN; Q47 closed).
- No code or data changed (the placement already used the approved width). check.py: does not exist.
- **Next (owner's go):** make MoGe-2's camera the room's camera for the anchor photo (`data/cameras.json`), so
  his outline, landmark and part-line rays and how he faces are all worked out from the same camera as his
  surface (today they still come from the six-inch camera).

## 2026-11-17 — Session 6 (cont.): the room's camera for the anchor photo is the depth model's (owner)
- Owner: "Yes" to making MoGe-2's camera the room's camera. `tools/scene.py` now takes `anchor_front` from the
  depth model's placement (`data/scene/visible_depth_moge2.json`); the six-inch camera is kept in
  `data/cameras.json` as `anchor_front_six_inches_superseded`. His outline, landmark and part-line rays
  (`data/scene/anchor_rays.json`, reprojection 0.006 px), the room pictures and how he faces were redone with it,
  so everything for this photo shares one camera. `tools/visible_depth.py` reads his widest row from his outline
  (no camera needed), so the two tools do not feed each other in a loop.
- How he faces, with this camera: tipped about 5 deg, his left side up (solid, 4-6); turned toward his left
  (direction solid; amount 5-13 deg: mirror pairs 12.7, eye ovals 5.3; not settled); body about 4 deg toward
  his right. Its "5-9 deg" summary had been written in by hand: now computed. The facing picture's header was
  cut off at the right: split into lines; its top view widened to show the camera at 30 cm.
- 3D page: one room camera (MoGe-2's) with its outline / landmark / part-line rays and the facing lines (now
  drawn at his measured eyes and peets); Depth Pro set aside, off by default; the six-inch camera off the page.
- His size stored to 2 decimals (top of head 16.65: it had shown as 16.6 on the page and 16.7 in the docs).
- check.py: does not exist (no match claimed).
- **Next:** owner's look. Possible later: read his head's turn and nod from his measured surface (it could
  settle the 5-13 deg).

## 2026-11-18 — Session 6 (cont.): his head's turn and nod, read from his measured surface (owner)
- Owner: "Yes, go ahead" (read his head's turn and nod from the measured 3D points). `tools/facing.py`
  `from_surface()` reads MoGe-2's room points (`tools/visible_depth.py room_points`): mirror pairs in 3D (eyes,
  nostril wings, lip corners; mouth corners and ear bases left out, with reasons), the way each eye faces (a
  plane through its measured surface inside 0.7 x its oval, steady from 0.5 to 0.9), his nose against his eyes
  less what his tip does; landmarks wobbled. Photo-only reading kept as `head_photo_only` (superseded).
- Result: **tipped 4.8 deg** (his left side up; 3D pairs 4.0-5.9, wobble 4.1-5.6; photo alone 4.9: agree).
  **Turned 0.5 deg toward his left** (readings -3.2 to +2.2, wobble 0 to 1.1): square to the camera. The
  photo-only 5-13 deg came from his tip being read as a turn (DECISIONS lesson 31). Body still ~4 deg toward
  his right, so on his body his head turns ~5 deg toward his left. **Nod**, as measured slopes: eyes-to-nose
  line 40 deg below level, nose-to-chin 46, eyes face ~15 deg up (left 17, right 12). A plane through the
  front of his face was tried and not used (round muzzle: depends on the window).
- Caught before showing: the 3D pairs first gave a 19 deg tip (a raw point difference handed to a helper that
  needs a unit direction); fixed; every other caller checked (all unit). The set-aside Depth Pro was looked at
  only as a cross-check (eye facing +4 to +7, eye pair +3.3): not used.
- `docs/images/space/facing.png` and the 3D page redrawn (head axis now the measured one). Tests: 58 passed
  (new: `tests/test_facing.py::test_head_read_from_his_measured_surface`). check.py: does not exist.
- **Next:** owner's look; then whatever the owner picks.

## 2026-11-18 — Session 6 (cont.): where we are; small parts deferred (owner)
- Owner asked where we are: 3D grounding is done for the anchor photo (steps 1-5); step 6 (another angle) waits
  for the owner's next photo. Two stale status lines fixed (SPACE steps 4-5, PLAN 3D grounding).
- Owner: "The remaining parts are very small. I say we save them for when we work on his fur and other delicate
  areas." Recorded (PLAN 2a and build checklist, STRAND_PLAN status, DECISIONS, SPACE): ears' pixel tweaks,
  eyes / lashes / hotot marks, whisker pads, mouth, nose, Bnuy Perturbances, with the precision protocol then.
- Docs only. check.py: does not exist.
- **Next (owner's call):** the next photo, or how his measured surfaces become his parametric model (the later
  plan predates the owner's one-photo-per-area method).

## 2026-11-18 — Session 6 (cont.): the method for more photos (owner)
- Owner: he moves and fluffs differently between photos; previous Claude choked on other angles; make one
  cohesive model from his objective biology, each photo with one master; and "entirely objective ... no
  subjective sculpting": seams and poorly covered areas sorted and covered by rule. A belly-up photo exists
  (mid-roll, awkward angle) for his underside and peet undersides.
- Written up: `docs/MORE_PHOTOS.md` (linked from CLAUDE.md, SPACE step 6, DECISIONS): biology fixed / pose and
  fur per photo; home pose = the anchor's; head first, then rigid parts, then the body (as-rigid-as-possible);
  scale from biology; masters by a quality score (anchor first); seams along least disagreement, fixed blend
  weights; gaps covered by photos; checks on biology only, tolerances fixed in advance. Docs only.
- **Next:** the owner sends the belly-up photo (background removed if it shows the room); before placing it, fix
  the tolerances, seam band and quality-score formula.

## 2026-11-18 — Session 6 (cont.): the old branch's photos, brought in and sorted (owner)
- Owner: get every photo from the old branch (`claude/quirky-hopper-4ag8pj`) and sort them by angle; they won't
  line up perfectly (he moves); some are stylized expressions for rigging his face later; backgrounds are blurred.
- Only its `references/` pictures were taken (none of its docs or tools). In `data/photos/` with
  `data/photos/index.json`: 18 photos sorted by where the camera is around his body (`by_angle/01_front` x8 ...
  `11_front_low`) + the owner's labelled sheet; 12 images made from the front photo (`expressions/`, for his face
  later); 27 AI-generated close-ups (`ai_generated/`: C2PA content credentials say ChatGPT's gpt-image made them,
  2026-10-17), kept but never used to measure him. The old master is pixel for pixel our anchor. Not copied: the
  old branch's small crops of the sheet and its JSON.
- Sides checked by geometry (nose to the picture's right = the camera on his right): the owner's labels name
  his sides, except "Looking Left/Right" (camera side). CLAUDE.md: a note that only real photos measure him.
- check.py: does not exist.
- **Next:** owner's look at the sorting; then fix the tolerances, seam band and quality score
  (`docs/MORE_PHOTOS.md`) before placing any photo.

## 2026-11-19 — Session 6 (cont.): the AI close-ups explained (owner)
- Owner: the 27 close-ups were zoomed-in crops of existing photos, upscaled with AI to help the previous attempt;
  "AI upscaling is very unobjective and we shouldn't use those ones." Recorded in `data/photos/index.json` and
  DECISIONS (rule: no AI-upscaled, generated or edited image measures him; zoom the real photos instead). They
  stay in `data/photos/ai_generated/`, unused. Docs and index only.
- **Next:** fix the tolerances, seam band and quality score (`docs/MORE_PHOTOS.md`) before placing any photo.
