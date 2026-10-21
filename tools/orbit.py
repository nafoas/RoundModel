"""Clay renders of the sculpt from chosen directions around the head, for
comparing with close-up photos taken from those directions.
usage: orbit.py SCULPT_DIR OUT.png AZ:EL [AZ:EL ...] [--size 520] [--samples 8]
azimuth in degrees, 0 = straight on his face, + toward his left side,
90 = his left profile, -90 = his right profile; elevation + from above."""
import argparse
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import render_clay as RC  # noqa: E402

TARGET = np.array([0.0, 0.045, 0.115])  # middle of the head


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sculpt_dir")
    ap.add_argument("out")
    ap.add_argument("views", nargs="+")
    ap.add_argument("--size", type=int, default=520)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--dist", type=float, default=0.42)
    ap.add_argument("--lens", type=float, default=85)
    ap.add_argument("--target", nargs=3, type=float, default=None)
    a = ap.parse_args()
    d = Path(a.sculpt_dir)
    global TARGET
    if a.target:
        TARGET = np.array(a.target)
    sc = RC.reset()
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    RC.load_mesh(d / "head.obj")
    for e in sorted(d.glob("eye_*.obj")):
        RC.load_mesh(e, colour=(0.015, 0.012, 0.012), roughness=0.08, name="eye")
    RC.lights(sc)
    sc.view_settings.exposure = -0.8
    sc.render.resolution_x = sc.render.resolution_y = a.size
    cd = bpy.data.cameras.new("cam")
    cd.lens = a.lens
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    fill = bpy.data.objects.new("fill", bpy.data.lights.new("fill", "AREA"))
    fill.data.energy, fill.data.size = 1.8, 0.6
    sc.collection.objects.link(fill)
    tiles = []
    for v in a.views:
        az, el = (np.radians(float(x)) for x in v.split(":"))
        # azimuth + toward his left (-x); forward is +y
        dirn = np.array([-np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])
        pos = TARGET + dirn * a.dist
        cam.location = tuple(pos)
        cam.rotation_euler = Vector(TARGET - pos).to_track_quat("-Z", "Y").to_euler()
        fill.location = tuple(pos + np.array([0, 0, 0.12]))
        fill.rotation_euler = Vector(TARGET - pos - np.array([0, 0, 0.12])).to_track_quat("-Z", "Y").to_euler()
        tmp = Path(a.out).with_name("_orbit.png")
        sc.render.filepath = str(tmp)
        bpy.ops.render.render(write_still=True)
        rgba = np.asarray(Image.open(tmp).convert("RGBA")).astype(np.float32)
        al = rgba[..., 3:4] / 255
        tiles.append((rgba[..., :3] * al + 228 * (1 - al)).astype(np.uint8))
    Image.fromarray(np.concatenate(tiles, 1)).save(a.out)


if __name__ == "__main__":
    main()
