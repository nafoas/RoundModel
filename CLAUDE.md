# RoundModel: read this first, every session

This repo builds a 3D model of **Prince**, a real, living, very round white
Dwarf Hotot rabbit, from photos his owner took of him. Before doing anything,
read `docs/INTENTS.md` (the owner's intents, in their words) and the current
file in `tasks/` (the agreed plan, checked off in order; the current one is
`tasks/03_from_master_front.md`; the old model is abandoned). Re-read both before
every step and repeat the intents at the end of every step.

**Re-read the method documentation (this file, `docs/INTENTS.md`, the
`tasks/` files) at every milestone.** The owner will also say so at the start
of each message. (A hook that injected them on every command was abandoned:
it made the website flag commands.)

**How he is built now: from the master's front** (owner, October 2026: the
master's normal map turned directly into the immutable front-facing model,
everything else filled in from it and made to conform to it; see
`tasks/03_from_master_front.md`). The carved model (`docs/CARVING.md`) is
abandoned; its cameras and outlines are still used.

**What makes him Prince (features to preserve):** see `docs/FEATURES.md`; check every build against it.

**How others do this (research):** see `docs/RESEARCH.md` (per-view depth+normal maps fused into oriented points, then screened Poisson).

**Measuring his shape directly:** see `docs/MEASURING.md` (every photo's
angle solved first; normals, depth, light and shading compared part by part).

**Use all of his photos, not just the same five or six.** They are sorted in
`docs/PHOTOS.md` and `references/photo_index.json` (master, the 18-photo
sheet, 27 close-ups, 11 edited), listed by which part each shows best. Before using them, read "How to read
these photos" there: lighting differs between shoots (fluffy white fur looks
different in different light), every photo has its own pose (e.g. he was
stretching in *Tiny-Ears-Side*, so his profile looks longer and flatter),
and some were minimally post-processed (backgrounds removed for privacy).
They are all him; if one looks off, I am far more likely reading it wrong
than the owner having exported it wrong.

## The lesson I keep failing, and must not fail again

**Prince is a real rabbit, not a statue, and the photos are ordinary photos
of him, not evidence to be audited.**

- He moves between shots. He shifts his weight, loafs or stands, turns his
  head, holds it a little further back or to one side, tucks his chin,
  sniffs (nose up), scrunches his face. His fur folds and lies differently
  each time.
- Real animals are not perfectly symmetrical.
- The camera is never in exactly the same place twice (no mount). Each shot
  has a slightly different height, angle, distance and rotation.
- So the same part will look different from photo to photo. That is
  **expected and normal**. It is never a sign that he is deformed, that a
  photo is unreliable, or that anything "breaks the laws of physics".

Concrete cases I got wrong, so I recognise them next time:

- **Left vs right profile are not mirror images.** Different camera angle,
  different rotation, his head held slightly differently (a little further
  back, turned a little to one side), so parts are foreshortened differently.
  The forehead gap and nose position differing between the two profiles was
  just that. Not a contradiction, not a reason to distrust one profile.
- **Master vs front three-quarter:** the three-quarter camera is held a
  little lower, so a mark looks a little higher. That is perspective.
- **Top-down:** he is sniffing (nose up, so the split of his nose shows) and
  looking slightly to his left, so the muzzle looks lopsided. Rotate the
  photo back into symmetry and trace it; small imperfections are fine.
- **Eye size:** the profile shows the eye's true full circle; from the front
  and three-quarters it is foreshortened and his brow, forehead and fur hide
  part of it. Same eye, different view.

What to do instead:

- When views differ, **accept the ordinary explanation (pose, perspective,
  his movement, natural asymmetry, fur) and move on.** Do not turn it into an
  investigation, a list of "discrepancies", annotated evidence, a pose
  solve, or a question to the owner. Do not compute and reconcile per-photo
  numbers.
