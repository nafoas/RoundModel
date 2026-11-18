# More photos: one Prince, many poses (agreed with the owner, 2026-11-18)

The method for every photo after the anchor (`data/photos/anchor_front.webp`).

## The problem (owner)
"The little guy is pretty fluffy. He moves a lot. He doesn't look the same between photos ... Even him shifting
his weight is enough to cause a difference. Previous Claude had a heart attack dealing with different angles ...
we need to devise a way to make a cohesive model based on his objective biology between shots, not just how he
looks between them ... Keep in mind that each photo will have one master."

And: "I'd rather this remain entirely objective- I don't want any subjective sculpting put into it. That means
seams and other areas not covered well would need to be objectively sorted and covered."

So: **every placement, seam and fill is decided by a fixed rule from measurements**, never by hand; the owner
reviews the results. Photos are compared on what he IS, never on how he LOOKS.

## 1. Three layers of him
| Layer | Between photos | What it is |
|---|---|---|
| **His biology** | fixed | skull and face proportions (eye size and spacing, eye to nose), ear size and shape, peet size, his markings (hotot rings, cream right peet, grey left peet), his overall size |
| **His pose** | a few numbers per photo | head turn / tip / nod on his body; each ear's angle at its base; body lean and weight shift; how upright or loafed; where his peets are |
| **His fur** | per photo, soft | how puffed or pressed down it is: a soft layer over his body |

His outline is NOT biology: it is fur + pose + viewpoint. Comparing outlines is what made other angles look
"wrong" before.

## 2. Home pose = the anchor's pose
No neutral pose is invented. Every other photo is bent back into how he sat in the anchor photo (head tipped
~5 deg, turned 0.5 deg; `docs/SPACE.md`).

## 3. Placing a new photo: rigid parts first
1. **Head first** (a skull: the most rigid part): the photo's camera from head landmarks it shares with the
   anchor (eyes, nose, ear bases), least squares.
2. **Other rigid-ish parts** (each ear, each peet) from their own landmarks: their pose numbers.
3. **The soft body last**: the gentlest bend (as-rigid-as-possible) that makes the overlaps agree. This absorbs
   weight shifts and fur. Computed, not sculpted.
4. **Scale from biology** (eye spacing, head width), never from the outline; his size stays as approved
   (15.5 cm wide).
Each photo's surface is measured the same way as the anchor's (MoGe-2, its own camera, nothing invented;
`tools/visible_depth.py`).

## 4. Who masters which area: a quality score
Every patch of his surface gets a score for how well each photo sees it: how face-on, how far from that
photo's outline (the edge band is least sure), how close the camera. **The anchor masters everything it sees
well** (it is the anchor: CLAUDE.md rule 4); every other patch goes to the photo that scores best. Where
another photo also sees a mastered patch, it is used ONLY to place that photo (camera and pose): it never
changes the master's surface.

## 5. Seams: placed and joined by rule
Neighbouring areas overlap a little (that overlap is how a photo is placed). Within it the seam runs along the
path where the two photos' measured surfaces agree best (least-difference seam, as in photo stitching). Across
a narrow band the two are blended by fixed weights: each point leans toward the photo that sees it more
face-on. No hand-drawn bridges.

## 6. Gaps: found by rule, covered by photos
The quality map lists every patch no photo sees well, and where a camera would have to be to see it face-on.
Gaps are covered by photos, never filled by hand. Physical rule in the home pose: nothing of him goes below the
surface he sits on.
**His underside:** owner, 2026-11-18: a belly-up photo exists, taken while he was midway through rolling over
("the only view of him belly up we have"; not posed: "I don't wanna hurt him"). His peets are rigid parts, so
their undersides come over cleanly; his belly is soft and mid-roll, so it takes the biggest bend: its biology
checks and seam agreement are shown to the owner.

## 7. Checks: biology only, with tolerance
The only consistency checked between photos: does his biology come out the same (eye spacing, ear length,
peet size, ...) within a tolerance? Everything else differing is expected (pose, fur) and never an error. A
biology check outside tolerance is shown to the owner; the owner's eye decides. A photo is never "wrong".
**Fixed before any new photo is placed** (so no number is tuned to make a result look good, rule 8): the
tolerances, the seam band's width, and the quality score's formula.

## 8. For each new photo
1. Owner sends it (background removed if it shows the room: the repo is public).
2. Landmarks it shares with the anchor, named the same.
3. Its surface measured (MoGe-2, its own camera).
4. Placed: head, then rigid parts, then body; scale from biology.
5. Its mastered patches brought into the home pose; seams by rule.
6. Shown to the owner: the biology checks, the seam agreement, the remaining gaps.

## Precedent
Research that builds animals which move between shots keeps one fixed body shape and fits a few pose numbers
and a camera per image or frame: SMAL ("3D Menagerie", CVPR 2017), BANMo (CVPR 2022), RAC (CVPR 2023).
