# Carving Prince (the subtractive method)

Owner's direction: "it should be subtractive. Think of it like you're
sculpting him rather than putting blobs together. Start with a shape bigger
than all sides, and chisel." Everything about the technique is written here.
Read with CLAUDE.md, docs/INTENTS.md, docs/PHOTOS.md and the current task file.

## 1. His outlines (tools/outlines.py -> checkpoints/cp4/outlines/)

- Photos used: the master and the six sheet originals with refined cameras
  (02 front 3/4 right, 03 right profile, 04 back 3/4 right, 07 left profile,
  08 front 3/4 left, 09 top-down). Sheet 05 (back) and 06 (back 3/4 left)
  use their small panel traces from checkpoints/cp1.
- Traced with **BiRefNet** (`birefnet-general`, a background-removal
  segmentation model run locally through the `rembg` package; the photos
  never leave the machine). It follows the edge of his dense fur and leaves
  the whiskers out. Thin whisker spikes it keeps are removed with a 6 px
  round opening; only the largest piece is kept.
- One photo per process (`python tools/outlines.py VIEW`): the model needs
  ~14 GB and was killed when several ran in one process.
- **Manual patches**, checked by eye on gridded zooms (`PATCHES` in
  tools/outlines.py): sheet 02, the dark gap between his front peets under
  the hanging fur; sheet 09, a lobe of whiskers caught at his left jaw.
- What did not work (don't repeat): colour rules and GrabCut (lost his
  shaded grey lower fur, took in the lamp-lit wall); scaling the small panel
  traces up to the originals (they do not line up).
- Review sheet: checkpoints/cp4/outlines/_review.png. The owner checked the
  outlines and asked for the two patches above.

## 2. The rough-out: carving the block (tools/carve.py)

- Start: a block of 1.5 mm cubes bigger than him on every side
  (x +-12 cm, y +-15 cm, z -4..21 cm; metres, +x his right, +y forward).
- From each photo's fitted camera, every cube that projects outside his
  outline is cut away. What is left is the largest shape all the photos agree
  he could be (the "visual hull").
- He is a real rabbit, not a statue: in each photo his head is posed as he
  holds it there (checkpoints/cp3/head_poses_parts, the head turns on the
  neck pivot, the body stays). Each photo also gets a small tolerance for its
  camera fit, in that photo's pixels: top-down 3, master 3, right profile 6,
  three-quarters 8, left profile 14 (his head is held differently there),
  panel photos 2 panel px. Top-down (his circumference) and the master cut
  hardest.
- Then: one solid piece, holes filled, surface by marching cubes on the
  lightly blurred block, voxel steps relaxed with Taubin smoothing (does
  not shrink him).
- `python tools/carve.py OUTDIR [--round R] [--keep_mm K]`

## 3. Chiselling

- **2a, corners off** (`--round R`): carving leaves flat planes meeting at
  hard edges wherever no photo looked squarely. The signed distance to the
  carved surface is blurred over R; at an edge the blurred surface lies
  inside, so the edge is cut. Only cuts, never adds. R = 6 mm keeps the
  outlines (1-6 % of his area shaved); 10 mm rounds more and shaves more.
- **2b, by eye** (next): what no outline can show (hollows such as the dip
  between cheek and chest and under the chin, the shape of the face inside
  its outline, where flat planes remain) is chiselled by hand against his
  photos and close-ups, master first: small, local cuts, one at a time, each
  checked against him.

## 4. Checking

- tools/silhouette_check.py MODEL_DIR OUT.png: per photo, his outline
  (green), the model's (red), both (yellow), through the fitted camera with
  his head posed; under each, how much of the model sticks out past him and
  how much of him it misses. A check to look at, not a target.
- tools/parts_sheet.py OUT.png MODEL_DIR...: shaded model beside his photos
  (fitted cameras and close-ups), to judge form by eye.
- State the differences measured and seen, never "about right".

## 5. What the first carving showed (October 2026)

