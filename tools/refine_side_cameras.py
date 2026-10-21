"""Refine the cameras of the full-size sheet originals against the current
sculpt, so side and three-quarter comparisons are made from the right place.

Each camera starts from the Checkpoint 2 sheet-panel camera (scaled up to the
original) and is nudged (turn, position, zoom) until the sculpt's silhouette
matches his outline in the photo. The top of the head (ears) is left out.
Output: checkpoints/cp3/side_cameras.json, in the same format as
cameras_fit.json but for the originals' full resolution.

usage: refine_side_cameras.py SCULPT_DIR
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[1]
S, DX = 1 / 0.222, 7 / 0.222
VIEWS = {"sheet_02_front_3q": "02_front_3q", "sheet_03_right_profile": "03_right_profile",
         "sheet_07_left_profile": "07_left_profile", "sheet_08_front_3q_left": "08_front_3q_left"}


def load_obj(p):
    V, F = [], []
    for line in open(p):
        if line.startswith("v "):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith("f "):
            F.append([int(x.split("/")[0]) - 1 for x in line.split()[1:4]])
    return np.array(V), np.array(F)


def main(d):
    V, F = load_obj(Path(d) / "head.obj")
    cams = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]
    out = {}
    for vn, orig in VIEWS.items():
        v = cams[vn]
        m = np.asarray(Image.open(ROOT / f"work/orig/{orig}.mask.png")) > 0
        m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 4) > 0.5  # fur envelope
        h, w = m.shape
        ys = np.nonzero(m.any(1))[0]
        keep = np.ones_like(m)
        keep[: ys.min() + int(0.18 * (ys.max() - ys.min()))] = False  # ears
        R0 = R.from_rotvec(v["rotvec_world_to_cam"])
        c0 = np.array(v["camera_position_m"])
        f0 = v["focal_px"] * S
        cx0, cy0 = v["size"][0] * S / 2 + DX, v["size"][1] * S / 2

        def params(q):
            Rm = (R.from_rotvec(q[:3] * 0.05) * R0).as_matrix()
            return Rm, c0 + q[3:6] * 0.02, f0 * np.exp(q[6] * 0.05)

        def sil(q):
            Rm, c, f = params(q)
            Xc = (V - c) @ Rm.T
            P = np.stack([f * Xc[:, 0] / Xc[:, 2] + cx0, f * Xc[:, 1] / Xc[:, 2] + cy0], 1)
            # front-facing triangles only (fillPoly treats overlaps even-odd,
            # punching holes where front and back surfaces overlap), then
            # close pinholes and fill any enclosed gaps
            fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
            front = np.einsum("ij,ij->i", fn, c - V[F[:, 0]]) > 0
            sel = np.round(P[F[front]]).astype(np.int32)
            img = np.zeros((h, w), np.uint8)
            cv2.fillPoly(img, list(sel), 1)
            img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            ff = img.copy()
            cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
            return (img | (1 - ff)) > 0

        def cost(q):
            s = sil(q)
            return 1 - (s & m & keep).sum() / max(1, ((s | m) & keep).sum()) + 0.002 * np.sum(q ** 2)

        q0 = np.zeros(7)
        before = 1 - cost(q0)
        r = minimize(cost, q0, method="Powell", options={"maxfev": 2500, "xtol": 1e-3, "ftol": 1e-5})
        Rm, c, f = params(r.x)
        print(f"{vn:26s} silhouette agreement {before * 100:.1f}% -> {(1 - r.fun) * 100:.1f}%", flush=True)
        out[vn] = {"image": f"references/sheet_originals/{orig}.webp", "size": [w, h],
                   "rotvec_world_to_cam": R.from_matrix(Rm).as_rotvec().tolist(),
                   "camera_position_m": c.tolist(), "focal_px": float(f),
                   "principal_px": [float(cx0), float(cy0)], "agreement": float(1 - r.fun)}
    (ROOT / "checkpoints/cp3/side_cameras.json").write_text(json.dumps({"views": out}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
