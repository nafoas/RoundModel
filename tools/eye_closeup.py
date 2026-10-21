"""Zoomed eye comparison after a face_check run: the master's two eyes and
the profile eye, photo next to sculpt, same camera, same crop.
usage: eye_closeup.py SCULPT_DIR OUT.png  (run face_check.py first; it leaves
the raw renders _<view>.png next to its output in SCULPT_DIR)"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DX = 7 / 0.222


def clay(p):
    a = np.asarray(Image.open(p).convert("RGBA")).astype(np.float32)
    al = a[..., 3:4] / 255
    return Image.fromarray((a[..., :3] * al + 228 * (1 - al)).astype(np.uint8))


def main(d, out):
    d = Path(d)
    tiles = []
    master = Image.open(ROOT / "references/master/master_front_standing.webp").convert("RGB")
    mrender = clay(d / "_master_front_standing.png")
    for cx, cy in ((338, 467), (699, 442)):
        box = (cx - 60, cy - 70, cx + 60, cy + 70)
        tiles.append((master.crop(box), mrender.crop(box)))
    prof = Image.open(ROOT / "references/sheet_originals/03_right_profile.webp").convert("RGB")
    prender = clay(d / "_sheet_03_right_profile.png")
    cx, cy = 815, 465
    tiles.append((prof.crop((cx - 90, cy - 90, cx + 90, cy + 90)),
                  prender.crop((cx - DX - 90, cy - 90, cx - DX + 90, cy + 90))))
    H = 360
    row = []
    for a, b in tiles:
        for im in (a, b):
            row.append(im.resize((round(im.width * H / im.height), H), Image.LANCZOS))
    W = sum(i.width for i in row) + 8 * len(row)
    o = Image.new("RGB", (W, H), (252, 252, 251))
    x = 0
    for k, im in enumerate(row):
        o.paste(im, (x, 0))
        x += im.width + (24 if k % 2 else 4)
    o.save(out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
