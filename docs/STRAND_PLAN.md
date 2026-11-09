# Strand-by-strand classification of the anchor photo

**Status: AGREED with the owner (2026-11-07). This is the current plan. Work
starts with step 1 below. The peets/underfluff/body line is already approved.**

## Why this exists
Three automatic attempts (2026-11-07) to split the anchor photo into
core / fluff / wisps all failed the same way: the dark tufts hanging down from
the undercarriage, between and around the paws, were labelled as solid body.
Rule-based whole-image methods treat "dark and dense" as "solid", and tweaking
them piles mistake on mistake. The owner decided: go hair by hair, done once,
done right.

## Classes
The owner first described three levels (solidly him / denser fluff / wispy
hairs); that became the parts table below, each part with its own colour.
- **BODY (head, undercarriage)** — solidly, immutably him, bounded by a gentle
  smooth curve. Includes the fine natural fuzz along his edge as a soft-edge
  quality.
- **EARS, PEETS** — his other solid parts, each shaped separately.
- **FLUFF** — distinct tufts of fur that hang off or stick out from the body,
  e.g. the tuft under the undercarriage between the peets (owner: there "he"
  ends and "fur" begins). NOT the general fine fuzz along his edge.
- **WISPS** — individual long wispy hairs (full length, bases included), fluff
  under the peets. Kept exactly as in the photo.
- **WHISKERS** — their own class; coloured precisely, otherwise ignored until last.
- **BACKGROUND** — pure white.
Definitions are refined with the owner on the golden tiles (step 2).

## Scope (stated honestly)
"Every hair" means every strand that **crosses or forms the edge** of him, plus
whiskers lying over his face. The interior coat is thousands of overlapping
hairs that are already CORE; classifying them one by one would change nothing.
The edge band runs from where fur is fully solid out to the last strand tip,
around the whole outline. Step 1 measures how many strands that is.

## Parts, colours, and order (owner direction, 2026-11-07)
Each part gets its **own colour** and is **shaped in its own step**. Shaping
one simple shape at a time is easier and safer than shaping everything at once.

| Part | Notes |
|---|---|
| BODY: head | smoother, sloping; ends at the chin fold |
| BODY: undercarriage | fluffier mass under the chin, down to the peets |
| EARS (left, right) | short, wide, rounded |
| LEFT PEET | its own part, like each ear: own colour, own shaping step |
| RIGHT PEET | its own part, like each ear: own colour, own shaping step |
| FLUFF | distinct tufts, e.g. the tuft hanging between the peets |
| WISPS | distinct long wispy hairs, fluff under the peets |
| WHISKERS | all whiskers, including those lying over his face |

Order: body outline → ears (each) → peets (each) → fluff → wisps → whiskers (last).
Each step gets its own review before the next starts.

### Peets / underfluff / body boundary: APPROVED
`data/lines/peet_line.json` (picture: `docs/images/peet_line_approved.png`).
Notch on his left side → along the faint gray crease on top of the left peet →
across, with a gentle dip between the peets → a hump over the right peet → the
notch on his right side. Body above; below it are three separate things: the
**left peet**, the **right peet** (each its own part, like the ears, decided
2026-11-07), and the **underfluff** tuft between them. Each peet's soft
underside belongs to that peet. Owner-guided,
approved after 5 rounds (see DECISIONS.md). Use it as given; don't refit it.

### Whiskers: colour them, otherwise they don't exist
- Whiskers, including those lying over the cheeks and face, are coloured as
  WHISKERS, precisely (only the whisker itself, nothing around it).
- They are **never removed, painted over, or "filled in"**.
- For every other step, whisker pixels are **ignored**: neither positive nor
  negative. They don't count as body, as gap, or as background, and they're
  excluded from all colour/texture estimates, outline fits, and scores
  (weight 0). Overlapping whiskers would otherwise corrupt what's under them.
- They're added back only once everything else is done.

