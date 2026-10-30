"""His head turn in each photo, against the new front (tasks/03 step 2).

Cameras are kept; only how his head is turned in that photo (turn, nod, a
little tilt) is re-fitted so the front's eyes, nose and mouth split
(checkpoints/cp6/landmarks3d.json) land on his marked ones. Photos with
fewer than two face points keep their earlier head pose. The extra turn is
stored on top of the earlier pose: checkpoints/cp6/head_poses/<view>.json.

usage: python tools/front_head_turns.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from fill_from_photos import VIEWS, unpose  # noqa: E402
from maps_model import camera, posed  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FACE = ("eye_R", "eye_L", "nose_tip", "mouth_split")
# his marks on the sheet originals (placed by eye on gridded images, full-resolution px)
SHEET_MARKS = {
    "sheet_03_right_profile": {"eye_R": [806, 457], "nose_tip": [1005, 608]},
    "sheet_07_left_profile": {"eye_L": [365, 409], "nose_tip": [194, 525]},
    "sheet_02_front_3q": {"eye_R": [263, 419], "eye_L": [610, 397], "nose_tip": [383, 660], "mouth_split": [395, 745]},
    "sheet_08_front_3q_left": {"eye_R": [273, 426], "eye_L": [585, 419], "nose_tip": [379, 646], "mouth_split": [390, 724]},
    "sheet_09_top_down": {"eye_R": [351, 997], "eye_L": [673, 1007], "nose_tip": [509, 1216]},
    "sheet_04_back_3q_right": {"eye_R": [789, 362]},
}


def main():
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    L3 = json.loads((ROOT / "checkpoints/cp6/landmarks3d.json").read_text())
    L2 = json.loads((ROOT / "checkpoints/cp4/cams/landmarks2d.json").read_text())
    _, _, mpose = camera("master_front_standing")
    out = ROOT / "checkpoints/cp6/head_poses"
    out.mkdir(parents=True, exist_ok=True)
    marks_all = dict(SHEET_MARKS)
    for v in VIEWS:
        if v in L2:
            marks_all[v] = {k: L2[v][k] for k in FACE if k in L2[v]}
    for v in VIEWS:
        marks = {k: p for k, p in marks_all.get(v, {}).items() if k in FACE}
        proj, _, pose = camera(v)
        pose = pose or {"rotvec": [0, 0, 0], "shift_m": [0, 0, 0]}
        if len(marks) < 2:
            print(f"{v}: {len(marks)} face point(s), head pose kept")
            continue
        P = unpose(np.array([L3[k] for k in marks]), mpose)
        want = np.array(list(marks.values()), float)

        def pz(x):
            p = dict(pose)
            p["rotvec"] = (R.from_rotvec(np.asarray(pose["rotvec"])) * R.from_euler("zxy", x, degrees=True)).as_rotvec().tolist()
            return p

        def err(x):
            uv, _ = proj(posed(P, pz(x)))
            return uv - want
        r = minimize(lambda x: (err(x) ** 2).sum() + 2.0 * x[2] ** 2 + 0.05 * (x[:2] ** 2).sum(), [0, 0, 0], method="Powell")
        e0, e1 = np.linalg.norm(err([0, 0, 0]), axis=1), np.linalg.norm(err(r.x), axis=1)
        p = pz(r.x)
        p["extra_turn_nod_tilt_deg"] = np.round(r.x, 1).tolist()
        p["note"] = "head pose re-fitted against the new front (tools/front_head_turns.py)"
        (out / f"{v}.json").write_text(json.dumps(p, indent=1))
        print(f"{v}: face points off {e0.round().astype(int).tolist()} -> {e1.round().astype(int).tolist()} px; "
              f"extra turn/nod/tilt {np.round(r.x, 1).tolist()} deg")


if __name__ == "__main__":
    main()
