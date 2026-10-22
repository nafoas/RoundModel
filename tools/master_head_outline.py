"""His head's outline in the master without the ears: above the ear bases
the outline is replaced by a smooth crown, two curves leaving each side of
the head along its own direction and meeting level at the dip between the
ears (548, 272). Output: checkpoints/cp3/master_head_outline.png"""
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
Y0, TOP = 400, np.array([548.0, 272.0])


def main():
    m = np.asarray(Image.open(ROOT / "checkpoints/cp1/masks/master_front_standing.outline.png")) > 0
    ms = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 7) > 0.5

    def edge(y, side):
        xs = np.nonzero(ms[y])[0]
        return xs.min() if side < 0 else xs.max()

    pts = []
    for side in (-1, 1):
        p0 = np.array([edge(Y0, side), Y0], float)
        p1 = np.array([edge(Y0 + 30, side), Y0 + 30], float)
        tang = (p0 - p1) / np.linalg.norm(p0 - p1)
        L = np.linalg.norm(TOP - p0)
        P0, P1 = p0, p0 + tang * L * 0.45
        P2, P3 = TOP + np.array([side * abs(TOP[0] - p0[0]) * 0.55, 0]), TOP
        t = np.linspace(0, 1, 200)[:, None]
        B = (1 - t) ** 3 * P0 + 3 * (1 - t) ** 2 * t * P1 + 3 * (1 - t) * t ** 2 * P2 + t ** 3 * P3
        pts.append(B if side < 0 else B[::-1])
    curve = np.vstack(pts)
    out = ms.copy()
    out[:Y0] = False
    poly = np.vstack([curve, [[curve[-1][0], Y0 + 2], [curve[0][0], Y0 + 2]]]).astype(np.int32)
    c = np.zeros_like(out, np.uint8)
    cv2.fillPoly(c, [poly], 1)
    out |= c > 0
    Image.fromarray((out * 255).astype(np.uint8)).save(ROOT / "checkpoints/cp3/master_head_outline.png")


if __name__ == "__main__":
    main()
