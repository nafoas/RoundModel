# Prince's 3D space

Owner, 2026-11-16: before any sculpting, ground him in a real 3D space, so every shape can be traced
back and nothing of him is misread between shots ("previous claude had nothing to anchor him in and I
think that caused a ton of confusion"). This file defines that space. Code: `prince/space.py`
(tests: `tests/test_space.py`).

## The one rule

**Every pixel is a ray from the camera, never a point on a flat sheet.** A photo fixes the direction from
the camera to each bit of him, not how far away it is. Code turns picture measurements into rays (lines
going out from the camera), never into flat shapes. His outline is not the edge of a cut-out: it is
where his round body turns away from the camera (the line of sight grazes him there).

## The room

| | |
|---|---|
| Units | centimetres |
| Floor | the flat plane y = 0; he rests on it, nothing of him goes below it |
| +X | **his left** (in the front photo: the picture's right) |
| +Y | up |
| +Z | **his forward** (the way his face points) |
| Origin | on the floor, in his midline plane (x = 0), under the front of his peets: the floor under `floor_contact_midpoint` (`data/strands/landmarks.json`) |
| Midline plane | x = 0, splitting him into his left and right |

Names of anything with a side use **his** side (`eye_his_left` is on the picture's right), the same as
the room's +X, so left and right cannot swap on the way into 3D.

## Cameras

A pinhole camera: position C in the room, rotation R (room to camera), focal length f (pixels) and
principal point (cx, cy). Camera frame: x = picture right, y = picture down, z = the way it looks.
Picture coordinates as everywhere in the project: pixel (c, r) covers [c, c+1) x [r, r+1).
Placement words (as in `docs/PLAN.md`): yaw 0 = straight in front of his face, yaw 90 = on his left,
pitch > 0 = above looking down, roll > 0 = camera turned clockwise (the room looks turned anticlockwise).

Cameras live in `data/cameras.json`, one entry per photo (plus the superseded six-inch record).

## The anchor camera: the depth model's (since 2026-11-17)

Owner, 2026-11-17: "I agree with whatever the model says", and yes to making it the room's camera. The room's
camera for the anchor photo (`data/cameras.json` `anchor_front`) is MoGe-2's, as placed in "His surface as
the anchor photo sees it" (below): its own lens (1795 px), straight on, his eyes 0.5 cm above it, 24.5 cm from
his nose, 12.9 cm up; his approved width (15.5 cm) sets the size. His outline, landmark and part-line rays
(`data/scene/anchor_rays.json`), the room pictures and how he faces (`data/scene/facing.json`) are all worked
out from it, so everything for this photo shares one camera.

### Superseded: the camera as the owner first remembered the shot (kept in `data/cameras.json` as `anchor_front_six_inches_superseded`)

Owner, 2026-11-16: straight on, "roughly 6 inches away from the camera" ("it couldn't have been more"),
"basically exactly at his eye level. Maybe just a tiny bit lower", looking level or "ever so slightly up";
he sat on a soft surface; the picture was cropped when his background was removed. The photo carries no
camera data. Placed like that (`tools/scene.py`, `data/cameras.json`):

| Input | Value | From |
|---|---|---|
| Distance, camera to his nose | 15.24 cm, six inches (range 12-15.24) | owner |
| Height | his eyes 2.4 cm above the camera: as little below eye level as lets him reach the owner's size floor (top of his head >= 12.7 cm) | owner ("a tiny bit lower") + owner's size floor |
| Tilt | level, tilted up 1 deg (range 0-2); not turned, not rolled | owner ("straight on", "ever so slightly up") |
| Aim point in the picture | x 548 (his nose), y 610 (the camera's height on him: between his eyes and his nose); NOT the picture's centre (lesson 26) | owner's memory + the photo |
| Lens | 1237 px: the SHORTEST lens that fits (a 26 mm-equivalent phone main camera, the picture cropped from a 3:4 frame centred on the aim point, the smallest frame that holds it); any longer lens makes him smaller | the photo + owner's size floor |
| His peets' front | right under the front of his face | assumed |

**His size floor (owner, 2026-11-16):** he is an adult, "not a juvenile": the top of his head is at least
12.7 cm (the smallest adult rabbit he could be). This is a floor on his overall size ONLY; no breed shapes
him (owner: he is just him). (At his eyes' height, the shortest lens made him 12.3 cm wide and 10.5 cm tall:
too small, owner.) At six inches, only the camera's height on him and the lens can change his size; the lens
is already the shortest that fits, so the camera sat a little lower: 2.4 cm below his eyes, between his eye
and nose height (with a 24 mm-equivalent lens it would be about 1.5 cm).

Result: camera 7.4 cm above the surface, 15.2 cm in front of the origin, level (tilted up 1 deg).
**SUPERSEDED 2026-11-17 by the depth model (below, "His surface as the anchor photo sees it"): 15.5 cm wide,
16.7 cm to the top of his head.** Was: **his size (rough, `his_size_estimate_cm` in `data/cameras.json`): about 15.5 cm wide, 12.7 cm to the top
of his head, ear tips 13.6 cm, eyes 9.9 cm up, nose 6.0 cm up**: at the floor, so he may be a little
bigger. **Owner-approved 2026-11-16: "those numbers seem to fit him"** (no tape measure, so as not to
disturb him).
In the 3D page the floor's horizon runs through his eyes, as a level camera at his eye level should.

Nothing measured depends on these numbers: landmarks and part outlines stay in picture pixels, and the
rays are recomputed from them whenever the camera changes.

## How he is being looked at (`tools/facing.py` -> `data/scene/facing.json`, `docs/images/space/facing.png`)

With the room's camera (the depth model's, since 2026-11-17), from the photo:
- **His head is tipped about 5 deg, his left side up** (a little head tilt toward his right): solid (4-6
  whatever pair is left out, landmarks wobbled by their uncertainty, or the camera varied: the other model's
  lens, tilted 2 deg). His peets don't tip the same way, so it is his head, not the phone.
- **His head is turned toward his own left (his nose toward the picture's right), about 5-13 deg**: the
  direction is solid (the six mirror pairs give 12.7, the two eye ovals 5.3, and his nose sits right of the
  middle of his eyes); the amount is not (the pairs disagree: his mouth, lip corners and ear bases can be
  truly lopsided; with this longer lens the pairs spread more than with the six-inch camera, which gave 7.8
  and 5.7). His measured surface could settle it (not done yet).
- His body, from where his peets meet the surface (rough): turned about 4 deg toward his right.
- His head's nod (up or down): his measured surface has it; not read yet.

## What exists (steps 1-3)

- `prince/space.py`: the room and the camera (project, rays, back to the picture, floor hits).
- `tools/landmarks.py` -> `data/strands/landmarks.json`: 27 named landmarks, each with its part, picture
  position, how found, how sure (px), mirror partner, and kind (`surface point`: a fixed point of him;
  `view-dependent`: slides over him as the camera moves, e.g. an ear's topmost point, a catchlight, a
  peet's lowest point). Picture: `docs/images/space/landmarks.png`, eyes `landmarks_eyes.png`.
- `tools/scene.py` -> `data/cameras.json` (anchor camera), `data/scene/anchor_rays.json` (his outline
  rays, coloured by part, marked *grazing*; the approved part lines and part outlines; every landmark),
  pictures `docs/images/space/room_behind.png`, `room_side.png`, `room_top.png`.
- `tools/room_viewer.py` -> `docs/space/room.html`: the room in 3D, interactive, one file, no internet
  needed (three.js r159, MIT, in `tools/vendor/`). Shows his surface as each depth model measured it, with
  that model's camera; "Camera's view" puts your eye where the shown camera was (with its own principal
  point; the photo hidden, so every point lands on its own pixel). The six-inch camera, its rays and the
  blue/red facing lines are under "The camera as first remembered". (The scrapped shell is no longer shown.)
- `tools/facing.py`: how he is being looked at (above).

## His parts in 3D (owner)

- Every part keeps one identity in every shot: identity comes from the 3D model, never from a photo.
  A new photo is placed in the room by its camera (solved from the landmarks); the labelled model is
  projected through it; the photo then only measures.
- The thin strip joining his ears is the top of his head seen from above; the underfluff tuft between
  his peets is his belly. In 3D they are where his top and his belly start going back.

## Depth lines (step 5): SCRAPPED by the owner (2026-11-16)

The depth approach was scrapped: the parametric blob shell fitted to his outline (its face came out flat), its
depth lines, and the depth read from the light on his fur (lopsided; its chest dipped below the surface he sits
on). Owner: "I dislike this. Scrap it, lemme think of another method." Removed from the repo (recoverable from
git history at commit ac8e35a). Don't rebuild it; the owner is choosing another method.
Kept from this work, as findings: the light read straight from his fur and eyes (one soft light from above,
about 34 deg toward his right; the blue in the shade is his navy blanket; `docs/images/space/light_reading.png`),
and that his eyes bulge (not flat) and face well to the sides.

## His surface as the anchor photo sees it (owner's method, 2026-11-16)

"Have it invent absolutely nothing": every area of him is governed by one photo, and from each photo only
what it shows. `tools/visible_depth.py` (tests `tests/test_visible_depth.py`):
- Two depth models measure one distance for every pixel of him (637,497 px): Depth Pro (Apple) and MoGe-2
  (Microsoft), each with its own lens estimate. Saved untouched: `data/scene/visible_depth_<model>.png`
  (16-bit) and `.json`. `python tools/visible_depth.py --measure` re-runs them (slow); without it, only the
  placing below is redone.
- **Placed in the room, each with ITS OWN camera** (owner: "Either way I trust them"): its own lens and rays,
  straight on; one number per model sets the units so he is 15.5 cm wide (approved), shape untouched; up
  from the owner's memory (his eyes 0.5 cm above the camera: "basically exactly at his eye level. Maybe just
  a tiny bit lower"), not from the cropped picture's centre (lessons 26, 29); the surface through his two
  peet bottoms, the origin under their middle. Every pixel's ray from that camera, cut at the model's
  distance: each point lies exactly on its own pixel. Nothing smoothed, filled or merged.
- His outermost 4 px blend into the removed background: their distances are least sure (Depth Pro pulls
  them up to 40 cm back). Shown on their own toggle; edge landmarks and his width are read 4 px inside.

| Model | Camera to his nose | Camera height | Top of his head | Eyes | Nose | Ear tips | Peets behind his nose | Picture's centre |
|---|---|---|---|---|---|---|---|---|
| Depth Pro | 30.4 cm | 14.3 cm | 18.3 cm | 14.8 | 11.0 | 19.7 | 13.1 cm | 5.6 deg below the aim |
| MoGe-2 | 24.5 cm | 12.9 cm | 16.7 cm | 13.4 | 9.5 | 18.0 | 5.7 cm | 7.1 deg below the aim |

**His size from here on: MoGe-2's** (owner, 2026-11-17: "I agree with whatever the model says"): 15.5 cm wide
(approved; the model alone cannot tell size from this photo), 16.7 cm to the top of his head, eyes 13.4, nose
9.5, ear tips 18.0; camera 24.5 cm from his nose, 12.9 cm up. Above his adult floor (12.7).
**MoGe-2 is used from here on** (owner, 2026-11-17: "very obvious which one looks more like a rabbit"; overlay
`docs/images/space/visible_depth_compare.png`); Depth Pro is kept, set aside, for the record.
(Six-inch camera, for comparison: 15.2 cm, 7.4 cm, top of head 12.7, eyes 9.9, nose 6.0, peets assumed
right under his face, aim 4.9 deg above the picture's centre.) Free checks: his two peet bottoms come out
level within 0.13 cm (Depth Pro) and 0.01 cm (MoGe-2). **Open (Q47):** at the models' distance his approved
width and height cannot both hold. Pictures: `docs/images/space/visible_depth_side_top.png`; 3D:
`docs/space/room.html` (the six-inch camera is still there, off by default, with the rays and facing lines
that were worked out with it).

## The 3D grounding steps (owner reviews each)

1. Define the room: done.
2. Name the landmarks: done.
3. Every part and boundary as rays from the anchor camera: done.
4. Place the anchor camera (as the owner remembers the shot) and work out how he is being looked at:
   done (above). Open: his head's nod (needs depth).
5. Depth lines: SCRAPPED (above). Replaced by the owner's method: his surface as each photo sees it, measured
   by two depth models, each placed with its own camera (above). Open: his size (Q47).
6. When the owner adds another angle: solve its camera from the landmarks, project his parts, compare,
   and only then use it for depth.

After the 3D grounding, the broader plan resumes (`docs/PLAN.md`, `docs/STRAND_PLAN.md`): the paused part
steps (ears' pixel tweaks, eyes / lashes / hotot marks, whisker pads, mouth, nose, Bnuy Perturbances),
then building and fitting the 3D model.
