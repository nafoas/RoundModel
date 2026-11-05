# Tasks: Prince rebuilt from the master's front (owner, October 2026)

Agreed with the owner after the normal-map work (tasks/02). The old model
is abandoned: "The model just isn't right at all. It doesn't look like him
at all and I see no redeeming qualities in using it." Re-read CLAUDE.md,
docs/INTENTS.md, docs/PHOTOS.md, docs/MEASURING.md and this file at every
milestone.

## The method (owner)

Turn the master's normal map directly into a model and take that as the
immutable front-facing model, to fill in from, everything else made to
conform to the master, never the other way round.

- Blender add-ons that turn a normal map into a model (e.g. DeepBump) do
  normal integration (map -> height field -> displaced sheet), the same
  thing tools/master_shell.integrate already does; installing one means
  fetching outside code, which this environment blocked before (DSINE). So
  the integration in this repo is used (owner may ask to try a plugin).
- The old model is not used for anything: not for shape, not for scale.

## Steps

- [ ] 1. (built; shown to the owner, checkpoints/cp6/front.jpg, front_sheet.png; regenerate: python tools/master_front_mesh.py work/m/front) The front, from the master alone: his front surface from the
  master's normal map (checkpoints/cp5/maps/master_front_standing), over
  his whole outline, full resolution, as a mesh (tools/master_front_mesh.py).
  Immutable from here on. Its one free number, his distance (size), from
  the master camera: his nose tip at the master camera's depth for it
  (until the owner gives his real width or length). Shown to the owner on
  its own, from the front and from the side.
- [ ] 2. (first try stopped, not used: the other photos cut most of the master's face away (their cameras, solved against the old model, don't line up with the new front; and the front wasn't protected from them), the hidden parts came out faceted, and the block was too short (flat back). Proposed to the owner: re-solve the other cameras against the new front, never cut what the master sees, longer block, shape the hidden parts with normals. Waiting for the owner.) Fill in the rest from the other solved photos: their outlines
  carve what the master can't see (sides, top, back, underneath,
  haunches), their normals shape it; the fill meets the front's edge
  smoothly and never moves the front. Ears from the photos that show them.
- [ ] 3. Checked after each step: master first, then the profiles and the
  top-down; then the close-ups.

## Measured on the new front (tools/front_landmarks.py, checkpoints/cp6/landmarks3d.json)

- From the front (sheet 01, 18, edited fronts) his nose, mouth split and eyes
  land within about 8-25 px: it lines up.
- In every side view his eye lands 65-173 px off while his nose is within
  6-14 px (close-ups 21, 02, 08, 10): the front's eyes sit about 30 mm
  behind his nose, the profiles say about 42 mm. The front is about 70% as
  deep as he is (the estimator flattens a little everywhere).
- His peets on the front sit level with his nose; in the photos they are
  well back under his chest (35-185 px off): the normal map can't show that
  step, so the integration smoothed over it.
- Put to the owner: A) let the profiles set the depth but not the shape
  (one number deepens the front; the front split at the step under his
  chest so his peets sit back), or B) keep the front exactly as it is.
  Recommended A. Owner: the offsets are him moving (head held a little
  differently, weight shifted), not the front: re-fitting only his head turn
  in each photo makes eyes and noses land within ~2-20 px
  (tools/front_head_turns.py -> checkpoints/cp6/head_poses/). So B: the
  front stays exactly as it is; loafed photos don't cut his chest/peets.
- Fill, second try (tools/fill_from_photos.py -> work/m/fill2,
  checkpoints/cp6/fill2_sheet.png): no photo cuts within 4 mm behind his
  front; loafed photos don't cut below his mouth within 60 mm of the front;
  block 300 mm long. Result: the front survives whole (master and 3/4s look
  like him); the filled sides/back/top are faceted (outlines only, no
  normals yet), and the join between the front and the fill is a ragged
  ridge, a cliff in the left profile.
- Smoothing the filled-in rest with his front held (tools/finish_fill.py ->
  work/m/fin1, checkpoints/cp6/fin1_sheet.png): the facets are gone, the
  sides, back and top are smooth. But the front's rim stays a flap standing
  off the body (a crease behind it in both profiles, the back 3/4 and from
  above): with every front point held, nothing can close it. Put to the
  owner: let only the front's outer band (near his outline in the master)
  slide along the master's own lines of sight, which leaves it identical
  in outline from the master, so it can meet the sides. Normal shaping of
  the rest not run yet.
