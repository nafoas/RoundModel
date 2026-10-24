"""Comparison sheet for the parts model: his photo beside the model, whole
body. Photos with fitted cameras are rendered from that camera (pixel for
pixel); the rest from a plain direction (a loose match, judged by eye).

usage: blender-python tools/parts_sheet.py OUT.png MODEL_DIR [MODEL_DIR ...]
       [--views master,s01,s03,...] [--samples 10]
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import render_clay as RC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BODY = np.array([0.0, 0.0, 0.07])  # middle of him, for plain-direction views

# name: (photo, fitted camera name or None, az, el, dist) -- az from the front
# toward his right, el above
VIEWS = {
    "master": ("references/master/master_front_standing.webp", "master_front_standing", 0, 0, 0),
    "s01": ("references/sheet_originals/01_front.webp", None, 0, 12, 0.6),
    "s02": ("references/sheet_originals/02_front_3q.webp", "sheet_02_front_3q", 0, 0, 0),
    "s03": ("references/sheet_originals/03_right_profile.webp", "sheet_03_right_profile", 0, 0, 0),
    "s04": ("references/sheet_originals/04_back_3q_right.webp", "sheet_04_back_3q_right", 0, 0, 0),
    "s05": ("references/sheet_originals/05_back.webp", None, 180, 12, 0.6),
    "s07": ("references/sheet_originals/07_left_profile.webp", "sheet_07_left_profile", 0, 0, 0),
    "s08": ("references/sheet_originals/08_front_3q_left.webp", "sheet_08_front_3q_left", 0, 0, 0),
    "s09": ("references/sheet_originals/09_top_down.webp", "sheet_09_top_down", 0, 0, 0),
    "c07": ("references/closeups/07-Head-45-Degrees.png", None, 40, 8, 0.55),
    "c08": ("references/closeups/08-Head-Side-Profile.png", None, 90, 6, 0.6),
    "c09": ("references/closeups/09-Head-120-Degrees.png", None, -130, 12, 0.55),
    "c10": ("references/closeups/10-Whole-Facial-Contour-Side-Depth.png", None, 80, 5, 0.45),
    "c06": ("references/closeups/06-Eyes-and-Bridge-Depth.png", None, 0, 2, 0.22, (0.0, 0.05, 0.11)),
    "c25": ("references/closeups/25-Frontal-Bridge-Alternate.png", None, 0, 6, 0.22, (0.0, 0.05, 0.11)),
    "c19": ("references/closeups/19-D4-Approved-Other-Angle.png", None, 28, 4, 0.22, (0.0, 0.05, 0.11)),
    "c20": ("references/closeups/20-Other-Eye-D4-Companion.png", None, -28, 4, 0.22, (0.0, 0.05, 0.11)),
    "c21": ("references/closeups/21-Local-Side-Muzzle-Alternate.png", None, 80, 5, 0.22, (0.0, 0.05, 0.11)),
    "c02": ("references/closeups/02-Eye-Side-On.png", None, -80, 5, 0.22, (0.0, 0.05, 0.11)),
    "c14": ("references/closeups/14-Tiny-Ears-Top.png", None, 180, 45, 0.35),
    "eback": ("references/edited/back.webp", None, 180, 5, 0.6),
    "eloaf": ("references/edited/front_loaf.webp", None, 0, 5, 0.6),
}


def cameras():
    cams = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]
    side = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
    for k, v in side.items():
        cams[k] = dict(v, full=True)
    return cams


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--views", default="master,s01,s02,s03,s04,s05,s07,s08,s09,c07,c08,c09,c10")
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--tile", type=int, default=420)
    a = ap.parse_args(argv)
    cams = cameras()
    views = a.views.split(",")
    tiles = {}
    for d in a.dirs:
        sc = RC.reset()
        sc.cycles.samples = a.samples
        sc.cycles.use_denoising = True
        RC.load_mesh(Path(d) / "head.obj")
        for e in sorted(Path(d).glob("eye_*.obj")):
            RC.load_mesh(e, colour=(0.015, 0.012, 0.012), roughness=0.08, name="eye")
        RC.lights(sc)
        sc.view_settings.exposure = -0.8
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
        for vn in views:
            photo, cn, az, el, dist = VIEWS[vn][:5]
            target = np.asarray(VIEWS[vn][5]) if len(VIEWS[vn]) > 5 else BODY
            W, H = Image.open(ROOT / photo).size
            out = Path(d) / f"ps_{vn}.png"
            if cn:
                v = cams[cn]
                f = v["focal_px"]
                RC.set_camera(sc, cam, (W, H), v["rotvec_world_to_cam"], v["camera_position_m"], f)
                if "principal_px" in v:
                    cam.data.shift_x = (v["principal_px"][0] - W / 2) / max(W, H)
                    cam.data.shift_y = (v["principal_px"][1] - H / 2) / max(W, H)
            else:
                azr, elr = np.radians(az), np.radians(el)
                dirv = np.array([np.sin(azr) * np.cos(elr), np.cos(azr) * np.cos(elr), np.sin(elr)])
                pos = target + dist * dirv
                fwd = -dirv
                right = np.cross(fwd, [0, 0, 1.0])
                right /= np.linalg.norm(right)
                down = np.cross(fwd, right)
                f_px = max(W, H) / 2 / np.tan(np.radians(18))
                RC.set_camera(sc, cam, (W, H), R.from_matrix(np.stack([right, down, fwd])).as_rotvec(), pos, f_px)
            sc.render.filepath = str(out.resolve())
            bpy.ops.render.render(write_still=True)
            cam.data.shift_x = cam.data.shift_y = 0
            tiles.setdefault(vn, []).append(out)
    T = a.tile
    cells = []
    for vn in views:
        ims = [Image.open(ROOT / VIEWS[vn][0]).convert("RGB")]
        for p in tiles[vn]:
            im = Image.open(p).convert("RGBA")
            bg = Image.new("RGBA", im.size, (228, 228, 228, 255))
            bg.alpha_composite(im)
            ims.append(bg.convert("RGB"))
        r = Image.new("RGB", (len(ims) * (T + 4), T), "white")
        for i, im in enumerate(ims):
            im.thumbnail((T, T))
            r.paste(im, (i * (T + 4), 0))
        cells.append(r)
    ncol = 3 if len(a.dirs) == 1 else 2
    nrow = (len(cells) + ncol - 1) // ncol
    cw, ch = cells[0].width + 24, T + 10
    o = Image.new("RGB", (ncol * cw, nrow * ch), "white")
    for i, r in enumerate(cells):
        o.paste(r, ((i % ncol) * cw, (i // ncol) * ch))
    o.save(a.out)


if __name__ == "__main__":
    main()
