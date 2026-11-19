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

## The photos (2026-11-18)
All in `data/photos/` (`data/photos/index.json`): the anchor, plus 18 photos of him sorted by where the camera
is around HIS body (`by_angle/01_front` ... `11_front_low`, from the old branch, with the owner's labelled
sheet). His underside: `by_angle/10_underneath/10_bottom_up.webp` (belly up, mid-roll). Not for measuring:
`expressions/` (made from the front photo; for his face later).

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
Every patch of his surface gets a score for how well each photo sees it: **the size of one of that photo's
pixels on his surface there** (distance from the camera / focal length / cos of the viewing angle: smaller is
better; it grows as the camera moves away and as the surface turns edge-on). A photo's outermost 4 px count as
not seen (measured: their depth blends into the background). **The anchor masters everything it sees
well** (it is the anchor: CLAUDE.md rule 4); every other patch goes to the photo that scores best. Where
another photo also sees a mastered patch, it is used ONLY to place that photo (camera and pose): it never
changes the master's surface.

## 5. Seams: placed and joined by rule
Neighbouring areas overlap a little (that overlap is how a photo is placed). The seam runs where the two
photos' scores are equal. **No blending band:** the less-sure photo's surface bends, as gently as possible
(as-rigid-as-possible), until it meets the surer one along the seam; the anchor never bends. The bend's size
is reported. (A blend band "no steeper than his surface's own bumps" was tried 2026-11-19 and dropped: the
measured surface is so smooth that it would spread a 1 mm disagreement over about 8 cm.) No hand-drawn bridges.

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
tolerances, the seam rule, and the quality score's formula.

## 8. Where the numbers come from (2026-11-19)
Owner: "We need to determine how to determine objectivity from a little fluffy creature that moves a lot."
**He sets the yardstick:** photos of him from about the same angle at different moments show how much a
measurement of him changes when only time changes. That measured spread is the tolerance (2 standard
deviations: 95%, the usual convention). `tools/his_variation.py` -> `data/scene/his_variation.json`.
- First try (2026-11-19): his eye spacing (3D) / an eye's size, on the anchor and 6 front photos. With his
  head level (anchor, 01, 18) it agrees within 1.5%, which is encouraging, but it follows his head's nod
  (raised +20%, lowered -33%): an eye's size read flat off the picture changes with the angle the eye is seen
  at. **Not usable.** Next: only 3D distances between rigid points (between his eyes, from his eyes to his
  nose), which do not change when he turns or nods; that needs his nose found objectively in each photo.
- Eye fits that run into the background are rejected (more than 3 px off).
- **The one number measurement cannot give:** how strongly the anchor is favoured (it is "at his most him").
  Owner's call.

## 9. For each new photo
1. Owner sends it (background removed if it shows the room: the repo is public).
2. Landmarks it shares with the anchor, named the same.
3. Its surface measured (MoGe-2, its own camera).
4. Placed: head, then rigid parts, then body; scale from biology.
5. Its mastered patches brought into the home pose; seams by rule.
6. Shown to the owner: the biology checks, the seam agreement, the remaining gaps.

## Precedent
Research that builds animals which move between shots keeps one fixed body shape and fits a few pose numbers
and a camera per image or frame: SMAL ("3D Menagerie", CVPR 2017), BANMo (CVPR 2022), RAC (CVPR 2023).
