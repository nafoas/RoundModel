"""Write a copy of a sculpt with the head posed as he holds it in one photo
(head_poses.json, found by head_pose.py), eyes included, for side-by-side
renders from that photo's camera.
usage: pose_copy.py SCULPT_DIR VIEW OUT_DIR"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight, write_obj  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(d, view, out):
    d, out = Path(d), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pp = ROOT / "checkpoints/cp3/head_poses_parts" / f"{view}.json"
    p = json.loads(pp.read_text()) if pp.exists() else json.loads((ROOT / "checkpoints/cp3/head_poses.json").read_text())[view]
    Rm, t = R.from_rotvec(p["rotvec"]).as_matrix(), np.array(p["shift_m"])
    V, F = load_obj(d / "head.obj")
    hw = head_weight(V)
    write_obj(out / "head.obj", V + hw[:, None] * (((V - NECK_PIVOT) @ Rm.T + NECK_PIVOT + t) - V), F)
    for e in list(d.glob("eye_*.obj")) + list(d.glob("ring_*.obj")):
        Ve, Fe = load_obj(e)
        write_obj(out / e.name, (Ve - NECK_PIVOT) @ Rm.T + NECK_PIVOT + t, Fe)


if __name__ == "__main__":
    main(*sys.argv[1:4])
