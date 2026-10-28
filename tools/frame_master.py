"""His own frame from the master (docs/MEASURING.md step B).

In the master he looks straight forward at the camera. So his midline plane
is vertical, faces the master camera (the camera sits on it), and passes
through the middle of his face as the master shows it: the column halfway
between his eyes, which is also halfway between his front peets (his head's
small tilt and shift in the master is his head pose there, not his frame).
Not the plane the carving found for itself (turned 2.4 deg: he came out
angled to his left).

usage: python tools/frame_master.py  -> checkpoints/cp4/frame.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402


def unalign(uv, a):
    """Photo pixel back to the camera's own pixel (undo the per-photo shift, roll, scale)."""
    c, th = np.asarray(a["c"]), np.radians(a["roll_deg"])
    q = (np.asarray(uv, float) - c - np.asarray(a["t"]))
    q[1] /= a.get("sy", 1.0)
    q /= a["s"]
    Rm = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
    return q @ Rm + c  # inverse rotation (row vector times Rm = Rm^T applied)


def main():
    cam, _ = C.view_data("master_front_standing")
    L = json.loads((C.ROOT / "references/landmarks.json").read_text())["views"]["master_front_standing"]["points"]
    eyes = (np.asarray(L["eye_R"]) + np.asarray(L["eye_L"])) / 2
    peets = (np.asarray(L["peet_FR"]) + np.asarray(L["peet_FL"])) / 2
    print("middle column: between eyes x", eyes[0], " between front peets x", peets[0])
    uv = np.array([(eyes[0] + peets[0]) / 2, eyes[1]])
    if cam.get("align"):
        uv = unalign(uv, cam["align"])
    Rc = R.from_rotvec(cam["rot"]).as_matrix()
    d = np.r_[(uv - np.asarray(cam["pp"])) / cam["f"], 1.0] @ Rc  # ray in the world
    h = np.array([d[0], d[1], 0.0])
    h /= np.linalg.norm(h)
    n = np.array([h[1], -h[0], 0.0])  # horizontal, across him
    if n[0] < 0:
        n = -n
    pos = np.asarray(cam["pos"])
    x_m = float(n @ pos / n[0])  # where the plane crosses y = z = 0
    th = float(np.arctan2(n[1], n[0]))
    old = json.loads((C.ROOT / "checkpoints/cp4/midline.json").read_text())
    print(f"his midline from the master: x = {x_m*1000:.1f} mm, turned {np.degrees(th):.2f} deg "
          f"(carving's own: x = {old['x_m']*1000:.1f} mm, turned {np.degrees(old['turn_rad']):.2f} deg)")
    (C.ROOT / "checkpoints/cp4/frame.json").write_text(json.dumps({
        "note": "his midline plane from the master (tools/frame_master.py): vertical, the master camera on it, through the column halfway between his eyes and between his front peets. Same form as midline.json: normal (cos turn, sin turn, 0), through (x_m, 0, 0).",
        "x_m": x_m, "turn_rad": th}, indent=1))


if __name__ == "__main__":
    main()