- The outlines agree well in every photo except top-down, where the carved
  shape misses ~10 % of him: he is longer at the rump and at the nose there
  than the side and back photos allow. In the top-down photo he is lying low
  with his nose down sniffing (a loaf spreads down and out), and the other
  photos are of him standing; the model is him standing, so the length comes
  from the profiles and the width from top-down. The owner decides if that
  call is wrong.
- The right profile cuts his face front back by a few millimetres compared
  with the old model (the owner had said the old nose sat too far out).
- The carved form is still blocky: flat planes on the face and top of the
  head, and the face front sits behind the cheeks from the front. That is
  what the chiselling is for.

## 6. Second round (owner: "you carved too much... all sides missing something...
## his nose is a square from above"; "only add and remove just what is needed")

- **Gentle carving** (`--votes 2 --hard 1.5`): a cube is cut only if at
  least two photos put it outside him by more than their tolerance, or one
  photo by more than 1.5x its tolerance. One photo's small camera or pose
  error can no longer cut him alone. (votes 2 / hard 4 left him 5-11 % too
  big all round; hard 1.5 is the balance.)
- Surfaces are now written facing outward (marching cubes on an inside-high
  field faces inward; this made the first fine pass grow him everywhere).
- **Fine passes** (tools/refine_rim.py, section 3c): each round, the model's
  rim from every photo is compared with his outline and moved in or out
  along the surface normal by the gap (photo pixels converted to mm at that
  depth), capped at 1 mm per round, weighted (top-down 3, master 2.5,
  others 0.5-1), spread into a smooth field so it is a gentle reshaping,
  never a lump. 6 rounds: moves up to 3.8 mm out and 5.2 mm in.
- Result (work/c/f1, regenerate: carve.py --votes 2 --hard 1.5, then
  refine_rim.py --rounds 6): model past him / missing of his area:
  master 1.1 / 1.9 %, right profile 2.5 / 1.9, back 3/4 right 3.0 / 0.5,
  front 3/4 right 1.9 / 2.2, front 3/4 left 2.9 / 2.7, left profile
  4.6 / 2.5, back 1.7 / 2.3, back 3/4 left 2.5 / 2.6, top-down 0.4 / 8.4.
- **Top-down**: the model still stops short at the rump (about 16 mm,
  a straight edge) and at the nose (a flat front, about 2-3 mm short at
  the middle). Those edges are where the side and back photos, of him
  standing, cut; in the top-down photo he is lying low with his nose down.
  Weighting top-down 10x (rolled back, sheet 06) only brought it to 5.7 %
  missing, made the model 3-7 % too big in every other photo, and put lumps
  above the eyes and on the side: not kept.
- **Form**: the carved form is faceted (flat face front, flat top of the
  head, a steep cut under the jaw that reads as a dark ledge from the
  front). Carving without the head poses gives the same, so it is not the
  poses: outlines cannot shape these areas. They are the by-eye chiselling.

## 7. Scaling the photos to each other (owner: "you've not properly scaled the
## images to each other ... you're just not accounting for distance")

- Hooks added: carve.project() applies a per-photo scale / shift / roll from
  checkpoints/cp4/view_align.json (scale about where his body centre lands,
  equivalent to moving that camera nearer or further).
- Try 1, tools/align_views.py (fit each photo to the carved shape, repeat):
  ran away (top-down scale fell to 0.78 in 5 rounds; the carved shape is
  always a little small, so it pulled every photo smaller). Not used.
- Try 2, tools/scale_views.py (his size measured in mm at each photo's
  distance, one scale per photo solved by least squares, master fixed):
  measured width / length / height: master 162 / - / 197 mm, top-down
  157 / 225 / -, right profile - / 209 / 200, left profile - / 212 / 208,
  back 174 / - / 208. Solved size 160 x 213 x 200 mm; scales 0.94-1.01.
  After scaling, top-down still shows him ~7.5 mm longer and ~5.5 mm
  narrower than the others: a difference in proportion, which no distance
  (a uniform scale) can produce. With the scales applied, top-down missing
  rose 8.4 -> 11.5 % and back 2.3 -> 11.0 %: rolled back
  (view_align.rejected.json, sheet 08).
