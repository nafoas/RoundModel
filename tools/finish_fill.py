"""Step 2, finishing (tasks/03_from_master_front.md): the filled-in rest of
him smoothed and shaped by the other photos' normals; his front (the
master's, step 1) never moved.

1. His front points: the surface points the master sees that lie on his front
   (within 0.3 mm of it along their master ray). They are held exactly.
2. Smooth: every other point relaxes to a smooth surface (bending kept low)
   that stays near where the photos carved it (min |L V|^2 + w |V - V0|^2,
   front held), so the cut-stone facets and the ragged join go, and the
   join meets his front without a step.
3. Shape (--shape): the other photos' normals (checkpoints/cp5/maps), each
   photo seen through its camera with his head turned as re-fitted against
   the new front (checkpoints/cp6/head_poses), blended per point (face-on
   counts more; a reading 30 deg from the blend dropped), then the surface
   slid along its normals so its edges lie flat against them (as
   tools/chisel_normals.py), front held, a light hold elsewhere. Loafed
   photos give no readings on his chest and peets.

usage: python tools/finish_fill.py FILL_DIR FRONT_DIR OUT_DIR [--w 0.02] [--shape]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from PIL import Image
from scipy import ndimage as nd
from scipy.ndimage import map_coordinates
from scipy.sparse.linalg import cg, factorized
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from fill_from_photos import MASTER, POSES, STANDING, VIEWS, unpose  # noqa: E402
from maps_model import camera, posed, splat, vertex_normals  # noqa: E402
from master_shell import master_intrinsics  # noqa: E402
from refine_rim import laplacian  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def master_proj():
    f, pp, Rc, pos, _ = master_intrinsics()

    def proj(P):
        X = (P - pos) @ Rc.T
        return f * X[:, :2] / X[:, 2:3] + pp, X[:, 2]
    return proj, pos


def front_points(V, F, zfront):
    proj, pos = master_proj()
    H, W = zfront.shape
    uv, z = proj(V)
    (_,), zb = splat(V, F, [np.zeros(len(V), np.int8)], proj, H, W)
    px = np.clip(np.round(uv).astype(int), 0, [W - 1, H - 1])
    seen = np.abs(z - zb[px[:, 1], px[:, 0]]) < 0.0015
    zt = map_coordinates(np.nan_to_num(zfront, nan=0), [uv[:, 1], uv[:, 0]], order=1, cval=0)
    return seen & (zt > 0) & (np.abs(zt - z) < 0.0003), uv


def readings(V, F, name, mpose, lower):
    """One photo's surface direction at each point it sees (world = him as in the master), and weights."""
    mp = ROOT / f"checkpoints/cp5/maps/{name}"
    if not (mp / "normals.npy").exists():
        return None, None
    Np = np.load(mp / "normals.npy").astype(float)
    p = ROOT / f"checkpoints/cp4/outlines/{name}.png"
    mask = np.asarray(Image.open(p).convert("L")) > 127
    mask = nd.binary_erosion(mask, iterations=10)
    H, W = mask.shape
    proj, Rc, pose = camera(name)
    if (POSES / f"{name}.json").exists():
        pose = json.loads((POSES / f"{name}.json").read_text())
    Vo = unpose(V, mpose)  # to the old frame the cameras live in
    Vp = posed(Vo, pose)
    uv, z = proj(Vp)
    (_,), zb = splat(Vp, F, [np.zeros(len(V), np.int8)], proj, H, W)
    px = np.round(uv).astype(int)
    ok = (px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < H)
    pi = np.where(ok, px[:, 1], 0), np.where(ok, px[:, 0], 0)
    ok &= np.abs(z - zb[pi]) < 0.0015
    ok &= mask[pi]
    Nm = vertex_normals(Vp, F)
    sight = proj.pos - Vp
    sight /= np.linalg.norm(sight, axis=1, keepdims=True)
    c = np.einsum("ij,ij->i", Nm, sight)
    ok &= c > np.cos(np.radians(70))
    if name not in STANDING:
        ok &= ~lower
    n = (Np[pi] * np.array([1, -1, -1])) @ Rc  # photo -> camera -> world (old frame, head as in the photo)
    hw = head_weight(Vo)[:, None] > 0.5
    if pose:  # head back to the old rest, then into the master's pose
        n = np.where(hw, n @ R.from_rotvec(pose["rotvec"]).as_matrix(), n)
    if mpose:
        n = np.where(hw, n @ R.from_rotvec(mpose["rotvec"]).as_matrix().T, n)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    return n, np.where(ok, c ** 2, 0.0)


