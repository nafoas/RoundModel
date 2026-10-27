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
