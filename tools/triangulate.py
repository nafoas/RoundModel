"""3D positions of the points marked in several photos (part_traces.json
'points'), in the head's own frame: each photo's camera with his head posed
as in that photo (head_poses.json; the master has no pose). Points seen in
one photo only are placed with their left/right mirror partner (x -> -x).
Prints each point, its reprojection error per photo, and how far the
sculpt's surface is from it.
usage: triangulate.py SCULPT_DIR"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from part_score import cameras  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(d):
    T = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
    # head poses found from parts of his head that stay put (pose_parts.py)
    poses = {}
    for f in (ROOT / "checkpoints/cp3/head_poses_parts").glob("sheet_*.json"):
        if f.stem.count("_") >= 3 and f.stem.split("_")[-1] in ("neck", "atlas"):
            continue
        poses[f.stem] = json.loads(f.read_text())
    pv = {v: np.array(p.get("pivot", NECK_PIVOT)) for v, p in poses.items()}
    cams = cameras()

    def proj(view, X):
        if view in poses:
            p = poses[view]
            X = (X - NECK_PIVOT) @ R.from_rotvec(p["rotvec"]).as_matrix().T + NECK_PIVOT + np.array(p["shift_m"])
        c = cams[view]
        Xc = (X - c["pos"]) @ np.asarray(c["R"]).T if "R" in c else None
        return Xc

    from scipy.spatial.transform import Rotation as Rot
    camR = {}
    for v, c in cams.items():
        camR[v] = Rot.from_rotvec(c["rotvec"]).as_matrix()

    def project(view, X):
        if view in poses:
            p = poses[view]
            X = (X - pv[view]) @ Rot.from_rotvec(p["rotvec"]).as_matrix().T + pv[view] + np.array(p["shift_m"])
        c = cams[view]
        Xc = (X - np.asarray(c["pos"])) @ camR[view].T
        return c["f"] * Xc[:2] / Xc[2] + np.asarray(c["c"])

    pts = T["points"]
    groups = []
    done = set()
    for k in pts:
        if k in done:
            continue
        mate = k.replace("_R", "_L") if "_R" in k else k.replace("_L", "_R") if "_L" in k else None
        if mate in pts:
            groups.append((k, mate))
            done |= {k, mate}
        else:
            groups.append((k,))
            done.add(k)
    V, F = load_obj(Path(d) / "head.obj")
    out = {}
    for g in groups:
        obs = []
        for i, k in enumerate(g):
            for v, px in pts[k].items():
                obs.append((v, np.array(px, float), -1.0 if i == 1 else 1.0))
        x0 = np.array([0.025 if len(g) == 2 else 0.0, 0.06, 0.12])

        def res(x):
            r = []
            for v, px, s in obs:
                X = x * np.array([s, 1, 1])
                r.extend(project(v, X) - px)
            return np.array(r)

        sol = least_squares(res, x0)
        x = sol.x
        for i, k in enumerate(g):
            X = x * np.array([-1.0 if i == 1 else 1.0, 1, 1])
            errs = {v: float(np.linalg.norm(project(v, X) - np.array(px))) for v, px in pts[k].items()}
            dist = float(np.min(np.linalg.norm(V - X, axis=1)))
            out[k] = {"xyz_m": X.tolist(), "reproj_px": errs, "sculpt_surface_mm": dist * 1000}
            print(f"{k:13s} at ({X[0]*1000:6.1f},{X[1]*1000:6.1f},{X[2]*1000:6.1f}) mm | reprojection "
                  + ", ".join(f"{v[6:18] if v.startswith('sheet') else 'master'} {e:.1f}px" for v, e in errs.items())
                  + f" | nearest sculpt surface {dist*1000:.1f} mm")
    (ROOT / "checkpoints/cp3/points3d.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
