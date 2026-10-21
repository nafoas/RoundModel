"""Fast look at the current sculpt next to a reference, from that reference's
camera. Meant to be run after every change (seconds, not minutes).

usage: preview.py MESH.obj OUT.png [--view master_front_standing] [--eyes a.obj b.obj]
                  [--crop x0 y0 x1 y1] [--scale 0.5] [--samples 12]

Output: reference crop | grey render crop | both overlaid (render at 50%).
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import render_clay as RC  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("out")
    ap.add_argument("--view", default="master_front_standing")
    ap.add_argument("--cameras", default=str(ROOT / "checkpoints/cp2/cameras_fit.json"))
    ap.add_argument("--eyes", nargs="*", default=[])
    ap.add_argument("--crop", nargs=4, type=int, default=[240, 160, 860, 900])
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--samples", type=int, default=12)
    a = ap.parse_args()

    sc = RC.reset()
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    RC.load_mesh(a.mesh)
    for e in a.eyes:
        RC.load_mesh(e, colour=(0.015, 0.012, 0.012), roughness=0.08, name="eye")
    RC.lights(sc)
    sc.view_settings.exposure = -0.8  # keep the top of his head from blowing out
    # soft fill from beside the camera, like the even light in his photos
    # (a single top light leaves anything facing slightly down in shade)
    v0 = json.loads(Path(a.cameras).read_text())["views"][a.view]
    ld = bpy.data.lights.new("fill", "AREA")
    ld.energy = 1.8
    ld.size = 0.6
    lo = bpy.data.objects.new("fill", ld)
    cpos = np.array(v0["camera_position_m"])
    lo.location = tuple(cpos + np.array([0, 0, 0.12]))
    d = np.array([0, 0, 0.08]) - lo.location
    from mathutils import Vector
    lo.rotation_euler = Vector(d).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(lo)
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    v = json.loads(Path(a.cameras).read_text())["views"][a.view]
    size = np.array(v["size"]) * a.scale
    RC.set_camera(sc, cam, size, v["rotvec_world_to_cam"], v["camera_position_m"], v["focal_px"] * a.scale)
    tmp = Path(a.out).with_suffix(".raw.png")
    sc.render.filepath = str(tmp)
    bpy.ops.render.render(write_still=True)

    rgba = np.asarray(Image.open(tmp).convert("RGBA")).astype(np.float32)
    al = rgba[..., 3:4] / 255
    clay = (rgba[..., :3] * al + 228 * (1 - al)).astype(np.uint8)
    clay = np.asarray(Image.fromarray(clay).resize(tuple(int(s) for s in v["size"]), Image.LANCZOS))
    ref = np.asarray(Image.open(ROOT / v["image"]).convert("RGB"))
    x0, y0, x1, y1 = a.crop
    r, c = ref[y0:y1, x0:x1], clay[y0:y1, x0:x1]
    blend = (r.astype(np.float32) * 0.5 + c.astype(np.float32) * 0.5).astype(np.uint8)
    Image.fromarray(np.concatenate([r, c, blend], 1)).save(a.out)
    tmp.unlink()


if __name__ == "__main__":
    main()
