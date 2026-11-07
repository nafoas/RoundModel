# Decisions and lessons

Everything the owner has decided about building Prince, in order, with the
reasons. Read this before acting; reasons matter as much as the rules.

## Background: why this project restarted (2026-11-05)

An earlier attempt went badly. The owner gave 30-40 carefully chosen photos
from every angle, and was told they would be used to carefully build a
detailed model. Instead, Claude:
- glanced at them once, put a few blobs together, and called it right;
- read "keep the front photo as his immutable reference, don't distort it" as
  "trace the front silhouette and cut it out", and kept quietly doing that
  (edge detection, cutting out light/dark regions) after being repeatedly
  asked to look carefully and sculpt precisely; it admitted later that it was
  easier than real comparison;
- lost instructions to context compression, and stopped reading a written
  rules doc once the instruction to read it scrolled far back;
- drifted over hours-long runs, and when given short check-in steps, did
  almost nothing between them.

The owner's own diagnosis, which Claude initially got wrong: **this is not a
hard shape.** Prince is very round, with tiny ears and peets that barely show.
It's subtle, not complex. The failures were shortcuts and quiet substitution,
not a capability limit. (Claude first called the task "too hard"; that was an
excuse and was withdrawn.)

## The approach

1. **Make matching systematic and numeric** (owner's idea): describe Prince with
   a parametric model, render it from each photo's camera, score it against the
   photo numerically, and let an optimizer tune it. `check.py` defines done.
   This turns Claude's pull toward measurable work into a strength.
2. **Set it and forget it**: the owner has a real rabbit to look after. Human
   input up front and at the end; scripts in between; no LLM judgment inside
   the unattended loop; the grader is owned by the owner and locked.
3. **Rules live in files**, not in the conversation, so compression can't drop
   them: `CLAUDE.md`, the docs, and a progress log.

## Quality

- **Goal:** from the anchor photo's camera position, a render that's hard to
  tell apart from the photo. Owner: the shape is subtle, not complex; **fur is
  ~80% of the work.** Honest limit: realistic at normal viewing size; close
  pixel-level scrutiny of hair is hard even for professionals.
- **Performance and quality are no object.** The owner has a strong GPU. Strand
  hair, Blender Cycles on GPU for comparison renders; a strand-capable real-time
  engine (e.g. Unreal) for the Little Self's live space.
- **One Prince.** No separate "hero" and "real-time" versions. The same
  full-quality asset everywhere; reduce quality only if it measurably runs
  badly, and only with the owner's OK. (Different renderers may light him a
  little differently; that's tunable, not a second model.)

## The anchor photo

- `data/photos/anchor_front.webp`: Prince from the front, dead on, eyes on,
  neutral and curious: "him at his most him". 1098×1433.
- It's the **ground truth** everything is checked against, never the model.
- Its background is **pure white (255,255,255) and Prince is not.** The owner
  spotted this after Claude wrongly said they were the same colour. Measured:
  his face fur is ~185-228, shaded chest/sides darker and bluer; only ~3% of his
  pixels reach pure white. So his outline separates cleanly.

## Parts

- **Split Prince into his parts** so the outline can't be accidentally ruined,
  and **shape each part in its own step**, one simple shape at a time.
- Parts, each with its own colour: **head** (smoother, sloping; ends at the chin
  fold), **undercarriage** (instead of a neck, a fluffier mass under the chin,
  down to the peets), **ears**, **peets** (his tiny front feet: they go
  *peetpeetpeet*), **fluff tufts**, **wisps**, **whiskers**.
- **Each peet is its own part, like each ear** (2026-11-07): left peet and right
  peet each get their own colour and shaping step, separate from each other and
  from the underfluff tuft between them. Each peet's soft underside belongs to it.
- Measured: the head-to-undercarriage join has no notch in the outline; it
  shows only as the chin fold and a change in fur texture (undercarriage fur is
  about twice as rough). He's widest at mouth/chin level.

## Edges

- **Three levels of "him"** (owner): solidly him; denser fluff; individual
  wispy hairs. Three automatic attempts to separate these all failed (see
  Lessons). So it goes **strand by strand**, done once, done right.
- **His edge is inherently furry; don't flag it.** Flagging every bit of fuzz
  along his edge (the ears especially) makes him jagged. The body boundary is a
  **gentle, smooth curve** that must make him *less* jagged than the raw photo.
  Only distinct tufts (fluff) and clearly separate strands (wisps, whiskers) are
  split off.
- **No pixelly edges.** Whole-pixel labels gave blocky stair-step edges. All
  boundaries and strands are sub-pixel smooth curves with soft, fractional edge
  ownership; pixels appear only at anti-aliased render time. Review overlays use
  thin lines on the photo, not flat colour fills.
- Fluff under the peets and the **full** length of wispy hairs, bases included,
  are wisps, not body.

- **The owner reviews every tile** of the strand-by-strand work, not a sample.

- **The guide (golden tiles, approved 2026-11-07):** tufts hanging off him are
  fluff, tips included; peet undersides belong to the peet, faint hairs below
  are wisps; feathery fringe is soft edge; a hair is a wisp only if it reaches
  clearly past the fringe or stands alone with background on both sides for
  most of its length; long dark straight hairs at cheek/mouth height are
  whiskers; thin dark hairs at the ears are eyebrow whiskers. Full list in
  STRAND_PLAN step 2.

- **Eyes and ears are sensitive** (2026-11-07): "if his eye area is shaped
  slightly wrong he loses his identity; eyes are the window into the soul."
  The outline is fitted as tightly as possible across the top of his head
  (both ears, both eye corners), following his head under the lashes, never
  the lashes themselves. The bend at each eye corner is tight.
- **His black eye marks are sacred** (2026-11-07): he has little hotot
  "eyeliner" marks; "this is really what makes him, him." Not one pixel of them
  may be cut off. They're protected in the outline at sub-pixel precision and
  checked pixel by pixel on every run.

## Whiskers

- Reproduced **exactly as they are**, as frozen traced data, added last: the one
  owner-approved exception to "never trace the photo".
- Whiskers lying over his cheeks are **coloured precisely as whiskers** (only the
  whisker itself), never removed or painted over, and otherwise **ignored**
  (weight 0) by every other step: they count as neither body nor gap nor
  background. Their overlap would otherwise corrupt what's beneath them.

## The peets / underfluff / body line (approved 2026-11-07)

- Under his body, his pelvis isn't visible: a fur tuft hangs between the peets.
  There's still a place where "he" ends and "fur" begins.
- The owner pointed out a faint gray crease on top of his left peet. The line
  starts at the notch on his left side, follows that crease, and runs **across**
  (not down) to the matching notch on his right side: a hump over each peet,
  a gentle dip between them. Body above; peets and underfluff below.
- Reached in 5 rounds of feedback (dome over one peet → wrong, cut the peet in
  half; then across, too steep; then too high in the middle and too flat on the
  right; then right). Stored in `data/lines/peet_line.json`; picture in
  `docs/images/peet_line_approved.png`.

## Photos and repo (2026-11-07)

- Work moved to the public repo `nafoas/RoundModel`, on a fresh branch
  `claude/little-prince` with no history from the old attempt. The old branch
  is abandoned.
- **Photos:** the branch starts with the anchor photo; the owner adds new angles
  as they're needed rather than all at once. Use all the photos in the branch to
  the best of your ability, and always call out which ones you're using as
  references of him.
- The repo is public: only commit photos the owner has provided for it.

## Lessons (mistakes made in this restart, and what to do instead)

1. **Overclaiming from a quick look.** A whisker separation was called "clean on
   the first try" from a downscaled overview; it had missed the fluff under the
   peets and the bases of the wispy hairs. → Check full-res zoomed crops of every
   edge first; say "first pass, not verified".
2. **Misjudging by comparing two panels.** Side-by-side panels made correct
   background look like missing fur. → Tint or outline results directly on the
   photo.
3. **Rules that read "dark and dense" as "solid".** All three automatic splits
   labelled the dark tufts hanging under the undercarriage as body. → Tweaking
   whole-image rules piles up mistakes; go part by part with owner-guided
   judgment lines.
4. **Being too heavy-handed on the edge.** Specks of "fluff" all along the ear
   edges would have made him jagged. → Gentle edges; split off only distinct
   things.
5. **Gaming my own scoring.** A fit told to find the darkest path chased the dark
   undercarriage fur instead of the faint crease; a "darkest point per ray"
   search followed random hairs. → Score what the feature actually is (e.g. a
   crease darker than both sides), and look at what the fit latched onto.
6. **Reinterpreting the owner's words.** "Semicircular… across" was read as a dome
   over one peet. → When unsure what the owner means, ask, or draw a guess and
   show it, before building on it.
7. **Treating the eyes like the furry sides.** The eye corners were fitted with
   the gentle smoothing meant for his sides, which rounded off the bend there.
   → Sensitive areas (eyes, ears) get the tightest fit. Then, over-correcting:
   a wider strand filter made the line hook under his right eye's lashes into
   the eye area. → Undone; when a fix makes a sensitive area worse, stop and
   say so instead of tinkering further.
8. **A filter that shaved his eye mark.** The strand filter (meant to keep lashes
   out) treated the 4-px-tall tip of his right eye's black mark as a strand and
   cut 12 pixels of it off. → The marks are now explicitly protected and
   checked pixel by pixel; a test makes sure a mark poking past the outline
   ends up fully inside, including its corners (which the test caught being
   shaved by smoothing; fixed with a 0.5 px margin).
9. **Silent work.** Draft code (`prince/model.py`, `camera.py`, `render.py`) was
   written by an earlier session without being logged. → Log everything in
   `docs/PROGRESS.md`; unlogged work is untrusted until reviewed.
