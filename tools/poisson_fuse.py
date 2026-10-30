"""Prince from all photos the way the field does it (docs/RESEARCH.md):
per-photo depth+normal maps -> oriented points in one world -> screened
Poisson -> his master front placed back exactly.

1. Each photo with a reliable camera: its normal map (checkpoints/cp5/maps)
   integrated into a depth map inside its outline (perspective integration,
   master_shell.integrate). The master's is step 1's front (work/m/front).
2. Each photo's points put in the world (him as in the master) through its
   own camera, his head turned as re-fitted (checkpoints/cp6/head_poses);
   normals turned the same way. Each photo's one free number (its distance,
   a scale along its rays) is set so its surface sits on the outline hull
   of him (work/m/fill2: carved from all the photos' outlines, the front
   from the master): the median distance to it smallest.
3. Points the master puts outside his outline are dropped (the master's
   edge is his edge); points far from the hull (> DROP_MM) dropped.
4. Screened Poisson (PyMeshLab), point weight 4, the master's points
   counting most (confidence).
5. Every surface point the master sees near his front is placed exactly on
   it along its master ray.

usage: python tools/poisson_fuse.py FRONT_DIR HULL_DIR OUT_DIR [--depth 10]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd
from scipy.ndimage import map_coordinates
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from fill_from_photos import POSES, unpose  # noqa: E402
from maps_model import camera, posed  # noqa: E402
from master_shell import integrate, master_intrinsics  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MASTER = "master_front_standing"
VIEWS = ["sheet_02_front_3q", "sheet_08_front_3q_left", "sheet_03_right_profile", "sheet_07_left_profile",
         "sheet_09_top_down", "sheet_04_back_3q_right", "e_back_3q_left_high", "s01", "s18",
         "c02", "c21", "c08", "c10", "c09", "c26", "c03", "c12"]
DROP_MM = 8.0
MASTER_W = 4.0


def intrinsics(name):
    """f, principal point, world->camera rotation, camera position, in the photo's own pixels."""
    p = ROOT / f"checkpoints/cp4/cams/{name}.json"
    if p.exists():
        c = json.loads(p.read_text())
        return c["focal_px"], np.asarray(c["principal_px"], float), R.from_rotvec(c["rotvec_world_to_cam"]).as_matrix(), \
            np.asarray(c["camera_position_m"], float)
    cam, _ = C.view_data(name)
    f, pp, Rc = cam["f"], np.asarray(cam["pp"], float), R.from_rotvec(cam["rot"]).as_matrix()
    a = cam.get("align")
    if a:
        th = np.radians(a["roll_deg"])
        Rr = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        c0 = np.asarray(a["c"])
        pp = (pp - c0) @ Rr.T * a["s"] + c0 + np.asarray(a["t"])
        f = f * a["s"]
        R3 = np.eye(3)
        R3[:2, :2] = Rr
        Rc = R3 @ Rc
    return f, pp, Rc, np.asarray(cam["pos"], float)


def unpose_view(P, pose):
    """From his head as in that photo back to the old rest frame."""
    if not pose:
        return P
    Rm = R.from_rotvec(pose["rotvec"]).as_matrix()
    Q = (P - NECK_PIVOT - np.asarray(pose.get("shift_m", [0, 0, 0]))) @ Rm + NECK_PIVOT
    return P + head_weight(P)[:, None] * (Q - P)


