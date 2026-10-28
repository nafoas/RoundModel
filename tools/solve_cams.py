"""Solve the camera of photos without one (docs/MEASURING.md step A).

For each photo: where the camera was, which way it pointed, and its lens,
relative to the model, from his landmarks (checkpoints/cp4/cams/
landmarks2d.json, against checkpoints/cp4/landmarks3d.json) and his outline
where it is not cut off by the photo's edge (checkpoints/cp4/outlines/
<name>.png). The outline term is robust (large misses, such as the ears,
which move between photos, count less). Several starting directions around
the photo's rough one; the best kept.

writes checkpoints/cp4/cams/<name>.json and a check image (photo with the
model's outline and landmarks drawn on it).

usage: python tools/solve_cams.py MODEL_DIR NAME [NAME ...]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as nd
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from refine_side_cameras import load_obj  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CAMS = ROOT / "checkpoints/cp4/cams"
# rough direction to start from: azimuth (deg, toward his right), elevation, distance (m)
ROUGH = {"c06": (0, 0, 0.30), "c25": (0, 0, 0.30), "c19": (35, 5, 0.25), "c20": (-35, 5, 0.25),
         "c21": (88, 5, 0.25), "c02": (-88, 5, 0.25)}
FACE = np.array([0.0, 0.07, 0.11])


def look(az, el, dist, target):
    a, e = np.radians(az), np.radians(el)
    dv = np.array([np.sin(a) * np.cos(e), np.cos(a) * np.cos(e), np.sin(e)])
    pos = target + dist * dv
    fwd = -dv
    right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    return R.from_matrix(np.stack([right, down, fwd])).as_rotvec(), pos


def project(P, rv, pos, f, pp):
    Xc = (P - pos) @ R.from_rotvec(rv).as_matrix().T
    return f * Xc[:, :2] / Xc[:, 2:3] + pp, Xc[:, 2]


def main():
    md = Path(sys.argv[1])
    V, F = load_obj(md / "head.obj")
    L3 = json.loads((ROOT / "checkpoints/cp4/landmarks3d.json").read_text())
    L2all = json.loads((CAMS / "landmarks2d.json").read_text())
    k = 0.25
    for name in sys.argv[2:]:
        L2 = L2all[name]
        photo = np.asarray(Image.open(ROOT / L2["photo"]).convert("RGB"))
        H, W = photo.shape[:2]
        pp = np.array([W / 2, H / 2])
        mask = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{name}.png")) > 127
        sm = cv2.resize(mask.astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA) > 0
        edge = sm & ~nd.binary_erosion(sm)
        b = 3
        edge[:b], edge[-b:], edge[:, :b], edge[:, -b:] = False, False, False, False
        dist_photo = nd.distance_transform_edt(~edge)
        bp = np.argwhere(edge)[:, ::-1].astype(float)
        keys = [kk for kk in L2 if kk in L3]
        P3 = np.array([L3[kk] for kk in keys])
        p2 = np.array([L2[kk] for kk in keys], float)

        def cost(x, detail=False):
            rv, pos, f = x[:3], x[3:6], np.exp(x[6])
            uv, z = project(V, rv, pos, f * k, pp * k)
            if (z <= 0.01).any():
                return 1e9
            M = np.zeros(sm.shape, np.uint8)
            tri = np.round(uv[F] * 4).astype(np.int32)
            cv2.fillPoly(M, list(tri), 1, shift=2)
            M = cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8)).astype(bool)
            me = M & ~nd.binary_erosion(M)
            me[:b], me[-b:], me[:, :b], me[:, -b:] = False, False, False, False
            dm = nd.distance_transform_edt(~me)
            d1 = dm[bp[:, 1].astype(int), bp[:, 0].astype(int)] / k
            mp = np.argwhere(me)
            d2 = dist_photo[mp[:, 0], mp[:, 1]] / k if len(mp) else np.array([1e3])
            hub = lambda d, c=25.0: np.where(d < c, 0.5 * d * d, c * (d - 0.5 * c))
            sil = (hub(d1).mean() + hub(d2).mean()) / 2
            lu, _ = project(P3, rv, pos, f, pp)
            lm = ((lu - p2) ** 2).sum(1).mean() if len(keys) else 0
            fprior = 50 * (x[6] - np.log(2000)) ** 2
            if detail:
                return sil, np.sqrt(((lu - p2) ** 2).sum(1)), f
            return sil + 2.0 * lm + fprior

        best = None
        az0, el0, d0 = ROUGH[name]
        for daz in (-8, 8):
            for dd in (1.0,):
                rv, pos = look(az0 + daz, el0, d0 * dd, FACE)
                x0 = np.r_[rv, pos, np.log(2000)]
                r = minimize(cost, x0, method="Powell", options={"maxiter": 2500, "xtol": 1e-3, "ftol": 1e-3})
                if best is None or r.fun < best.fun:
                    best = r
        x = best.x
        sil, lerr, f = cost(x, True)
        rv, pos = x[:3], x[3:6]
        out = {"photo": L2["photo"], "size": [W, H], "rotvec_world_to_cam": rv.tolist(),
               "camera_position_m": pos.tolist(), "focal_px": float(f), "principal_px": pp.tolist(),
               "landmark_error_px": dict(zip(keys, np.round(lerr, 1).tolist())),
               "outline_cost": float(sil), "relative_to": "the model at rest (head and body together)"}
        (CAMS / f"{name}.json").write_text(json.dumps(out, indent=1))
        # check image
        uv, _ = project(V, rv, pos, f, pp)
        M = np.zeros((H, W), np.uint8)
        cv2.fillPoly(M, list(np.round(uv[F] * 4).astype(np.int32)), 1, shift=2)
        M = cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)
        img = photo.copy()
        img[M & ~nd.binary_erosion(M, iterations=3)] = (255, 0, 0)
        img[mask & ~nd.binary_erosion(mask, iterations=3)] = (0, 255, 0)
        lu, _ = project(P3, rv, pos, f, pp)
        for (u, v), (a, c) in zip(lu, p2):
            cv2.circle(img, (int(u), int(v)), 14, (255, 0, 255), 4)
            cv2.circle(img, (int(a), int(c)), 6, (0, 255, 0), -1)
        Image.fromarray(img).resize((W * 600 // H, 600)).save(CAMS / f"{name}_check.jpg", quality=85)
        print(name, "f", round(f), "dist", round(float(np.linalg.norm(pos - FACE)), 3),
              "landmark err px", dict(zip(keys, np.round(lerr, 1).tolist())), "outline", round(float(sil), 1), flush=True)


if __name__ == "__main__":
    main()
