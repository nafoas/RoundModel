"""Model outline against his, per photo, through each photo's fitted camera
with his head posed as he holds it there.

Green = his, red = the model, yellow = both. Under each tile: how much of
the model sticks out past him, and how much of him the model is missing, as
a share of his area. A check to look at, not a target.

usage: python tools/silhouette_check.py MODEL_DIR OUT.png
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402

LABELS = {
    "sheet_09_top_down": "top-down", "master_front_standing": "master",
    "sheet_03_right_profile": "right profile", "sheet_04_back_3q_right": "back 3/4 right",
    "sheet_02_front_3q": "front 3/4 right", "sheet_08_front_3q_left": "front 3/4 left",
    "sheet_07_left_profile": "left profile", "sheet_05_back": "back", "sheet_06_back_3q_left": "back 3/4 left",
}


def main():
    d, out = Path(sys.argv[1]), sys.argv[2]
    V, F = load_obj(d / "head.obj")
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    tiles = []
    for name in C.VIEWS:
        cam, H = C.view_data(name)
        uv = C.project(C.posed(V, cam["pose"]), cam)
        M = np.zeros(H.shape, np.uint8)
        cv2.fillPoly(M, list(np.round(uv[F] * 4).astype(np.int32)), 1, shift=2)
        # close the hairline gaps between tiny triangles at full resolution
        M = cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        im = np.zeros(H.shape + (3,), np.uint8)
        im[H & ~M] = (0, 170, 0)
        im[M & ~H] = (210, 0, 0)
        im[M & H] = (215, 190, 0)
        ys, xs = np.nonzero(H | M)
        pad = max(H.shape) // 30
        im = im[max(ys.min() - pad, 0):ys.max() + pad, max(xs.min() - pad, 0):xs.max() + pad]
        t = Image.fromarray(im)
        t.thumbnail((330, 330))
        tile = Image.new("RGB", (340, 390), (0, 0, 0))
        tile.paste(t, ((340 - t.width) // 2, 5))
        g = ImageDraw.Draw(tile)
        over, miss = (M & ~H).sum() / H.sum(), (H & ~M).sum() / H.sum()
        g.text((8, 340), LABELS[name], fill="white", font=font)
        g.text((8, 362), f"model past him {over:.1%}   missing {miss:.1%}", fill=(220, 220, 220), font=font)
        tiles.append(tile)
    n = 5
    o = Image.new("RGB", (n * 345, ((len(tiles) + n - 1) // n) * 395), (0, 0, 0))
    for i, t in enumerate(tiles):
        o.paste(t, ((i % n) * 345, (i // n) * 395))
    o.save(out)


if __name__ == "__main__":
    main()
