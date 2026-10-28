"""Round the top of his head (tasks/02 F2, docs/CARVING.md 16).

From above the head top was a flat plateau with steep shoulders (across his
head the top dropped 1.4 mm over the middle 32 mm, then fell away fast); his
head top is one round arc. For each slice across his head (constant y) the
top of the slice (points above z_cut, within his head) is fitted with a
circular arc in least squares, and the surface is eased toward that arc
along its normal: the flat middle comes down a little, the shoulders come up
a little. The ease fades out at the slice ends and the region's edges.
Symmetric about his midline.

usage: python tools/round_crown.py IN_DIR OUT_DIR [--y0 -0.02 --y1 0.07 --zcut 0.14 --amount 0.8]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
import refine_rim as RR  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402


def fit_circle(x, z):
    A = np.c_[2 * x, 2 * z, np.ones_like(x)]
    b = x * x + z * z
    (a, c, k), *_ = np.linalg.lstsq(A, b, rcond=None)
    return a, c, np.sqrt(k + a * a + c * c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--y0", type=float, default=-0.02)
    ap.add_argument("--y1", type=float, default=0.07)
    ap.add_argument("--zcut", type=float, default=0.14)
    ap.add_argument("--amount", type=float, default=0.8)
    ap.add_argument("--xmax", type=float, default=0.032, help="half-width of the crown worked on (m)")
    a = ap.parse_args()
    V, F = load_obj(Path(a.inp) / "head.obj")
    pl = json.loads((C.ROOT / "checkpoints/cp4/midline.json").read_text())
    N = RR.normals(V, F)
    xm = V[:, 0] - pl["x_m"]  # across his head from his midline (turn ignored: 2 deg)
    d = np.zeros(len(V))
    w = np.zeros(len(V))
    step = 0.003
    for y in np.arange(a.y0, a.y1 + 1e-9, step):
        sel = (np.abs(V[:, 1] - y) < step) & (V[:, 2] > a.zcut) & (N[:, 2] > 0.2) & (np.abs(xm) < a.xmax + 0.006)
        if sel.sum() < 30:
            continue
        x, z = xm[sel], V[sel, 2]
        fit = np.abs(x) < a.xmax
        cx, cz, r = fit_circle(np.r_[x[fit], -x[fit]], np.r_[z[fit], z[fit]])  # symmetric fit
        dz = np.hypot(x - 0, z - cz) - r  # + outside the arc
        idx = np.nonzero(sel)[0]
        # fade toward the slice ends (where the top meets the sides)
        fx = np.clip((a.xmax - np.abs(x)) / 0.006, 0, 1)  # full over the shoulders, fades beyond
        fz = np.clip((z - a.zcut) / 0.008, 0, 1)
        fy = np.clip(min(y - a.y0, a.y1 - y) / 0.015, 0, 1)
        ww = fx * fz * fy
        d[idx] += -dz * ww
        w[idx] += 1
    d = np.where(w > 0, d / np.maximum(w, 1), 0) * a.amount
    # symmetric
    nrm = np.array([np.cos(pl["turn_rad"]), np.sin(pl["turn_rad"]), 0.0])
    dd = (V - [pl["x_m"], 0, 0]) @ nrm
    j = cKDTree(V).query(V - 2 * dd[:, None] * nrm)[1]
    d = 0.5 * (d + d[j])
    # gentle: spread a little so it is a smooth reshaping
    import scipy.sparse as sp
    L = RR.laplacian(F, len(V))
    deg = L.diagonal()
    Avg = sp.diags(1 / deg) @ (sp.diags(deg) - L)
    for _ in range(10):
        d = Avg @ d
    radial = (V[:, 2] - 0.10)  # move along the vertical-ish normal
    V2 = V + d[:, None] * N
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    C.write_obj(o / "head.obj", V2, F)
    for e in Path(a.inp).glob("eye_*.obj"):
        (o / e.name).write_bytes(e.read_bytes())
    print(f"crown: up {d.max()*1000:.2f} mm, down {-d.min()*1000:.2f} mm")


if __name__ == "__main__":
    main()
