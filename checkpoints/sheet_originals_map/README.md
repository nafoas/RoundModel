# The 18 sheet originals: cameras and what each one shows

Supporting references only; the master stays the immutable reference.
Made by `tools/map_sheet_originals.py`.

- `camera_map.png` — where each photo was taken from, seen from above and
  from his right side, with the master's camera as the blue star.
- `coverage.png` — for each photo, how squarely it sees each part of him
  (0 = not visible, 1 = straight on).
- `contact_sheet.png` — all 18 with the marked landmarks (green circles) and
  where the solved camera puts them (pink crosses), labelled with each angle.
- `cameras.json`, `coverage.json` — the numbers.

## How the cameras were found

- **Face photos (01, 02, 08, 10–18):** solved from landmarks marked on each photo
  (eyes, nostrils, nose tip, mouth split, ear tips), relative to his **head**,
  since he moved his head between shots. Typical fit 8–20 px on 1131×1391 images.
- **Back photos (04, 05, 06):** too few landmarks; the cameras come from the
  Checkpoint 2 silhouette solve of the same photos.
- **Profiles (03, 07) and top-down (09):** angles read from the photo. The
  landmark solve can't reach them (next section).

Azimuth: 0 = straight in front, + = toward his left. Elevation: + = above.
Distances assume a phone lens and his assumed size, so they're approximate.

## Finding: his eyes sit further back than the 3D face says

The profile and top-down photos can't be matched by the current 3D face. In
all three, the distance from ear tip to eye compares with the distance from
eye to nose tip as follows:

| photo | ear tip → eye | eye → nose tip | ratio |
|---|---|---|---|
| 03 right profile | 280 px | 185 px | 1.5 |
| 07 left profile | 280 px | 185 px | 1.5 |
| 09 top-down | 348 px | 222 px | 1.6 |
| current 3D face | 8.4 cm | 2.4 cm | 3.5 |

In the top-down photo his eyes are about 75% of the way from his tail to his
nose; the 3D face puts them at about 89%. So his eyes sit **further back**
along his head (and more on its sides) than the face solve placed them,
roughly 5 cm behind the nose tip rather than 2.4 cm. This agrees with the
correction about his eyes being on the sides of his head. The 3D face came
from the edited head-turn photos, where depth is hard to read; the face
rebuild should use these photos for depth. The master can't show depth, so
this doesn't conflict with it.

## Coverage, in short

- **Nose, mouth, chin, nose bridge:** very well covered (front, 3/4,
  looking up/down).
- **Each eye from its own side:** 03 and 16 (his right), 07 and 15 (his left).
- **Ears:** only the top-down and looking-down photos see them squarely.
- **Sides, back:** profiles and back photos, moderately.
- **Underside and peets:** only the bottom-up photo.

Least covered, so most useful from the close-up photoshoot: **ears**,
**cheeks**, and **each eye up close** (lids and lashes), as he allows.
