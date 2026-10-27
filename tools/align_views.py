"""Scale his photos to each other (owner: "he is as long as he is in the top
down, and as long as he is in the profiles, you're just not accounting for
distance of the photos").

Each photo was taken from its own distance, and the fitted cameras do not
agree exactly on how far away he was, so the photos seem to disagree about
his size. Here every photo except the master (the anchor, never changed)
gets a scale, a shift and a small roll in its own image plane. They are
solved together, round by round:
  1. carve him from all photos with the current scales (gentle carving);
  2. for each photo, find the scale, shift and roll that best lay the
     carved shape's outline onto his outline in that photo;
  3. move each photo half way there (so no one photo runs off), repeat.
The result is written to checkpoints/cp4/view_align.json, which carve.py,
refine_rim.py and silhouette_check.py all use.

usage: python tools/align_views.py [--rounds 5]
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

ANCHOR = "master_front_standing"


def silhouette(V, F, cam, shape):
    uv = C.project(C.posed(V, cam["pose"]), cam)
    M = np.zeros(shape, np.uint8)
    cv2.fillPoly(M, list(np.round(uv[F] * 4).astype(np.int32)), 1, shift=2)
    return cv2.morphologyEx(M, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)


def best_fit(Mmodel, H):
    """Scale s, roll, shift t that move the model's outline onto his (IoU)."""
    k = 360 / max(H.shape)
    small = lambda m: cv2.resize(m.astype(np.uint8), None, fx=k, fy=k, interpolation=cv2.INTER_AREA).astype(np.float32)
    A, B = small(Mmodel), small(H)
    ys, xs = np.nonzero(A > 0.5)
    c = np.array([xs.mean(), ys.mean()])

    def warp(p):
        s, th, tx, ty = p
        th = np.radians(th)
        M = np.array([[s * np.cos(th), -s * np.sin(th), 0], [s * np.sin(th), s * np.cos(th), 0]])
        M[:, 2] = c - M[:, :2] @ c + [tx, ty]
        return cv2.warpAffine(A, M, (B.shape[1], B.shape[0]), flags=cv2.INTER_LINEAR)

    def cost(p):
        W = warp(p)
        return -(np.minimum(W, B).sum() / np.maximum(W, B).sum())

    yb, xb = np.nonzero(B > 0.5)
    p0 = [np.sqrt(B.sum() / A.sum()), 0.0, xb.mean() - c[0], yb.mean() - c[1]]
    r = minimize(cost, p0, method="Powell", options={"xtol": 1e-3, "ftol": 1e-5})
    s, th, tx, ty = r.x
    return dict(s=float(s), roll_deg=float(th), t=[float(tx / k), float(ty / k)], c=[float(c[0] / k), float(c[1] / k)]), -r.fun


def compose(old, new):
    """Apply `new` (found in the already-aligned image) after `old`."""
    if not old:
        return new
    # both are similarity maps about their own centres: compose as matrices
    def mat(a):
        th = np.radians(a["roll_deg"])
        Rm = a["s"] * np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        c = np.asarray(a["c"])
        return Rm, c - Rm @ c + np.asarray(a["t"])
    R1, t1 = mat(old)
    R2, t2 = mat(new)
    Rn, tn = R2 @ R1, R2 @ t1 + t2
    s = float(np.sqrt(abs(np.linalg.det(Rn))))
    th = float(np.degrees(np.arctan2(Rn[1, 0], Rn[0, 0])))
    c = np.asarray(old["c"])
    t = tn - (c - Rn @ c)
    return dict(s=s, roll_deg=th, t=[float(t[0]), float(t[1])], c=[float(c[0]), float(c[1])])


def damp(a, f=0.5):
    return dict(s=1 + f * (a["s"] - 1), roll_deg=f * a["roll_deg"], t=[f * a["t"][0], f * a["t"][1]], c=a["c"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=5)
    a = ap.parse_args()
    out = C.ROOT / "checkpoints/cp4/view_align.json"
    align = {}
    for r in range(a.rounds):
        C.ALIGN = align
        vol, axes, _ = C.carve_votes(0.002, hard=1.5, votes=2)
        V, F = C.mesh(vol, axes, 0.002, smooth_iters=6)
        line = []
        for name in C.VIEWS:
            if name == ANCHOR:
                continue
            cam, H = C.view_data(name)
            M = silhouette(V, F, cam, H.shape)
            fit, iou = best_fit(M, H)
            # the fit maps the model onto him; the photo's correction is the inverse
            th = -fit["roll_deg"]
            inv = dict(s=1 / fit["s"], roll_deg=th, t=[0, 0], c=fit["c"])
            Rm = inv["s"] * np.array([[np.cos(np.radians(th)), -np.sin(np.radians(th))],
                                      [np.sin(np.radians(th)), np.cos(np.radians(th))]])
            inv["t"] = (-(Rm @ np.asarray(fit["t"]))).tolist()
            align[name] = compose(align.get(name), damp(inv))
            line.append(f"{name.replace('sheet_', '')[:14]} s{align[name]['s']:.3f} iou{iou:.3f}")
        print(f"round {r}: " + " | ".join(line), flush=True)
        out.write_text(json.dumps(align, indent=1))
    print("written", out)


if __name__ == "__main__":
    main()
