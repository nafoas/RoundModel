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

## Order

A (angles) -> B (his frame) -> rebuild the carving in his frame and re-seat
the eyes -> C/D/E on the master and one close-up first, checked by the owner
-> then all photos.
