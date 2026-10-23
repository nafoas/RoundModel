# RoundModel: read this first, every session

This repo builds a 3D model of **Prince**, a real, living, very round white
Dwarf Hotot rabbit, from photos his owner took of him. Before doing anything,
read `docs/INTENTS.md` (the owner's intents, in their words) and the current
file in `tasks/` (the agreed plan, checked off in order). Re-read both before
every step and repeat the intents at the end of every step.

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