- What could make him look longer from above and shorter from the side
  without a distance error: the profile cameras looking slightly more from
  the front or back than fitted (or his body turned a little toward or away
  from them), which shortens his length only (a 20 deg turn shortens it 6 %);
  or his posture (lying low and stretched from above, standing in the
  others). Asked the owner.

## 8. Reading the top-down photo as his shape, not his length (owner)

Owner: "he looks longer in the top down one merely because he is such a
compact loaf. In the profiles you can really see how short he is, but from
the top you lose all sense of reference - his legs, ears, anything - so even
his sides and back kinda get lost within the sheer fluffy loaf form, so he
looks 'longer' when in reality it is just because there's not a lot of
perspective." (A new top-down photo is on offer if ever needed.)

- So: **his length comes from the profiles (213 mm); the top-down outline
  gives the shape of his circumference** (the round of his nose, the curve
  of his rump, how his sides run). In checkpoints/cp4/view_align.json the
  top-down photo alone gets a length factor (the model's projection there is
  stretched along his length, `sy`, 225/213 to start) and a shift; both were
  then solved against the carved shape (sy 1.077, shift -10, -11 px).
- Then gentle carving and the fine passes as before. Current base:
  work/c/tf2 (regenerate: carve.py work/c/t2 --votes 2 --hard 1.5;
  refine_rim.py work/c/t2 work/c/tf2 --rounds 6).
- Outlines (model past him / missing): top-down 3.0 / 3.3 % (was 0.4 / 8.4),
  master 1.2 / 1.9, right profile 2.9 / 1.9, back 3/4 right 3.3 / 0.5, front
  3/4 right 1.9 / 2.2, front 3/4 left 3.0 / 2.7, left profile 4.8 / 2.4,
  back 1.7 / 2.4, back 3/4 left 2.8 / 2.6.
- From above (sheet 10): the nose is round now and his sides follow his
  outline; the rump end is still a little flat in the middle (~20 px short
  of his curve) and there is a slight bulge past him at the upper left.

## 9. The top-down photo turned; his back rounded (owner)

- Owner: "you just oriented the photo wrong ... he is pointed slightly to
  the left in the photo, but the model doesn't reflect that." The top-down
  photo is turned in its own plane (same as turning him on the spot), solved
  with its shift and length factor: 5.4 deg (every starting turn from -6 to
  +6 deg converged to 5.4-6.4), shift (-10.8, -8.6) px, length factor 1.074.
  His sides now follow his outline all round from above (sheet 11).
- The rump end from above stays a little flat in the middle (~25 px, ~4 mm):
  behind the middle the profiles put his rump end ~4 mm further forward
  than the top-down photo. Re-solving the length did not change it.
- **From behind** he is a smooth ball; the carving was faceted there (a flat
  back wall and hard corners between the views: outlines only show his
  edge, not how round his back is). Fix: chisel the corners off over a
  wider radius (`--round 0.014`, 250 cm3 cut), then the fine passes put his
  outlines back (`refine_rim.py --rounds 10 --cap_mm 1.2`; up to 9.5 mm back
  out at the rims). His back now rounds over like his (sheet 12).
- Surface: blur 1.6 cubes before meshing and 30 Taubin rounds, which took
  out the rings (cube steps) on gentle curves. Renders now have a soft light
  following each camera, so back and top views are lit as in his photos.
- Current base: work/c/rrf2 (regenerate: carve.py work/c/rr2 --votes 2
  --hard 1.5 --round 0.014; refine_rim.py work/c/rr2 work/c/rrf2 --rounds
  10 --cap_mm 1.2). Outlines (past him / missing): top-down 1.6 / 3.8 %,
  master 1.3 / 2.5, right profile 2.0 / 2.3, back 3/4 right 2.5 / 0.7, front
  3/4 right 1.8 / 2.8, front 3/4 left 2.7 / 3.2, left profile 3.2 / 2.8,
  back 1.3 / 2.9, back 3/4 left 1.4 / 3.1.