## Gentle edges and judgment lines (owner direction, 2026-11-07)
- **His edge is inherently furry. Don't flag it.** The fine fuzz along his
  outline (ears, head, sides) is a soft-edge *quality* of CORE, recreated later by
  the fur. It is NOT cut into separate fluff/wisp fragments. Flagging every
  little bit of fuzz produces jagged edges.
- **The core boundary is a gentle, smooth curve.** It's fitted with a smoothness
  constraint (limited curvature, few control points) and runs *through* the soft
  fuzzy edge rather than hugging individual hairs.
- **The outline step must make him smoother and less jagged than the raw
  pixels, never more.** Test: the core boundary's curvature/roughness must be
  lower than the raw edge's, everywhere.
- **Only distinct things are split off:** real tufts (e.g. the one hanging under
  the undercarriage between the paws) become FLUFF; individual strands that
  clearly stand out (whiskers, long wispy hairs, fluff under the feet) become
  WISPS.
- **Judgment lines.** Where his body is hidden (e.g. his underside behind the
  tuft between the paws), the boundary is the most plausible smooth body contour
  (paw to paw, continuing the curvature of the visible body), with fur hanging
  below it. Such segments are marked **inferred** in the data and listed for the
  owner to review one by one. They're never presented as detected.
- Consequence for scope: "strand by strand" applies to WISPS, whiskers and named
  FLUFF tufts, not to the general edge fuzz.

## No pixelly edges (owner requirement)
Labelling whole pixels produced blocky, stair-stepped edges that make his fur
look pixelly. A real edge doesn't line up with the pixel grid. So:
- **Strands are smooth curves, not pixel blobs.** Centerlines are fitted with
  sub-pixel precision (fit the brightness profile across the strand) and stored
  as splines with width and opacity varying along the length (tapering tips).
- **The core boundary is a smooth curve**, placed between pixels where needed,
  never a pixel staircase.
- **Edge pixels have soft, fractional ownership** (e.g. 60% fluff, 40%
  background), from how far each pixel is from pure white.
- **Pixels exist only at render time.** Masks and overlays are drawn from the
  curves with anti-aliasing. The 3D comparison uses soft edges against soft
  edges, never binary masks.
- **Review overlays use thin outlines and curves** on the photo, not flat colour
  fills, which hide the detail the owner needs to judge.
- Limit: many hairs are 1-3 px wide in a 1098×1433 photo. Sub-pixel fitting goes
  past the grid but can't recover what the camera didn't capture. Strands too
  faint or blurry to trace confidently are marked **uncertain**, never invented.

## Process

### 1. Tile the edge, keep a ledger — DONE 2026-11-07
Result (`python tools/edge_tiles.py`; reference: anchor photo only):
- 152 tiles of 64×64 px: 108 along the outline (T001-T108, starting at the top
  of his left ear and going round toward image-right) + 44 extensions (E001-E044)
  following the outer fringe and whiskers to their tips. Ledger:
  `data/strands/ledger.json`; picture: `docs/images/edge_tiles_overview.png`.
- Coverage proof: all 107,874 edge-band pixels are inside a tile (0 uncovered).
  Tests: `tests/test_edge_tiles.py`.
- Checked at zoom on all sides (peets, both sides, ears, whisker tips).
- Job size, honestly: an automatic count found 95 strand pieces ≥ 8 px outside
  the body (18 ≥ 20 px, 5 ≥ 40 px), but crossing hairs split and overlapping
  ones merge. Visual estimate: **about 40-100 distinct wisps and whiskers.**
  The fine fuzz along his edge stays part of him (gentle-edge rule) and isn't
  counted.
- **Not yet tiled:** whiskers lying over his face *inside* the outline. They
  need their own small set of tiles before the whisker step.

Original description:
- Walk the full outline and cut the edge band into small overlapping tiles
  (about 64×64 px, viewed at 8× zoom), numbered in order around him.
