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
- Close-ups 19 and 20, first try: not solved (one landmark each). Looking at
  them whole: they are not three-quarter views but near-front shots taken
  very close (about 17 cm, wide lens), one half of his face each (19: his
  right half, his nose just past the edge; 20: his left half with nose and
  mouth split). Fixed by (1) the dark eye's extent as four landmarks (left,
  right, top, bottom; matched to the model eyeball's visible cap inside the
  lids: eye_X_box in landmarks2d.json), (2) nose tip and mouth split on 20,
  (3) the right rough starting direction (about 12 deg off the front), and
  (4) for companion shots, a start from the mirror image of the other one's
  camera across his frame.
- Step B done (docs/CARVING.md section 17); all close-up cameras re-solved
  against the model in his frame (work/b/lite; earlier ones kept in
  cams/before_frame/). Landmark errors (px, photos about 1100x1430):
  06: eyes 7, 22, nose 15, mouth 9; 25: eyes 9, 13, nose 5, mouth 11;
  21: eye 5, nose 7; 02: eye 11, nose 6; 19: eye 5, eye extent 2-18;
  20: eye 4, eye extent 1-27, nose 29, mouth split 24. Checked by eye
  (review/closeups_solved.jpg): 19 and 20 mirror each other as they should.
- Seen in 19 and 20 (for step F): his head is higher and fuller above the
  eyes than the model (the same as 25 and 02: the clearest finding so far);
  the model's eye opening is a little taller than his (14-27 px); its nose
  sits a little high and its mouth split a little low (about 25 px each:
  the model's nose-to-mouth is longer than his here); his ears are bigger
  and set wider.
- Step A, all photos (October 2026). Every photo's outline traced
  (checkpoints/cp4/outlines/: sNN sheet, cNN close-up, e_<name> edited).
  Landmarks placed by eye on gridded images (eyes, nose tip, mouth split,
  front peets; checkpoints/cp4/cams/landmarks2d.json, with a rough
  direction and his head's turn as read from each photo). Front peets added
  to the 3D landmarks (cast from the master, made mirror images).
- Solver changes (tools/solve_cams.py), after the first runs went wrong
  (owner: "some of them keep failing"): letting his head turn freely let
  the solver tilt his head (26 deg in sheet 14) to hit a few points instead of
  placing the camera by his body. Now: (1) the camera is placed from his
  body first (outline, peets; head held as read from the photo), then only
  his head turn is fitted, kept near that reading (turn 25, nod 20, tilt 4
  deg); (2) where his body is in another posture (standing tall in 11/12,
  hunched in 13/14, from below in 10 and 17, head turned in 15/16, walking
  off in two edited ones: frame "head"), the camera is placed from his head
  alone (face points and the head's own rim against his outline). The
  owner's note on the white-background photos: all taken from directly in
  front, like the master, as he moved off however he liked.
- Results, judged by eye on each check image (photo, his outline green,
  model red, landmarks):
  - Hold (model outline on his, points within ~5-25 px): master; sheet
    01, 02, 03, 04, 07, 08, 09, 18 (01 and 18 from their first solve, which
    fit better by eye than the re-solve); sheet 11 and 17 (head-only);
    close-ups 02, 03, 06, 08, 09, 10, 12, 14, 19, 20, 21, 25, 26; edited
    front_blink, front_head_lifted, front_head_lowered, front_peet_lift_right,
    head_turn_left_mouth_closed, back_3q_left_high, front_3q_left_toddle.
  - Rough (usable loosely): edited front_loaf and front_peet_lift_left
    (face points land; he is loafed lower and wider than the model);
    close-up 07 (outline fits, his right eye 50 px off).
  - Not solved (too little of him, or his posture too far from the model's
    for the head rim to place it): sheet 10, 13, 14, 15, 16; edited
    head_turn_right_mouth_open; close-ups 11, 16, 27 (muzzle only: two
    points in a line), 13 (one eye), and with no landmarks at all 01, 04, 05
    (one eye), 15 (one ear), 17, 18, 22, 23, 24 (peets, underbody). These
    are used by eye for their part in step F, not measured.
  - Sheet 05, 06: cameras from the first checkpoint (panels), unchanged.
- Seen across the front photos (for step F): his eyes sit closer together
  than the model's (the model's land 15-50 px wider in every front view);
  his head is higher and fuller above the eyes (close-ups 02, 19, 20, 25).

## Steps C, D, E: first pass on the master and close-up 25

- C (tools/maps_photo.py -> checkpoints/cp5/maps/<view>/): surface direction
  from Marigold normals (prs-eth/marigold-normals-v1-1, 4 runs averaged;
  DSINE needs code fetched from GitHub, which this environment refused),
  relative depth from Depth Anything V2 Large, his fur mask (bright, nearly
  colourless; his bib's lavender cast counts as fur), and one light fitted
  to his fur brightness against those normals (ambient + one direction;
  from a front view only its right/up parts are pinned). Checked by eye on
  the photos: nose and its split, whisker pads, eye bulges, brow, cheeks,
  body curving away, peets all read correctly; depth puts muzzle and chest
  nearest, ears furthest. Light: from above and a little from his right in
  both (master explains 63% of his fur brightness, close-up 25 31%: one
  light is too simple there).
- D and E (tools/maps_model.py -> checkpoints/cp5/compare/<view>/): the
  model's surface direction and depth through the photo's own solved camera
  (his head posed as there), drawn by splatting points (no renderer), then
  the angle between his surface and the model's, per part, the shading
  difference under his light, and depth order (numbers.json, compare.jpg).
- What the two photos agree on (model minus his surface direction, degrees,
  master / close-up 25; y + means the model faces more upward there):
  - forehead and brow: model faces up more (+8 / +17): his forehead rises
    more upright and faces the camera; the model's slopes back like a dome.
    The same thing as "his head is higher and fuller above the eyes".
  - muzzle: model faces down more (-14 / -20), and is one soft mound: his
    has a rounded nose bump, two whisker-pad lobes and a deep split.
  - cheeks: model faces down more (-10 / -15).
  - chest: model faces down more (-18 / -27): the model's chest tucks under
    the chin (a crease shows there); his bib comes forward smoothly.
  - eyes: his sit in bulges with a crease round them; the model's sit in
    dished sockets (38 / 42 deg median angle there, the worst part).
  - depth order agrees well (0.90 / 0.92): the overall depth is right; the
    differences are in how each part faces.
- Fur edges show as a red rim in every angle map (fur is see-through at the
  edge; the estimator does not put the normal fully sideways there): not a
  shape difference.

## Normals from every side onto the model (owner's method, October 2026)

Owner: "take his normals from every side, and fit every side's normals to
the model and to the other sides, with the master taking preference. We
already have a very accurate general shape; if we stick the normals from
every side onto it and chisel away very finely, we get the best of both
worlds." Agreed. Why it suits him: the model's overall size and depth are
right (depth order agrees 0.90-0.92 with the photos); what is wrong is how
each part faces (fine form). A normal map alone can't become him (it only
sees one side, small slope errors add up into bends, it can't see depth
jumps such as chin over chest), but laid onto a shape that is already right
it gives the fine form at photo resolution.

1. Normals from every photo with a reliable camera (docs/MEASURING.md step
   A "Hold" list): Marigold normals, several runs averaged
   (tools/maps_photo.py). Photos where his body is in another posture count
   for his head only.
2. Onto the model: each model point is seen through each photo's own camera
   (his head turned as he held it there; hidden points left out), and the
   photo's surface direction there is taken back to his rest pose. So every
   point gets one reading per photo that sees it.
3. One target direction per point, blended from those readings: the master
   counts most; a photo counts more where it sees the surface face-on and
   little near its own outline (fur is see-through at the edge); where
   photos disagree (he moved, his fur lay differently) the master and the
   majority win and a stray reading is dropped, not averaged in
   (tools/fuse_normals.py). Shown to the owner before any chiselling.
4. A finer surface on the head first (0.3-0.5 mm between points, against
   1.5 mm now), or the nose split and creases can't be held.
5. Fine chiselling: the surface moved in small, gentle rounds so its
   directions turn toward the targets (nose bump, split, whisker pads, eye
   bulges, brow, bib, creases, and the larger shape too where the normals
   say so). Only a light hold on the current shape, enough that one round
   can't run away, not enough to stop the normals reshaping him.
- **The master's normals, complete and unaltered, for his front (owner):**
  wherever the master sees him, the target is the master's own surface
  direction, as the estimator gave it: not blended with the other photos,
  not trimmed back from his outline, not smoothed. The model conforms to it
  there and fleshes it out; the other photos only fill what the master
  can't see (sides, back, top, underneath), smoothed across their seams
  into the master's region, never the other way (tools/master_front.py).
- **The normals almost always win (owner).** If his normals stick out past
  the model, or the model doesn't come all the way up to them, then either
  I made the model wrong or that photo's scan went wrong, and so far it has
  much more often been the model. So: the model moves to the normals. The
  scan loses only where I can see on the photo itself that it misreads him
  there (checked by eye on the photo, and when other sides disagree with
  that one photo); never because the model "already looked fine".
6. After each round: look at him through the master first, then the
   profiles and close-ups; keep or change it on looks.
- In reserve: for what no photo shows well enough, small parts built from a
  close-up's own normals the same way.

### Correction (owner): the model must conform to his normals, not the other way round

The first chisel pass sampled his normal maps only at the model's own
points, so the model's shape decided where his normals could go: wherever
he is bigger than the model (his outline past the model's in the master:
his left side, lower cheeks, peets) his map was never used, and wherever the
model sticks out past him it got other photos' guesses. And comparing only
which way the surface faces can't see a surface that faces right but sits
too far in or out, so it read as "close" when it wasn't. Owner: "You're
conforming the normals to his existing model, rather than the other way
around."

Now (tools/master_shell.py):
1. His front from the master's map itself, over his whole outline: the
   normals integrated into his front surface (depth along each master
   pixel's ray; perspective integration: d log z / du = -n_x / (f n.r)),
   so the map alone fixes the shape; the model sets only one number, his
   overall scale (distance).
2. The model takes that shape: everything in front of his surface is cut,
   everything between it and the model's own back is filled (it grows where
   he is bigger), everything outside his outline in the master is cut.
   Behind his front, the model keeps its back, sides and top (fleshing out).
3. Checked against him through the master first (outline and surface),
   then the profiles and close-ups.

Result (stopped by the owner): his front from the master's normals alone
looked like him (outline, depth, face). Putting it onto the model failed
twice: tools/master_shell.py (extruding along the master's rays) made flat
walls and a slab cut off his left side; tools/conform_master.py (bending
the model's surface onto it) moved points up to 37 mm and came out crooked
and wrong. I should have stopped and said so after the first one. Neither
result is used; the kept model is still work/b/eyes4e. Waiting for the
owner on how to go on.

## The master's front reads like a human face mask (owner, seen; October 2026)

Owner: "in the first one [the master] it looks like a rabbit, and then in the
second one [the front from the master's normal map] it almost looks like a
human depth mask... it technically got the shape right from the very front,
but there are multiple ways to get the shape right from the very front, and
from the sides or back it looks more and more off... the more I look at the
normals map for his front, the more it looks uncanny." Seen and agreed:

- Nose and muzzle: his is broad and soft, sloping back from a small nose
  into his cheeks; the front has a narrow, ridged, pointed human nose with a
  bridge.
- Whisker pads and mouth: his are two rounded, puffy cushions over a short
  split; on the front they are sculpted lobes curving down like a human upper
  lip and smile lines.
- Eyes: his sit on the sides of his head and bulge outward (seen past the
  curve of his cheeks from the front); the front puts them in frontal sockets
  under brow ridges, like a human's.
- Neck and chin: in his profile there is a chin, a soft dip, then his bib;
  the front runs straight from mouth to chest like a mask with no neck.
- Peets: his are fluffy and tucked under him; the front has two small
  separate lumps stuck on below.
- From the side the front is an almost upright, flat face plate; his face
  slopes back from the nose and his head is round behind it.

Why: from one view many 3D shapes give the same picture (the bas-relief
ambiguity of shape from shading: shallow or deep, broad and sloped or narrow
and pointed). The normal estimator (Marigold, trained mostly on people and
indoor scenes) has to pick one, and where his white fur gives it little to
go on it fills in a human face. It matched the master from the front
exactly and is wrong in the ways only the other photos show. Treating it as
immutable then forced every other photo to bend around a face that isn't
his: the main reason nothing has lined up since (flap, gaps, layers, the
"too shallow" reading).

Consequence: the master is still the immutable reference for how he looks
from the front, but a normal map estimated from it is not his shape. The
front's depth and form must come from all the photos together (the side
photos decide how the muzzle slopes, where the eyes sit, the neck), with the
master deciding his outline and his look from the front.
