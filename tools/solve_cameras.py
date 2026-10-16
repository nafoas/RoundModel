"""Solve each reference view's camera from the hand-placed landmarks.

Joint solve (a small bundle adjustment): Prince's landmark positions in 3D
are shared by every view, and each view gets its own camera position,
orientation and focal length. Reprojection errors are weighted by tier so
the master dominates where views disagree (the deferential rule).

World frame (metres, assumed real-world scale for a dwarf rabbit):
  origin on the ground under his body centre
  +x = Prince's right, +y = forward (toward his nose), +z = up
  (right-handed: facing +y with +z up, +x is on his right)
Azimuth is measured from straight in front, positive toward his LEFT side.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[1]

TIER_WEIGHT = {"master": 10.0, "edited": 3.0, "sheet": 1.0}

# Initial 3D guesses, from the sheet's proportions (length:width:height about
# 1.35 : 1 : 1.1) at an assumed body width of 14 cm.
INIT_POINTS = {
    "eye_R": (0.045, 0.055, 0.115), "eye_L": (-0.045, 0.055, 0.115),
    "nose_tip": (0.0, 0.090, 0.085), "mouth_split": (0.0, 0.088, 0.072),
    "ear_tip_R": (0.030, 0.015, 0.170), "ear_tip_L": (-0.030, 0.015, 0.170),
    "peet_FR": (0.035, 0.055, 0.0), "peet_FL": (-0.035, 0.055, 0.0),
    "peet_BR": (0.040, -0.050, 0.0), "peet_BL": (-0.040, -0.050, 0.0),
    "tail": (0.0, -0.095, 0.030),
}
PAIRS = [("eye_R", "eye_L"), ("ear_tip_R", "ear_tip_L"),
         ("peet_FR", "peet_FL"), ("peet_BR", "peet_BL")]
MIDLINE = ["nose_tip", "mouth_split", "tail"]
GROUND = ["peet_FR", "peet_FL", "peet_BR", "peet_BL"]
# landmarks that move with pose (ears, peets) trust less than skull points
POINT_WEIGHT = {"ear_tip_R": 0.5, "ear_tip_L": 0.5, "peet_FR": 0.7, "peet_FL": 0.7,
                "peet_BR": 0.7, "peet_BL": 0.7, "tail": 0.7}
TARGET = np.array([0.0, 0.0, 0.08])  # roughly his centre, for initial aim
DIST0 = 0.40


def look_at(cam, target, up):
    f = target - cam
    f /= np.linalg.norm(f)
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    d = np.cross(f, r)  # image down
    # rows: camera x (right), y (down), z (forward)
    return np.stack([r, d, f])


def view_dir(az, el):
    # unit vector from Prince toward the camera; az positive toward his left (-x)
    return np.array([-np.sin(az) * np.cos(el), np.cos(az) * np.cos(el), np.sin(el)])


def init_camera(v, size):
    az, el = np.radians(v["init"]["az"]), np.radians(v["init"]["el"])
    dirn = view_dir(az, el)
    cam = TARGET + DIST0 * dirn
    up = np.array([0, 0, 1.0])
    if v["init"].get("image_up") == "tail":
        up = np.array([0, -1.0, 0])
    elif v["init"].get("image_up") == "nose":
        up = np.array([0, 1.0, 0])
    Rm = look_at(cam, TARGET, up)
    f = size[1] / 2 / np.tan(np.radians(35) / 2)
    return R.from_matrix(Rm).as_rotvec(), cam, np.log(f)


def project(rotvec, cam, logf, size, X):
    Rm = R.from_rotvec(rotvec).as_matrix()
    Xc = (X - cam) @ Rm.T
    f = np.exp(logf)
    u = f * Xc[:, 0] / Xc[:, 2] + size[0] / 2
    v = f * Xc[:, 1] / Xc[:, 2] + size[1] / 2
    return np.stack([u, v], 1), Xc[:, 2]


def solve(data):
    views = data["views"]
    names = list(INIT_POINTS)
    vnames = list(views)
    sizes = {}
    for vn in vnames:
        with Image.open(ROOT / views[vn]["image"]) as im:
            sizes[vn] = np.array(im.size, float)

    x0 = [np.array([INIT_POINTS[n] for n in names]).ravel()]
    for vn in vnames:
        rv, c, lf = init_camera(views[vn], sizes[vn])
        x0.append(np.concatenate([rv, c, [lf]]))
    x0 = np.concatenate(x0)
    npt = len(names) * 3

    def unpack(x):
        P = x[:npt].reshape(-1, 3)
        cams = {vn: x[npt + 7 * i: npt + 7 * i + 7] for i, vn in enumerate(vnames)}
        return P, cams

    idx = {n: i for i, n in enumerate(names)}
    P0 = x0[:npt].reshape(-1, 3)

    gauge_w = 200.0  # stage 1: landmarks held at the initial guess, cameras solve

    def residuals(x):
        P, cams = unpack(x)
        res = []
        for vn in vnames:
            v = views[vn]
            c = cams[vn]
            pts = v["points"]
            X = np.array([P[idx[n]] for n in pts])
            uv, z = project(c[:3], c[3:6], c[6], sizes[vn], X)
            obs = np.array(list(pts.values()), float)
            norm = sizes[vn].max()
            w = TIER_WEIGHT[v["tier"]]
            pw = np.array([POINT_WEIGHT.get(n, 1.0) for n in pts])[:, None]
            res.append((w * pw * (uv - obs) / norm * 100).ravel())  # in % of image
            res.append(10 * np.minimum(z - 0.05, 0))  # stay in front of camera
            # weak prior: camera distance near DIST0 (focal and distance trade off)
            res.append([0.3 * np.log(np.linalg.norm(c[3:6] - TARGET) / DIST0)])
            # the sheet labels / my reading of each view give its rough angle;
            # hold the camera direction loosely to it (about 25 degrees)
            d0 = view_dir(np.radians(v["init"]["az"]), np.radians(v["init"]["el"]))
            d = (c[3:6] - TARGET) / np.linalg.norm(c[3:6] - TARGET)
            res.append(2.3 * (d - d0))
            # lens prior: an ordinary phone-camera view (~35 deg vertical FOV
            # for the crop); without it lens and distance trade off freely
            f_prior = sizes[vn][1] / 2 / np.tan(np.radians(35) / 2)
            res.append([1.5 * (c[6] - np.log(f_prior))])
        # bilateral symmetry
        for a, b in PAIRS:
            pa, pb = P[idx[a]], P[idx[b]]
            res.append(20 * np.array([pa[0] + pb[0], pa[1] - pb[1], pa[2] - pb[2]]))
        for n in MIDLINE:
            res.append([20 * P[idx[n]][0]])
        for n in GROUND:
            res.append([20 * P[idx[n]][2]])
        # gauge: keep scale and placement near the initial guess (weak)
        res.append(gauge_w * (P - P0).ravel())
        return np.concatenate([np.atleast_1d(r) for r in res])

    sol = least_squares(residuals, x0, loss="soft_l1", f_scale=1.0, max_nfev=300, x_scale="jac")
    # stage 2: let the landmarks move too, still loosely tied to plausible
    # positions so scale and placement stay fixed
    gauge_w = 15.0
    sol = least_squares(residuals, sol.x, loss="soft_l1", f_scale=1.0, max_nfev=300, x_scale="jac")
    P, cams = unpack(sol.x)

    out = {"points_3d": {n: P[idx[n]].round(5).tolist() for n in names}, "views": {}}
    for vn in vnames:
        v = views[vn]
        c = cams[vn]
        pts = v["points"]
        X = np.array([P[idx[n]] for n in pts])
        uv, _ = project(c[:3], c[3:6], c[6], sizes[vn], X)
        obs = np.array(list(pts.values()), float)
        err = np.linalg.norm(uv - obs, axis=1) / sizes[vn].max() * 100
        cam = c[3:6]
        rel = cam - TARGET
        dist = np.linalg.norm(rel)
        az = np.degrees(np.arctan2(-rel[0], rel[1]))
        el = np.degrees(np.arcsin(rel[2] / dist))
        f = float(np.exp(c[6]))
        out["views"][vn] = {
            "image": v["image"], "tier": v["tier"], "size": sizes[vn].tolist(),
            "rotvec_world_to_cam": c[:3].round(6).tolist(),
            "camera_position_m": cam.round(5).tolist(),
            "focal_px": round(f, 2),
            "vertical_fov_deg": round(float(np.degrees(2 * np.arctan(sizes[vn][1] / 2 / f))), 2),
            "azimuth_deg": round(float(az), 1), "elevation_deg": round(float(el), 1),
            "distance_m": round(float(dist), 3),
            "reprojection_error_pct": {n: round(float(e), 2) for n, e in zip(pts, err)},
            "mean_error_pct": round(float(err.mean()), 2),
        }
    out["_convention"] = ("World: metres, +x Prince's right, +y forward, +z up, origin on ground under body centre. "
                          "Camera: x right, y down, z forward; pixel = f*(x/z, y/z) + image centre. "
                          "rotvec maps world-frame vectors into camera frame. Scale is assumed, not measured.")
    return out


def main():
    data = json.loads((ROOT / "references/landmarks.json").read_text())
    out = solve(data)
    dst = ROOT / "checkpoints/cp1/cameras.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=2))
    for vn, v in out["views"].items():
        print(f"{vn:28s} az {v['azimuth_deg']:7.1f} el {v['elevation_deg']:6.1f} "
              f"d {v['distance_m']:.2f} vfov {v['vertical_fov_deg']:5.1f} err {v['mean_error_pct']:.2f}%")
    for n, p in out["points_3d"].items():
        print(f"  {n:12s} {p}")


if __name__ == "__main__":
    sys.exit(main())
