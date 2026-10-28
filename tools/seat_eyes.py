"""Seat his eyes in the carved head (tasks/02 F1, docs/CARVING.md 15).

His eyes (checkpoints/cp4/eyes.json: the fitted eyes, un-posed, symmetric)
lie under the carved surface: outlines cannot show the hollow round each
eye. Around each eye the head surface is lowered along the eye's axis:
- inside the lid opening (half-angle psi from the axis) to just under the
  eyeball, so the eye shows as in his photos;
- the lid rim at the opening's edge, h_lid = r cos(psi) in front of the
  eye's centre;
- outside it, the surface rises from the lid rim at `slope` back into his
  face; nothing is ever moved outward.
The lowering is relaxed a little so the socket has no hard edge.

usage: python tools/seat_eyes.py BODY_DIR OUT_DIR [--slope 0.6] [--psi 74]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
import refine_rim as RR  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402


def sphere(c, r, n1=32, n2=64):
    a, b = np.meshgrid(np.linspace(0, np.pi, n1), np.linspace(0, 2 * np.pi, n2), indexing="ij")
    P = np.stack([np.sin(a) * np.cos(b), np.sin(a) * np.sin(b), np.cos(a)], -1).reshape(-1, 3) * r + c
    F = []
    for i in range(n1 - 1):
        for j in range(n2 - 1):
            p, q, s, t = i * n2 + j, i * n2 + j + 1, (i + 1) * n2 + j, (i + 1) * n2 + j + 1
            F += [(p, s, q), (q, s, t)]
    return P, np.array(F)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("body")
    ap.add_argument("out")
    ap.add_argument("--slope", type=float, default=0.6)
    ap.add_argument("--psi", type=float, default=0.0, help="lid opening half-angle (deg); 0 = fitted")
    ap.add_argument("--under", type=float, default=0.0004, help="surface this far under the eyeball (m)")
    ap.add_argument("--relax", type=int, default=6)
    a = ap.parse_args()
    E = json.loads((C.ROOT / "checkpoints/cp4/eyes.json").read_text())
    psi = np.radians(a.psi or E["opening_deg"])
    V, F = load_obj(Path(a.body) / "head.obj")
    total = np.zeros(len(V))
    for s in ("R", "L"):
        c, ax, r = np.asarray(E[s]["centre"]), np.asarray(E[s]["axis"]), E[s]["radius"]
        ax = ax / np.linalg.norm(ax)
        q = V - c
        h = q @ ax
        rho = np.linalg.norm(q - h[:, None] * ax, axis=1)
        ro, hl = r * np.sin(psi), r * np.cos(psi)
        inside = np.sqrt(np.maximum(r * r - rho * rho, 0)) - a.under
        target = np.where(rho < ro, np.maximum(inside, hl - a.under), hl + a.slope * (rho - ro))
        d = np.where(h > -0.3 * r, np.maximum(h - target, 0), 0)
        V = V - d[:, None] * ax
        total = np.maximum(total, d)
    if a.relax:
        L = RR.laplacian(F, len(V))
        deg = L.diagonal()
        Avg = sp.diags(1 / deg) @ (sp.diags(deg) - L)
        m = (total > 1e-5).astype(float)
        m = np.clip(Avg @ (Avg @ m) * 3, 0, 1)  # the socket and a rim round it
        for _ in range(a.relax):
            V = V + 0.5 * m[:, None] * (Avg @ V - V)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", V, F)
    for s in ("R", "L"):
        P, Fe = sphere(np.asarray(E[s]["centre"]), E[s]["radius"])
        C.write_obj(out / f"eye_{s}.obj", P, Fe)
    print(f"eyes seated: up to {total.max()*1000:.1f} mm lowered, {int((total>1e-4).sum())} vertices")


if __name__ == "__main__":
    main()
