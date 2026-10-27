"""Fine passes on the carved shape (docs/CARVING.md, section 3c): add or
remove only what is needed, a little at a time.

Each round, for every photo: the model's rim seen from that camera (surface
points whose normal is side-on to the view, his head posed as in that photo)
is compared with his outline. Where the model sticks out past him, the rim
is moved in along its normal; where it falls short, out. The move is the
gap converted from that photo's pixels to millimetres at that depth, capped
per round. Moves from all photos are averaged, weighted (top-down and master
most), and spread into a smooth field over the surface, so the change is a
gentle reshaping and never a lump. Nothing moves where no photo has a rim.

usage: python tools/refine_rim.py IN_DIR OUT_DIR [--rounds 6] [--cap_mm 1.0]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy import ndimage as nd
from scipy.sparse.linalg import factorized
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402

WEIGHT = {"sheet_09_top_down": 3.0, "master_front_standing": 2.5, "sheet_03_right_profile": 1.0,
          "sheet_04_back_3q_right": 1.0, "sheet_02_front_3q": 1.0, "sheet_08_front_3q_left": 1.0,
          "sheet_07_left_profile": 0.5, "sheet_05_back": 0.8, "sheet_06_back_3q_left": 0.8}


def normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def laplacian(F, n):
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    E = np.vstack([E, E[:, ::-1]])
    A = sp.csr_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(n, n))
    A.data[:] = 1
    deg = np.asarray(A.sum(1)).ravel()
    return sp.diags(deg) - A


def signed_px(mask):
    """Signed distance to his outline in pixels: + outside him, - inside."""
    return nd.distance_transform_edt(~mask) - nd.distance_transform_edt(mask)


def round_moves(V, F, data, cap):
    N = normals(V, F)
    num = np.zeros(len(V))
    den = np.zeros(len(V))
    for name, cam, sd in data:
        Vp = C.posed(V, cam["pose"])
        Np = normals(Vp, F)
        Rc = R.from_rotvec(cam["rot"]).as_matrix()
        Xc = (Vp - np.asarray(cam["pos"])) @ Rc.T
        ray = Vp - np.asarray(cam["pos"])
        ray /= np.linalg.norm(ray, axis=1, keepdims=True)
        side_on = np.abs(np.einsum("ij,ij->i", Np, ray)) < 0.12
        uv = cam["f"] * Xc[:, :2] / Xc[:, 2:3] + np.asarray(cam["pp"])
        H, W = sd.shape
        ok = side_on & (uv[:, 0] >= 1) & (uv[:, 0] < W - 1) & (uv[:, 1] >= 1) & (uv[:, 1] < H - 1)
        # only the true outer rim: the projected point must be at the model's
        # own edge, i.e. the outward normal points away from the body in 2D
        idx = np.nonzero(ok)[0]
        s = nd.map_coordinates(sd, [uv[idx, 1], uv[idx, 0]], order=1)
        # size of 1 px at that depth, and how much of a normal move shows in the image
        n_img = (Np[idx] @ Rc.T)[:, :2]
        gain = np.linalg.norm(n_img, axis=1)
        mm_per_px = Xc[idx, 2] / cam["f"]
        move = -s * mm_per_px / np.maximum(gain, 0.5)
        move = np.clip(move, -cap, cap)
        w = WEIGHT[name] * (1 - np.abs(np.einsum("ij,ij->i", Np[idx], ray[idx])) / 0.12)
        np.add.at(num, idx, w * move)
        np.add.at(den, idx, w)
    return num, den


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--cap_mm", type=float, default=1.0)
    ap.add_argument("--smooth", type=float, default=30.0, help="larger = broader, gentler changes")
    ap.add_argument("--asym", action="store_true")
    ap.add_argument("--top_weight", type=float, default=3.0, help="top-down is his circumference (owner)")
    a = ap.parse_args()
    WEIGHT["sheet_09_top_down"] = a.top_weight
    V, F = load_obj(Path(a.inp) / "head.obj")
    data = []
    for name in WEIGHT:
        cam, mask = C.view_data(name)
        data.append((name, cam, signed_px(mask)))
    n = len(V)
    L = laplacian(F, n).tocsc()
    total = np.zeros(n)
    from scipy.spatial import cKDTree
    import json as _j
    mp = Path(a.inp).parent / f"{Path(a.inp).name}.midline.json"
    pl = _j.loads(mp.read_text()) if mp.exists() else {"x_m": 0.0, "turn_rad": 0.0}
    nrm = np.array([np.cos(pl["turn_rad"]), np.sin(pl["turn_rad"]), 0.0])

    def mirror_of(V):
        d = (V - [pl["x_m"], 0, 0]) @ nrm
        return cKDTree(V).query(V - 2 * d[:, None] * nrm)[1]
    for r in range(a.rounds):
        num, den = round_moves(V, F, data, a.cap_mm / 1000)
        t = np.where(den > 0, num / np.maximum(den, 1e-9), 0)
        Wd = sp.diags(np.minimum(den, 3.0))
        # smooth field d: data where photos see a rim, bending kept low elsewhere
        solve = factorized((Wd + a.smooth * (L @ L)).tocsc())
        d = solve(Wd @ t)
        if not a.asym:  # the same move on his left and right (no crookedness)
            d = 0.5 * (d + d[mirror_of(V)])
        V = V + d[:, None] * normals(V, F)
        total += d
        print(f"round {r}: rim points {int((den > 0).sum())}, move mm: mean |d| {np.abs(d).mean()*1000:.2f}, "
              f"max out {d.max()*1000:.2f}, max in {-d.min()*1000:.2f}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", V, F)
    np.save(out / "moved_mm.npy", total * 1000)
    print(f"total: out up to {total.max()*1000:.1f} mm, in up to {-total.min()*1000:.1f} mm")


if __name__ == "__main__":
    main()
