"""Scale his photos to each other by distance (owner: "you've not properly
scaled the images to each other ... you're just not accounting for distance
of the photos").

Each photo's camera puts him at some distance; an error in that distance
makes him look bigger or smaller in that photo than in the others. Here his
size is measured in every photo in millimetres at that photo's distance
(width across him, length nose to rump, height to the ear tips, whichever
that photo shows side-on), and one scale per photo is solved together with
his true width, length and height (least squares on the logarithms), the
master fixed at 1 (the immutable reference). A photo's scale is applied
about the point where his body centre lands in it, which is the same as
moving that camera nearer or further. What no scale can explain is his
posture in that photo, and is reported, not forced.

writes checkpoints/cp4/view_align.json (used by carve.py, refine_rim.py,
silhouette_check.py).
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402

PC = np.array([0.0, 0.0, 0.07])  # middle of his body
# what each photo shows side-on: image x / image y -> his W (width), L (length), H (height)
SHOWS = {
    "master_front_standing": ("W", "H"),
    "sheet_09_top_down": ("W", "L"),
    "sheet_03_right_profile": ("L", "H"),
    "sheet_07_left_profile": ("L", "H"),
    "sheet_05_back": ("W", "H"),
}


def main():
    C.ALIGN = {}
    rows, rhs, names = [], [], list(SHOWS)
    dims = ["W", "L", "H"]
    meas = {}
    for name, (ax, ay) in SHOWS.items():
        cam, H = C.view_data(name)
        Rc = R.from_rotvec(cam["rot"]).as_matrix()
        Z = ((PC - np.asarray(cam["pos"])) @ Rc.T)[2]
        ys, xs = np.nonzero(H)
        for dim, px in ((ax, xs.max() - xs.min()), (ay, ys.max() - ys.min())):
            mm = px * Z / cam["f"] * 1000
            meas[(name, dim)] = mm
            # log(mm) + log(s_v) = log(true dim)
            r = np.zeros(len(names) + 3)
            r[names.index(name)] = 1
            r[len(names) + dims.index(dim)] = -1
            rows.append(r)
            rhs.append(-np.log(mm))
    # master fixed: s = 1
    r = np.zeros(len(names) + 3)
    r[names.index("master_front_standing")] = 1
    rows.append(r * 100)
    rhs.append(0.0)
    x, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    s = np.exp(x[:len(names)])
    true = dict(zip(dims, np.exp(x[len(names):])))
    print("his size (mm):", {k: round(v, 1) for k, v in true.items()})
    align = {}
    for name, sv in zip(names, s):
        cam, H = C.view_data(name)
        c = C.project(PC[None], cam)[0]
        align[name] = dict(s=float(sv), roll_deg=0.0, t=[0.0, 0.0], c=[float(c[0]), float(c[1])])
        left = {d: round(meas[(name, d)] * sv - true[d], 1) for d in SHOWS[name]}
        print(f"{name:26s} scale {sv:.3f}   left over after scaling (mm, his posture): {left}")
    out = C.ROOT / "checkpoints/cp4/view_align.json"
    out.write_text(json.dumps(align, indent=1))
    print("written", out)


if __name__ == "__main__":
    main()
