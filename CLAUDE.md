# Little Prince: rules for every Claude session

This project builds a 3D model of Prince, the owner's small, very round, white,
fluffy rabbit, to be the body of the owner's "Little Self" project. He means a
great deal to the owner. Get him right. Read this whole file before doing
anything, and re-read it (plus the current plan file) at every milestone.

**Start here:** the latest entry in `docs/PROGRESS.md`, then **`docs/METHOD.md`
(the working method: what to do in which situation)**, then `docs/DECISIONS.md`
(everything the owner has decided, and why), then the current plan:
`docs/STRAND_PLAN.md`.

**Sensitive areas get the precision protocol (METHOD §3), always:** his eyes and
black hotot eye marks, ears, peets, underfluff/pelvis (his stance), and later
his mouth, nose and whisker pads. Tightest fit, identity features protected and
checked pixel by pixel, owner-guided bridges, and stop if a fix makes it worse.

## Non-negotiable rules

1. **The model is parametric. Never trace, cut out, or segment a photo to make
   the model.** Masks of the photos exist only to *measure* the model. If you
   catch yourself extruding an outline or building geometry from image regions,
   stop. That is the exact failure this project exists to avoid.
   **One narrow, owner-approved exception:** whiskers and wispy hairs. Those
   thin strands are traced from the anchor photo and reproduced exactly, as
   frozen data, added last. This exception covers whiskers and wisps ONLY, never
   the head, undercarriage, ears, peets, fluff tufts, or fur coat.
2. **"Done" is defined by `python check.py`, not by your judgment.** Never say the
   model matches, looks right, or is finished unless `check.py` passes, and
   always paste its full output when you report.
3. **The grader belongs to the owner.** Do NOT edit `check.py`,
   `config/thresholds.json`, anything in `data/` (photos, lines, strands, masks,
   landmarks), or the scoring code in `prince/score.py` to make numbers better.
   If you believe one of these is wrong, say so and stop; let the owner decide.
4. **The front photo is the anchor** (`data/photos/anchor_front.webp`): Prince
   dead-on, eyes on, at his most "him". It's the ground truth everything is
   checked against (not something to trace), and it carries the highest
   scoring weight. Never lower its weight or drop it.
5. **Be honest about being stuck.** If scores plateau, or something isn't going
   well, or you can't do something, or you've lost track of these rules, stop
   and say so plainly before writing any new fix. Never quietly substitute an
   easier task for the one requested.
6. **Check visual work at full resolution before claiming it works.** Never judge
   an image result from a downscaled overview, and never by comparing two
   separate panels by eye: tint or outline the result *on top of* the photo.
   Inspect zoomed crops of every edge region (peets, sides, top, ears) and show
   them to the owner. Say "first pass, not yet verified" until then.
7. **When the owner flags a mistake:** fix it, name the *cause*, re-check every
   place the same cause could apply, log it, and show the fix. Agreeing without
   finding the cause and re-checking doesn't count as fixing it.
8. **Don't game your own scoring.** If a fit or search rewards something (e.g.
   "darkest path"), check what it actually latched onto. A score that went up
   while the result looks wrong means the scoring is wrong.
9. **Keep sessions small.** One bounded task per session. At the end, append to
   `docs/PROGRESS.md`: what you did, results/check output, the next step.

## Photos

- **Use all the photos in this branch (`data/photos/`) to the best of your
  ability, and always call out which ones you're using as references of him.**
  The owner adds new angles as they're needed.
- **The old branch `claude/quirky-hopper-4ag8pj` is abandoned.** Don't follow
  its docs or reuse its tools.
- **This repo is PUBLIC.** Anything committed can be seen by anyone. Only commit
  photos the owner has provided for the repo, and never anything that shows the
  owner's home.
- Prince is a living rabbit: between photos he moves, shifts his weight and turns
  his head, and the camera is never in the same place twice. Differences between
  photos are normal, not errors.

## How he's being built (details in docs)

- **Parts, each with its own colour and its own step:** head, undercarriage,
  each ear, each peet (left and right peets are separate parts, like the ears),
  fluff tufts, wisps, whiskers. Order: body outline → ears → peets → fluff →
  wisps → whiskers (last). Owner reviews each step. See `docs/STRAND_PLAN.md`.
- **Gentle edges.** His edge is naturally furry. The body boundary is a smooth,
  gentle curve that must come out *less* jagged than the raw photo, never more.
  Only distinct tufts and strands are split off.
- **No pixelly edges.** Store boundaries and strands as sub-pixel smooth curves
  with soft edges; pixels appear only when rendering, anti-aliased.
- **Whiskers are coloured precisely, then ignored** (weight 0) by every other
  step until they're added last. Never remove or paint over them.
- **Hidden boundaries are judgment calls**, marked *inferred* or *owner-guided*
  and reviewed by the owner. The approved peets/underfluff/body line is in
  `data/lines/peet_line.json`.
- **One Prince, full quality** (strand hair, GPU rendering). Only reduce quality
  if it measurably runs badly, and only with the owner's OK.

## Where things are

- `docs/METHOD.md`: the working method and when to do what.
- `docs/DECISIONS.md`: every owner decision, with reasons and lessons learned.
- `docs/STRAND_PLAN.md`: current plan: classifying the anchor photo part by part.
- `docs/PLAN.md`: the overall pipeline (numeric fitting, unattended runs).
- `docs/PRINCE_SPEC.md`: what Prince looks like, with measurements.
- `docs/PROGRESS.md`: running log. Read the latest entry first.
- `data/`: owner-owned inputs (photos, approved lines). `prince/`: library code
  (currently an unreviewed draft; see PROGRESS). `tests/`: run
  `python -m pytest -q` before committing any code change.
- Commits end with the trailers the session gives; push to the working branch.
