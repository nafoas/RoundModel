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
# (19 and 20 are near-front shots taken very close: one half of his face each)
ROUGH = {"c06": (0, 0, 0.30), "c25": (0, 0, 0.30), "c19": (12, 5, 0.2), "c20": (-12, 5, 0.2),
         "c21": (88, 5, 0.25), "c02": (-88, 5, 0.25)}
FACE = np.array([0.0, 0.07, 0.11])
# companion shots of the other half of his face: also start from the mirror
# image (across his frame from the master) of the companion's solved camera
COMPANION = {"c19": "c20", "c20": "c19"}


def mirrored_start(other):
    p = CAMS / f"{other}.json"
    if not p.exists():
        return None
    c = json.loads(p.read_text())
    fr = json.loads((ROOT / "checkpoints/cp4/frame.json").read_text())
    n = np.array([np.cos(fr["turn_rad"]), np.sin(fr["turn_rad"]), 0.0])
    o = np.array([fr["x_m"], 0, 0])
    M = np.eye(3) - 2 * np.outer(n, n)
    Rc = R.from_rotvec(c["rotvec_world_to_cam"]).as_matrix()
    fwd, down = M @ Rc[2], M @ Rc[1]
    right = np.cross(down, fwd)
    pos = np.asarray(c["camera_position_m"])
    pos = pos - 2 * ((pos - o) @ n) * n
    return np.r_[R.from_matrix(np.stack([right, down, fwd])).as_rotvec(), pos, np.log(c["focal_px"])]


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


def eye_cap(side):
    """Points on the visible part of his eyeball (inside the lid opening)."""
    E = json.loads((ROOT / "checkpoints/cp4/eyes.json").read_text())[side]
    c, ax, r = np.asarray(E["centre"]), np.asarray(E["axis"]), E["radius"]
    ax = ax / np.linalg.norm(ax)
    psi = np.radians(json.loads((ROOT / "checkpoints/cp4/eyes.json").read_text())["opening_deg"])
    g = np.random.default_rng(0).normal(size=(4000, 3))
    g /= np.linalg.norm(g, axis=1, keepdims=True)
    g = g[g @ ax > np.cos(psi)]
    return c + r * g, g


def eye_box(cap, rv, pos, f, pp):
    """The dark eye's extent in the photo: left, right, top, bottom (px)."""
    P, n = cap
    vis = np.einsum("ij,ij->i", P - pos, n) < 0
    uv, _ = project(P[vis] if vis.any() else P, rv, pos, f, pp)
    return np.array([uv[:, 0].min(), uv[:, 0].max(), uv[:, 1].min(), uv[:, 1].max()])


def head_turn(P, hw, rv):
    """His head turned by rotation vector rv about the neck (weighted as in
    carve.posed: the head turns, the body stays)."""
    if rv is None:
        return P
    from sculpt import NECK_PIVOT
    Pp = (P - NECK_PIVOT) @ R.from_rotvec(rv).as_matrix().T + NECK_PIVOT
    return P + hw[:, None] * (Pp - P)


