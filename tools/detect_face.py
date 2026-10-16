"""Detect Prince's face features in a white-background reference.

  eyes       the darkest blobs in the upper face (eyeball core, below the
             lashes): centroid, plus top/bottom of the dark region
  nose       the pink V: its lowest point (the V's tip) and its two upper
             ends (nostril tops), where visible
  mouth      the darkest point a little below the V's tip (the split)

Every detection is drawn on an overlay so it can be checked by eye.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def detect(path):
    rgb = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    lum = rgb.mean(2)
    h, w = lum.shape
    out = {}
    # eyes: dark cores in the upper 45% of the image
    dark = (lum < 55).astype(np.uint8)
    dark[int(0.45 * h):] = 0
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(dark, 8)
    blobs = sorted([i for i in range(1, n) if st[i, 4] > 150], key=lambda i: -st[i, 4])[:2]
    eyes = []
    for i in blobs:
        ys, xs = np.nonzero(lab == i)
        eyes.append({"centre": [float(xs.mean()), float(ys.mean())], "top": [float(xs[ys.argmin()]), float(ys.min())],
                     "bottom": [float(xs[ys.argmax()]), float(ys.max())], "area": int(st[i, 4]),
                     "box": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]})
    out["eyes_by_x"] = sorted(eyes, key=lambda e: e["centre"][0])
    # nose: pink, in the middle band
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    pink = ((r - g > 14) & (b - g > 0) & (r > 110)).astype(np.uint8)
    pink[: int(0.35 * h)] = 0
    pink[int(0.75 * h):] = 0
    pink = cv2.morphologyEx(pink, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(pink, 8)
    if n > 1:
        i = 1 + int(np.argmax(st[1:, 4]))
        ys, xs = np.nonzero(lab == i)
        tip = [float(xs[ys.argmax()]), float(ys.max())]
        out["nose_tip"] = tip
        top_l = np.argmin(xs + 0.5 * ys)
        top_r = np.argmax(xs - 0.5 * ys)
        out["nostril_ends_by_x"] = [[float(xs[top_l]), float(ys[top_l])], [float(xs[top_r]), float(ys[top_r])]]
        out["nose_box"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        # mouth split: darkest point in a window below the tip
        x0, y0 = int(tip[0]), int(tip[1])
        win = lum[y0 + 15: y0 + 110, max(0, x0 - 40): x0 + 40]
        if win.size:
            yy, xx = np.unravel_index(np.argmin(cv2.GaussianBlur(win, (9, 9), 0)), win.shape)
            out["mouth_split"] = [float(max(0, x0 - 40) + xx), float(y0 + 15 + yy)]
    return out


def overlay(path, det, dst):
    img = cv2.cvtColor(np.asarray(Image.open(path).convert("RGB")), cv2.COLOR_RGB2BGR)
    for e in det["eyes_by_x"]:
        x0, y0, x1, y1 = e["box"]
        cv2.rectangle(img, (x0, y0), (x1, y1), (255, 0, 255), 2)
        cv2.circle(img, tuple(int(v) for v in e["centre"]), 5, (255, 0, 255), -1)
    for k, col in (("nose_tip", (0, 0, 255)), ("mouth_split", (255, 120, 0))):
        if k in det:
            cv2.circle(img, tuple(int(v) for v in det[k]), 6, col, -1)
    for p in det.get("nostril_ends_by_x", []):
        cv2.circle(img, tuple(int(v) for v in p), 6, (0, 160, 0), -1)
    cv2.imwrite(str(dst), img)


if __name__ == "__main__":
    res = {}
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    for p in sys.argv[2:]:
        p = Path(p)
        d = detect(p)
        res[p.stem] = d
        overlay(p, d, outdir / f"{p.stem}.face.png")
    print(json.dumps(res, indent=1))