- Owner: the front's edge is his edge; fill in the side normals and make
  them conform to his edge. Tried (tools/finish_fill.py --shape, edge
  direction carried on near the front's edge -> work/m/fin2,
  checkpoints/cp6/fin2_sheet.png): no better. The flap stays and new
  crumpled patches appear under his cheeks: the gap behind the front's edge
  is a missing chunk several mm deep (the fill's carving cut it), which
  sliding points 2-3 mm along their normals can't cross. Stopped and put to
  the owner: keep the volume behind his front's edge in the fill itself
  (so it is never carved open), then round off the join.
- Owner: the master's edge should BE the model's edge; no second model.
  Built him along the master's lines of sight instead
  (tools/build_along_master.py -> work/m/along1,
  checkpoints/cp6/along1_sheet.png): front from step 1, back where the other
  photos agree he ends along each line. Didn't work: the back jumps between
  neighbouring lines (several photos, each lining up a little differently),
  so from the sides he is long streaks and stretched sheets; lines grazing
  his sides make slivers; dark patches on the front from a joining bug.
  Stopped and put to the owner: find his back as one smooth rounded surface
  fitting what the other photos say overall, and fix the joining bug.
- Owner: research instead of guessing (docs/RESEARCH.md). Tried the
  field's recipe (tools/poisson_fuse.py -> work/m/pois1,
  checkpoints/cp6/pois1_sheet.png): every photo's normal map integrated to
  depth, placed through its camera, all as oriented points, screened
  Poisson. Didn't work: each photo's surface sits 2-7 mm (one 11 mm) off
  the others and bends differently, so the points form several layers and
  Poisson made overlapping shards; nothing underneath him, so the bottom
  came out open like a bell. The recipe assumes the per-photo depths agree
  to about a millimetre (they come from multi-view stereo or scanners
  there); depths integrated from one photo's normals don't. Stopped and
  told the owner.
- Back to building along the master's lines of sight, fixed rule: his back
  is the LAST place the photos agree he's still there (the first-outside
  rule cut him off right behind the front wherever photos were slightly
  off), smoothed (tools/build_along_master.py -> work/m/along2,
  checkpoints/cp6/along2_sheet.png). Master: whole, like him, dark patches
  gone. Other sides: a long tube to the end of the search (too few photos
  see behind him to say where he ends) and streaky walls (surface made
  straight from two depth maps). Put to the owner: let the photos that see
  behind him (profiles, top-down, back 3/4) decide where he ends, and make
  the surface from a volume.

## Known risks (said up front)

- The master can't show depth jumps inside his outline (how far his chin
  stands off his chest, how deep his body goes behind his cheeks): the
  profiles decide those, and may show the front's overall depth scale needs
  changing (one number, not its shape).
- The other photos' cameras were solved against the old model: still in the
  same world frame as the master, but some may need re-solving against the
  new shape.

## Standing rule for this stage (owner)

If a step comes out looking wrong, or a number is far outside what I
expected, I stop and tell the owner plainly ("this isn't going well")
before doing anything else. No pushing through, no new fix written first.

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

Owner, on the expression: "compare the facial expression on the left [the
master] to the right [the front from its normal map]. One is a very
mysterious, neutral, yet curious uniquely rabbit expression. The one on the
right gives 'victorian death mask' with a completely closed mouth and slight
peaceful smile. It's uncanny." His: a short soft split under a small nose,
whisker pads puffed out round it, eyes on the sides. The front's: a defined
nose bridge, the pads carved into a closed upper lip with a faint smile,
eyes in frontal sockets.

Next (owner): "for now, we just do the front, to see if it works properly":
new normal maps for the master, his front built from each, judged from the
front AND the side against his photos (broad softly sloping muzzle, eyes on
the sides of his head, a neck distinct from his head, his expression)
before anything else is built.

## New fronts (tools/front_candidates.py; checkpoints/cp6/front_candidates.jpg, front_candidates_views.png)

Depth maps of his front from three estimators, put at his distance, edges
capped (they bled into the background up to 0.5-0.7 m behind his nose),
judged against docs/FEATURES.md:
- Depth Pro (Apple, metric): from the front and three-quarters the most
  rabbit-like: broad soft muzzle, full cheeks, no nose bridge, no carved
  lip or smile; noisy (fine stripes, fur texture). Eyes ~56 mm behind the nose.
- Marigold depth: fur-texture noise and a hole at his nose: not usable.
- Depth Anything V2: clean, eyes on the sides, but the nose fairly defined
  again; eyes ~73 mm behind the nose.
- From the side, both usable ones make his muzzle stick out as a point
  (a cone), not his broad, softly sloping muzzle: no estimator from the
  master alone gets the side right (the same one-view ambiguity).

## Joint front from several angles (owner's idea; tools/joint_front.py; checkpoints/cp6/joint_sheet.png)

