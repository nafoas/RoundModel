# The method: how Prince is being built, and what to do when

This is the working method, built up with the owner over many rounds. It says
what to do in each situation and why. When in doubt, follow this file;
`docs/DECISIONS.md` has the history behind each rule.

---

## 1. First principles (always)

- **He has to look like he is.** Prince is a real, small, very round, white,
  fluffy rabbit with little hotot eye marks. Every step is judged by whether it
  keeps him *him*, against the anchor photo (`data/photos/anchor_front.webp`).
- **The anchor photo is the ground truth**, never something to trace (except
  whiskers and wisps, see §6). Say which photos you're using as references.
- **Not a hard shape, but subtle.** Never excuse a shortcut by calling it hard.
  The difficulty is precision, and precision is the job.
- **Rules live in files.** Re-read `CLAUDE.md`, this file and the current plan
  at every milestone. Log every step in `docs/PROGRESS.md`.

---

## 2. Two kinds of area, two ways of working

Every part of his edge is either a **gentle area** or a **sensitive area**.
Decide which before touching it.

### Gentle areas: his furry sides
Where: the long sweep of his sides (cheeks down along the undercarriage), and
anywhere his edge is just fur.
- The boundary follows **the edge of his body: where his solid body ends and the
  intermediate fur begins** (owner, 2026-11-08). The intermediate fur between
  his body and the wisps is its own class with its own colour; the body line must
  not run through it. (The first version ran through the middle of the fuzzy
  edge and sat out in the intermediate fur; a too-strong correction then cut
  into him near the eyes.) Current: edge of the 50% coverage region with
  anything narrower than a 9 px-radius disk removed, 2 px RMS spline; peets use
  r = 5, 1 px RMS. Checked with the into-fringe measure (§7).
- It must come out **less jagged than the raw photo edge, never more** (checked
  per tile).
- **Don't flag the natural fuzz.** It stays part of him as a soft-edge quality,
  recreated later by the fur. Only distinct tufts and strands are split off
  (§5).
- **Approved stretches are locked as data.** Once the owner approves a sensitive
  stretch (the top of his head: ears, eyes, eye marks, wisp bridge), it is
  saved under `data/lines/` and used exactly; later changes elsewhere can't move
  it. Hand-offs into it are short and checked for kinks.

### Sensitive areas: where his identity lives
Owner: "I need him to look like he is, and that involves you being incredibly
precise when it gets to his little sensitive, detailed areas." List so far:

| Area | Why it matters (owner) | Status |
|---|---|---|
| **Eyes and his black hotot eye marks ("eyeliner")** | "Eyes are the window into the soul"; the marks are "really what makes him, him"; "if his eye area is shaped slightly wrong he loses his identity" | Protected in the outline (§3) |
| **Ears** (each one) | Tiny, detailed, identity | Tight fit in the outline |
| **Peets** (each one) | His little front feet | Faithful fit **below the approved peet line** (the line defines the zone, not a row); own step later |
| **Underfluff / pelvis** | "His pelvis needs to look right and he needs to have the right stance" | Peet line approved; own step later |
| **Eye lashes** | "The ear and eye lashes need to be incredibly precise"; "his little eyes mean a lot" | Own separate step later; band at ears/eyes provisional |
| **Mouth, nose, whisker pads** | Detailed, identity | Later steps |

When working in a sensitive area, **use the precision protocol (§3)**, always.

**For later: each of these gets special care as a unit of its own** (owner,
2026-11-07). The body outline only places them roughly within his silhouette.
Each ear, each peet, the underfluff, and later the mouth, nose and whisker pads
will be worked on **individually and separately**, each in its own step with
the precision protocol and the owner's review. Known to-do: **the ears need
pixel-perfect tweaks**, saved for when they're worked on individually.

---

## 3. The precision protocol (sensitive areas)

Use this for eyes, eye marks, ears, peets, underfluff/pelvis, mouth, nose,
whisker pads, and anything the owner calls sensitive.

1. **Fit as tightly as possible.** Low blur, tight spline (currently 2.5 px blur,
   0.8 px RMS across the top of his head). Never the gentle-area settings.
2. **Keep strands from pulling the line**, but never let a strand filter touch a
   protected feature. Thin strands (lashes, eyebrow whiskers, single hairs) are
   removed before fitting (grey opening, r = 4) so the line follows *him* under
   them. Then protected features are merged back in exactly (step 3).
3. **Protect identity features explicitly.** For the eye marks: every pixel
   darker than 130 connected to the eye's dark core is the mark. It is merged
   into the outline on a grid 8× finer than the photo, with a 0.5 px safety
   margin, so the line follows the mark's own edge. **Not one pixel of a mark
   may be outside.** Do the same for any new identity feature the owner names.
