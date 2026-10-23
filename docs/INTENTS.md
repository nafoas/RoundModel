# The owner's intents for this stage (re-read and repeat after every step)

**FIRST, ALWAYS: Prince is a real, living rabbit, not a statue, and his photos
are ordinary photos, not evidence to audit.** He moves, turns and tilts his
head, sniffs, loafs, his fur folds; he is not perfectly symmetrical; the
camera is never in exactly the same place twice (left and right profiles are
not mirror images; the three-quarter camera is a little lower than the
master's; from above he is sniffing and looking slightly left). Differences
between photos are expected: accept the ordinary explanation and move on.
Never treat them as discrepancies to investigate, never distrust a photo or
conclude he is deformed, never reconcile per-photo numbers. Look at him,
judge by eye, make gentle changes toward what the photos plainly show
together. See CLAUDE.md for the cases I got wrong.

Written from the owner's own words. Read it before each step, and repeat it at
the end of each step. Do not paraphrase it into something easier.

**Numbers serve the eye.** Scoring tools are fine only if they measure real
visual likeness to him, not patterns and outlines. "This looks wrong but the
number went up" is a major betrayal. Stop, think, listen to the owner and to
my own judgement: if the look and the number disagree, the look wins.

## The task (this stage)
- Start from the kept build (commit d9f1d7c, restored in 716e530).
- Like the body: draw lines around each part in both his photos and the model,
  and do similarity checks until it is as close to 100% as possible, for the
  **shape, depth and orientation of every part of his eyes and upper face**:
  eye shape, eye orientation, eye depth, socket shape, socket orientation,
  socket depth, ridge shape, ridge orientation, ridge depth, forehead shape,
  forehead orientation, forehead depth, and so on.
- Divide each part into smaller sub-shapes (eye, eyelid, ridge over the eye,
  socket, forehead, muzzle) and make each agree in silhouette, depth,
  orientation and size from as many angles as possible, weighted toward the
  master (the immutable reference).
- Trace his eye as accurately as possible from as many angles as possible and
  put in a real 3D eye built from those traces, weighted to the master.

## How to judge
- **Compare the render to him, to his photo, at every single step.** Not to
  the previous render. Not to a score. To him.
- Do not use "outline agreement" as a target or as proof of progress. Never
  sacrifice his actual geometry for an outline number. Looking only at "the
  difference between the light and the dark" is lazy and not what was asked.
- Use logic and judgement to work out depth, orientation, angle, and how to
  make him look like him, from the photos that are available.
- After every step, ask "is this actually getting closer to him?" If not,
  roll it back myself, right away, without being told, and say so.
- Don't deform him. The overall head stays; the work is in the parts.

## Conflicts between photos
- If photos disagree, it is probably the angle, the distance, or what he was
  doing in that photo. Work out which, and trust what most views agree on.
- **He is not a static being, not a stone.** Between photos he sits
  differently, turns his head, his fur creases and lies differently, and he
  sniffs. These are not anatomical inconsistencies, and the model must never
  be deformed to "fix" them. Example: from above you can see the split of his
  nose because he is sniffing there, nose upturned; in the other photos his
  nose points forward. Logically work out how the views fit together given
  what he was doing in each. The owner got what photos he could give.
- Don't just mechanically observe shapes. For every inconsistency, make a
  judgement call from what I know about rabbits: is it more likely he shifted
  his weight, turned, sniffed, his fur folded, or is it an error? The former
  is much more likely. Look for the reason behind each inconsistency and
  reason it away with that logic, myself, without being told.
- Don't overscrutinize. He is a little round rabbit who looks a bit different
  from different angles; that is expected and is not something to analyse
  at length. Spend the effort on making him look like him.
- **Think about perspective before calling anything a difference.** A part
  seen at an angle is foreshortened (looks narrower), and parts in front of it
  hide some of it (in the master and three-quarters his brow ridge and
  forehead hide part of the eye), without it being any smaller. The profile
  shows the eye's true full circumference because it looks at it side-on.
  Work out what each view can actually show before comparing.
- Get the parts agreeing with as many angles as possible first; don't hold
  the front rigid. Then make it look like the master while keeping the
  other views agreeing as much as possible.
- Don't back a change off because it hurts the master: change it so it
  looks like the master.

## How to work
- Do the things asked **as described**. No spontaneous judgement calls
  substituted for instructions. If an instruction is unclear, or seems not
  doable, or I want to do it another way: stop and ask.
- Don't turn a hard instruction into an easier version and report that as
  done.
- **If I was told to do something a certain way, I will always assume there
  is a reason for it, and I will not simplify it unless I get explicit
  permission first.**
- Don't run for hours on my own decisions. Work in small steps and check in
  at the agreed points. Wasted time is the owner's money and usage.
- Report exactly what was done, including what was rolled back and why.
- Repeat these intents at the end of each step.