def edges(F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    return np.unique(E, axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fill")
    ap.add_argument("front")
    ap.add_argument("out")
    ap.add_argument("--w", type=float, default=0.02, help="pull toward the carved surface while smoothing")
    ap.add_argument("--shape", action="store_true")
    ap.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    V, F = load_obj(Path(a.fill) / "head.obj")
    zfront = np.load(Path(a.front) / "depth.npy")
    fixed, uvm = front_points(V, F, zfront)
    print(f"front points held: {fixed.sum()} of {len(V)}", flush=True)
    n = len(V)
    L = laplacian(F, n).tocsr()
    free = np.nonzero(~fixed)[0]
    fx = np.nonzero(fixed)[0]
    # 2. smooth, front held
    M = (L.T @ L + a.w * sp.eye(n)).tocsr()
    Mff = M[free][:, free].tocsc()
    Mfx = M[free][:, fx]
    solve = factorized(Mff)
    V0 = V.copy()
    for k in range(3):
        V[free, k] = solve(a.w * V0[free, k] - Mfx @ V0[fx, k])
    mv = np.linalg.norm(V - V0, axis=1)
    print(f"smoothed: moved mean {mv.mean()*1000:.2f} mm, max {mv.max()*1000:.2f} mm", flush=True)
    C.write_obj(out / "smoothed.obj", V, F)
    if a.shape:
        _, _, mpose = camera(MASTER)
        L2m = json.loads((ROOT / "references/landmarks.json").read_text())["views"][MASTER]["points"]
        proj_m, _ = master_proj()
        _, zq = proj_m(V)
        zt = map_coordinates(np.nan_to_num(zfront, nan=0), [uvm[:, 1], uvm[:, 0]], order=1, cval=0)
        lower = (uvm[:, 1] > L2m["mouth_split"][1] + 30) & (zt > 0) & (zq < zt + 0.06)
        E = edges(F)
        i, j = E[:, 0], E[:, 1]
        for r in range(a.rounds):
            Ns, Ws = [], []
            for name in VIEWS:
                nr, w = readings(V, F, name, mpose, lower)
                if nr is not None:
                    Ns.append(nr)
                    Ws.append(w)
            Ns, Ws = np.stack(Ns), np.stack(Ws)
            t = (Ws[..., None] * Ns).sum(0)
            t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
            ang = np.degrees(np.arccos(np.clip(np.einsum("vpi,pi->vp", Ns, t), -1, 1)))
            Ws = Ws * (ang < 30)
            t = (Ws[..., None] * Ns).sum(0)
            wt = Ws.sum(0)
            t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
            N0 = vertex_normals(V, F)
            te = t[i] + t[j]
            te /= np.maximum(np.linalg.norm(te, axis=1, keepdims=True), 1e-9)
            w = np.minimum(np.sqrt(np.minimum(wt[i], wt[j])), 2.0)
            m = np.nonzero(w > 0)[0]
            A = sp.csr_matrix((np.r_[w[m] * np.einsum("ij,ij->i", te[m], N0[j[m]]), -w[m] * np.einsum("ij,ij->i", te[m], N0[i[m]])],
                               (np.r_[np.arange(len(m))] * 1 if False else np.r_[np.arange(len(m)), np.arange(len(m))], np.r_[j[m], i[m]])),
                              shape=(len(m), n))
            b = -w[m] * np.einsum("ij,ij->i", te[m], V[j[m]] - V[i[m]])
            S = sp.csr_matrix((np.r_[np.full(len(E), 0.3), np.full(len(E), -0.3)],
                               (np.r_[np.arange(len(E)), np.arange(len(E))], np.r_[j, i])), shape=(len(E), n))
            Mm = (A.T @ A + S.T @ S + 0.05 * sp.eye(n)).tocsr()
            Mfree = Mm[free][:, free]
            d = np.zeros(n)
            d[free], _ = cg(Mfree, (A.T @ b)[free], rtol=1e-6, maxiter=800)
            big = np.abs(d).max()
            if big > 0.003:
                d *= 0.003 / big
            V = V + d[:, None] * N0
            print(f"shape round {r}: points with a reading {(wt > 0).sum()}, slide mean {np.abs(d).mean()*1000:.2f} mm, "
                  f"max {np.abs(d).max()*1000:.2f} mm", flush=True)
    C.write_obj(out / "head.obj", V, F)


if __name__ == "__main__":
    main()
