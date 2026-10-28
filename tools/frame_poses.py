"""His head poses re-expressed in his frame from the master (step B).

The carving's head at rest sat about 10 mm to his left of his midline (the
master pose then pushed it back to his right): the crookedness the owner
saw. Here his head at rest is moved onto his midline (the frame plane at
eye height) and every photo's head pose is changed so that the head in that
photo stays exactly where it was: shift_new = shift - R_view @ delta (a
photo with no pose gets rotation 0, shift -delta). Written to
checkpoints/cp4/head_poses_frame/ (the old ones stay in cp3).

usage: python tools/frame_poses.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    old = json.loads((ROOT / "checkpoints/cp4/midline.json").read_text())
    fr = json.loads((ROOT / "checkpoints/cp4/frame.json").read_text())
    y = 0.061  # his eyes
    x_old = old["x_m"] - y * np.tan(old["turn_rad"])
    x_new = fr["x_m"] - y * np.tan(fr["turn_rad"])
    delta = np.array([x_new - x_old, 0.0, 0.0])
    print(f"head at rest moved {delta[0]*1000:.1f} mm to his right, onto his midline")
    out = ROOT / "checkpoints/cp4/head_poses_frame"
    out.mkdir(exist_ok=True)
    for name in C.VIEWS:
        p = ROOT / f"checkpoints/cp3/head_poses_parts/{name}.json"
        pose = json.loads(p.read_text()) if p.exists() else {"rotvec": [0.0, 0.0, 0.0], "shift_m": [0.0, 0.0, 0.0]}
        Rv = R.from_rotvec(pose["rotvec"]).as_matrix()
        pose["shift_m"] = (np.asarray(pose["shift_m"]) - Rv @ delta).tolist()
        pose["frame"] = f"re-expressed in his frame from the master (tools/frame_poses.py, head at rest moved {delta[0]*1000:.1f} mm)"
        (out / f"{name}.json").write_text(json.dumps(pose, indent=1))
        print(name, np.round(np.asarray(pose["shift_m"]) * 1000, 1))
    (out / "delta.json").write_text(json.dumps({"delta_m": delta.tolist()}))


if __name__ == "__main__":
    main()
