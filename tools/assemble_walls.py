"""Checkpoint 2: assemble the walls into one volume.

Each wall is Prince's outline from one view, swept through space along that
camera's rays. The volume where the walls agree is space-carved from a voxel
grid. Because the photos were taken at different moments (ears and head
move a little) and the cameras are estimates, a plain intersection would
over-carve, so each voxel is kept by weighted consensus:

  - the master is a hard constraint: nothing may stick outside his outline
    in the master view (deferential rule)
  - every other view can veto: a wall saying "nothing here" is strong
    evidence, but a wall saying "something here" often isn't (a front view
    can't judge depth). A voxel is carved away once the weighted views
    that place it outside their outline reach VETO, so one stray view
    (a moved ear, a turned head) can't carve him on its own

Cameras and volume are refined together: carve, then nudge each non-master
camera so the carved volume's silhouette best matches that view's outline,
then carve again. The master camera never moves.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R
from skimage import measure

ROOT = Path(__file__).resolve().parents[1]
CP1 = ROOT / "checkpoints/cp1"
CP2 = ROOT / "checkpoints/cp2"

WEIGHT = {"master": 0.0, "edited": 1.5, "sheet": 1.0}  # master is hard, not a vote
VETO = 1.5         # weighted "outside" votes needed to carve a voxel
VOXEL = 0.0015     # 1.5 mm
BOUNDS = np.array([[-0.11, 0.11], [-0.13, 0.13], [-0.012, 0.215]])
SMOOTH_VOXELS = 4.0  # 6 mm: where views disagree, Prince is round
SHAPE = None
WORK_H = 360       # silhouette resolution used while refining cameras


def mask_path(vn, image):
    stem = Path(image).stem
    return CP1 / "masks" / (f"sheet_{stem}.outline.png" if vn.startswith("sheet_") else f"{stem}.outline.png")


class View:
    def __init__(self, name, v):
        self.name = name
        self.tier = v["tier"]
        self.size = np.array(v["size"], float)
        self.rotvec = np.array(v["rotvec_world_to_cam"], float)
        self.cam = np.array(v["camera_position_m"], float)
        self.logf = np.log(v["focal_px"])
        self.mask = np.asarray(Image.open(mask_path(name, v["image"]))) > 0
        s = WORK_H / self.size[1]
        self.ws = s
        self.small = cv2.resize(self.mask.astype(np.uint8), (round(self.size[0] * s), WORK_H),
                                interpolation=cv2.INTER_AREA) > 0
        self.raw = dict(v)

    def params(self):
        return np.concatenate([self.rotvec, self.cam, [self.logf]])

    def set_params(self, p):
        self.rotvec, self.cam, self.logf = p[:3], p[3:6], p[6]

    def project(self, X, p=None, scale=1.0):
        rv, cam, lf = (self.rotvec, self.cam, self.logf) if p is None else (p[:3], p[3:6], p[6])
        Xc = (X - cam) @ R.from_rotvec(rv).as_matrix().T
        f = np.exp(lf) * scale
        u = f * Xc[:, 0] / Xc[:, 2] + self.size[0] * scale / 2
        v = f * Xc[:, 1] / Xc[:, 2] + self.size[1] * scale / 2
        return u, v, Xc[:, 2]


def grid():
    global SHAPE
    axes = [np.arange(lo + VOXEL / 2, hi, VOXEL) for lo, hi in BOUNDS]
    shape = tuple(len(a) for a in axes)
    SHAPE = shape
    X = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    return X, shape, axes


def inside(view, X, tol_px=0):
    m = view.mask
    if tol_px:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol_px + 1, 2 * tol_px + 1))
        m = cv2.dilate(m.astype(np.uint8), k) > 0
    u, v, z = view.project(X)
    ui, vi = np.round(u).astype(int), np.round(v).astype(int)
    h, w = m.shape
    inframe = (ui >= 0) & (ui < w) & (vi >= 0) & (vi < h) & (z > 0)
    res = np.zeros(len(X), bool)
    res[inframe] = m[vi[inframe], ui[inframe]]
    return res, inframe


def carve(views, X):
    master = [v for v in views if v.tier == "master"][0]
    keep, _ = inside(master, X, tol_px=1)
    veto = np.zeros(len(X))
    for v in views:
        if v.tier == "master":
            continue
        # each view gets a tolerance of ~1% of its image for camera error
        tol = max(1, round(0.01 * v.size.max()))
        ins, seen = inside(v, X, tol_px=tol)
        veto += WEIGHT[v.tier] * (seen & ~ins)
    return clean(keep & (veto < VETO))


def clean(occ):
    """Keep only Prince: the largest connected piece, with internal voids
    filled. Other pieces are ghost volume no camera happened to rule out."""
    from scipy.ndimage import binary_fill_holes, label
    vol = occ.reshape(SHAPE)
    lab, n = label(vol)
    if n > 1:
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        vol = lab == sizes.argmax()
    return binary_fill_holes(vol).reshape(-1)


def surface(occ, shape):
    vol = occ.reshape(shape)
    er = np.zeros_like(vol)
    er[1:-1, 1:-1, 1:-1] = (vol[1:-1, 1:-1, 1:-1] & vol[2:, 1:-1, 1:-1] & vol[:-2, 1:-1, 1:-1]
                            & vol[1:-1, 2:, 1:-1] & vol[1:-1, :-2, 1:-1]
                            & vol[1:-1, 1:-1, 2:] & vol[1:-1, 1:-1, :-2])
    return (vol & ~er).reshape(-1)


def splat(view, S, p):
    u, v, z = view.project(S, p, scale=view.ws)
    h, w = view.small.shape
    img = np.zeros((h, w), np.uint8)
    ok = (z > 0) & (u >= 0) & (u < w) & (v >= 0) & (v < h)
    img[np.round(v[ok]).astype(int).clip(0, h - 1), np.round(u[ok]).astype(int).clip(0, w - 1)] = 1
    # projected voxel size in work pixels decides the splat radius
    f = np.exp(p[6]) * view.ws
    r = max(1, int(np.ceil(f * VOXEL / np.median(z[ok]) * 0.9)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    img = cv2.dilate(img, k)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, k)
    ff = img.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
    return (img | (1 - ff)) > 0


def iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def refine_camera(view, S, full=False):
    """Nudge one camera so the carved volume's silhouette best matches its
    outline. Only turning and sliding sideways are allowed: zoom and
    distance stay fixed, otherwise every camera can 'zoom out' a little,
    letting more volume survive each round and inflating him."""
    p0 = view.params()
    Rwc = R.from_rotvec(p0[:3]).as_matrix()
    right, down = Rwc[0], Rwc[1]

    fwd = Rwc[2]

    def apply(dp):
        rv = (R.from_rotvec(dp[:3] * 0.02) * R.from_rotvec(p0[:3])).as_rotvec()
        cam = p0[3:6] + right * dp[3] * 0.01 + down * dp[4] * 0.01
        lf = p0[6]
        if full:
            cam = cam + fwd * dp[5] * 0.02
            lf = lf + dp[6] * 0.03
        return np.concatenate([rv, cam, [lf]])

    def cost(dp):
        sil = splat(view, S, apply(dp))
        # stay near the landmark solution (landmarks still matter)
        return (1 - iou(sil, view.small)) + 0.002 * np.sum(dp ** 2)

    r = minimize(cost, np.zeros(7 if full else 5), method="Powell",
                 options={"maxfev": 300, "xtol": 1e-3, "ftol": 1e-4})
    return apply(r.x), 1 - r.fun


def main():
    cams = json.loads((CP1 / "cameras.json").read_text())
    views = [View(n, v) for n, v in cams["views"].items()]
    X, shape, axes = grid()
    print("voxels", len(X), "grid", shape)
    log = []
    for it in range(4):
        occ = carve(views, X)
        S = X[surface(occ, shape)]
        print(f"round {it}: occupied {occ.sum()}  surface {len(S)}")
        if it == 3:
            break
        for v in views:
            if v.tier == "master":
                continue
            before = iou(splat(v, S, v.params()), v.small)
            full = it == 0 and before < 0.85
            target = S
            if full:
                # a badly placed camera is fitted, zoom included, to the
                # volume carved by all the *other* views, so it can't
                # shape the volume to suit itself
                others = [u for u in views if u is not v]
                target = X[surface(carve(others, X), shape)]
            p, after = refine_camera(v, target, full=full)
            v.set_params(p)
            log.append({"round": it, "view": v.name, "full_refit": bool(full),
                        "iou_before": round(before, 4), "iou_after": round(after, 4)})
            print(f"   {v.name:28s} IoU {before:.3f} -> {after:.3f}")

    CP2.mkdir(parents=True, exist_ok=True)
    # Carving from fringed outlines leaves facets and grooves. Smooth the
    # signed distance to the surface (not the occupancy, which would shrink
    # him) and take its zero level.
    from scipy.ndimage import distance_transform_edt, gaussian_filter
    vol = np.pad(occ.reshape(shape), 8)
    sdf = (distance_transform_edt(~vol) - distance_transform_edt(vol)) * VOXEL
    sdf = gaussian_filter(sdf, SMOOTH_VOXELS)
    verts, faces, normals, _ = measure.marching_cubes(sdf, 0.0, spacing=(VOXEL,) * 3)
    verts = verts + (BOUNDS[:, 0] + VOXEL / 2 - 8 * VOXEL)
    np.savez_compressed(CP2 / "volume.npz", occupancy=occ.reshape(shape), voxel=VOXEL,
                        origin=BOUNDS[:, 0] + VOXEL / 2)
    with open(CP2 / "hull.obj", "w") as fh:
        fh.write("# Prince - Checkpoint 2 assembled walls (metres; +x his right, +y forward, +z up)\n")
        for p in verts:
            fh.write(f"v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n")
        for t in faces + 1:
            fh.write(f"f {t[0]} {t[2]} {t[1]}\n")
    out = {"_convention": cams["_convention"], "points_3d": cams["points_3d"], "views": {}}
    for v in views:
        d = dict(v.raw)
        d["rotvec_world_to_cam"] = v.rotvec.round(6).tolist()
        d["camera_position_m"] = v.cam.round(5).tolist()
        d["focal_px"] = round(float(np.exp(v.logf)), 2)
        d["vertical_fov_deg"] = round(float(np.degrees(2 * np.arctan(v.size[1] / 2 / np.exp(v.logf)))), 2)
        rel = v.cam - np.array([0, 0, 0.08])
        dist = np.linalg.norm(rel)
        d["azimuth_deg"] = round(float(np.degrees(np.arctan2(-rel[0], rel[1]))), 1)
        d["elevation_deg"] = round(float(np.degrees(np.arcsin(rel[2] / dist))), 1)
        d["distance_m"] = round(float(dist), 3)
        out["views"][v.name] = d
    (CP2 / "cameras.json").write_text(json.dumps(out, indent=2))
    (CP2 / "refine_log.json").write_text(json.dumps(log, indent=2))
    ext = verts.max(0) - verts.min(0)
    print("mesh", len(verts), "verts", len(faces), "faces; extent (cm) x/y/z", (ext * 100).round(1))


if __name__ == "__main__":
    sys.exit(main())
