# Tasks: rebuild Prince from his parts

Agreed with the owner after the eye/upper-face stage (tasks/01). Done one by
one, in order, checked off here. Re-read CLAUDE.md, docs/INTENTS.md,
docs/PHOTOS.md and this file at every milestone. Nothing is simplified or
skipped without the owner's explicit permission.

## Why we are starting again

- The body was built by fitting outlines: its surface was pushed sideways
  until its edge matched his silhouette in each photo. So the silhouette
  agrees, and nothing inside it does. His cheeks, chest bib, lower skirt,
  haunches and the way his head sits into his body were never shaped from
  what the photos show; they are whatever surface fell between the matched
  edges. That is the "outline agreement" method the owner later said must
  never be the target, and it was the foundation.
- Everything since, including the eye and face work, was patches on that
  foundation. Each new change fought the earlier steps instead of shaping
  him (the cheek fill did nothing, the temple fill made a lobe, the forehead
  fill made a mound).
- The head was made before the close-ups existed. There are now 57 photos
  (docs/PHOTOS.md) showing him from far more angles.
- Owner: "the body itself doesn't look like any angle. Only the silhouette
  does. All the actual constituent parts don't even look like the master."

## What carries over

- docs/PRINCE.md (who he is, how he is shaped), docs/INTENTS.md, CLAUDE.md
  (the lessons), docs/PHOTOS.md and references/photo_index.json.
- The fitted cameras (master + sheet 02, 03, 04, 07, 08, 09), the world frame
  (metres, +x his right, +y forward, +z up) and his overall size.
- tools/look_render.py (the model beside any photo, from a plain direction)
  and the comparison sheets.
- What we learned about his eye: its true size from the profiles; from the
  front and three-quarters the brow and fur hide part of it.
- The old model stays in the repository history. Nothing is deleted.

## How he is built now

- He is made of his parts, each a soft rounded volume, blended into one
  smooth surface (no seams): head, cheeks, chest bib, lower skirt, haunches,
  peets, tail, ears; then the eyes set in, then the face parts.
- Each part is shaped from the forms the photos show, judged by its shading
  and form, not its edge. The question every time: does this part look like
  that part of him?
- The silhouette is not fitted. It comes out right because the parts are
  right.

## How each part is judged (every step)

1. Look at his photos for that part (master first, then the ones listed
   below) and write two or three plain sentences: what he looks like there
   and what the model gets wrong.
2. Make one change aimed only at that.
3. Render the model beside those photos (fitted cameras where they exist,
   look_render.py otherwise) and write a plain yes or no: does it look more
   like him? Numbers only as a minor sanity check; the eye wins.
4. Keep it, or change it so it looks like him; undo only when I can see it
   is further from him. Say so plainly either way.
5. Photos differ because he moves, the camera moves, the light differs and
   fur is fur. Accept that and move on; never investigate it.

## How sculptors do this (looked up at the owner's request)

- Block out with separate primitives first; the goal is the balance of the
  overall form. No detail until the blockout already looks like him.
- Compare against the photos through matched perspective cameras (photos are
  perspective, not orthographic; lining a model up as if they were ortho
  skews the proportions). We have fitted cameras for the master and sheet
  02, 03, 04, 07, 08, 09.
- Overlay the model on the photo (tools/parts_overlay.py) as a check of
  proportions by eye, and rotate the blockout to check it from every side.
- Where front and side disagree (he moves, the camera moves), settle on what
  most views show and match the likeness at the master and a three-quarter.
- Sources: 80.lv character production workflow; ZBrushCentral / Polycount /
  BlenderArtists likeness threads.

## The steps

- [x] 0. **Tool:** a parts file (each part: centre, size, orientation,
  softness) built into one smooth mesh, in the same world frame, so it drops
  into the existing renderers. Comparison sheet: master + sheet + close-ups
  beside the model.
- [x] 1. **Main body mass:** the big round body, as he stands in the master.
  Photos: master, sheet 01-09, edited front/back, close-ups 07, 08, 09.
- [x] 2. **Head mass and how it joins the body** (no visible neck; the head
  flows straight in). Photos: master, close-ups 06, 25, 07, 08, 10, 14;
  sheet 01, 03, 07, 09, 13-16, 18.
- [x] 3. **Cheeks** (full, round). Photos: master, close-ups 06, 25, 10, 21;
  sheet 01, 18.
- [x] 4. **Chest bib and lower skirt** (the layers under the chin).
  (First pass of 1-4 done: tools/parts.py + tools/parts_sheet.py; models/prince_parts.json has body, floor, head (tipped nose-down), crown, temples behind the eyes, broad muzzle, cheeks, bib, skirt. Sheets in checkpoints/cp4/. Rolled back on the way: a tall knob head, cheeks over the eyes, a hard-ledged skirt, cheeks blended so wide they buried the eyes.) Photos:
  master, close-ups 16, 22; sheet 01, 10, 11, 12, 17; edited front set.
- [x] 4b. **Proportion pass** (owner: chisel the broad strokes before any detail).
  Body set back and higher at the rear and a little narrower; cheeks narrower;
  muzzle smaller and forward-low; chest set back; jowl filling under the nose;
  ears blocked in (set back, leaning back). Rolled back: setting the head and
  crown back (it made the eyes bulge out of the face again).
- [ ] 5. **Haunches.** Photos: sheet 03, 04, 05, 06, 07; close-ups 17, 18,
  08, 09; edited back set.
- [ ] 6. **Peets** (small, round, fluffy; dark specks on the front ones).
  Photos: master, sheet 10, close-ups 16, 17, 18, 23, 24; edited peet lifts.
- [ ] 7. **Tail** (small round cottontail, whorl above it). Photos: sheet 05,
  10; edited back.
- [ ] 8. **Ears** (short, rounded, set wide apart). Photos: master, close-ups
  13, 14, 15, 09, 26; sheet 05, 06, 14.
- [ ] 9. **Eyes set in:** true size from the profiles, seated so the brow and
  fur hide part of them from the front. Photos: master, close-ups 01-06, 19,
  20, 21, 25; sheet 03, 07.
- [ ] 10. **Face parts,** one at a time: forehead and bridge, brow, socket,
  muzzle and nose, mouth, whisker pads. Photos per docs/PHOTOS.md "By part".
- [ ] 11. **Whole-model check** against every photo, master first; then show
  the owner.

After each step: a comparison sheet saved to checkpoints/cp4/, committed and
pushed, and the intents repeated.
