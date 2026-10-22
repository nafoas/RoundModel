"""His head pose in one photo, found from parts of his head that stay put,
not from his whole outline: the eyes (fixed in the skull; the visible cap of
the model's eyeball against his traced eye), the nose V where his nose points
forward, and his forehead/muzzle lines where traced (distance from each traced
point to the model's projected edge). The model is not changed; only the
head's turn and shift about the neck are found. Large turns are allowed (he
turns his head a lot, e.g. the left profile looks back over his shoulder).

usage: pose_parts.py SCULPT_DIR VIEW [--yaw=DEG] [--nosave]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from part_score import cameras  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NOSE_FORWARD = {"master_front_standing", "sheet_02_front_3q", "sheet_08_front_3q_left"}


PIVOT = NECK_PIVOT
# he can move his head relative to his body (the cameras were solved from his
# body); --free lets the head shift as freely as it turns
SHIFT_W = 0.0001 if "--free" in sys.argv else 0.002


def main(d, view):
    global PIVOT
    pv = [a for a in sys.argv if a.startswith("--pivot=")]
    if pv:
        PIVOT = np.array([float(v) for v in pv[0][8:].split(",")])
    d = Path(d)
    T = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
    parts = T[view]
    cam = cameras()[view]
    Rc = R.from_rotvec(cam["rotvec"]).as_matrix()
    cpos, f, cc = np.asarray(cam["pos"]), cam["f"], np.asarray(cam["c"])
    V, F = load_obj(d / "head.obj")
    hw = head_weight(V)
    log = json.loads((ROOT / "sculpt/head_log.json").read_text())
    eyes = {}
    sock = [x for x in log["steps"] if x["op"] == "socket"][-1]
    for st in log["steps"]:
        if st["op"] == "eye":
            ax = np.asarray(st["axis"], float)
            ax /= np.linalg.norm(ax)
            if st.get("mirror") is None:
                eyes[st["side"]] = (np.asarray(st["centre"], float), st["radius"], ax)
    # cap of each eyeball inside the lid opening (socket rim)
    caps = {}
    rng = np.random.default_rng(0)
    for s, (c, r, ax) in eyes.items():
        P = rng.normal(size=(3000, 3))
        P /= np.linalg.norm(P, axis=1, keepdims=True)
        cosmax = np.cos(np.arcsin(min(sock["rim"] / r, 0.999)))
        P = P[P @ ax > cosmax * 0.0 + np.sqrt(max(0, 1 - (sock["rim"] / r) ** 2))]
        caps[s] = (c + P * r, P)
    W, H = int(cc[0] * 2 + 1), int(cc[1] * 2 + 1)
    img = cv2.imread(str(ROOT / cam["image"])) if False else None
    from PIL import Image
    W, H = Image.open(ROOT / cam["image"]).size
    ppm = None

    def pose(q):
        return R.from_rotvec(np.radians(q[:3])).as_matrix(), q[3:] / 1000

    def proj(X):
        Xc = (X - cpos) @ Rc.T
        return f * Xc[:, :2] / Xc[:, 2:3] + cc, Xc[:, 2]

    traces = {k: np.array(v, np.int32) for k, v in parts.items() if k.startswith("eye_")}
    tmasks = {}
    for k, poly in traces.items():
        m = np.zeros((H, W), np.uint8)
        cv2.fillPoly(m, [poly], 1)
        tmasks[k] = m
    lines = [np.array(parts[k], float) for k in ("forehead", "muzzle") if k in parts
             and not (k == "muzzle" and view == "sheet_09_top_down")]
    nose = None
    if view in NOSE_FORWARD and view in T["points"]["nose_V"]:
        from sculpt import Master
        nose = (Master().hit(V, F, [545, 745]), np.array(T["points"]["nose_V"][view], float))

    def cost(q, detail=False):
        Rm, t = pose(q)
        Vp = V + hw[:, None] * (((V - PIVOT) @ Rm.T + PIVOT + t) - V)
        z_head = ((np.array([0, 0.06, 0.12]) - cpos) @ Rc.T)[2]
        pmm = f / z_head / 1000  # px per mm
        terms = {}
        # eyes: overlap of the visible cap with the trace
        ious = []
        for k, tm in tmasks.items():
            s = k[-1]
            P, N = caps[s]
            Pp = (P - PIVOT) @ Rm.T + PIVOT + t
            Np = N @ Rm.T
            vis = np.einsum("ij,ij->i", Np, cpos - Pp) > 0
            m = np.zeros((H, W), np.uint8)
            if vis.sum() > 5:
                uv, _ = proj(Pp[vis])
                hull = cv2.convexHull(np.round(uv).astype(np.int32))
                cv2.fillPoly(m, [hull], 1)
            ious.append((m & tm).sum() / max(1, (m | tm).sum()))
        terms["eyes"] = 1 - np.mean(ious) if ious else 0.0
        # nose V (mm)
        if nose is not None:
            X = (nose[0] - PIVOT) @ Rm.T + PIVOT + t
            uv, _ = proj(X[None])
            terms["nose_mm"] = np.linalg.norm(uv[0] - nose[1]) / pmm
        # forehead / muzzle lines: distance to the model's projected edge (mm)
        if lines:
            uv, _ = proj(Vp)
            fn = np.cross(Vp[F[:, 1]] - Vp[F[:, 0]], Vp[F[:, 2]] - Vp[F[:, 0]])
            front = np.einsum("ij,ij->i", fn, cpos - Vp[F[:, 0]]) > 0
            s = np.zeros((H, W), np.uint8)
            cv2.fillPoly(s, list(np.round(uv[F[front]]).astype(np.int32)), 1)
            s = cv2.morphologyEx(s, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            edge = (cv2.dilate(s, np.ones((3, 3), np.uint8)) - s).astype(np.uint8)
            dt = cv2.distanceTransform(1 - edge, cv2.DIST_L2, 3)
            L = np.vstack(lines).astype(int)
            L[:, 0] = np.clip(L[:, 0], 0, W - 1)
            L[:, 1] = np.clip(L[:, 1], 0, H - 1)
            terms["lines_mm"] = float(np.mean(dt[L[:, 1], L[:, 0]])) / pmm
        c = (terms["eyes"] + 0.05 * terms.get("nose_mm", 0) + 0.05 * terms.get("lines_mm", 0)
             + 0.0002 * np.sum(q[:3] ** 2) + SHIFT_W * np.sum(q[3:] ** 2))
        return (c, terms) if detail else c

    starts = [float(a.split("=")[1]) for a in sys.argv if a.startswith("--yaw=")] or [0.0]
    pitches = [float(a.split("=")[1]) for a in sys.argv if a.startswith("--pitch=")] or [0.0]
    best = None
    for y, pt in [(y, pt) for y in starts for pt in pitches]:
        q0 = np.zeros(6)
        q0[2] = y
        q0[0] = pt
        q0[3:] = [float(v) for v in ([a[9:] for a in sys.argv if a.startswith("--shift0=")] or ["0,0,0"])[0].split(",")]
        r = minimize(cost, q0, method="Powell", options={"maxfev": 1200, "xtol": 1e-2, "ftol": 1e-5})
        if best is None or r.fun < best.fun:
            best = r
    c, terms = cost(best.x, True)
    c0, terms0 = cost(np.zeros(6), True)
    print(f"{view}: turn {np.linalg.norm(best.x[:3]):.1f} deg (rotvec deg {np.round(best.x[:3], 1)}), "
          f"shift {np.round(best.x[3:], 1)} mm | eyes overlap {(1 - terms0['eyes']) * 100:.0f}% -> {(1 - terms['eyes']) * 100:.0f}%"
          + (f" | nose {terms0['nose_mm']:.1f} -> {terms['nose_mm']:.1f} mm" if "nose_mm" in terms else "")
          + (f" | lines {terms0['lines_mm']:.1f} -> {terms['lines_mm']:.1f} mm" if "lines_mm" in terms else ""), flush=True)
    if "--nosave" not in sys.argv:
        pd = ROOT / "checkpoints/cp3/head_poses_parts"
        pd.mkdir(exist_ok=True)
        tag = [a[6:] for a in sys.argv if a.startswith("--tag=")]
        (pd / f"{view}{'_' + tag[0] if tag else ''}.json").write_text(json.dumps({"rotvec": np.radians(best.x[:3]).tolist(), "shift_m": (best.x[3:] / 1000).tolist(),
                      "terms": {k: float(v) for k, v in terms.items()}, "pivot": PIVOT.tolist(), "source": "pose_parts.py (eyes, nose V, forehead/muzzle lines)"}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
