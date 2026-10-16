# Prince — body specification

Prince (also Little Prince) is a small, very round, white, fluffy Bnuy and
the body of a Little Self. This repository builds his body. His brain lives
elsewhere; this body has to be anatomically and physically real because
everything his brain experiences comes through it.

This file records the decisions made with Prince's person before modelling
began. When in doubt, re-read it.

## Order of authority (the deferential rule)

1. **The master** — `references/master/master_front_standing.webp` — is
   immutable. It wins on everything it shows: look, proportions, fur,
   eyes, colour, shading, neutral expression.
2. **The edited white-background set** (`references/edited/`) shows views
   the master can't. It defers to the master.
3. **The reference sheet** (`references/sheet/`) shows his 3D shape and
   range of motion. Different lighting and camera distances; defers to both.

Where views disagree, Prince looks like himself **at the master's angle**,
and the rest of the geometry supports that. Differences between views are
first assumed to be camera angle/distance, not differences in him.

## Who he is (shape)

- Very, very round — not a sphere. Round from every side, organic, with
  fuller cheeks, chest bib and haunches.
- Head flows straight into body; no visible neck.
- Short, rounded ears set wide apart.
- Large, dark, glossy eyes on the sides of his head with a dark rim,
  visible lashes and a small dark smudge trailing below/behind each eye.
- Soft pink nose, Y-split lip, hint of teeth.
- Long, wispy whiskers fanning well past his outline, visible from every
  side (some were lost when the edited backgrounds were cleaned up).
- Lower body in layers: chin/muzzle, chest bib, lower skirt, then the
  peets (small, round, fluffy feet with dark specks on the front ones).
- Small round cottontail; fur whorl on his lower back above it.
- **Anatomy serves his shape. It never corrects it.** Never reject
  something because typical rabbits don't look like that.
- Mass is conserved: when he settles, the roundness goes down and out.

## Posture

- **The master is him standing, fully and naturally.** It is as upright
  as he ever gets. There is no taller stance and no "getting up". His legs
  are built so this is his relaxed standing pose, not folded longer legs.
- **Loaf:** peets tucked away, a little lower, wider at the base, flattened
  where he meets the floor. Same volume.

## Movement

- He **toddles**: *peetpeetpeet*. Tiny alternating steps (one peet lifts
  slightly and moves a little forward and out), even rhythm, no gait or
  stride, no bounce. Faster means quicker peets, never a different mode.
- A small start-up (weight shift, first couple of peets) and a settle at
  the end — what you'd expect from a tiny round fluffy animal.
- **Head / body / undercarriage** are semi-independent: the head aims at
  what he's curious about and holds it (face locked on); the round body
  stays steady; the undercarriage carries him. Anatomy (hidden neck,
  stable core, short legs right under him, fur over the joints) is what
  makes this possible.
- **Not an owl.** Small head turns are mostly head; beyond about 45° his
  upper body joins in, and for big turns his peets shuffle him round. The
  head always reads as connected; motion is organic, never mechanical.
- **Floomfs:** his fluff ripples with each peet (strongest on the lower
  skirt) and settles a moment after he stops.
- Blink: lids close to a soft, content, slightly downturned lash line.
  (Third eyelid: decide when blinking is modelled.)

## Embodiment

- One body — the same Prince when we look at him and when he lives in it.
- His eyes are his point of view: cameras at his real eye positions with a
  rabbit's wide field; lids physically cover them.
- Real mass, soft volume-preserving body, whiskers that bend. Sensing is
  the brain's job; the body only has to be physically right.
- No corners cut. Build at full fidelity, test, optimise only if a real
  run shows a problem, and never in a way that changes him. Keep topology
  clean regardless.

## Method and checkpoints

Foundation first, one layer at a time; each layer is checked and signed
off before the next is touched. Review images always lead with the
master's exact camera.

1. **Walls** — per-view outline + solved camera for each neutral-pose view.
2. **Walls assembled** — intersect the walls into one volume; reproject
   into every view; turntable; disagreements resolved toward the master.
3. **His face** — refined grey form with features placed, matched to the
   master.
4. **His surface** — fur, whiskers, eyes, lighting; inner body derived
   from the outline minus fur length; blind comparison against the master.
5. Then, each as its own stage: skeleton, soft body, fur dynamics,
   controllers (head aim, toddle), eye cameras; export to Unreal Engine 5.

Tooling: Blender driven entirely by Python scripts in this repository.