- `data/strands/ledger.json` lists every tile with a status:
  `todo → annotated → self-checked → owner-approved`.
- A coverage script proves that every edge pixel falls in at least one tile.
  No tile can be skipped silently.

### 2. Calibrate on golden tiles first — DONE 2026-11-07
Golden tiles: T050, T056, T073, T082, T027, T002. Reference sheet:
`docs/images/golden_tiles.png`. **Viewing:** tiles are reviewed at **4x with
their surroundings**, the tile outlined (8x was too blurry, with no context).

**THE GUIDE: owner-approved definitions. Judge every tile against these.**
1. **Tufts hanging off the body** (e.g. T050, between the peets): the whole
   tuft, spike tips included, is FLUFF (underfluff). Not split into strands
   unless a hair clearly stands apart from the tuft.
2. **Peet undersides** (e.g. T056): the soft blurry edge belongs to that PEET.
   Faint thin hairs lying below it are WISPS (fluff under the peets).
3. **Feathery/spiky fringe along his edge** (e.g. T073, T082, T027): part of the
   body's (or ear's) soft edge. Not split off.
4. **Spike vs wisp rule:** a hair is a WISP only if it reaches clearly past the
   general fringe line, or stands on its own with background on both sides for
   most of its length. Otherwise it's soft edge. Wisps are taken full length,
   base included.
5. **Long, dark, straight hairs at cheek and mouth height on both sides** (e.g.
   T073, T082, T027) are WHISKERS, traced full length, including where the root
   runs back into the fur.
6. **Thin dark hairs at the ears** (e.g. T002) are **eyebrow whiskers**: WHISKERS.
7. **Ear halo** (e.g. T002): the ear's soft edge, part of that EAR.

Original description:
- Before any bulk work, the owner and Claude go through about 6 tiles together:
  the hanging tufts under the undercarriage, the paw undersides, a dense side
  fringe, the long wisps on the right, an ear edge, and cheek whiskers.
- The owner's decisions on these become the written definitions above, with
  crops saved as reference. Every later tile is judged against them.

### 3. Annotate each tile strand by strand — IN PROGRESS
**Ears (2026-11-09): pixel-precise, PROPOSED v3 (bases lowered to where each ear meets the flat part of his head), awaiting owner review (Q19).**
Outline over the top of the head is pixel-precise (`tools/ear_edges.py` →
`data/lines/top_of_head_precise.json`, spliced in by `tools/body_outline.py`),
whisker roots bridged. Ear bases end on real notches (`data/strands/ear_bases.json`,
which also holds the ear parts). Pixel views: `docs/images/ear_left_pixels.png`,
`ear_right_pixels.png`. Lashes still reserved for their own step.

**Peets split off (2026-11-09): OWNER-APPROVED.**
`python tools/split_peets.py` → `data/strands/parts_peets.json`: cream peet
(image left), underfluff tuft, gray peet (image right) as closed sub-pixel
polygons; they fill the region below the peet line exactly (0 px gap, 0 px
overlap; test `tests/test_split_peets.py`). Overlays: `docs/images/parts_peets*.png`.
The peet line had to be joined to the outline at both notches
(`data/lines/peet_line_joins.json`): cream side a straight 9.8 px continuation,
gray side an INFERRED curve down the peet's shadowed side to the notch (Q16).
**Peet dividers: owner-approved 2026-11-09** (gray v2, cream v4) (v1: straight, cut the peets off; v2: follows the peets' roundness, but the junction cut off the shoulder; v3: junction moved to x 450; v4: the peet is completed under the tuft fur that covers its edge, widest x 464.5) (`data/strands/peet_dividers.json`,
`docs/images/peet_dividers_*.png`), awaiting owner review before the peets are
split off (Q11). Ears: no dividing line yet; to be proposed next.