3b. **Pixel-precise edges for identity areas** (owner, 2026-11-09, the ears:
   "go pixel by pixel, including all the little notches, kinks ... they're his
   little ears. They are detailed, and very intricate"). The edge is the 50%
   fur-coverage level at the photo's own resolution (no blur), long strands
   removed first, smoothed only enough to remove pixel stair-steps (≤ 0.25 px
   RMS; result within 0.2 px median / 0.9 px max of the raw edge). Whisker roots
   are bridged (the part continues under them). Spliced in with short blends
   that are checked for kinks. Real animals are asymmetric: keep it.
4. **Measure, don't eyeball.** Check every protected pixel's inside fraction at
   1/8-px precision on every run (`eye_marks_check` in `body_outline.json`).
   Expected result: 0 pixels not fully inside, 0.000 px area outside.
5. **Look pixel by pixel.** Render the area at 10-16× with a grid, one square per
   photo pixel, the line drawn on the photo, and row/column numbers. Read the
   rows where the line meets the feature. Show these grids to the owner.
6. **Measure smoothness at joints.** Where curves join or a bridge meets the
   outline, measure direction change per 2 px and compare with the natural curve
   next to it. A joint sharper than its neighbours is a kink: find why and fix it.
7. **Owner-guided bridges** for things the owner says are not his body (e.g. the
   rogue wisp above his right eye): replace only that stretch with a cubic
   Hermite curve, joining directions measured **only from outside the stretch**.
   Record name, rows and the owner's words under `owner_guided`. Send the thing
   bridged past (a wisp, a whisker) to its own layer so it isn't lost.
8. **If a fix makes a sensitive area worse, undo it and stop.** Say so plainly,
   show what happened, and ask. (A wider strand filter once hooked the line into
   his eye area: undone, not tinkered with.)
8b. **The owner's sizes win.** "A tiny bit" means a few px. Do what was said;
   if a measurement suggests more, mention it, don't apply it.
9. **When you can't tell whether something is him** (a bump: his head or fur?),
   don't guess: show the pixel view and ask the owner. Their answer becomes an
   owner-guided decision.
10. **Every protection gets a test** (`tests/`), including edge cases. Tests
    have already caught a real flaw (smoothing shaving a mark's corners).

---

## 3b. Parts are whole, even where something covers them

Owner, 2026-11-09: "some of the little bluish fur tufts cover some of the edge
of the cream peets, but the peets still extend that far ... we can make the peet
then extend the fur over it when we make it, but we need to not cut off part of
his peets for the fur."
- A part's boundary marks where **the part itself** ends, not where it stops
  being visible. Where fur, a tuft, lashes or whiskers overlap a part, the part
  continues underneath, completed from its own visible shape (fit its whole
  visible edge and continue the curvature under the overlap).
- The overlapping thing is its own layer and is laid back over the part when
  he's built. Never cut a part short to make room for what covers it.
- Applies everywhere: peets under the tuft, ears and eyes under lashes and
  brow fur, the mouth and nose under whiskers, etc.
- When unsure how far a hidden part reaches, err on the side of more part, and
  show the owner.

## 4. Judgment lines (hidden or ambiguous boundaries)

Where a boundary isn't visible (e.g. his pelvis hidden under the underfluff):
- Look for the faint real cue first (the owner spotted a faint gray crease on
  top of the left peet). Measure where it's clear, judge where it's faint, and
  say which is which.
- **Show a drawn guess before building on it.** Don't reinterpret the owner's
  words ("semicircular… across" was once misread as a dome over one peet).
- Iterate with the owner until approved; store the control points, smoothing
  and how it was reached (`data/lines/peet_line.json`). Approved lines are used
  as given, never refit.

---

## 5. What is what: the guide (owner-approved definitions)

From the golden tiles (`docs/images/golden_tiles.png`):
1. **Tufts hanging off him** (e.g. between the peets): FLUFF, tips included.
2. **Peet undersides:** belong to that PEET. Faint hairs lying below: WISPS.
3. **Feathery/spiky fringe along his edge:** soft edge of the body or ear.
3b. **Intermediate fur** (owner, 2026-11-08): the band of fringe between the
   edge of his body and the wisps is its own class (own colour), not body.
   This supersedes the earlier "fringe = soft edge of the body". Its outer edge
   is the general edge of the dense fringe: smooth, tied to the body line,
   never pulled out by long single hairs (they're removed before measuring).
   Below the approved peet line, the band belongs to the peets / underfluff.
4. **A hair is a WISP** only if it reaches clearly past the general fringe
   line, or stands on its own with background on both sides for most of its
   length. Wisps are taken full length, bases included.
5. **Long, dark, straight hairs at cheek and mouth height:** WHISKERS, full
   length, including the root running into the fur.
6. **Thin dark hairs at the ears:** eyebrow WHISKERS.
7. **Ear halo:** the ear's soft edge.
8. **Lashes:** outside the body line; the black eye *mark* is inside (§3).
9. **Rogue wisp above his right eye:** WISP (owner-guided bridge in the outline).

Parts, each with its own colour and step: head, undercarriage, each ear, each
peet, fluff tufts, wisps, whiskers. Order: body outline → ears → peets → fluff →
wisps → whiskers. Whiskers are coloured precisely, then ignored (weight 0)
until last, never removed or painted over.

---

## 6. Representation

- **Pixel convention (project-wide):** pixel (col, row) covers [col, col+1) x
  [row, row+1); its centre is at (col+0.5, row+0.5). Stored curves, drawings,
  checks and tiles all use it (a half-pixel mismatch was found and fixed; a test
  guards it).
- **No pixelly edges.** Boundaries and strands are sub-pixel smooth curves
  (splines), never pixel masks. Pixels appear only when rendering, anti-aliased.
- Edge pixels have soft, fractional ownership.
- **Tracing is allowed only for whiskers and wisps** (frozen data, reproduced
  exactly, added last). Never for the body, ears, peets, tufts or coat.

---

## 7. Viewing and checking (all areas)

- **Overlay on the photo, never side-by-side panels.** Comparing two panels by
  eye once made correct background look like missing fur.
- **Review tiles at 4× with their surroundings**, the tile outlined (8× of a
  64 px tile was too blurry and had no context).
- **Sensitive areas: 10-16× pixel grids** (§3.5).
- **Never claim from a downscaled overview.** Say "first pass, not yet verified"
  until zoomed checks are done and shown.
- **Don't game your own scoring.** When a fit rewards something ("darkest path",
  "darkest point per ray"), check what it latched onto (it once chased dark
  undercarriage fur instead of a faint crease). Score what the feature really is
  (e.g. a crease darker than *both* sides).
- **Check the check.** A per-tile "smoother than raw" test passed even when the
  line was wiggly, because the raw edge is so jagged. A passing number is not
  approval; the eye and the owner decide.
- Rendering artefacts aren't defects: a gap in a drawing may just be an unclosed
  polyline. Measure before "fixing".

---

## 8. Working with the owner

- **The owner reviews every tile**, in batches of about 20, in chat with review
  sheets (no local web page). Nothing is done until they approve it. The ledger
  (`data/strands/ledger.json`) records per-part status per tile: `todo →
  self-checked → owner-approved`. Only the owner's words make a tile approved.
- **When the owner flags a mistake:** fix it, name the cause, re-check every
  place the same cause could apply (e.g. *both* eyes, *both* ears), log it in
  PROGRESS and the Lessons in DECISIONS, and show the fix with zoomed proof.
- **Ask only what only the owner can answer** (is this bump his head or fur?
  whisker or wisp?), with a picture. Resolve everything else yourself.
- **One bounded task per session**; don't run long loops on your own decisions.
  If a step isn't going well, stop and say so before writing another fix.
- **Report honestly**: what was done, what failed, what was undone, numbers with
  what they do and don't prove.

---

### Measured fidelity check (`tools/review_batch.py`)
Per tile: **cut** = solid body pixels outside the line by > 1 px; **bulge** =
pure-background pixels inside the line by > 3 px; **smooth** = smoother than the
raw edge. Plus: every eye-mark pixel inside; the approved peet line inside the
silhouette. Its sensitivity was tested: shrinking the outline 3 px or growing
it 4 px is detected. **Limit:** sharpest on crisp edges (ears, eyes); in fuzzy
fringe a few-px drift may not register, so the visual check of every tile is
still required.

## 9. Per-batch routine (step 3 onward)

1. Re-read `CLAUDE.md`, this file, the current plan, the latest PROGRESS entry.
2. For the batch's tiles, decide: gentle or sensitive (§2). Sensitive → §3.
3. Do the work; run `python -m pytest -q`, the tool's built-in checks, and
   `python tools/review_batch.py <batch> <first> <last>` (fidelity + sheets).
4. Self-check: 4× context for every tile; pixel grids for every sensitive spot;
   measure joints and protected features.
5. Update the ledger (`self-checked` + a one-line note per tile).
6. Regenerate review sheets; commit and push.
7. Send the sheets (or, when working on my own, keep going); list what was
   checked and what's uncertain. Questions go in `docs/OWNER_QUESTIONS.md` with
   what I did in the meantime (intuition + earlier guidance).
8. Apply the owner's verdicts; mark approved tiles `owner-approved`.

---

## 10. Tools and files

| What | Where |
|---|---|
| Edge tiles + ledger | `tools/edge_tiles.py` → `data/strands/ledger.json` |
| Body outline (gentle + sensitive + eye-mark protection + owner-guided bridges) | `tools/body_outline.py` → `data/strands/body_outline.json` |
| Approved peet line | `data/lines/peet_line.json` |
| Review images | `docs/images/` (batch sheets, golden tiles, eye-corner pixel grids) |
| Tests | `tests/` (`python -m pytest -q`) |
