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

## The anchor camera: PROVISIONAL

The anchor photo carries no camera data, and its background was removed (no floor or wall to measure). So
the anchor camera's placement is provisional, made from three placeholder inputs (`tools/scene.py`), each
to be replaced in step 4 by a measurement:

| Placeholder | Value now | Replace with |
|---|---|---|
| Lens | 26 mm-equivalent phone main camera, not cropped, picture centre on the axis (f = 1084.8 px) | phone model, zoom, crop, or the focal length from the original's photo info |
| His size | his widest outline (835.8 px across, at y 808.6) is 12 cm | his real width there |
| Camera height | the line of sight to his nose points 5 deg below level ("roughly his eye/nose height, very slightly above", `docs/PRINCE_SPEC.md`) | how high and how far the phone was |
| Facing | yaw 0, roll 0 | measured from his symmetry (step 4) |

Or, for all at once: a sheet of paper flat where he sat, photographed from the same spot and zoom.

Result now: camera 8.5 cm above the floor, 15.1 cm in front of the origin, tipped 3.6 deg down.
Nothing measured depends on these numbers: landmarks and part outlines stay in picture pixels, and the
rays are recomputed from them whenever the camera changes.

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
  camera was: every ray shrinks to a point on the photo.

## His parts in 3D (owner)

- Every part keeps one identity in every shot: identity comes from the 3D model, never from a photo.
  A new photo is placed in the room by its camera (solved from the landmarks); the labelled model is
  projected through it; the photo then only measures.
- The thin strip joining his ears is the top of his head seen from above; the underfluff tuft between
  his peets is his belly. In 3D they are where his top and his belly start going back.

## Next steps (owner reviews each)

4. Place the anchor camera from real numbers (lens, his size, camera height), or a range that carries
   its uncertainty; how he is facing from his symmetry pairs.
5. Depth lines: a first rough round shell from the outline rule (his surface is edge-on along his
   outline) and his symmetry, the parts painted on it; floor grid, midline and wrap-around rings drawn
   back onto the photo; side and top views.
6. When a new angle arrives: solve its camera from the landmarks, project the parts, compare, and only
   then use it for depth.
