"""Measure the dark of each eye in a master-camera render against the master.
usage: eye_compare.py RENDER_RGBA.png  (full master resolution)"""
import sys

import cv2
import numpy as np
from PIL import Image

MASTER_BOX = {"R": (316, 429, 361, 505), "L": (677, 400, 721, 485)}


def boxes(lum, win):
    out = {}
    for side, (x0, y0, x1, y1) in win.items():
        pad = 40
        sub = lum[y0 - pad:y1 + pad, x0 - pad:x1 + pad]
        m = (sub < 60).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
        if n < 2:
            out[side] = None
            continue
        i = 1 + int(np.argmax(st[1:, 4]))
        x, y, w, h = st[i, :4]
        out[side] = (x0 - pad + x, y0 - pad + y, x0 - pad + x + w, y0 - pad + y + h)
    return out


def main(path):
    rgba = np.asarray(Image.open(path).convert("RGBA")).astype(np.float32)
    lum = rgba[..., :3].mean(2) * (rgba[..., 3] / 255) + 228 * (1 - rgba[..., 3] / 255)
    got = boxes(lum, MASTER_BOX)
    for s in "RL":
        m, g = MASTER_BOX[s], got[s]
        if g is None:
            print(s, "not visible")
            continue
        print(f"eye {s}: master {m[2]-m[0]}x{m[3]-m[1]} px at ({(m[0]+m[2])/2:.0f},{(m[1]+m[3])/2:.0f}) | "
              f"sculpt {g[2]-g[0]}x{g[3]-g[1]} px at ({(g[0]+g[2])/2:.0f},{(g[1]+g[3])/2:.0f})")


if __name__ == "__main__":
    main(sys.argv[1])
