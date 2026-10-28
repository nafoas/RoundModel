"""Prince, carved (tasks/02, base shape). Subtractive, like sculpting: start
from a block bigger than him on every side and chisel it away.

Pass 1, the rough-out: carving from his photos. The block is a grid of small
cubes (voxels). From each photo's fitted camera, every cube that falls
outside his outline in that photo is cut away; what is left is the largest
shape every photo agrees he could be (the "visual hull"). He is not a
statue: in each photo his head is posed as he holds it there (the head
poses already worked out), and each photo gets a small tolerance for its
camera fit, more for photos whose camera or pose is less certain. Top-down
(his circumference) and the master cut hardest.

What carving cannot do: a photo outline only shows the edge, so hollows
(the dip between cheek and chest, under the chin) and the corners between
views are left too full. Those are chiselled next, by eye, against his
photos (pass 2, tools/chisel.py).

usage: python tools/carve.py OUTDIR [--step 0.0015]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as nd
from scipy.spatial.transform import Rotation as R
from skimage import measure

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parents[1]
_ap = ROOT / "checkpoints/cp4/view_align.json"
ALIGN = json.loads(_ap.read_text()) if _ap.exists() else {}  # tools/align_views.py
USE_POSES = True
NO_EARS = True  # his head as he holds it in each photo (--no_poses to carve without)
BLOCK = ((-0.12, 0.12), (-0.15, 0.15), (-0.04, 0.21))  # bigger than him on all sides

# view: tolerance in that photo's own pixels (camera / pose certainty)
VIEWS = {
    "sheet_09_top_down": 3,
    "master_front_standing": 3,
    "sheet_03_right_profile": 6,
    "sheet_04_back_3q_right": 8,
    "sheet_02_front_3q": 8,
    "sheet_08_front_3q_left": 8,
    "sheet_07_left_profile": 14,
    "sheet_05_back": 2,          # small sheet panel: tolerance in panel pixels
    "sheet_06_back_3q_left": 2,
}


def view_data(name):
    cams = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]
    side = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
    if name in side:
        c = side[name]
        mask = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{name}.png")) > 127
        cam = dict(rot=c["rotvec_world_to_cam"], pos=c["camera_position_m"], f=c["focal_px"], pp=c["principal_px"])
    else:
        c = cams[name]
        if name == "master_front_standing":
            mask = np.asarray(Image.open(ROOT / "checkpoints/cp4/outlines/master_front_standing.png")) > 127
        else:
            mask = np.asarray(Image.open(ROOT / f"checkpoints/cp1/masks/{name}.outline.png").convert("L")) > 127
        cam = dict(rot=c["rotvec_world_to_cam"], pos=c["camera_position_m"], f=c["focal_px"],
                   pp=[mask.shape[1] / 2, mask.shape[0] / 2])
    pose = ROOT / f"checkpoints/cp3/head_poses_parts/{name}.json"
    cam["pose"] = json.loads(pose.read_text()) if pose.exists() and USE_POSES else None
    ne = ROOT / f"checkpoints/cp4/outlines/{name}.noears.png"
    if NO_EARS and ne.exists():  # ears are built separately (tools/ears_out.py)
        mask = np.asarray(Image.open(ne)) > 127
    al = ALIGN.get(name)
    if al:
        cam["align"] = al
    return cam, mask


def posed(P, pose):
    if pose is None:
        return P
    from sculpt import NECK_PIVOT, head_weight
    hw = head_weight(P)
    Rm = R.from_rotvec(pose["rotvec"]).as_matrix()
    Pp = (P - NECK_PIVOT) @ Rm.T + NECK_PIVOT + np.asarray(pose["shift_m"])
    return P + hw[:, None] * (Pp - P)


def project(P, cam):
    Rc = R.from_rotvec(cam["rot"]).as_matrix()
    Xc = (P - np.asarray(cam["pos"])) @ Rc.T
    uv = cam["f"] * Xc[:, :2] / Xc[:, 2:3] + np.asarray(cam["pp"])
    a = cam.get("align")
    if a:  # scale between photos (each taken from its own distance), shift, roll
        c = np.asarray(a["c"])
        th = np.radians(a["roll_deg"])
        Rm = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        uv = (uv - c) @ Rm.T * a["s"]
        uv[:, 1] *= a.get("sy", 1.0)  # along his length in the top-down photo
        uv = uv + c + np.asarray(a["t"])
    return uv


def carve(step, views=VIEWS):
    axes = [np.arange(lo, hi + step, step) for lo, hi in BLOCK]
    shape = tuple(len(a) for a in axes)
    P = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    keep = np.ones(len(P), bool)
    report = {}
    for name, tol in views.items():
        cam, mask = view_data(name)
        m = nd.binary_dilation(mask, iterations=tol) if tol else mask
        uv = np.round(project(posed(P[keep], cam["pose"]), cam)).astype(int)
        H, W = m.shape
        inside = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
        ok = np.zeros(len(uv), bool)
        ok[inside] = m[uv[inside, 1], uv[inside, 0]]
        idx = np.nonzero(keep)[0]
        cut = idx[~ok]
        keep[cut] = False
        report[name] = int(len(cut))
        print(f"{name:28s} cut {len(cut):9d}  left {int(keep.sum()):9d}", flush=True)
    vol = keep.reshape(shape)
    # one solid piece, no holes
    lab, n = nd.label(vol)
    if n > 1:
        sizes = nd.sum(vol, lab, range(1, n + 1))
        vol = lab == 1 + int(np.argmax(sizes))
    vol = nd.binary_fill_holes(vol)
    return vol, axes, report


def chisel_corners(vol, step, radius=0.008, keep_mm=0.0):
    """Pass 2a: take the corners off. Carving from outlines leaves flat planes
    meeting at hard edges wherever no photo looked squarely (between views).
    The signed distance to the carved surface is blurred over `radius`; where
    planes meet at an edge the blurred surface lies inside the old one, so the
    edge is cut away. Only cuts, never adds (intersected with the carving).
    keep_mm shifts the result outward a little so smooth stretches, already
    right, are not shaved."""
    inside = nd.distance_transform_edt(vol) * step
    outside = nd.distance_transform_edt(~vol) * step
    sdf = outside - inside
    sm = nd.gaussian_filter(sdf, radius / step)
    return vol & (sm < keep_mm / 1000)


def carve_votes(step, views=VIEWS, hard=4.0, votes=2):
    """Gentler carving (owner: the first carving took too much off every side,
    and squared his nose from above). One photo's small camera or pose error
    should not be able to cut him alone. A cube is cut only when
      - one photo puts it outside him by more than `hard` x its tolerance, or
      - at least `votes` photos put it outside him by more than their
        tolerance.
    Distances are measured in each photo's pixels from his outline."""
    axes = [np.arange(lo, hi + step, step) for lo, hi in BLOCK]
    shape = tuple(len(a) for a in axes)
    P = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    n_out = np.zeros(len(P), np.int16)
    hard_cut = np.zeros(len(P), bool)
    report = {}
    for name, tol in views.items():
        cam, mask = view_data(name)
        dist = nd.distance_transform_edt(~mask)  # px outside his outline
        uv = np.round(project(posed(P, cam["pose"]), cam)).astype(int)
        H, W = mask.shape
        inside = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
        d = np.full(len(P), 1e6)
        d[inside] = dist[uv[inside, 1], uv[inside, 0]]
        n_out += d > tol
        hard_cut |= d > hard * tol
        report[name] = int((d > hard * tol).sum())
    keep = ~(hard_cut | (n_out >= votes))
    print("kept", int(keep.sum()), "cubes", flush=True)
    vol = keep.reshape(shape)
    lab, n = nd.label(vol)
    if n > 1:
        sizes = nd.sum(vol, lab, range(1, n + 1))
        vol = lab == 1 + int(np.argmax(sizes))
    return nd.binary_fill_holes(vol), axes, report


