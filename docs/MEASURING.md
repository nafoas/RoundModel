# Measuring his shape directly (plan, owner's method)

Owner: put the model and his photos on the same plane, and measure more than
the outline: depth and shape, by mapping his normals, albedo and other
properties tied to depth (lighting, perspective, orientation) in each photo,
so depth is a property of each image that can be compared with the model
without guessing. Also: account for angles. He is angled slightly to the
left in the model, which spoils his shape against the master (in the master
he looks straight forward, maybe a touch more weight on his right peet);
and many comparison renders are not from the same angle as his photo
(close-up 06: the photo is from lower and nearer, the render from straight
ahead), which made his eye sockets come out wrong.

## Why his photos suit this

He is white all over (except eyes, nose, inner ears). With one colour of fur
everywhere, how bright a spot is depends almost only on which way the surface
faces and how the light falls. So his brightness is a direct read of his
surface direction, far more than for a patterned animal.

## Step A: the angle of every photo first (nothing is compared before this)

For every photo used (master, sheet, close-ups, edited), solve its camera
(where it was, which way it pointed, its lens) and his head pose in it,
against the model, from:
- landmarks traced by hand on a zoomed grid: both eye centres, nose tip,
  mouth split, ear tips and bases, peets where they show;
- his outline (where it shows);
- the photo's own vanishing hints where there are any.
Fitted cameras already exist for the master and sheet 02, 03, 04, 07, 08,
09; the close-ups and edited photos get theirs now. The guessed plain
directions in tools/parts_sheet.py are retired. Check: model landmarks
projected onto each photo land on his within a few pixels.

## Step B: his own frame (no crookedness)

His midline plane is set from the master, where he looks straight forward:
vertical, facing the master camera, through the middle of his face (between
his eyes, through his nose and mouth split). Not from the carving (which
found a plane turned 2.4 deg). Everything symmetric is mirrored across this
plane; per-photo head poses are measured relative to it.

## Step C: maps from each photo

For each photo (only inside his outline):
1. **Surface direction (normals)** from a single-image normal estimator
   (DSINE first: a regression network, fast enough on CPU; StableNormal
   if DSINE is weak on fur).
2. **Relative depth** from a single-image depth estimator (Depth Anything
   V2), used for ordering (what is nearer) rather than absolute size.
3. **Light**: where the light comes from in that photo, solved from his
   outline: along the outline the surface faces exactly sideways (its
   direction is known from the outline itself), so the brightness along it
   gives the light direction. Then his brightness inside the outline,
   with his fur colour constant, gives a second, physics-based read of his
   surface direction (shape from shading). Albedo: his white fur is one
   value; eyes, nose and inner ears are masked out.
4. **Landmarks** (step A) and part outlines (eye, ear, nose, mouth split).
Each map is checked by eye on the photo before it is used.

## Step D: the same maps from the model

Rendered from each photo's own solved camera, his head posed as there:
normals, depth, and his fur lit by that photo's light. Same image, same
pixels.

## Step E: compare, part by part

Per photo and per part (eyes and sockets, forehead, cheeks, muzzle and nose,
chin and chest, ears, back, haunches, peets):
- angle between his surface direction and the model's (degrees), as a map
  and a per-part number;
- shading difference under his light;
- depth ordering difference;
- landmark offsets.
Shown side by side (photo | model | difference map) on one sheet, like the
outline sheet. Changes are then made where the maps agree he differs, part
by part, small and checked by eye, master first. Numbers serve the eye.

## Step F: parts made separately, in fine detail, then fitted (owner)

Owner: "assemble constituent parts separately, in much finer detail, using
more of the chiselling technique, then fit it to the model, with respect to
all the angles, especially the master."

- Parts: each eye with its lids and socket; the forehead and brow; each
  cheek; the muzzle (nose, nostrils, whisker pads, mouth split, chin); each
  ear; the chest bib; each front peet; the back peets and haunches; the tail.