His face solved at once against the master (Depth Pro's surface), both
three-quarters and both profiles (their normal maps, his head turned as
re-fitted, profiles counting for his head only), per-pixel depth at 1/4
resolution, light smoothness. The four side views agreed about three times
better afterwards. By eye: hints of the right thing (eye bulges move out to
the sides of his head, rounder whisker pads in the 3/4), but the surface
tore (flakes, shards, steps, spikes on his forehead and cheeks): each
pixel moved freely and the views' noise and small misalignments pulled
neighbours apart. Stopped and put to the owner: solve coarse to fine (broad
shape first, detail after), as methods like SuperNormal do.

- Coarse to fine (owner: go): the depth may only change as a smooth field,
  cells of 128, then 64, then 32 photo px; fine detail stays Depth Pro's
  (tools/joint_front.py --stages 32,16,8 -> work/m/joint/j2,
  checkpoints/cp6/joint2_face.jpg). No tearing; the four other views agree
  better at every stage. By eye: muzzle broad and soft from the front and
  three-quarter, sloping a little more gently from the side; still Depth
  Pro's fine contour ripples (its depth steps) over the face, and judged
  from a front-only shell the side is hard to read.

## The other angles decide his shape; the master only regulates (owner, November 2026)

Owner: "the same silhouette from the front can produce multiple shapes as it
goes further back... use the other angles as a means to *achieving* the
front, not making the front straight up overwrite them... He has a gently
sloping, broad forehead, with a tiny bit of depth, but that same thing can
be emulated with that weird nose thing on the model previously that looked
like a death mask... The front can still look like the front even if you
defer to the other angles, the front just serves as a means of regulating,
like 'okay so we didn't go too far from this angle, the front is still the
front'." And: "the problem with the current method is we essentially stick
with one possible way that it could have the same shape from directly
ahead, even if it's wrong."

So:
- Every method so far picked ONE shape matching the master from the front
  (Marigold's guess, then Depth Pro's) and made it fixed or the start that
  everything else bent around; if it was the wrong one of the many, nothing
  could undo it.
- From now on no front guess is committed to. The other angles (profiles,
  three-quarters, top, back, close-ups) decide his shape; the master only
  rules out shapes that don't look like him from the front: his outline in
  the master stays his outline, and from the front his surface still reads
  like the master, as a gentle check, never the main pull.
- His head is one closed surface (not a front shell along the master's lines
  of sight, which the side photos can't shape: from the side it is only a
  grazing edge), starting as a smooth rounded head from the photos'
  outlines, shaped coarse to fine through every photo's camera (his head
  turned as re-fitted) by their normal maps and outlines.
- Judged by eye against docs/FEATURES.md, the side and three-quarters as
  much as the front.

- First whole-head solve (tools/whole_head.py -> work/m/wh1,
  checkpoints/cp6/wh1_sheet.png): failed. The neutral hull still has the flat
  shelf across his chest (my fix to the loafed-photo rule didn't remove it),
  and the solve covered him in spikes: single points slid up to 54 mm (the
  smoothness term was far too weak for a 2 mm mesh, and points near the rim
  were pulled by misaligned outlines). Stopped and told the owner.

- Chest shelf, cause found: below his mouth the loafed photos are not
  allowed to cut (their chest posture differs), and the only photos left
  there are front-facing ones, which can't carve depth; so that band stays
  as far forward as the block reaches. Starting the block at his nose tip's
  depth made the slab smaller but a ridge remains at mouth level
  (checkpoints/cp6/hull2_sheet.png): the band rule itself makes the step.
  Stopped (bump solve not run) and put to the owner: drop that rule for the
  starting head (let all photos carve his chest; the solve, with the
  standing photos, then shapes it).
- The solve now changes his shape only through broad smooth bumps (60 of
  30 mm, then 300 of 13 mm), so no single point can spike.

- Shaping step with smooth bumps (tools/whole_head.py -> work/m/wh3,
  checkpoints/cp6/wh3_sheet.png): no spikes, no tearing, but it does not
  look more like him: the same lumpy egg, a little lumpier; no face, eyes,
  muzzle or neck emerge from any side. The photos' normals barely moved it
  (agreement 0.119 -> 0.121, no better). Stopped and told the owner.

## Never let angles overlap (owner, November 2026)

Owner: "I believe the automatic routes can work, if we are simply
systematic. If we never let angles overlap, this wouldn't be a problem."
Looking back, every automatic attempt let photos overlap (fused normals
averaged every photo that saw a spot; Poisson stacked every photo's surface;
the joint solves let every photo pull on every point), so where two photos
disagreed (he moved, cameras don't line up exactly) they fought (spikes,
layers) or cancelled (lumps). The parts model was rebuilt by mistake and
shown as if new (it is tasks/02's, unchanged): not that again.

Method:
1. Ownership map: his surface divided into patches, each owned by exactly
   ONE photo, the one that sees it most face-on (loafed photos own his head
   only; the master's estimated normals are still not his shape, but the
   master stays the reference for how he looks from the front). Shown to
   the owner before anything is shaped.
2. Each patch takes its shape from its owner's normal map alone, never
   blended with another photo.
3. Only at borders do neighbours meet, in a narrow band where the two
   surfaces are joined smoothly (no step).
4. Checked by eye after the map, then after each patch is shaped. If
   neighbouring patches meet badly offset somewhere, stop and show the owner.
(As in photogrammetry texturing: one photo per patch, smooth seams; here for
shape.)