def symmetric(vol, axes, step):
    """Left and right made the same (owner: don't let the top-down photo,
    where he points a little to his left, make him crooked). His own
    midline plane is found first (where it is across him and which way it
    faces, a vertical plane), as the plane his carved shape is most nearly a
    mirror image across; then the signed distance is averaged with its
    mirror image across that plane."""
    from scipy.optimize import minimize
    sdf = nd.distance_transform_edt(~vol) - nd.distance_transform_edt(vol)
    o = np.array([ax[0] for ax in axes])
    near = np.abs(sdf) < 6  # cubes near his surface
    P = np.stack(np.nonzero(near), -1) * step + o
    sub = P[:: max(1, len(P) // 40000)]

    def mirror(Q, c, th):
        n = np.array([np.cos(th), np.sin(th), 0.0])
        d = (Q - [c, 0, 0]) @ n
        return Q - 2 * d[:, None] * n

    def sample(Q):
        return nd.map_coordinates(sdf, ((Q - o) / step).T, order=1, mode="nearest")

    def cost(p):
        return np.mean((sample(sub) - sample(mirror(sub, p[0], p[1]))) ** 2)

    r = minimize(cost, [0.0, 0.0], method="Powell", options={"xtol": 1e-5})
    c, th = r.x
    print(f"his midline: x = {c * 1000:.1f} mm, turned {np.degrees(th):.2f} deg", flush=True)
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    sym = (sdf.ravel() + sample(mirror(G, c, th))) / 2
    return (sym < 0).reshape(vol.shape), (float(c), float(th))


def mesh(vol, axes, step, smooth_iters=30):
    """Surface of the carved block; voxel steps relaxed (Taubin smoothing,
    which does not shrink him)."""
    f = nd.gaussian_filter(vol.astype(float), 1.6)  # no cube steps (rings) on gentle curves
    V, F, _, _ = measure.marching_cubes(np.pad(f, 2), 0.5, spacing=(step, step, step))
    V += np.array([a[0] for a in axes]) - 2 * step
    F = F[:, ::-1]  # outward-facing (marching cubes on an inside-high field faces inward)
    n = len(V)
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E = np.vstack([E, E[:, ::-1]])
    import scipy.sparse as sp
    A = sp.csr_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(n, n))
    A.data[:] = 1
    deg = np.asarray(A.sum(1)).ravel()
    L = sp.diags(1 / np.maximum(deg, 1)) @ A
    for _ in range(smooth_iters):
        V = V + 0.5 * (L @ V - V)
        V = V - 0.53 * (L @ V - V)
    return V, F


def write_obj(path, V, F):
    with open(path, "w") as fh:
        fh.write("".join(f"v {a:.6f} {b:.6f} {c:.6f}\n" for a, b, c in V))
        fh.write("".join(f"f {a + 1} {b + 1} {c + 1}\n" for a, b, c in F))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--step", type=float, default=0.0015)
    ap.add_argument("--votes", type=int, default=0, help="gentle carving: photos that must agree to cut")
    ap.add_argument("--hard", type=float, default=4.0, help="one photo alone cuts beyond this x its tolerance")
    ap.add_argument("--round", type=float, default=0.0, help="chisel the corners off over this radius (m)")
    ap.add_argument("--keep_mm", type=float, default=0.0)
    ap.add_argument("--no_poses", action="store_true")
    ap.add_argument("--close", type=float, default=0.0, help="fill creases narrower than twice this radius (m)")
    ap.add_argument("--asym", action="store_true", help="don't make left and right the same")
    ap.add_argument("--ears", action="store_true", help="carve with the ears left in the outlines")
    a = ap.parse_args()
    global USE_POSES
    USE_POSES = not a.no_poses
    global NO_EARS
    NO_EARS = not a.ears
    if a.votes:
        vol, axes, report = carve_votes(a.step, hard=a.hard, votes=a.votes)
    else:
        vol, axes, report = carve(a.step)
    if a.close:
        # fill narrow creases only (a rounded tool of this radius cannot reach
        # into them from outside): the carving and the per-photo head turns
        # leave a crease from cheek to cheek under the muzzle that he does
        # not have
        r = int(round(a.close / a.step))
        g = np.add.outer(np.add.outer(np.arange(-r, r + 1) ** 2, np.arange(-r, r + 1) ** 2), np.arange(-r, r + 1) ** 2) <= r * r
        before = int(vol.sum())
        vol = nd.binary_closing(np.pad(vol, r + 1), structure=g)[r + 1:-r - 1, r + 1:-r - 1, r + 1:-r - 1]
        print(f"creases filled: {int(vol.sum()) - before} cubes ({(vol.sum() - before) * a.step ** 3 * 1e6:.1f} cm3)")
    if not a.asym:
        vol, plane = symmetric(vol, axes, a.step)
        json.dump({"x_m": plane[0], "turn_rad": plane[1]}, open(Path(a.out).parent / f"{Path(a.out).name}.midline.json", "w"))
    if a.round:
        before = int(vol.sum())
        vol = chisel_corners(vol, a.step, a.round, a.keep_mm)
        print(f"corners chiselled: {before - int(vol.sum())} cubes cut ({(before - vol.sum()) * a.step ** 3 * 1e6:.1f} cm3)")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "volume.npy", vol)
    json.dump({"step": a.step, "origin": [ax[0] for ax in axes], "cut": report},
              open(out / "carve.json", "w"), indent=1)
    V, F = mesh(vol, axes, a.step)
    write_obj(out / "head.obj", V, F)
    print("mesh", len(V), "vertices; extent", V.min(0).round(3), V.max(0).round(3))


if __name__ == "__main__":
    main()
