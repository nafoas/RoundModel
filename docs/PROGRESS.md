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
