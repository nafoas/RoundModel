"""Render the model from a plain direction (no fitted camera), to put beside
photos that have none (close-ups, edited set). Compare by eye; a loose match
of direction is enough.

usage: blender-python look_render.py MODEL_DIR OUT.png AZ EL [--dist 0.32] [--fov 30]
AZ: degrees round from the front toward his right (+x); EL: degrees above.
"""
import argparse
import sys
from pathlib import Path

import bpy
import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import render_clay as RC  # noqa: E402

TARGET = np.array([0.0, 0.04, 0.132])  # middle of his face, just behind the eyes

ap = argparse.ArgumentParser()
ap.add_argument("model")
ap.add_argument("out")
ap.add_argument("az", type=float)
ap.add_argument("el", type=float)
ap.add_argument("--dist", type=float, default=0.36)
ap.add_argument("--fov", type=float, default=30)
ap.add_argument("--size", type=int, default=520)
ap.add_argument("--samples", type=int, default=12)
a = ap.parse_args()

sc = RC.reset()
sc.cycles.samples = a.samples
sc.cycles.use_denoising = True
d = Path(a.model)
RC.load_mesh(d / "head.obj")
for e in sorted(d.glob("eye_*.obj")):
    RC.load_mesh(e, colour=(0.015, 0.012, 0.012), roughness=0.08, name="eye")
RC.lights(sc)
sc.view_settings.exposure = -0.8
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
az, el = np.radians(a.az), np.radians(a.el)
dirv = np.array([np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])
pos = TARGET + a.dist * dirv
fwd = -dirv
right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right)
down = np.cross(fwd, right)
Rwc = np.stack([right, down, fwd])
f_px = a.size / 2 / np.tan(np.radians(a.fov) / 2)
RC.set_camera(sc, cam, (a.size, a.size), R.from_matrix(Rwc).as_rotvec(), pos, f_px)
sc.render.filepath = str(Path(a.out).resolve())
bpy.ops.render.render(write_still=True)
