"""His front from the master's normals, complete and unaltered (owner; see
docs/MEASURING.md, "Normals from every side").

Wherever the master sees the model's surface (not hidden, inside his
outline in the master; only a 2 px margin at the outline, where the fur
edge leaves the photo), the target direction is exactly the master's
estimated surface direction at that pixel, taken back to his head at rest.
No blending with other photos, no smoothing there.

Everywhere else the blend from the other photos (tools/fuse_normals.py)
stays, smoothed over the surface so the seams between one photo's coverage
and the next don't get carved in; the master's points are held fixed while
smoothing, so the smoothing runs into the master's region and never the
other way. Points no photo saw keep no target.

Reads checkpoints/cp5/fused/target.npy, weight.npy (the blend); writes
target.npy, weight.npy (the blend kept as target_blend.npy, weight_blend.npy)
and master_seen.npy, and remakes master.jpg / profile.jpg.

usage: python tools/master_front.py MODEL_DIR [--smooth 20]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from PIL import Image
from scipy import ndimage as nd
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from fuse_normals import OUT, show  # noqa: E402
from maps_model import camera, posed, splat, vertex_normals  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VIEW = "master_front_standing"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--smooth", type=int, default=20, help="rounds of neighbour averaging for the other photos' blend")
    ap.add_argument("--fade_mm", type=float, default=15.0, help="how far the blend is faded into the master's along their border")
    a = ap.parse_args()
    md = Path(a.model)
    V, F = load_obj(md / "head.obj")
    occ = [(V, F)] + [load_obj(e) for e in sorted(md.glob("eye_*.obj"))]
    Vocc = np.vstack([o[0] for o in occ])
    Focc = np.vstack([o[1] + sum(len(q[0]) for q in occ[:i]) for i, o in enumerate(occ)])
    keep = OUT / "target_blend.npy"
    if not keep.exists():  # the blend from every photo, kept
        np.save(keep, np.load(OUT / "target.npy"))
        np.save(OUT / "weight_blend.npy", np.load(OUT / "weight.npy"))
    T = np.load(keep)
    Wt = np.load(OUT / "weight_blend.npy")
    # the master's readings, complete
    Np = np.load(ROOT / f"checkpoints/cp5/maps/{VIEW}/normals.npy").astype(float)
    outline = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{VIEW}.png").convert("L")) > 127
    inside = nd.binary_erosion(outline, iterations=2)
    H, W = outline.shape
    proj, Rc, pose = camera(VIEW)
    Vp, Vop = posed(V, pose), posed(Vocc, pose)
    (_,), zbuf = splat(Vop, Focc, [np.zeros(len(Vop), np.int8)], proj, H, W)
    uv, z = proj(Vp)
    px = np.round(uv).astype(int)
    ok = (px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < H) & (z > 0)
    pi = np.where(ok, px[:, 1], 0), np.where(ok, px[:, 0], 0)
    ok &= np.abs(z - zbuf[pi]) < 0.002
    ok &= inside[pi]
    sight = proj.pos - Vp
    sight /= np.linalg.norm(sight, axis=1, keepdims=True)
    ok &= np.einsum("ij,ij->i", vertex_normals(Vp, F), sight) > 0  # facing the master at all
    n = (Np[pi] * np.array([1, -1, -1])) @ Rc
    hw = head_weight(V)
    if pose:
        Rh = R.from_rotvec(pose["rotvec"]).as_matrix()
        n = np.where((hw > 0.5)[:, None], n @ Rh, n)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    # everywhere else: the other photos' blend, smoothed with the master held fixed
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    E = np.unique(E, axis=0)
    A = sp.csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(len(V), len(V)))
    has = (Wt > 0) | ok
    t = np.where(ok[:, None], n, T)
    t[~has] = 0
    free = has & ~ok
    # the other photos' blend faded into the master's along the border: a
    # smooth correction (screened Laplace: equal to master - blend at the
    # master's points, dying away over about FADE_MM outside), so there is
    # no kink (crease) where one meets the other. The master's own points
    # are not changed.
    deg = np.asarray(A.sum(1)).ravel()
    L = sp.diags(deg) - A
    h = float(np.median(np.linalg.norm(V[E[:, 0]] - V[E[:, 1]], axis=1)))
    mu = (h / (a.fade_mm / 1000)) ** 2
    fixed = ok
    D = np.zeros_like(t)
    border = ok & (A @ free.astype(float) > 0)
    D[border] = n[border] - T[border]
    Mf = (L + mu * sp.eye(len(V))).tocsr()
    fi = np.nonzero(~fixed)[0]
    Mff = Mf[fi][:, fi]
    from scipy.sparse.linalg import cg
    for k in range(3):
        rhs = -(Mf[fi][:, np.nonzero(fixed)[0]] @ D[fixed, k])
        x, _ = cg(Mff, rhs, rtol=1e-6, maxiter=2000)
        D[fi, k] = x
    t[free] = T[free] + D[free]
    t[free] /= np.maximum(np.linalg.norm(t[free], axis=1, keepdims=True), 1e-9)
    for _ in range(a.smooth):  # and a light smoothing of the blend's own seams
        avg = A @ t
        cnt = A @ has.astype(float)
        s_ = np.where((cnt > 0)[:, None], avg / np.maximum(cnt, 1)[:, None], t)
        t[free] = 0.5 * t[free] + 0.5 * s_[free]
        t[free] /= np.maximum(np.linalg.norm(t[free], axis=1, keepdims=True), 1e-9)
    w = np.where(ok, 4.0, Wt)  # the master's front counts as sure
    np.save(OUT / "target.npy", t)
    np.save(OUT / "weight.npy", w)
    np.save(OUT / "master_seen.npy", ok)
    cur = vertex_normals(V, F)
    off = np.degrees(np.arccos(np.clip((cur * t).sum(1), -1, 1)))
    print(f"master sees {ok.mean()*100:.0f}% of the points (their target is the master's, unaltered); "
          f"other photos {free.mean()*100:.0f}%; none {(~has).mean()*100:.0f}%. "
          f"Model vs target: master region median {np.median(off[ok]):.1f} deg, elsewhere {np.median(off[free]):.1f} deg", flush=True)
    show(V, F, cur, t, VIEW, "master", w)
    show(V, F, cur, t, "sheet_03_right_profile", "profile", w)


if __name__ == "__main__":
    main()
