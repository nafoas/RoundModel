# Checkpoint 1 — the walls

Each "wall" is one neutral-pose view of Prince: his outline traced from
that photo, plus the camera that took it (position, direction, lens),
solved so every view lives in one shared 3D space. Nothing is assembled
yet; that is Checkpoint 2.

## What's here

- `review/00_master_front_standing.png` — the master, at its own framing.
- `review/01…12_*.png` — every other wall view.
- `review/all_walls.png` — all of them on one sheet, master first and large.
- `review/camera_map.png` — where each camera was, seen from above and from
  his right side.
- `cameras.json` — the solved cameras and 3D landmark positions.
- `masks/` — the traced masks for every reference (walls and pose views).

In the overlays: **red** = his body outline (where fur is dense enough to
read as his surface), **blue** = his fringe (wispy outer hairs), **orange**
= whiskers (kept separate, not part of any wall), **green dots** =
landmarks placed by hand, **magenta crosses** = where the solved camera
puts those landmarks. Green and magenta sitting on top of each other means
that camera agrees with the rest of the views.

## Wall views used

| Tier | Views |
|---|---|
| master | front, standing |
| edited | back; back three-quarter (his left, from slightly above) |
| sheet | 01 front; 02 + 08 front three-quarter; 07 left profile; 03 right profile; 06 back three-quarter left; 04 back three-quarter right; 05 back; 09 top-down; 10 bottom-up |

Not walls (different pose — kept as checks for later stages): head lifted,
head lowered, head turned both ways, blink, loaf, both peet lifts, the
toddling three-quarter, sheet 11–18.

## How it was done

1. Outlines on the white-background images: anything measurably below pure
   white and attached to him is him; whiskers removed by width; the outline
   is where local fur coverage passes 50%. (`tools/segment_white_bg.py`)
2. Outlines on the sheet panels: a learned background-removal model
   (IS-Net), because colour thresholds lost his ears' pink insides and
   confused the lamp. (`tools/segment_sheet_ml.py`)
3. Landmarks (eyes, nose, mouth, ear tips, peets, tail) placed by hand on
   gridded zooms. (`references/landmarks.json`)
4. Cameras: one joint solve across all views, with the master weighted 10×,
   edited 3×, sheet 1×; bilateral symmetry for paired landmarks; a normal
   phone-lens prior. (`tools/solve_cameras.py`)

## Things to check

- Do the red outlines match him in every view? Missing fluff, extra
  background, a cut-off ear or peet?
- Are the whiskers (orange) all whiskers and nothing else?

## Known limitations (honest notes)

- **Back views with only two visible landmarks** (sheet 04, 05, 06) are
  held mostly by their label's angle, not by measurement. Their outlines
  will pin them properly in Checkpoint 2, when cameras are refined against
  every outline at once.
- **Scale is assumed** (a dwarf-rabbit size), not measured. Proportions
  are what matter; absolute size can be set any time.
- **Ear tips move** between photos, so they're trusted less than skull
  points (eyes, nose, mouth).
- The **edited back** solves as slightly from his right (about 23° off
  straight-behind). That may be real or may be the edit; Checkpoint 2's
  outline fit will tell.

## Observations for Prince's person

- Sheet panels **02 ("Front 1/4 Right") and 08 ("Front 1/4 Left") both show
  his left side**. No problem: his right three-quarter comes from mirroring.
- The sheet's **top-down oval is consistent** with its front and side views
  once perspective is accounted for — an angle effect, as you said.
