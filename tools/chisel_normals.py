"""Fine chiselling toward his normals from every side (docs/MEASURING.md,
"Normals from every side", step 5).

Each round, every point may slide in or out along its own surface direction
by d (one number per point). Every edge of the surface is asked to lie flat
against his target direction there (target . (v_j - v_i) = 0, weighted by
how sure the target is). Where no photo gave a target, the slide is only
kept smooth with its neighbours. A light pull keeps each round from running
away (the normals almost always win: the hold is small). Solved as one
sparse least-squares problem per round (conjugate gradients).

The targets come from tools/fuse_normals.py on the same mesh
(checkpoints/cp5/fused/target.npy, weight.npy).

usage: python tools/chisel_normals.py IN_DIR OUT_DIR [--rounds 3] [--hold 0.05]
       [--cap_mm 1.5]
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import cg

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from maps_model import vertex_normals  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def edges(F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    return np.unique(E, axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--fused", default=str(ROOT / "checkpoints/cp5/fused"))
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--hold", type=float, default=0.05, help="pull back toward the current surface (small: the normals win)")
    ap.add_argument("--smooth", type=float, default=0.2, help="keeps the slide smooth where no photo gave a target")
    ap.add_argument("--cap_mm", type=float, default=1.5, help="largest slide per round")
    a = ap.parse_args()
    V, F = load_obj(Path(a.inp) / "head.obj")
    T = np.load(Path(a.fused) / "target.npy")
    Wt = np.load(Path(a.fused) / "weight.npy")
    assert len(T) == len(V), "targets were fused on another mesh"
    E = edges(F)
    i, j = E[:, 0], E[:, 1]
    n = len(V)
    total = np.zeros(n)
    for r in range(a.rounds):
        N0 = vertex_normals(V, F)
        # the edge's target: the average of its two ends' targets, sure only if both are
        t = T[i] + T[j]
        t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        w = np.sqrt(np.minimum(Wt[i], Wt[j]))
        w = np.minimum(w, 2.0)
        has = w > 0
        # rows: w * ( t.(V_j - V_i) + d_j t.N0_j - d_i t.N0_i ) = 0
        tj = np.einsum("ij,ij->i", t, N0[j])
        ti = np.einsum("ij,ij->i", t, N0[i])
        rhs = -w * np.einsum("ij,ij->i", t, V[j] - V[i])
        m = np.nonzero(has)[0]
        A = sp.csr_matrix((np.r_[w[m] * tj[m], -w[m] * ti[m]], (np.r_[np.arange(len(m)), np.arange(len(m))],
                                                                np.r_[j[m], i[m]])), shape=(len(m), n))
        b = rhs[m]
        # smooth slide along every edge (stronger where no target), and the hold
        ws = np.where(has, a.smooth * 0.2, a.smooth)
        S = sp.csr_matrix((np.r_[ws, -ws], (np.r_[np.arange(len(E)), np.arange(len(E))], np.r_[j, i])), shape=(len(E), n))
        M = (A.T @ A + S.T @ S + a.hold * sp.eye(n)).tocsr()
        d, info = cg(M, A.T @ b, rtol=1e-6, maxiter=800)
        d = np.clip(d, -a.cap_mm / 1000, a.cap_mm / 1000)
        V = V + d[:, None] * N0
        total += d
        print(f"round {r}: edges with a target {len(m)}, slide mm: mean |d| {np.abs(d).mean()*1000:.3f}, "
              f"out up to {d.max()*1000:.2f}, in up to {-d.min()*1000:.2f} (cg {info})", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", V, F)
    np.save(out / "slide_mm.npy", total * 1000)
    for e in Path(a.inp).glob("eye_*.obj"):
        shutil.copy(e, out / e.name)
    off = np.degrees(np.arccos(np.clip((vertex_normals(V, F) * T).sum(1), -1, 1)))
    has = Wt > 0
    print(f"model vs target now: median {np.median(off[has]):.1f} deg")


if __name__ == "__main__":
    main()
