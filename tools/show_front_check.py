"""Picture of how the new front lines up in other photos (sheet photos only:
the close-up originals are not shared). His front (red, see-through) drawn
into each photo through its camera; his landmarks where they are in the photo
(green) and where the front puts them (red), joined by a yellow line.

usage: python tools/show_front_check.py FRONT_DIR OUT.jpg
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from fill_from_photos import unpose  # noqa: E402
from maps_model import camera, posed  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# photo name: (file, landmarks where they are in the photo)
SHOW = {
    "s01": ("references/sheet_originals/01_front.webp", None),
    "sheet_03_right_profile": ("references/sheet_originals/03_right_profile.webp",
                               {"eye_R": [806, 457], "nose_tip": [1005, 608], "peet_FR": [696, 1072]}),
    "sheet_07_left_profile": ("references/sheet_originals/07_left_profile.webp",
                              {"eye_L": [365, 409], "nose_tip": [194, 525], "peet_FL": [343, 1022]}),
}
NAMES = {"eye_R": "eye", "eye_L": "eye", "nose_tip": "nose", "mouth_split": "mouth", "peet_FR": "peet", "peet_FL": "peet"}


def main():
    fd, outp = Path(sys.argv[1]), sys.argv[2]
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    V, F = load_obj(fd / "head.obj")
    V = V[:: 7]
    L3 = json.loads((ROOT / "checkpoints/cp6/landmarks3d.json").read_text())
    L2 = json.loads((ROOT / "checkpoints/cp4/cams/landmarks2d.json").read_text())
    _, _, mpose = camera("master_front_standing")
    tiles = []
    for view, (photo, marks) in SHOW.items():
        if marks is None:
            marks = {k: L2[view][k] for k in NAMES if k in L2[view]}
        proj, _, pose = camera(view)
        im = Image.open(ROOT / photo).convert("RGB")
        ov = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        uv, _ = proj(posed(unpose(V, mpose), pose))
        for u, v in uv[:: 3]:
            d.point((u, v), fill=(255, 40, 40, 90))
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(im)
        for k, (gx, gy) in marks.items():
            P = unpose(np.array([L3[k]]), mpose)
            (rx, ry), = proj(posed(P, pose))[0]
            d.line([(gx, gy), (rx, ry)], fill=(255, 220, 0), width=6)
            d.ellipse([gx - 14, gy - 14, gx + 14, gy + 14], fill=(0, 220, 0), outline="white", width=3)
            d.ellipse([rx - 14, ry - 14, rx + 14, ry + 14], fill=(230, 0, 0), outline="white", width=3)
            off = np.hypot(rx - gx, ry - gy)
            tx = gx + 18 if gx < im.width - 260 else gx - 250
            d.text((tx, gy - 30), f"{NAMES[k]} {off:.0f}px", fill=(255, 255, 0), stroke_width=3, stroke_fill=(0, 0, 0),
                   font_size=34)
        tiles.append(im)
    T = 700
    for t in tiles:
        t.thumbnail((T, T * 2))
    W = sum(t.width for t in tiles) + 20 * (len(tiles) - 1)
    H = max(t.height for t in tiles) + 120
    sheet = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(sheet)
    x = 0
    for t, title in zip(tiles, ["front (sheet 01)", "right profile (sheet 03)", "left profile (sheet 07)"]):
        sheet.paste(t, (x, 70))
        d.text((x + 6, 8), title, fill=(0, 0, 0), font_size=30)
        x += t.width + 20
    d.text((6, H - 42), "red haze: the new front, seen through each photo's camera.   green: where he is in the photo.   red: where the front puts it.", fill=(0, 0, 0), font_size=26)
    sheet.save(outp, quality=88)


if __name__ == "__main__":
    main()