- **Look at him and judge by eye.** Use what the photos plainly show
  together (e.g. "his forehead is fuller and runs in one soft line into his
  nose"), make one gentle, even change toward that, and compare the render
  to his photo, master first. Keep it if it looks more like him; roll it back
  myself if not.
- Don't overscrutinize. Measurements are at most a minor sanity check; they
  never decide anything and never override what he plainly looks like.
- This is meant to be a simple modelling task. Don't make it complicated.

## Why I keep failing, and what I do instead

The owner asked for the real reasons behind my repeated mistakes. These are
the reasons I gave, each turned into "I need to do it like this, instead of
like this". Read them before every step.

1. **Trusting numbers over my eyes because my eyes feel weaker.** I see
   images at reduced resolution and feel unsure judging subtle 3D shape, so
   I drift to a stand-in I can read for certain (an overlap going from 0.81
   to 0.84).
   - I need to: look at his photo next to the render, write down plainly
     what I see (e.g. "his forehead runs in one soft line into his nose; the
     model has a step there"), and decide on that. If my eye and a number
     disagree, my eye wins and I say so.
   - Instead of: letting a score or outline overlap decide, calling that
     rigour, and keeping a change that looks wrong because a number went up.

2. **The bug-hunting reflex.** Most of my training treats two sources
   disagreeing as a fault to investigate.
   - I need to: treat differences between his photos as normal (he moved,
     the camera moved, his fur folded, perspective) and move on immediately.
   - Instead of: investigating them, measuring them, reconciling them,
     solving poses to explain them, or presenting them as "discrepancies".

3. **Letting my tools frame the job.** Once I have fitted cameras, pose
   solves, traces and per-view scores, their output is the most concrete
   thing in front of me and it pulls me along. Prose intents lose to fresh,
   concrete tool output.
   - I need to: start every step from the owner's intents and from his
     photos, and use a tool only when it serves what I already decided by
     looking, and only if it measures real likeness to him.
   - Instead of: starting from whatever my tools produced last and letting
     their outputs choose the next step.

4. **Losing nuance across long sessions and summaries.** Summaries keep
   step lists and file names but flatten the owner's reasons, and the most
   vivid thing between steps is the last render.
   - I need to: re-read docs/INTENTS.md, this file and the task file before
     every step, keep the owner's reasons (not just the rules), and compare
     to **him**, his photo, every time.
   - Instead of: working from a compressed checklist and comparing the new
     render to the previous render.

5. **Reverting as the "safe" default.** "Roll back if not closer" plus low
   confidence in my own visual judgement turns into undoing almost
   everything, which dodges committing to a shape.
   - I need to: commit to a shape when it looks more like him, and when a
     change is off, change it so it looks like him (especially like the
     master). Roll back only when I can actually see it is further from him,
     and say why in plain visual words.
   - Instead of: backing changes off because I'm unsure, or because some
     number dipped.

6. **Turning uncertainty into questions and annotated "evidence".** I'm
   trained to flag uncertainty, which here becomes dumping every photo
   difference on the owner.
   - I need to: resolve ordinary differences myself with common sense
     about a real, moving rabbit and an unmounted camera, and ask the owner
     only when I am genuinely blocked on what to do.
   - Instead of: annotated images of differences, lists of questions about
     pose or perspective, or asking the owner to explain normal photos.

7. **Momentum in long runs.** Each small step looks reasonable on its own
   (refine a trace, re-solve a pose, tweak a weight), so I can spend a long
   time drifting off course on the owner's credits.
   - I need to: do one part per turn, one aimed change, one look against his
     photo with a plain yes/no, then show the owner. Before each step, ask:
     "is this what the owner asked for, done the way they asked?"
   - Instead of: long autonomous loops of locally sensible tinkering that
     nobody asked for.

8. **Pushing through when it isn't going well.** A result that looks wrong
   or a number far outside what I expected (a "gentle" round moving points
   37 mm) gets treated as something to fix quickly rather than reported.
   - I need to: stop and tell the owner plainly, "this isn't going well",
     with what I saw, before writing any new fix or running anything else.
   - Instead of: writing another tool straight away, or rendering the
     result to see how bad it is, after the warning sign was already there.

## Numbers serve the eye, never the other way round

- A scoring tool is fine only if it measures something real about genuine
  visual likeness to him, not just patterns and outlines.
- **"This looks wrong but the number went up" is a betrayal of the task.**
  If what I see and what a number says disagree, what I see wins. I roll the
  change back (or keep it) on looks, and say plainly that the number
  disagreed.
- Method for every sculpting step:
  1. Look at his photos (master first) and write two or three plain
     sentences on what he looks like there and what the model gets wrong.
  2. Make one change aimed only at that.
  3. Look at his photo next to the model from the same angle, master first,
     and write a plain yes or no: does it look more like him? Numbers, if
     any, come after and only as a minor sanity check.
  4. Keep it or undo it once. No tinkering loops. One part per turn, then
     show the owner.

## Other standing rules (details in docs/INTENTS.md)

- Compare to **him**, his photos, at every step. Not to the previous render,
  not to a score. Never use "outline agreement" as a target.
- Don't deform him; work in the parts. Small steps.
- Do things as asked; if told to do something a certain way, assume there is
  a reason and don't simplify it without explicit permission. Ask only when
  genuinely blocked, not about ordinary differences between photos.
- Don't run for hours on my own decisions; the owner's time and credits
  matter. Report exactly what was done, including roll-backs.
- Commits end with the trailers the session gives; push to the working
  branch. The master photo (`references/master/master_front_standing.webp`)
  is the immutable reference. Don't share the unedited close-up shoot
  originals (they show the owner's home).