**Intermediate fur (2026-11-08): first pass done for all 108 tiles, awaiting
owner bulk review.** Band between the body line and an outer line along the
general edge of the dense fringe (`tools/intermediate_fur.py` →
`data/strands/intermediate_fur.json`; reviews `tools/review_fur.py`, sheets
`docs/images/batch*_fur_*.png`). Outer edge = how far the dense fringe reaches,
measured outward from the body line and averaged along the edge (12 px), with
long straight strands (whiskers, long wisps; >= 35 px, reaching >= 20 px out)
removed first; reach smoothed along the edge (8 px). Density threshold 0.18
(middle of three tried), then 0.21 after the owner's "in just a tiny bit"
(band width above the peet line 2-24 px, median ~8). **Reserved:** rows < 520
(ears, eyes, lashes): provisional, done in their own separate precise step.
Below the approved peet line the band belongs to the peets / underfluff.
Next: owner review; then split off the peets and ears along the drawn lines.

**Body outline: all 108 tiles done, awaiting owner bulk review (2026-11-08).**
T001-T012 owner-approved; T013-T108 self-checked, sheets
`docs/images/batch1..6_outline_*.png`, questions in `docs/OWNER_QUESTIONS.md`.
Next part step pending the owner's answer to Q4 (intermediate fur first?).
**Recalibrated (2026-11-08), resumed.** The owner looked again: the solid-body
line is right on his sides; only the eye areas cut in (the zone joining jumped
to the wrong part of the line under his right eye). Fix: the approved top of his
head (ears, eyes, eye marks, wisp bridge) is **locked** as approved data
(`data/lines/approved_top_of_head.json`, rows < 520, 40 px hand-off). History:
**Was paused (2026-11-08).** Owner: the line was
consistently too far out, sitting in the intermediate fur ("the little
intermediate fur gets its own colour"). First correction (edge of "solid body" =
coverage region opened with a 9 px disk) cut in too far; owner stopped it.
`tools/body_outline.py` currently holds that rejected experiment;
`data/strands/body_outline.json` and the sheets are still the previous (also
rejected, mid-fringe) line. **Next:** calibrate with the owner on ~4 spots
(candidate lines between the two, owner picks), apply that rule, verify with the
into-fringe check, re-review. T013-T060 reset to `todo`; T001-T012 (eyes/ears,
moved < 0.6 px) stay approved.

**Part 1, body outline** (`python tools/body_outline.py` →
`data/strands/body_outline.json`; reference: anchor photo only):
- One closed smooth curve around his whole silhouette (ears, peets, tuft
  included; split off in their own steps). Not drawn per tile, which would
  leave seams; fitted once and reviewed tile by tile.
- Runs through his soft edge (50% coverage). Three curves joined by row with
  40 px hand-offs:
  - **Sensitive zone, y < 520 (both ears and both eye corners): fitted as
    tightly as possible** (2.5 px blur, 0.8 px RMS), after removing thin strands
    (lashes, eyebrow whiskers; grey opening r=4) so the line follows his head
    under them. Owner: if his eye area is shaped slightly wrong he loses his
    identity.
  - **His black eye marks (hotot "eyeliner") are protected:** around each eye,
    every pixel darker than 130 connected to the eye's dark core is the mark.
    The mark (with its soft edge, +0.5 px safety margin) is merged into the
    outline on a grid 8x finer than the photo, so the line follows the mark's
    own edge. Checked every run: 0 of 3,024 (his right eye) and 0 of 4,175 (his
    left eye) mark pixels outside, 0.000 px of mark area outside. Test:
    `tests/test_body_outline.py`. Pixel view: `docs/images/eye_corners_pixels.png`.
  - Peets/tuft: faithful (4 px blur, 1 px RMS) **below the approved peet line**
    (+-10 px hand-off). It used to be "below row 1100", which wrongly made the
    lower furry sides wiggly (found in batch 2, T033-T038).
  - His furry sides: gentle (8 px blur, 4 px RMS).
  (A single smoothing level was tried first: either wiggly on the sides or it
  cut corners off the ears and peets.)
