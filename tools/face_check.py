"""Face check after every sculpt step: eyes, the ridge between them and the
muzzle, from three directions at once, each next to the photo from the same
camera.

  master (front)         full resolution
  sheet 02 three-quarter his left side, from the full-size original
  sheet 03 right profile from the full-size original

The sheet cameras were solved on the small sheet panels; a panel is the
original scaled by 0.222 and shifted 7 px, so rendering the panel camera
at 1/0.222 lines up with the original.

usage: face_check.py SCULPT_DIR OUT.png [--samples N]
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import render_clay as RC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PANEL_SCALE, PANEL_DX = 0.222, 7
VIEWS = {
    "master_front_standing": {"photo": "references/master/master_front_standing.webp", "scale": 1.0, "dx": 0},
    "sheet_02_front_3q": {"photo": "references/sheet_originals/02_front_3q.webp", "scale": 1 / PANEL_SCALE,
                          "dx": PANEL_DX / PANEL_SCALE},
    "sheet_03_right_profile": {"photo": "references/sheet_originals/03_right_profile.webp",
                               "scale": 1 / PANEL_SCALE, "dx": PANEL_DX / PANEL_SCALE},
}
HALF = 0.045  # half-size of the face crop, metres around the face centre


def project(v, scale, X):
    Rm = R.from_rotvec(v["rotvec_world_to_cam"]).as_matrix()
    Xc = (np.asarray(X) - np.asarray(v["camera_position_m"])) @ Rm.T
    f = v["focal_px"] * scale
    w, h = np.array(v["size"]) * scale
    return np.array([f * Xc[0] / Xc[2] + w / 2, f * Xc[1] / Xc[2] + h / 2]), f / Xc[2]


def render(sc, cam, v, scale, out):
    size = np.array(v["size"]) * scale
    RC.set_camera(sc, cam, size, v["rotvec_world_to_cam"], v["camera_position_m"], v["focal_px"] * scale)
    sc.render.filepath = str(out)
    bpy.ops.render.render(write_still=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sculpt_dir")
    ap.add_argument("out")
    ap.add_argument("--samples", type=int, default=12)
    ap.add_argument("--views", nargs="*", default=list(VIEWS),
                    help="camera names; any sheet_NN_* view uses its full-size original")
    ap.add_argument("--half", type=float, default=HALF, help="half-size of the crop, metres")
    a = ap.parse_args()
    originals = {p.stem[:2]: p for p in (ROOT / "references/sheet_originals").glob("*.webp")}
    d = Path(a.sculpt_dir)
    cams = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]
    # side cameras refined against the sculpt at full resolution, if present
    sp = ROOT / "checkpoints/cp3/side_cameras.json"
    if sp.exists():
        for vn, sv in json.loads(sp.read_text())["views"].items():
            if vn in cams:
                cams[vn] = dict(cams[vn], rotvec_world_to_cam=sv["rotvec_world_to_cam"],
                                camera_position_m=sv["camera_position_m"], focal_px=sv["focal_px"] * PANEL_SCALE)
    dj = json.loads((ROOT / "checkpoints/cp3/face_depth.json").read_text())
    centre = (np.array(dj["eye_R_m"]) + np.array(dj["eye_L_m"])) / 2 * 0.5 + np.array(dj["nose_tip_m"]) * 0.5

    sc = RC.reset()
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    RC.load_mesh(d / "head.obj")
    for e in sorted(d.glob("eye_*.obj")):
        RC.load_mesh(e, colour=(0.015, 0.012, 0.012), roughness=0.08, name="eye")
    RC.lights(sc)
    sc.view_settings.exposure = -0.8
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "AREA"))
    fill.data.energy, fill.data.size = 1.8, 0.6
    sc.collection.objects.link(fill)

    tiles = []
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    for vn in a.views:
        spec = VIEWS.get(vn) or {"photo": str(originals[vn[6:8]].relative_to(ROOT)), "scale": 1 / PANEL_SCALE,
                                 "dx": PANEL_DX / PANEL_SCALE}
        v = cams[vn]
        cpos = np.array(v["camera_position_m"])
        fill.location = tuple(cpos + np.array([0, 0, 0.12]))
        fill.rotation_euler = Vector(np.array([0, 0, 0.08]) - cpos - np.array([0, 0, 0.12])).to_track_quat(
            "-Z", "Y").to_euler()
        tmp = Path(a.out).with_name(f"_{vn}.png")
        render(sc, cam, v, spec["scale"], tmp)
        rgba = np.asarray(Image.open(tmp).convert("RGBA")).astype(np.float32)
        al = rgba[..., 3:4] / 255
        clay = (rgba[..., :3] * al + 228 * (1 - al)).astype(np.uint8)
        photo = np.asarray(Image.open(ROOT / spec["photo"]).convert("RGB"))
        uv, ppm = project(v, spec["scale"], centre)
        r = a.half * ppm
        x0, y0, x1, y1 = (int(uv[0] - r), int(uv[1] - r), int(uv[0] + r), int(uv[1] + r))

        def crop(img, dx=0):
            pil = Image.fromarray(img)
            return pil.crop((x0 + dx, y0, x1 + dx, y1)).resize((520, 520), Image.LANCZOS)

        ph = crop(photo, int(round(spec["dx"])))
        cl = crop(clay)
        t = Image.new("RGB", (1040, 560), (252, 252, 251))
        t.paste(ph, (0, 0))
        t.paste(cl, (520, 0))
        ImageDraw.Draw(t).text((8, 526), f"{vn.replace('_', ' ')}: photo | sculpt", fill=(11, 11, 11), font=font)
        tiles.append(t)
    sheet = Image.new("RGB", (1040, 560 * len(tiles)), (252, 252, 251))
    for i, t in enumerate(tiles):
        sheet.paste(t, (0, 560 * i))
    sheet.save(a.out)


if __name__ == "__main__":
    main()