- Still blocky: the face front (lumpy, flat), the top of the head (a flat
  plate with ridges at its edge from above). Next: the by-eye chiselling.

## 10. Better from above, without making him crooked (owner)

Owner: "trying to make him look better from above, with respect to the other
angles, could be very productive. Just be wary of making him crooked by
accidentally using the slightly left tilting image."

- **Ears out of the outlines** (tools/ears_out.py -> <view>.noears.png):
  left in, the front and side photos carved a slab at ear height between
  the ears, which from above was a flat plate with ridges at its edge. An
  ear is what a round opening ~1/9 of his size removes from the top third
  of his outline; carve.py uses the ear-less outlines (ears get their own
  step). Review: sheet 14.
- **Symmetric, about his own midline**: first try mirrored across the
  world's x = 0 and shifted him sideways (master: model past him on one
  side, short on the other: 5.7 / 6.9 %). His midline plane is found from
  the carving itself (the vertical plane his shape is most nearly a mirror
  image across): x = -5.4 mm, turned 2.35 deg (checkpoints/cp4/midline.json).
  The carved block's signed distance is averaged with its mirror across that
  plane, and every fine-pass move is averaged with the move at its mirror
  point. The top-down photo (him pointing a little left) can no longer bend
  him.
- Current base: work/c/ef2 (carve.py work/c/e2 --votes 2 --hard 1.5
  --round 0.014; refine_rim.py work/c/e2 work/c/ef2 --rounds 10 --cap_mm
  1.2). Outlines without ears (past him / missing): top-down 2.4 / 3.5 %,
  master 3.1 / 2.5, right profile 2.5 / 2.1, back 3/4 right 4.0 / 2.1, front
  3/4 right 2.2 / 2.2, front 3/4 left 3.3 / 2.4, left profile 3.2 / 2.2,
  back 1.6 / 3.0, back 3/4 left 1.8 / 6.1.
- From above (sheet 16) he is now a smooth, symmetric egg; the plate is
  mostly gone, a faint U-shaped rim remains where the head meets the body.
  From behind and above (close-up 14) smooth. Still to chisel: the face
  front and the jaw-to-chest ledge from the front; the placeholder eyes are
  not yet seated in this head.

## 11. Ripples out (no ridges along the photos' outline curves)

- Seen against the master, close-ups 06, 25, 19, 20, 21, 10 and the edited
  loaf front: arcs across his face front and a U on top of his head, which
  he does not have (his face runs softly into a full chest).
- Tried: filling creases with a 6 mm rounded tool (`carve.py --close`):
  hardly changed anything. The arcs are not one crease.
- Cause: the fine passes. Each photo's outline is a curve across his
  surface, and moving those curves in and out left a ridge along each. Fix
  (`refine_rim.py --fair 400 --smooth 1500`): Taubin smoothing first (no
  shrinking), then the fine passes with moves spread 50x more broadly
  (smoothness 1500 instead of 30). 300 was not enough.
- Outlines barely changed (each within half a percentage point; past him /
  missing): top-down 2.2 / 3.7, master 3.4 / 2.4, right profile 2.8 / 2.3,
  back 3/4 right 4.5 / 2.2, front 3/4 right 2.0 / 2.4, front 3/4 left
  3.0 / 2.5, left profile 3.4 / 2.2, back 1.5 / 3.2, back 3/4 left 1.8 / 5.9.
- Current base: work/c/sm1500 (carve.py work/c/e3 --votes 2 --hard 1.5
  --close 0.006 --round 0.014; refine_rim.py work/c/e3 work/c/sm1500 --fair
  400 --smooth 1500 --rounds 12 --cap_mm 1.2). Renders: plain-direction fill
  light lowered to 2.0 (6.0 washed out close framing).