- Check: smoother than the raw edge in all 152 tiles (total turning 33 vs 1872
  rad). Test: `tests/test_body_outline.py`.
- **Review happens in chat** with review sheets (4x with context), not a local
  web page; the ledger's per-tile `outline` field records status.
- Batch 1 (T001-T020): self-checked, sheets `docs/images/batch1_outline_*.png`,
  awaiting owner review.
- **Owner-guided bridge:** above his right eye (image left), rows 368-401, the
  outline had bent out to include the base of a wisp. Owner: "a little rogue
  piece of wispy fur, not an eyebrow." The outline is bridged smoothly past it
  (cubic Hermite, directions matched from outside the stretch; max turn 6.8
  deg/2 px, gentler than the natural curve below). Recorded in
  `data/strands/body_outline.json` under `owner_guided`. Pixel view:
  `docs/images/right_eye_bridge_pixels.png`.
- **Batch 1 (T001-T020): owner-approved 2026-11-07.** Owner: the ears could use
  pixel-perfect tweaks, saved for when each ear is worked on individually.
- **For later:** the ears, peets, underfluff, and later the mouth, nose and
  whisker pads each get special care as units of their own, separately (see
  METHOD §2).
- **For the fluff step:** the underfluff tuft's boundary must include its thin
  hanging spike tips (guide #1); the body outline currently passes just above them.
- **For the wisp step:** the rogue wisp above his right eye (rows ~380-386,
  running left from x ~318 to ~297) must be traced exactly as a WISP.

Original description:
- A ridge (line) detector *proposes* candidate strands. A proposal is only a
  suggestion: each one is individually accepted, edited, or rejected. Proposals
  are never bulk-accepted, and missed strands are added by hand.
- Each strand is recorded as: id, class, centerline spline (sub-pixel), width
  and opacity along its length, root point, tip point, and the tiles it passes
  through.
- The **core boundary** is an explicit smooth curve (sub-pixel) per tile: the line where fur
  becomes solid. Hanging tufts sit outside it.
- Strands crossing tile edges are matched to the same id across tiles.

### 4. Self-check (Claude) before anything is shown
For every tile, automatically:
- Every non-white pixel in the tile belongs to the core, a fluff region, or a
  strand. Zero unexplained pixels.
- Every strand is continuous, root to tip, and matches across tile borders.
- An overlay render of the annotation is placed next to the photo at 8×.
Then Claude visually compares overlay and photo and writes a one-line note per
tile. Anything uncertain is marked **uncertain**, not guessed.

### 5. Owner review in batches
- A local review page (HTML) shows each tile: photo, overlay, strand list, and
  approve / flag buttons with a comment box. Flags save to `data/strands/`.
- Batches of about 20 tiles. **The owner reviews every tile** (decided
  2026-11-07), not a sample.
- Nothing counts as done until every tile is owner-approved.

### 6. When the owner flags a mistake (anti-acquiescence rule)
1. Fix it in that tile.
2. Name the *cause* (which definition or habit produced it).
3. Re-check **every** tile where that cause could apply, not just the flagged one.
4. Log it in `data/strands/mistakes.md`: what, why, which tiles were rechecked.
5. Show the fix. Don't just say it's fixed.
Agreeing with the owner without doing steps 2-4 doesn't count as fixing it.

### 7. Persistence
Every tile's annotation and status is committed as it's done. A new session
reads the ledger and continues from the next unfinished tile. Nothing depends
on remembering the conversation.

## Output
- `data/strands/strands.json` — every strand, with class and geometry.
- `data/strands/core_boundary.json` — the solid-body outline as smooth curves.
- Soft (anti-aliased, fractional) label maps rendered from those, used as the measurement mask
  (body fit uses CORE + FLUFF per owner's decision; WISPS are the frozen layer).

## Open questions for the owner
