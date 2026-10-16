# Checkpoint 2 — the walls assembled

All the walls from Checkpoint 1 are combined into one volume: Prince's body
shape, grey, no face, no fur, no ears yet.

## What's here

- `prince_cp2.obj` — his body volume (metres; +x his right, +y forward, +z up).
  A closed surface of 10,242 evenly spaced vertices.
- `review/00_master_front_standing.png` — the shape from the master's camera,
  next to the master. Lead image.
- `review/01…12_*.png` and `review/all_views.png` — the same for every wall view.
- `review/turntable.gif`, `review/turntable_sheet.png` — 32 steps around him at
  the master's height and distance.
- `agreement.json` — how well the shape matches each view's outline.
- `cameras_fit.json` — the cameras after refinement (master never moves).
- `volume.npz` — the carved volume used as the starting shape.

In the comparisons: **red line** = the photo's outline, **blue line** = the
shape's outline. Right-hand panel: grey = agree, red = in the photo but not
the shape, blue = in the shape but not the photo.

## Agreement with each view

"Body only" leaves out the area around his ears (see below).

| View | Outline | Body only |
|---|---|---|
| **master front** | 94.0% | **97.2%** |
| sheet 01 front | 94.5% | 97.2% |
| sheet 02 front three-quarter | 91.8% | 93.6% |
| sheet 08 front three-quarter | 90.4% | 92.9% |
| sheet 07 left profile | 89.7% | 91.7% |
| sheet 03 right profile | 91.0% | 93.1% |
| edited back three-quarter (high) | 89.4% | 93.4% |
| sheet 06 back three-quarter left | 92.9% | 96.5% |
| sheet 04 back three-quarter right | 92.6% | 94.3% |
| edited back | 92.7% | 93.9% |
| sheet 05 back | 93.0% | 96.4% |
| sheet 09 top-down | 91.1% | 88.8% |
| sheet 10 bottom-up | 93.5% | 92.5% |

## How it was made

1. **Carving** (`tools/assemble_walls.py`). Each wall is swept through space
   from its camera; space any two sheet views (or one edited view) rule out
   is carved away, and nothing may stick outside the master's outline.
   Cameras were nudged to fit, with zoom locked after the first round so
   the shape can't inflate. Ghost volume behind him that no camera ruled
   out was dropped.
2. **Fitting one smooth surface** (`tools/fit_surface.py`). Carving can only
   remove volume, so every small disagreement between photos became a flat
   cut. Instead, a closed surface is fitted to all outlines at once:
   stay inside every outline, reach every outline, stay round, left and
   right match softly. Weighted by tier, master strongest; the master's
   "stay inside" is close to a hard limit. Cameras are refined with the
   surface (master fixed).

## Disagreements between views, and how they were resolved

- **Ears.** The photos have his ears in different places, and a closed body
  surface can't represent thin flaps anyway (seen only from the front, it
  smeared them into a crest over his head). The body now stops at the
  head; **ears become their own geometry in Checkpoint 3**, shaped from the
  master. That's the red at the top of the master comparison.
- **Real Prince versus edited Prince.** The sheet photos show the real
  bunny; the edited set and master show the intended, rounder Prince. They
  disagree slightly on his back and sides; the edited views and master
  are weighted above the sheet, so the shape follows them.
- **Top-down (sheet 09) is the weakest match (88.8% body).** The sheet's
  top-down Prince is a little longer and wider-hipped than the master's
  proportions allow; resolved toward the master. Also the most
  perspective-distorted photo.
- **Peets.** Small and pose-dependent; the body has only gentle bumps
  there. Peets are shaped with the face/detail stage.
- **Slight left-right difference in the master** (his left side is a touch
  fuller). Kept, because the master wins; symmetry is only a soft pull.

## Known limitations

- Scale is still assumed. The fitted body is about 16 × 21 × 18 cm
  (width × length × height, fur included), which is on the large side
  for a dwarf rabbit; proportions are what matter here.
- Some soft creases remain on his upper back where views met; they are
  shallow and will be refined with the face.