- Still to do: a soft shading band where his face meets his chest from the
  front; the face front shape itself; seating the eyes (placeholders); ears.

## 12. Fine registration: offsets, not shapes (owner)

Owner: "the master has some past him on one side, and some missing on the
other ... you've actually somewhat offset the master relative to his actual
proportions. Be very refined, deliberate, and gentle ... look and see if
what you did made it worse."

- tools/register_views.py: every photo (master included) gets a small shift
  and roll in its own image plane (never a scale), half the found
  correction per round, 3 rounds, capped (2 % of his size, 3 deg). Shifts
  found: 1-7 px per round; overlaps rose 0.002-0.03 in every photo.
  Before: view_align.before_register.json.
- The master still showed width on one side above and the other below:
  his head is held tilted in the master, not his body offset. A head pose
  for the master (head only, as the other photos already had) was solved
  against the carving: tilted 6.4 deg, shifted 4 mm, no turn or nod
  (checkpoints/cp3/head_poses_parts/master_front_standing.json).
- Result (work/c/gf2; past him / missing): master 2.5 / 1.3 (was 3.4 /
  2.4), top-down 2.2 / 3.5, right profile 3.2 / 2.3, back 3/4 right
  4.4 / 1.9, front 3/4 right 1.9 / 2.6, front 3/4 left 2.9 / 2.6, left
  profile 4.3 / 2.3, back 1.2 / 3.1, back 3/4 left 1.5 / 5.2. Form by eye
  (sheet 20): face and body as before, smooth; from above a touch cleaner.
- **Made worse, open**: a crease across the back of the head (behind
  where the ears go), seen from behind and above (close-up 14). By stage
  (sheet 21): the carving alone has a faint dip; the fine passes deepen it,
  more so after registration. Tried and rolled back: a 12 mm crease fill
  (no change); closing the dip between the ear stumps in the ear-less
  outlines (no change); skipping fine-pass moves near the removed ears
  (made him 5-8 % too big everywhere). Not solved yet; likely it goes with
  shaping the ears and the head top together.

## 13. The step behind his head

- Found by measuring the top line along his midline (work/c/gf2): it drops
  8 mm in one step just behind the head (151.7 mm high 10 mm behind the head
  line, 159.5 mm at it). That step is the "crease" seen from behind/above.
- tools/fill_hollows.py (fill toward a smoothed copy where the copy is
  outside him, in a box, symmetric): moved < 1 mm, no visible effect; the
  step sits on his overall convex dome, so it does not read as a hollow at
  any smoothing scale. Kept as a tool, not used.
- Cause found: cutting the ears out of the outlines also cut a notch at each
  ear base, and the earlier notch fix excluded exactly the ear's area. Now
  ears_out.py closes the ear-less outline with a round tool (8 % of his
  size) in the top band including the ear's area (closing cannot regrow the
  ear). Fills were small: in most photos the step is where his ear bases
  sit, not an outline notch.
- Result (work/c/gf6; carve.py work/c/g5 ... as before): the step is
  1.2 mm smaller (152.9 -> 159.9 mm), softer from behind (sheet 22);
  outlines the same or slightly better (master 2.5 / 1.2, back 1.0 / 3.1,
  others within 0.1).
- The rest of the step sits under his ear bases. Next: build the ears; if a
  crease still shows at their bases from behind, fill it locally then.

## 14. His ears (built leaves, not carved)

- Carving the ears does not work: his ears move independently and are held
  differently in every photo, so the photos never agree. Carved with all
  photos (votes): stubs 8 mm tall. Carved from master + right profile +
  back only: a lump spanning both ears and the head top; restricted to the
  master's ear areas: two small flat pills lying on his head
  (tools/ears_build.py, kept as a tool, not used).
