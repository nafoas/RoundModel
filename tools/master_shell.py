"""His front from the master's normal map, and the model made to take it
(docs/MEASURING.md, "Correction (owner): the model must conform to his
normals").

1. His front surface from the master's normals alone, over his whole
   outline (ears left to the built ear leaves): perspective normal
   integration of log depth, d log z/du = -n_x / (f (n . r)), d log z/dv =
   -n_y / (f (n . r)), solved as one sparse least-squares problem (half
   resolution: about 0.3 mm per pixel on him). The map fixes the shape; the
   model sets only one number per connected piece, his scale (distance),
   from the median depth ratio where both exist.
2. The model takes that shape, in a fine block of cubes (0.5 mm) at rest:
   each cube is seen through the master camera (his head posed as there);
   it is him if it is inside his outline there, behind his front surface,
   and in front of the model's own back (where the model doesn't reach as
   far out as he does, its back is carried over from the nearest place it
   does). So the model is cut where it sticks out past him or in front of
   his surface, and filled where he is bigger. Behind his front, it keeps
   its own back, sides and top.
3. Surface by marching cubes, lightly relaxed; ears (the built leaves) and
   eyes copied from the model.

writes OUT_DIR/head.obj (+ ears, eyes), shell_depth.npy (metres along the
master camera's z, NaN outside him) and shell.jpg (his photo | his front
surface from the normals, shaded | the model's front, same camera).

usage: python tools/master_shell.py MODEL_DIR OUT_DIR [--step 0.0005]
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from PIL import Image
from scipy import ndimage as nd
from scipy.sparse.linalg import spsolve
from scipy.spatial.transform import Rotation as R
from skimage import measure

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from maps_model import camera, posed, splat  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VIEW = "master_front_standing"


def master_intrinsics():
    """The master camera as seen in the photo's own pixels: focal, principal
    point, rotation (the per-photo roll/scale/shift folded in), position."""
    cam, _ = C.view_data(VIEW)
    f, pp = cam["f"], np.asarray(cam["pp"], float)
    Rc = R.from_rotvec(cam["rot"]).as_matrix()
    a = cam.get("align")
    if a:
        th = np.radians(a["roll_deg"])
        Rr = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        c = np.asarray(a["c"])
        pp = (pp - c) @ Rr.T * a["s"] + c + np.asarray(a["t"])
        f = f * a["s"]
        R3 = np.eye(3)
        R3[:2, :2] = Rr
        Rc = R3 @ Rc
    return f, pp, Rc, np.asarray(cam["pos"], float), cam["pose"]


def integrate(N, mask, f, pp, k):
    """Log depth from normals (camera frame: x right, y down, z forward),
    at 1/k resolution, over mask. Returns log depth up to a constant per piece."""
    H, W = mask.shape
    m = mask[::k, ::k]
    Nk = N[::k, ::k]
    h, w = m.shape
    v, u = np.mgrid[0:h, 0:w]
    u = u * k
    v = v * k
    r = np.stack([(u - pp[0]) / f, (v - pp[1]) / f, np.ones_like(u, float)], -1)
    nr = (Nk * r).sum(-1)
    nr = np.minimum(nr, -0.15)  # facing the camera; near the outline he turns away
    p = -Nk[..., 0] / (f * nr) * k  # per (coarse) pixel step
    q = -Nk[..., 1] / (f * nr) * k
    idx = -np.ones((h, w), int)
    idx[m] = np.arange(m.sum())
    rows, cols, vals, rhs = [], [], [], []
    e = 0
    for (dy, dx, g) in ((0, 1, p), (1, 0, q)):
        a = m[:h - dy, :w - dx] & m[dy:, dx:]
        i0 = idx[:h - dy, :w - dx][a]
        i1 = idx[dy:, dx:][a]
        gg = 0.5 * (g[:h - dy, :w - dx][a] + g[dy:, dx:][a])
        n_ = len(i0)
        rows += [np.arange(e, e + n_)] * 2
        cols += [i1, i0]
        vals += [np.ones(n_), -np.ones(n_)]
        rhs.append(gg)
        e += n_
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(e, m.sum()))
    b = np.concatenate(rhs)
    M = (A.T @ A + 1e-8 * sp.eye(m.sum())).tocsc()
    z = spsolve(M, A.T @ b)
    out = np.full((h, w), np.nan)
    out[m] = z
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("out")
    ap.add_argument("--step", type=float, default=0.0005)
    ap.add_argument("--k", type=int, default=2, help="integrate at 1/k of the photo's resolution")
    a = ap.parse_args()
    md, out = Path(a.model), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    f, pp, Rc, pos, pose = master_intrinsics()
    Np = np.load(ROOT / f"checkpoints/cp5/maps/{VIEW}/normals.npy").astype(float)
    Ncam = Np * np.array([1, -1, -1])  # photo frame -> camera frame
    noears = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{VIEW}.noears.png").convert("L")) > 127
    H, W = noears.shape
    omega = nd.binary_erosion(noears, iterations=2)
    # the model's front and back depth through the master camera
    V, F = load_obj(md / "head.obj")
    Vp = posed(V, pose)
    proj, _, _ = camera(VIEW)
    (_,), zf = splat(Vp, F, [np.zeros(len(Vp), np.int8)], proj, H, W)

    def proj_far(P):
        uv, z = proj(P)
        return uv, -z
    (_,), zb = splat(Vp, F, [np.zeros(len(Vp), np.int8)], proj_far, H, W)
    zb = -zb
    # 1. his front from the normals
    k = a.k
    lz = integrate(Ncam, omega, f, pp, k)
    lzf = np.full_like(lz, np.nan)
    zf_k = zf[::k, ::k]
    lab, nlab = nd.label(np.isfinite(lz))
    for c in range(1, nlab + 1):  # one scale per connected piece, from the model
        mm = lab == c
        both = mm & np.isfinite(zf_k)
        if both.sum() < 200:
            continue
        off = np.median(np.log(zf_k[both]) - lz[both])
        lzf[mm] = lz[mm] + off
    zs_k = np.exp(lzf)
    zs = np.asarray(Image.fromarray(np.nan_to_num(zs_k, nan=0).astype(np.float32)).resize((W, H), Image.BILINEAR))
    valid = np.asarray(Image.fromarray(np.isfinite(zs_k).astype(np.uint8) * 255).resize((W, H), Image.NEAREST)) > 0
    valid &= omega
    zs = np.where(valid, zs, np.nan)
    np.save(out / "shell_depth.npy", zs.astype(np.float32))
    # the model's back, carried over where he reaches further out than it does
    have = np.isfinite(zb)
    _, (iy, ix) = nd.distance_transform_edt(~have, return_indices=True)
    zback = zb[iy, ix]
    zback = np.maximum(zback, np.nan_to_num(zs, nan=0) + 0.004)
    d = np.nanmedian(zs[valid & np.isfinite(zf)] - zf[valid & np.isfinite(zf)])
    print(f"his front vs the model's front (master camera): median {d*1000:+.2f} mm "
          f"(+ = he is further back); he covers {valid.sum()} px, the model {np.isfinite(zf).sum()} px", flush=True)
    # 2. the block of cubes
    lo = V.min(0) - 0.012
    hi = V.max(0) + 0.012
    axes = [np.arange(lo[i], hi[i], a.step) for i in range(3)]
    shape = tuple(len(x) for x in axes)
    vol = np.zeros(shape, bool)
    X, Y = np.meshgrid(axes[0], axes[1], indexing="ij")
    for iz, zz in enumerate(axes[2]):
        P = np.c_[X.ravel(), Y.ravel(), np.full(X.size, zz)]
        uv, z = proj(posed(P, pose))
        px = np.round(uv).astype(int)
        ok = (px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < H)
        pi = np.where(ok, px[:, 1], 0), np.where(ok, px[:, 0], 0)
        s_ = zs[pi]
        inside = ok & valid[pi] & (z >= s_) & (z <= zback[pi])
        vol[:, :, iz] = inside.reshape(X.shape)
    print("cubes", shape, "him", int(vol.sum()), flush=True)
    vol = nd.binary_fill_holes(vol)
    lab3, n3 = nd.label(vol)
    if n3 > 1:
        sizes = nd.sum(vol, lab3, range(1, n3 + 1))
        vol = lab3 == 1 + int(np.argmax(sizes))
    # 3. surface
    fv = nd.gaussian_filter(vol.astype(np.float32), 0.8)
    Vn, Fn, _, _ = measure.marching_cubes(np.pad(fv, 2), 0.5, spacing=(a.step,) * 3)
    Vn += lo - 2 * a.step
    Fn = Fn[:, ::-1]
    # front points placed exactly on his front surface (no cube steps): each
    # surface point the master sees, close to his surface, is moved along
    # its master ray to his depth there (bilinear), and the move taken back
    # to his head at rest
    from scipy.ndimage import map_coordinates
    from sculpt import head_weight
    Vq = posed(Vn, pose)
    uvq, zq = proj(Vq)
    zs0 = np.nan_to_num(zs, nan=0.0)
    zss = map_coordinates(zs0, [uvq[:, 1], uvq[:, 0]], order=1, mode="constant", cval=0.0)
    vv = map_coordinates(valid.astype(float), [uvq[:, 1], uvq[:, 0]], order=1, mode="constant", cval=0.0)
    (_,), zfront = splat(Vq, Fn, [np.zeros(len(Vq), np.int8)], proj, H, W)
    pxq = np.clip(np.round(uvq).astype(int), 0, [W - 1, H - 1])
    seen = np.abs(zq - zfront[pxq[:, 1], pxq[:, 0]]) < 2 * a.step
    snap = seen & (vv > 0.99) & (zss > 0) & (np.abs(zss - zq) < 3 * a.step)
    delta = (Vq - pos) * (zss / np.maximum(zq, 1e-9) - 1)[:, None]
    delta[~snap] = 0
    hw = head_weight(Vn)[:, None]
    Rh = R.from_rotvec(pose["rotvec"]).as_matrix() if pose else np.eye(3)
    Vn = Vn + hw * (delta @ Rh) + (1 - hw) * delta
    print(f"front points placed on his surface: {snap.sum()} (moves up to {np.abs(delta).max()*1000:.2f} mm)", flush=True)
    Ve, Fe = load_obj(md / "ears.obj") if (md / "ears.obj").exists() else (np.zeros((0, 3)), np.zeros((0, 3), int))
    C.write_obj(out / "head.obj", np.vstack([Vn, Ve]), np.vstack([Fn, Fe + len(Vn)]))
    for e in md.glob("eye_*.obj"):
        shutil.copy(e, out / e.name)
    if (md / "ears.obj").exists():
        shutil.copy(md / "ears.obj", out / "ears.obj")
    print("surface", len(Vn), "points", flush=True)
    # review: photo | his front shaded | the model's front shaded (same light from upper left)
    L = np.array([-0.4, -0.5, -0.77])
    L /= np.linalg.norm(L)

    def shade_depth(z):
        zz = np.where(np.isfinite(z), z, np.nan)
        gy, gx = np.gradient(zz)
        v_, u_ = np.mgrid[0:H, 0:W]
        Pc = np.stack([(u_ - pp[0]) / f * zz, (v_ - pp[1]) / f * zz, zz], -1)
        du = np.gradient(Pc, axis=1)
        dv = np.gradient(Pc, axis=0)
        n = np.cross(du, dv)
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
        s = np.clip(-(n @ L), 0, 1) * 0.85 + 0.15
        im = (np.nan_to_num(s, nan=1) * 255).astype(np.uint8)
        return Image.fromarray(im)
    (_,), zf2 = splat(posed(Vn, pose), Fn, [np.zeros(len(Vn), np.int8)], proj, H, W)
    tiles = [Image.open(ROOT / "references/master/master_front_standing.webp").convert("RGB"),
             shade_depth(zs).convert("RGB"), shade_depth(zf).convert("RGB"), shade_depth(zf2).convert("RGB")]
    T = 520
    sheet = Image.new("RGB", (4 * (T + 6), T), "white")
    for i, t in enumerate(tiles):
        t.thumbnail((T, T))
        sheet.paste(t, (i * (T + 6), 0))
    sheet.save(out / "shell.jpg", quality=88)


if __name__ == "__main__":
    main()