def view_points(name, mpose, k=3):
    f, pp, Rc, pos = intrinsics(name)
    N = np.load(ROOT / f"checkpoints/cp5/maps/{name}/normals.npy").astype(float) * np.array([1, -1, -1])
    mask = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{name}.png").convert("L")) > 127
    mask = nd.binary_erosion(mask, iterations=6)
    lz = integrate(N, mask, f, pp, k)
    ok = np.isfinite(lz)
    lab, n = nd.label(ok)
    if n > 1:  # the main piece only
        ok = lab == 1 + int(np.argmax(nd.sum(ok, lab, range(1, n + 1))))
    vv, uu = np.nonzero(ok)
    u, v = uu * k, vv * k
    ray = np.stack([(u - pp[0]) / f, (v - pp[1]) / f, np.ones(len(u))], -1)
    z = np.exp(lz[vv, uu] - np.median(lz[vv, uu]))  # depth up to one scale
    nc = N[v, u]
    _, _, pose = camera(name)
    if (POSES / f"{name}.json").exists():
        pose = json.loads((POSES / f"{name}.json").read_text())

    def place(scale):
        P = pos + (ray * (z * scale)[:, None]) @ Rc
        Po = unpose_view(P, pose)  # old rest frame
        return posed(Po, mpose), Po
    # normals: camera -> world (head as in the photo) -> rest -> master's pose
    nw = nc @ Rc
    sight = -(ray / np.linalg.norm(ray, axis=1, keepdims=True)) @ Rc
    return place, nw, pose, sight


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("front")
    ap.add_argument("hull")
    ap.add_argument("out")
    ap.add_argument("--depth", type=int, default=10)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    fm, ppm, Rcm, posm, mpose = master_intrinsics()
    zfront = np.load(Path(a.front) / "depth.npy")
    Hm, Wm = zfront.shape
    noears = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{MASTER}.noears.png").convert("L")) > 127
    Vh, Fh = load_obj(Path(a.hull) / "head.obj")
    tree = cKDTree(Vh)
    allP, allN, allW = [], [], []
    # the master's front: its own points and normals (from its surface)
    Vf, Ff = load_obj(Path(a.front) / "head.obj")
    from maps_model import vertex_normals
    Nf = vertex_normals(Vf, Ff)
    sel = np.arange(0, len(Vf), 3)
    allP.append(Vf[sel])
    allN.append(Nf[sel])
    allW.append(np.full(len(sel), MASTER_W))
    print("master front points", len(sel), flush=True)
    for name in VIEWS:
        try:
            place, nw, pose, sight = view_points(name, mpose)
        except Exception as e:  # noqa: BLE001
            print("skip", name, e)
            continue
        best = None
        for s in np.exp(np.linspace(np.log(0.05), np.log(1.5), 120)):
            P, _ = place(s)
            d = np.median(tree.query(P[:: 20])[0])
            if best is None or d < best[0]:
                best = (d, s)
        lo, hi = best[1] * 0.97, best[1] * 1.03
        for s in np.linspace(lo, hi, 40):
            P, _ = place(s)
            d = np.median(tree.query(P[:: 5])[0])
            if d < best[0]:
                best = (d, s)
        P, Po = place(best[1])
        # normals into the master's pose (head points turned like the head)
        hw = head_weight(Po)[:, None] > 0.5
        n_ = nw.copy()
        if pose:
            n_ = np.where(hw, n_ @ R.from_rotvec(pose["rotvec"]).as_matrix(), n_)
        if mpose:
            n_ = np.where(hw, n_ @ R.from_rotvec(mpose["rotvec"]).as_matrix().T, n_)
        dist = tree.query(P)[0]
        Xc = (P - posm) @ Rcm.T
        uvm = fm * Xc[:, :2] / Xc[:, 2:3] + ppm
        inm = map_coordinates(noears.astype(float), [uvm[:, 1], uvm[:, 0]], order=0, cval=0) > 0.5
        keep = inm & (dist < DROP_MM / 1000)
        # don't add other photos' points on the master's own front: it is there already
        zt = map_coordinates(np.nan_to_num(zfront, nan=0), [uvm[:, 1], uvm[:, 0]], order=0, cval=0)
        facing_m = np.einsum("ij,ij->i", n_, -(Xc / np.linalg.norm(Xc, axis=1, keepdims=True)) @ Rcm) > 0.3
        keep &= ~(facing_m & (zt > 0) & (np.abs(Xc[:, 2] - zt) < 0.004))
        c2 = np.clip(np.einsum("ij,ij->i", nw, sight), 0, 1) ** 2
        allP.append(P[keep])
        allN.append(n_[keep])
        allW.append(c2[keep])
        print(f"{name}: scale {best[1]:.3f}, median distance to the hull {best[0]*1000:.1f} mm, points kept {keep.sum()}/{len(P)}", flush=True)
    P = np.vstack(allP)
    N = np.vstack(allN)
    Wt = np.concatenate(allW)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    np.save(out / "points.npy", np.c_[P, N, Wt].astype(np.float32))
    import pymeshlab as ml
    ms = ml.MeshSet()
    m = ml.Mesh(vertex_matrix=P, v_normals_matrix=N, v_scalar_array=Wt)
    ms.add_mesh(m)
    ms.generate_surface_reconstruction_screened_poisson(depth=a.depth, pointweight=4.0, samplespernode=1.5,
                                                         confidence=True, preclean=True)
    mesh = ms.current_mesh()
    V, F = mesh.vertex_matrix(), mesh.face_matrix()
    print(f"poisson surface: {len(V)} points, {len(F)} triangles", flush=True)
    # the master's front exactly
    Xc = (V - posm) @ Rcm.T
    uv = fm * Xc[:, :2] / Xc[:, 2:3] + ppm
    zt = map_coordinates(np.nan_to_num(zfront, nan=0), [uv[:, 1], uv[:, 0]], order=1, cval=0)
    from maps_model import splat

    def proj(Q):
        X = (Q - posm) @ Rcm.T
        return fm * X[:, :2] / X[:, 2:3] + ppm, X[:, 2]
    (_,), zb = splat(V, F, [np.zeros(len(V), np.int8)], proj, Hm, Wm)
    px = np.clip(np.round(uv).astype(int), 0, [Wm - 1, Hm - 1])
    seen = np.abs(Xc[:, 2] - zb[px[:, 1], px[:, 0]]) < 0.0015
    snap = seen & (zt > 0) & (np.abs(zt - Xc[:, 2]) < 0.003)
    V[snap] = posm + (V[snap] - posm) * (zt[snap] / Xc[snap, 2])[:, None]
    print(f"front points placed exactly: {snap.sum()}", flush=True)
    C.write_obj(out / "head.obj", V, F)


if __name__ == "__main__":
    main()