- tools/ears_leaf.py: each ear a thick, cupped leaf. Flat shape = his ear
  outline in the right profile (seen nearly flat-on), back-projected onto
  the vertical plane 21 mm to his right of his midline (head posed as there,
  then un-posed, per-photo alignment undone), outline smoothed (1.5 mm),
  base carried 7 mm down into his head. Thickness 7 mm with fur, rounded
  edges (4 mm), base flared 10 mm over 8 mm height into his head fur
  (smooth onset). Cupped 3 mm (edges out toward his side). Leaning out
  12 deg, turned 15 deg to face a little forward. The left ear is the mirror
  of the right across his midline.
- Tries: 3 mm thin leaf (blades: rolled back); 7 mm with a raw traced edge
  (ragged streaks, block-like base: rolled back, sheet 24b); turned 40 deg
  (from the master's ear width): broad from the front but nearly edge-on
  from behind, while from behind-right (close-ups 13, 15) his near ear
  shows its pink inside: rolled back (sheet 24c). 15 deg kept as the middle.
- Result (work/c/leaf5 = work/c/gf6 + ears): ear 37 mm wide incl. base,
  28.5 mm tall incl. the buried 7 mm, top 178 mm. Outlines with ears (past
  him / missing): master 3.2 / 1.5, right profile 4.0 / 2.4, back 2.0 /
  3.4, back 3/4 left 2.3 / 4.1, front 3/4 right 3.0 / 2.8, front 3/4 left
  4.0 / 3.1; back 3/4 right 7.7 / 1.9 and left profile 5.2 / 2.3, where
  he holds his ears differently (more upright, further forward). From
  behind/above his ears look larger and rounder at the base than the model's.

## 15. Fixing pass, F1: his eyes seated

- Before (sheet 26a): one small eye showing from the front, the other
  buried: the placeholder eyes from the old model, never seated in this head.
- checkpoints/cp4/eyes.json: the fitted eyes (eyes3d.json: true size from
  the profiles) un-posed from the master head pose (they were fitted when
  the master had none), made symmetric about his midline, then pushed 4 mm
  out along each eye's axis and lowered 1.5 mm. That puts them on his traced
  eyes in the master (they had been ~13 mm too close together) and the left
  profile. The three-quarter photos disagree whichever way (his head is
  turned differently there), so they do not decide this. Radius 10.1 mm.
- tools/seat_eyes.py: around each eye the head surface is lowered along the
  eye's axis: inside the lid opening (half-angle 74.5 deg, fitted) to just
  under the eyeball, the lid rim r cos(psi) in front of the centre, then
  rising at `slope` back into his face; never moved outward; relaxed a
  little so there is no hard edge.
- Slope 0.6 made a wide dish round each eye (rolled back, sheet 26b);
  2.0 still a dish; 3.5 kept: a tight socket with the fur close round the
  eye, as in close-ups 21 and 02.
- Current model: work/c/eyes4e (seat_eyes.py work/c/gf6 work/c/eyes4
  --slope 3.5; ears_leaf.py work/c/eyes4 work/c/eyes4e --turn 15; eyes from
  work/c/eyes4).
- Still: from the front a small notch at the side of the head round each
  eye where his fur fills in more.

## 16. Fixing pass, F2 and F3: measured, not shape problems at this scale

- F2, the "flat plateau" on top of his head from above: measured across
  his head 20 mm forward of the head line, the top falls 0.8 mm at 8 mm
  out, 2.7 at 16, 4.7 at 24, 10.7 at 32: already a round arc. The bright
  plateau is the top light on a round head top framed by the darker sides.
  tools/round_crown.py (ease each cross-slice toward a fitted circular arc)
  moved < 0.7 mm, no visible change (sheet 27); first version faded out at
  the shoulders and moved the wrong way (+1.1 mm in the middle). Not used.
- F3, the dark band under the muzzle from the front: fill_hollows.py in a
  box round the lower face moved <= 1.1 mm, no visible change (sheet 28).
  The band is the broad shading round a smooth, featureless muzzle mound,
  not a crease. What is missing there is fine form (nose, whisker pads,
  mouth, soft chin), which is the fine-detail step (owner has a method in
  mind). F4 (face in profile) belongs with it.
- Current model unchanged from F1: work/c/eyes4e.
