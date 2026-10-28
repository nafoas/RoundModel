"""Fill hollows that he does not have, adding only (docs/CARVING.md 13).

Carving and the outline passes can only cut, so a crease they leave (the
crease across the back of his head) cannot be carved away. Here the surface
is compared with a heavily smoothed copy of itself; where the smoothed copy
lies OUTSIDE the surface (a hollow), the surface is moved out toward it.
Where it lies inside (anything convex: his round body, cheeks, head) nothing
moves. Limited to a region (a soft-edged box) so real hollows elsewhere (the
eye sockets, under the chin) are kept. Symmetric about his midline.

usage: python tools/fill_hollows.py IN_DIR OUT_DIR --box x0 x1 y0 y1 z0 z1 [--iters 60] [--strength 1.0]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
import refine_rim as RR  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--box", type=float, nargs=6, required=True)
    ap.add_argument("--iters", type=int, default=60)
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--edge", type=float, default=0.012, help="soft edge of the box (m)")
    a = ap.parse_args()
    V, F = load_obj(Path(a.inp) / "head.obj")
    n = len(V)
    L = RR.laplacian(F, n)
    deg = L.diagonal()
    Avg = sp.diags(1 / deg) @ (sp.diags(deg) - L)
    S = V.copy()
    for _ in range(a.iters):
        S = Avg @ S
    N = RR.normals(V, F)
    out = ((S - V) * N).sum(1)  # + where the smooth copy is outside: a hollow
    x0, x1, y0, y1, z0, z1 = a.box
    e = a.edge

    def soft(v, lo, hi):
        return np.clip((v - lo) / e + 1, 0, 1) * np.clip((hi - v) / e + 1, 0, 1)

    w = soft(V[:, 0], x0, x1) * soft(V[:, 1], y0, y1) * soft(V[:, 2], z0, z1)
    d = np.maximum(out, 0) * w * a.strength
    # same on his left and right (his midline from the carving)
    mp = Path(a.inp).parent / "midline.json"
    pl = json.loads((C.ROOT / "checkpoints/cp4/midline.json").read_text())
    nrm = np.array([np.cos(pl["turn_rad"]), np.sin(pl["turn_rad"]), 0.0])
    dd = (V - [pl["x_m"], 0, 0]) @ nrm
    j = cKDTree(V).query(V - 2 * dd[:, None] * nrm)[1]
    d = 0.5 * (d + d[j])
    V2 = V + d[:, None] * N
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    C.write_obj(o / "head.obj", V2, F)
    print(f"filled: {int((d > 1e-4).sum())} vertices moved out, up to {d.max()*1000:.2f} mm, mean of moved {d[d>1e-4].mean()*1000:.2f} mm")


if __name__ == "__main__":
    main()