- Each part is carved on its own fine grid (about 0.3-0.5 mm, against
  1.5 mm for the whole body), from a block bigger than the part, using the
  part's own outline in every photo where it shows, cropped close at full
  resolution: the photos that show that part best (docs/PHOTOS.md "By
  part"), each through its solved camera (step A).
- Then chiselled the same way as the body, but finer: hollows and form from
  the maps (step C: surface direction, shading under his light, depth order),
  small cuts, checked by eye against his close-ups.
- Then fitted to the body: placed, turned and sized (within a little) so
  that, seen through every solved camera, it sits where his does, the master
  counting most; then blended into the body surface so there is no seam
  (the body surface under it is replaced, not stacked).
- Each part shown to the owner beside his photos before it goes on.

## Order

A (angles of every photo) -> B (his frame from the master) -> rebuild the
body carving in his frame -> C/D/E on the master and one close-up first,
checked by the owner -> then all photos -> F, part by part (eyes and
sockets first), each fitted to the body against all angles, master first,
and shown to the owner.

## Step A, progress

- 3D landmarks (tools/landmarks3d.py -> checkpoints/cp4/landmarks3d.json):
  the master is the authority; his nose tip (point of the nose V) and mouth
  split are cast from the master camera onto the model, with his head as in
  the master, then taken back to rest; eyes = the visible eye, half a radius
  in front of each eyeball centre (checkpoints/cp4/eyes.json). Ears left out
  (they move between photos). The first checkpoint's 3D landmarks were up to
  19 mm off this model: not used.
- 2D landmarks placed by eye on gridded zooms, full-resolution pixels
  (checkpoints/cp4/cams/landmarks2d.json): close-ups 06, 25 (both eyes,
  nose, mouth), 19, 20 (one eye), 21, 02 (one eye, nose tip in profile).
- Outlines of these close-ups traced with BiRefNet (as the others), in
  checkpoints/cp4/outlines/cNN.png.
- tools/solve_cams.py: camera position, direction and lens per photo,
  relative to the model, from landmarks + outline where it is not cut off
  by the frame (robust: misses such as the ears count less), weak lens prior,
  two starting directions round the rough one. Solved on a lighter copy of
  the model (vertices merged on a 2 mm grid: 31k vertices). Output:
  checkpoints/cp4/cams/<name>.json and <name>_check.jpg (photo with the
  model's outline in red, his in green, landmarks).
- First measured finding (close-up 25, landmarks within 4-7 px, so the
  camera is pinned): his head is wider than the model's above and beside
  the eyes up to the ears, and fuller at the cheeks (red model outline well
  inside his green one there). The same thing the owner saw earlier (eyes
  looking too big because the head round them is too narrow). For step F.
- Close-up 21 (right side, eye 5.6 px, nose 4.8 px): forehead-to-nose line
  matches; below the nose his chin falls back into his chest while the
  model's jaw sticks out past his line (up to ~25 px in the photo). For
  step F (muzzle and chin).
- Close-up 02 (left side, eye 11 px, nose 4 px): from the forehead back
  over the top of the head, the model's outline runs well inside his: his
  head is higher and fuller above the eye. Agrees with close-up 25 (front):
  the head round and above the eyes is too small, the clearest finding so
  far. His ear here is bigger than the model's.
- Close-up 19: NOT solved (lens 4004, model spills past his outline): one
  landmark and an outline mostly cut by the frame are too little. Needs
  more landmarks (eye corners, visible nose, ear bases) before solving.
- Close-up 20: NOT solved (eye 2.9 px but outline far off): same as 19.
- Step A so far: cameras fitted for the master and sheet 02, 03, 04, 07,
  08, 09 (earlier) and close-ups 06, 25, 21, 02 (new, checked by eye:
  review/closeups_solved.jpg). Close-ups 19, 20 need more landmarks. Still
  to do: the other close-ups, sheet 01, 05, 06, 10-18, the edited set.