def main():
    from sculpt import head_weight
    md = Path(sys.argv[1])
    V, F = load_obj(md / "head.obj")
    hwV = head_weight(V)
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
        # eye extents (left, right, top, bottom of the dark eye), where traced
        boxes = [(s, eye_cap(s), np.asarray(L2[f"eye_{s}_box"], float)) for s in "RL" if f"eye_{s}_box" in L2]
        # his head's turn in this photo is solved too where the photo shows his
        # body as well (sheet, edited, wider close-ups): head0_deg given
        free_head = "head0_deg" in L2
        hwP = head_weight(P3) if len(keys) else np.zeros(0)

        def head_of(x):
            return x[7:10] if free_head else None

        def cost(x, detail=False):
            rv, pos, f = x[:3], x[3:6], np.exp(x[6])
            hr = head_of(x)
            uv, z = project(head_turn(V, hwV, hr), rv, pos, f * k, pp * k)
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
            lu, _ = project(head_turn(P3, hwP, hr), rv, pos, f, pp)
            lm = ((lu - p2) ** 2).sum(1).mean() if len(keys) else 0
            bx = [eye_box(cap, rv, pos, f, pp) - want for _, cap, want in boxes]
            if bx:
                lm = lm + 2 * np.mean([(e ** 2).mean() for e in bx])
            fprior = 50 * (x[6] - np.log(2000)) ** 2
            if free_head:  # a weak pull toward his head held straight
                fprior = fprior + 20 * float(hr @ hr)
            if detail:
                return sil, np.r_[np.sqrt(((lu - p2) ** 2).sum(1)), np.abs(np.ravel(bx))], f
            return sil + 2.0 * lm + fprior

        best = None
        az0, el0, d0 = L2.get("rough", ROUGH.get(name))
        starts = [np.r_[look(az0 + daz, el0, d0, FACE)[0], look(az0 + daz, el0, d0, FACE)[1], np.log(2000)]
                  for daz in (-8, 8)]
        if free_head:
            h0 = R.from_euler("zxy", L2["head0_deg"], degrees=True).as_rotvec()
            starts = [np.r_[x0, h0] for x0 in starts]
        ms = mirrored_start(COMPANION[name]) if name in COMPANION else None
        if ms is not None:
            starts.append(ms)
        for x0 in starts:
            if True:
                r = minimize(cost, x0, method="Powell", options={"maxiter": 2500, "xtol": 1e-3, "ftol": 1e-3})
                if best is None or r.fun < best.fun:
                    best = r
        x = best.x
        sil, lerr, f = cost(x, True)
        keys_out = keys + [f"eye_{s}_box_{e}" for s, _, _ in boxes for e in ("left", "right", "top", "bottom")]
        rv, pos = x[:3], x[3:6]
        hr = head_of(x)
        out = {"photo": L2["photo"], "size": [W, H], "rotvec_world_to_cam": rv.tolist(),
               "camera_position_m": pos.tolist(), "focal_px": float(f), "principal_px": pp.tolist(),
               "landmark_error_px": dict(zip(keys_out, np.round(lerr, 1).tolist())),
               "outline_cost": float(sil), "relative_to": "the model at rest (head and body together)"}
        if free_head:
            out["head_pose"] = {"rotvec": hr.tolist(), "shift_m": [0.0, 0.0, 0.0],
                                "yaw_pitch_roll_deg": np.round(R.from_rotvec(hr).as_euler("zxy", degrees=True), 1).tolist()}
        (CAMS / f"{name}.json").write_text(json.dumps(out, indent=1))
        # check image
        uv, _ = project(head_turn(V, hwV, hr), rv, pos, f, pp)
        M = np.zeros((H, W), np.uint8)
        cv2.fillPoly(M, list(np.round(uv[F] * 4).astype(np.int32)), 1, shift=2)
        M = nd.binary_fill_holes(cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
        img = photo.copy()
        img[M & ~nd.binary_erosion(M, iterations=3)] = (255, 0, 0)
        img[mask & ~nd.binary_erosion(mask, iterations=3)] = (0, 255, 0)
        lu, _ = project(head_turn(P3, hwP, hr), rv, pos, f, pp)
        for (u, v), (a, c) in zip(lu, p2):
            cv2.circle(img, (int(u), int(v)), 14, (255, 0, 255), 4)
            cv2.circle(img, (int(a), int(c)), 6, (0, 255, 0), -1)
        for s_, cap, want in boxes:
            l, r_, t, b_ = eye_box(cap, rv, pos, f, pp)
            cv2.rectangle(img, (int(l), int(t)), (int(r_), int(b_)), (255, 0, 255), 3)
            cv2.rectangle(img, (int(want[0]), int(want[2])), (int(want[1]), int(want[3])), (0, 255, 0), 3)
        Image.fromarray(img).resize((W * 600 // H, 600)).save(CAMS / f"{name}_check.jpg", quality=85)
        print(name, "f", round(f), "dist", round(float(np.linalg.norm(pos - FACE)), 3),
              "landmark err px", dict(zip(keys_out, np.round(lerr, 1).tolist())),
              "head", out.get("head_pose", {}).get("yaw_pitch_roll_deg"), "outline", round(float(sil), 1), flush=True)


if __name__ == "__main__":
    main()
