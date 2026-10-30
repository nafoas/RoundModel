"""Step 2 (tasks/03_from_master_front.md): Prince built along the master's
lines of sight, so the master's edge is the model's edge (owner: "The edge
of the master should BE the edge of the model").

Everything of him lies inside his outline as the master sees it. So for
every master pixel inside his outline his body runs from his front (step 1,
work/m/front/depth.npy, unchanged) back to his back. The back is found by
stepping back along that pixel's line of sight until the other photos agree
he has ended there: a point is outside him if two photos put it outside
their outline of him by more than their tolerance, or one by more than
1.5x (as in tools/fill_from_photos.py; his head turned in each photo as
re-fitted against the new front; loafed photos say nothing about his chest
and peets). His back along that line is where the first run of outside
points starts. The other photos can only decide how far back he goes,
never make him narrower or shorter than the master's outline.

Then the back depth is smoothed lightly and both surfaces are meshed from
the same pixels, meeting at his outline (one surface, no seam).

writes OUT_DIR/head.obj, back_depth.npy, thickness.jpg

usage: python tools/build_along_master.py FRONT_DIR OUT_DIR [--k 3] [--step 0.001]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from fill_from_photos import MASTER, POSES, STANDING, VIEWS, unpose, view_mask  # noqa: E402
from maps_model import camera, posed  # noqa: E402
from master_shell import master_intrinsics  # noqa: E402
from sculpt import head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("front")
    ap.add_argument("out")
    ap.add_argument("--k", type=int, default=3, help="find the back at every k-th pixel")
    ap.add_argument("--step", type=float, default=0.001)
    ap.add_argument("--depth", type=float, default=0.25, help="how far back to look (m)")
    ap.add_argument("--run", type=int, default=3, help="outside points in a row that end him")
    a = ap.parse_args()
    fd, out = Path(a.front), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    zs = np.load(fd / "depth.npy").astype(float)
    H, W = zs.shape
    f, pp, Rc, pos, mpose = master_intrinsics()
    om = np.isfinite(zs)
    k = a.k
    vv, uu = np.mgrid[0:H:k, 0:W:k]
    sel = om[vv, uu]
    us, vs = uu[sel].astype(float), vv[sel].astype(float)
    z0 = zs[vv, uu][sel]
    ray = np.stack([(us - pp[0]) / f, (vs - pp[1]) / f, np.ones_like(us)], -1)
    ts = np.arange(0, a.depth, a.step)
    n, m = len(us), len(ts)
    print(f"lines of sight {n}, steps {m}", flush=True)
    L2m = json.loads((ROOT / "references/landmarks.json").read_text())["views"][MASTER]["points"]
    low_row = vs > L2m["mouth_split"][1] + 30
    votes = np.zeros((n, m), np.int8)
    hard = np.zeros((n, m), bool)
    # world points of every (line, step), done in slabs of steps
    views = []
    for name, tol in VIEWS.items():
        proj, _, pose = camera(name)
        if (POSES / f"{name}.json").exists():
            pose = json.loads((POSES / f"{name}.json").read_text())
        mask, head_only = view_mask(name)
        sd = nd.distance_transform_edt(~mask) - nd.distance_transform_edt(mask)
        views.append((name, tol, proj, pose, sd, head_only))
    for j0 in range(0, m, 20):
        tt = ts[j0:j0 + 20]
        Z = z0[:, None] + tt[None, :]
        Pc = ray[:, None, :] * Z[..., None]
        P = (pos + Pc.reshape(-1, 3) @ Rc)
        Po = unpose(P, mpose)
        hw = head_weight(Po)
        lower = (low_row[:, None] & (tt[None, :] < 0.06)).ravel()
        for name, tol, proj, pose, sd, head_only in views:
            uv, z = proj(posed(Po, pose))
            Hh, Ww = sd.shape
            inf = (uv[:, 0] >= 2) & (uv[:, 0] < Ww - 2) & (uv[:, 1] >= 2) & (uv[:, 1] < Hh - 2) & (z > 0)
            s = map_coordinates(sd, [uv[:, 1], uv[:, 0]], order=1, cval=-1e3)
            o = inf & (s > tol)
            hd = inf & (s > 1.5 * tol)
            if head_only:
                o &= hw > 0.9
                hd &= hw > 0.9
            if name not in STANDING:
                o &= ~lower
                hd &= ~lower
            votes[:, j0:j0 + len(tt)] += o.reshape(n, -1).astype(np.int8)
            hard[:, j0:j0 + len(tt)] |= hd.reshape(n, -1)
    outside = (votes >= 2) | hard
    # first run of `run` outside steps
    run = np.ones_like(outside)
    for r in range(a.run):
        run[:, : m - r] &= outside[:, r:]
        run[:, m - r:] = False
    first = np.where(run.any(1), run.argmax(1), m - 1)
    thick = ts[first]
    print(f"his thickness along the master's lines of sight: median {np.median(thick)*1000:.0f} mm, "
          f"max {thick.max()*1000:.0f} mm; lines that never ended: {(~run.any(1)).sum()}", flush=True)
    # back depth map, smoothed lightly, closed to the front at his outline
    T = np.full(vv.shape, np.nan)
    T[sel] = thick
    Tf = np.nan_to_num(T)
    wgt = nd.gaussian_filter(np.isfinite(T).astype(float), 1.5)
    Ts = nd.gaussian_filter(Tf, 1.5) / np.maximum(wgt, 1e-6)
    Tfull = np.asarray(Image.fromarray(Ts.astype(np.float32)).resize((W, H), Image.BILINEAR))
    edge = om & ~nd.binary_erosion(om)
    Tfull = np.where(om, np.maximum(Tfull, 0.0), np.nan)
    Tfull[edge] = 0.0
    zb = zs + Tfull
    np.save(out / "back_depth.npy", zb.astype(np.float32))
    # mesh: front and back from the same pixels, sharing the outline
    v, u = np.mgrid[0:H, 0:W]
    rr = np.stack([(u - pp[0]) / f, (v - pp[1]) / f, np.ones((H, W))], -1)
    Pf = pos + (rr * zs[..., None]) @ Rc
    Pb = pos + (rr * zb[..., None]) @ Rc
    fi = -np.ones((H, W), int)
    fi[om] = np.arange(om.sum())
    bi = -np.ones((H, W), int)
    inner = om & ~edge
    bi[inner] = om.sum() + np.arange(inner.sum())
    bi[edge] = fi[edge]
    Vall = np.vstack([Pf[om], Pb[inner]])

    def quads(ix, flip):
        a_, b_, c_, d_ = ix[:-1, :-1], ix[:-1, 1:], ix[1:, :-1], ix[1:, 1:]
        q = (a_ >= 0) & (b_ >= 0) & (c_ >= 0) & (d_ >= 0)
        t1 = np.c_[a_[q], c_[q], b_[q]]
        t2 = np.c_[b_[q], c_[q], d_[q]]
        Fq = np.vstack([t1, t2])
        return Fq[:, ::-1] if flip else Fq
    Fall = np.vstack([quads(fi, False), quads(bi, True)])
    C.write_obj(out / "head.obj", Vall, Fall)
    tv = np.where(om, Tfull, np.nan)
    im = (np.nan_to_num(tv / np.nanmax(tv)) * 255).astype(np.uint8)
    im[~om] = 255
    Image.fromarray(im).save(out / "thickness.jpg")
    print(f"surface {len(Vall)} points, {len(Fall)} triangles", flush=True)


if __name__ == "__main__":
    main()
