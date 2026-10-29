"""Step 1 of tasks/03_from_master_front.md: his front, from the master alone.

His front surface from the master's normal map (checkpoints/cp5/maps/
master_front_standing/normals.npy), over his whole outline (without the ears,
which come from the photos that show them), at full resolution, as a mesh.
Nothing from the old model.

- Perspective normal integration of log depth (master_shell.integrate):
  first at half resolution (solved directly), then refined at full
  resolution from it (conjugate gradients), so the map alone fixes his
  shape.
- Pieces of him the outline joins only thinly (a peet) get their depth level
  from the main piece next to them.
- One free number, his distance (size): his nose tip (master landmark) at
  the master camera's depth for it (checkpoints/cp4/landmarks3d.json), until
  the owner gives his real size.
- Mesh: one point per pixel, back-projected along the master camera's rays;
  two triangles per 2x2 block of his pixels.

writes OUT_DIR/head.obj (the front), depth.npy, and front.jpg (his photo |
the front, lit from the upper left | its depth).

usage: python tools/master_front_mesh.py OUT_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from PIL import Image
from scipy import ndimage as nd
from scipy.sparse.linalg import cg

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from master_shell import integrate, master_intrinsics  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VIEW = "master_front_standing"


def gradients(N, f, pp, H, W):
    v, u = np.mgrid[0:H, 0:W]
    r = np.stack([(u - pp[0]) / f, (v - pp[1]) / f, np.ones((H, W))], -1)
    nr = np.minimum((N * r).sum(-1), -0.15)
    return -N[..., 0] / (f * nr), -N[..., 1] / (f * nr)


def refine_full(lz0, N, mask, f, pp):
    """Full-resolution log depth, starting from the half-resolution one."""
    H, W = mask.shape
    p, q = gradients(N, f, pp, H, W)
    idx = -np.ones((H, W), int)
    idx[mask] = np.arange(mask.sum())
    rows, cols, vals, rhs = [], [], [], []
    e = 0
    for dy, dx, g in ((0, 1, p), (1, 0, q)):
        a = mask[:H - dy, :W - dx] & mask[dy:, dx:]
        i0, i1 = idx[:H - dy, :W - dx][a], idx[dy:, dx:][a]
        gg = 0.5 * (g[:H - dy, :W - dx][a] + g[dy:, dx:][a])
        n = len(i0)
        rows += [np.arange(e, e + n)] * 2
        cols += [i1, i0]
        vals += [np.ones(n), -np.ones(n)]
        rhs.append(gg)
        e += n
    A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(e, mask.sum()))
    b = np.concatenate(rhs)
    M = (A.T @ A + 1e-8 * sp.eye(mask.sum())).tocsr()
    x, info = cg(M, A.T @ b, x0=lz0[mask], rtol=1e-8, maxiter=3000)
    out = np.full((H, W), np.nan)
    out[mask] = x
    return out, info


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    f, pp, Rc, pos, _ = master_intrinsics()
    Np = np.load(ROOT / f"checkpoints/cp5/maps/{VIEW}/normals.npy").astype(float)
    N = Np * np.array([1, -1, -1])  # photo frame -> camera frame (x right, y down, z forward)
    noears = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{VIEW}.noears.png").convert("L")) > 127
    H, W = noears.shape
    mask = nd.binary_erosion(noears, iterations=2)
    lab, n = nd.label(mask)
    sizes = nd.sum(mask, lab, range(1, n + 1))
    print("pieces of his outline:", n, "sizes", sorted(sizes.astype(int))[::-1][:6], flush=True)
    mask = lab > 0
    mask &= np.isin(lab, 1 + np.nonzero(sizes > 500)[0])
    # half resolution, solved directly; then full resolution from it
    lz2 = integrate(N, mask, f, pp, 2)
    up = np.asarray(Image.fromarray(np.nan_to_num(lz2, nan=0).astype(np.float32)).resize((W, H), Image.BILINEAR))
    # pieces: level each to the main one
    lab2, n2 = nd.label(np.isfinite(lz2))
    if n2 > 1:
        s2 = nd.sum(np.isfinite(lz2), lab2, range(1, n2 + 1))
        main = 1 + int(np.argmax(s2))
        for c in range(1, n2 + 1):
            if c == main:
                continue
            ring = nd.binary_dilation(lab2 == c, iterations=4) & (lab2 == main)
            if ring.sum():
                edge = nd.binary_dilation(ring, iterations=4) & (lab2 == c)
                lz2[lab2 == c] += np.median(lz2[ring]) - np.median(lz2[edge])
        up = np.asarray(Image.fromarray(np.nan_to_num(lz2, nan=0).astype(np.float32)).resize((W, H), Image.BILINEAR))
    lz, info = refine_full(up, N, mask, f, pp)
    # his distance: the nose tip at the master camera's depth for it
    L2 = json.loads((ROOT / "references/landmarks.json").read_text())["views"][VIEW]["points"]
    nose_px = np.asarray(L2["nose_tip"], int)
    cam, _ = C.view_data(VIEW)
    L3 = np.asarray(json.loads((ROOT / "checkpoints/cp4/landmarks3d.json").read_text())["nose_tip"])
    from maps_model import posed
    nose3 = posed(L3[None], cam["pose"])[0]
    z_nose = float(((nose3 - pos) @ Rc.T)[2])
    near = np.nanmedian(lz[nose_px[1] - 3:nose_px[1] + 4, nose_px[0] - 3:nose_px[0] + 4])
    z = np.exp(lz - near) * z_nose
    np.save(out / "depth.npy", z.astype(np.float32))
    # mesh
    v, u = np.mgrid[0:H, 0:W]
    ray = np.stack([(u - pp[0]) / f, (v - pp[1]) / f, np.ones((H, W))], -1)
    P = pos + (ray * z[..., None]) @ Rc  # camera -> world
    ok = np.isfinite(z)
    idx = -np.ones((H, W), int)
    idx[ok] = np.arange(ok.sum())
    a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, :-1], idx[1:, 1:]
    q = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
    # keep the winding facing the camera (outward)
    Fm = np.vstack([np.c_[a[q], c[q], b[q]], np.c_[b[q], c[q], d[q]]])
    C.write_obj(out / "head.obj", P[ok], Fm)
    zr = z[ok]
    print(f"front: {ok.sum()} points, {len(Fm)} triangles (cg {info}); depth from his nose "
          f"{(zr.min()-z_nose)*1000:+.1f} to {(zr.max()-z_nose)*1000:+.1f} mm; nose at {z_nose*1000:.0f} mm from the camera", flush=True)
    # review
    Lt = np.array([-0.4, -0.5, -0.77])
    Lt /= np.linalg.norm(Lt)
    du = np.gradient(P, axis=1)
    dv = np.gradient(P, axis=0)
    nn = np.cross(du, dv) @ Rc.T  # camera frame
    nn /= np.maximum(np.linalg.norm(nn, axis=-1, keepdims=True), 1e-12)
    shade = np.where(ok, np.clip(-(nn @ Lt), 0, 1) * 0.85 + 0.15, 1.0)
    dd = np.where(ok, (z - np.nanmin(z)) / (np.nanmax(z) - np.nanmin(z)), 1.0)
    tiles = [Image.open(ROOT / "references/master/master_front_standing.webp").convert("RGB"),
             Image.fromarray((np.nan_to_num(shade, nan=1) * 255).astype(np.uint8)).convert("RGB"),
             Image.fromarray((np.nan_to_num(1 - dd, nan=1) * 255).astype(np.uint8)).convert("RGB")]
    T = 560
    sheet = Image.new("RGB", (3 * (T + 6), T), "white")
    for i, t in enumerate(tiles):
        t.thumbnail((T, T))
        sheet.paste(t, (i * (T + 6), 0))
    sheet.save(out / "front.jpg", quality=88)


if __name__ == "__main__":
    main()
