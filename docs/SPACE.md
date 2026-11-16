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

Cameras live in `data/cameras.json`, one entry per photo.

## The anchor camera: as the owner remembers the shot (lens provisional)

Owner, 2026-11-16: straight on, no more than six inches away, "basically exactly at his eye level. Maybe
just a tiny bit lower", looking level or "ever so slightly up"; he sat on a soft surface; the picture was
cropped when his background was removed. The photo carries no camera data. Placed like that
(`tools/scene.py`, `data/cameras.json`):

| Input | Value | From |
|---|---|---|
| Distance, camera to his nose | 13 cm (range 10-15.24) | owner |
| Height | his eyes 0.5 cm above the camera (range 0-1) | owner ("a tiny bit lower") |
| Tilt | level, tilted up 1 deg (range 0-2); not turned, not rolled | owner ("straight on", "ever so slightly up") |
| Aim point in the picture | x 548 (his nose), y 482 (puts his eyes a touch above the camera); NOT the picture's centre (lesson 26) | owner's memory + the photo |
| Lens | 1428 px: a 26 mm-equivalent phone main camera, the picture cropped from a 3:4 frame centred on the aim point, the smallest frame that holds it (the SHORTEST lens that fits) | **PROVISIONAL** |
| His peets' front | right under the front of his face | assumed |

Result: camera 6.5 cm above the surface, 12.8 cm in front of the origin, level (tilted up 1 deg). His nose
4.4 cm up; his widest outline is 7.5 cm across at his nose's distance (he is wider: his sides are further
back). A longer lens (tighter crop, or zoom) makes him smaller; **his real size fixes it** (his width across
his widest point, or his height to the top of his head). In the 3D page the floor's horizon runs through
his eyes, as a level camera at his eye level should.

Nothing measured depends on these numbers: landmarks and part outlines stay in picture pixels, and the
rays are recomputed from them whenever the camera changes.

## How he is being looked at (`tools/facing.py` -> `data/scene/facing.json`, `docs/images/space/facing.png`)

With the camera fixed as above, from the photo:
- **His head is tipped about 5 deg, his left side up** (a little head tilt toward his right): solid (4-6
  whatever pair is left out, landmarks wobbled by their uncertainty, or the camera moved across the owner's
  ranges). His peets don't tip the same way, so it is his head, not the phone.
- **His head is turned toward his own left (his nose toward the picture's right), about 5-9 deg**: the
  direction is solid (the six mirror pairs give 9.0, the two eye ovals 5.5, and his nose sits right of the
  middle of his eyes); the amount is not yet (the pairs disagree: his mouth, lip corners and ear bases can
  be truly lopsided; the eyes and nostrils alone leave it loose). It firms up with his round shell or
  another photo.
- His body, from where his peets meet the surface (rough): turned about 3 deg toward his right.
- His head's nod (up or down) needs his depth: later.

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
  needed (three.js r159, MIT, in `tools/vendor/`). "Camera's view" puts your eye where the anchor
  camera was (with its off-centre aim point): every ray shrinks to a point on the photo. Blue and red
  lines show how his head and body face.
- `tools/facing.py`: how he is being looked at (above).

## His parts in 3D (owner)

- Every part keeps one identity in every shot: identity comes from the 3D model, never from a photo.
  A new photo is placed in the room by its camera (solved from the landmarks); the labelled model is
  projected through it; the photo then only measures.
- The thin strip joining his ears is the top of his head seen from above; the underfluff tuft between
  his peets is his belly. In 3D they are where his top and his belly start going back.

## Next steps (owner reviews each)

4. Done as far as the photo allows (above): camera as the owner remembers it; how he faces. Still open:
   his real size (fixes the lens), and his head's nod (needs his depth).
5. Depth lines: a first rough round shell from the outline rule (his surface is edge-on along his
   outline) and his symmetry, the parts painted on it; floor grid, midline and wrap-around rings drawn
   back onto the photo; side and top views.
6. When a new angle arrives: solve its camera from the landmarks, project the parts, compare, and only
   then use it for depth.
