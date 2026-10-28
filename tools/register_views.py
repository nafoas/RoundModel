"""Fine registration of every photo to the carved shape (owner: "the master
has some past him on one side, and some missing on the other ... you've
somewhat offset the master relative to his actual proportions").

Past him on one side and missing on the other is a shift, not a shape
error: the photo's outline and the model are slightly offset. Each photo,
the master included, gets a small shift in its own image plane and a tiny
roll, never a scale (scaling runs away: the carved shape is always a little
small). Gentle: half the found correction per round, a few rounds, and the
corrections are capped (shift 2 % of his size, roll 3 deg). Composes with
the existing top-down turn and length factor in view_align.json.

usage: python tools/register_views.py [--rounds 3]
"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
import align_views as A  # noqa: E402


def fit_shift(V, F, cam, H):
    k = 400 / max(H.shape)
    Hs = cv2.resize(H.astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA).astype(np.float32)
    base = dict(cam.get("align") or dict(s=1.0, roll_deg=0.0, t=[0.0, 0.0],
                                         c=C.project(np.array([[0, 0, 0.07]]), {**cam, "align": None})[0].tolist()))

    def iou(p):
        a = dict(base)
        a["t"] = [base["t"][0] + p[0], base["t"][1] + p[1]]
        a["roll_deg"] = base["roll_deg"] + p[2]
        M = A.silhouette(V, F, {**cam, "align": a}, H.shape)
        Ms = cv2.resize(M.astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA).astype(np.float32)
        return -np.minimum(Ms, Hs).sum() / np.maximum(Ms, Hs).sum()

    r = minimize(iou, [0.0, 0.0, 0.0], method="Powell", options={"xtol": 0.1, "ftol": 1e-6})
    return base, r.x, -iou([0, 0, 0]), -r.fun


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=3)
    a = ap.parse_args()
    path = C.ROOT / "checkpoints/cp4/view_align.json"
    for rnd in range(a.rounds):
        C.ALIGN = json.loads(path.read_text()) if path.exists() else {}
        vol, axes, _ = C.carve_votes(0.002, hard=1.5, votes=2)
        vol, _ = C.symmetric(vol, axes, 0.002)
        V, F = C.mesh(vol, axes, 0.002, smooth_iters=10)
        align = dict(C.ALIGN)
        for name in C.VIEWS:
            cam, H = C.view_data(name)
            base, (dx, dy, dr), i0, i1 = fit_shift(V, F, cam, H)
            ys, xs = np.nonzero(H)
            cap = 0.02 * max(np.ptp(ys), np.ptp(xs))
            dx, dy = np.clip(dx, -cap, cap) / 2, np.clip(dy, -cap, cap) / 2
            dr = float(np.clip(dr, -3, 3)) / 2
            base["t"] = [base["t"][0] + float(dx), base["t"][1] + float(dy)]
            base["roll_deg"] = base["roll_deg"] + dr
            align[name] = base
            print(f"round {rnd} {name:26s} shift ({dx:+5.1f},{dy:+5.1f}) px roll {dr:+.2f} deg   overlap {i0:.3f} -> {i1:.3f}", flush=True)
        path.write_text(json.dumps(align, indent=1))


if __name__ == "__main__":
    main()
