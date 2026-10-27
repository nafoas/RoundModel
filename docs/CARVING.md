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
