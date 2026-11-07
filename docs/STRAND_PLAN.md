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
| PEETS (left, right) | his tiny front feet ("peets") |
| FLUFF | distinct tufts, e.g. the tuft hanging between the peets |
| WISPS | distinct long wispy hairs, fluff under the peets |
| WHISKERS | all whiskers, including those lying over his face |

Order: body outline → ears → peets → fluff → wisps → whiskers (last).
Each step gets its own review before the next starts.

### Peets / underfluff / body boundary: APPROVED
`data/lines/peet_line.json` (picture: `docs/images/peet_line_approved.png`).
Notch on his left side → along the faint gray crease on top of the left peet →
across, with a gentle dip between the peets → a hump over the right peet → the
notch on his right side. Body above; peets and underfluff below. Owner-guided,
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

### 2. Calibrate on golden tiles first
- Before any bulk work, the owner and Claude go through about 6 tiles together:
  the hanging tufts under the undercarriage, the paw undersides, a dense side
  fringe, the long wisps on the right, an ear edge, and cheek whiskers.
- The owner's decisions on these become the written definitions above, with
  crops saved as reference. Every later tile is judged against them.

### 3. Annotate each tile strand by strand
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
- Soft, blurry underside of the peets: assumed to be the peets' own soft edge
  (gentle-edge rule) unless the owner says otherwise.
