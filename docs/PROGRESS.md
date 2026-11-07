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
