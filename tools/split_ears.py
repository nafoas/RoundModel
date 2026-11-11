"""Split Prince's two ears off his head along the owner-approved ear base lines.

Inputs:  data/strands/body_outline.json (closed outline; the top of the head is
         the pixel-precise stretch from tools/ear_edges.py)
         data/strands/ear_bases.json    (approved base line per ear)
Output:  data/strands/parts_ears.json   (closed sub-pixel polygon per ear)

Usage: python tools/split_ears.py
Pixel convention: pixel (col, row) covers [col, col+1) x [row, row+1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import split_peets as sp  # noqa: E402


def build(body: np.ndarray, bases: dict) -> dict:
    poly = Polygon(body).buffer(0)
    out = {}
    for name, line in bases.items():
        pieces = sp.split_once(poly, np.asarray(line, float))
        out[name] = min(pieces, key=lambda g: g.centroid.y)     # the piece above the base line
    return out


def main() -> int:
    body = np.array(json.loads(Path("data/strands/body_outline.json").read_text())["sampled_curve"])
    eb = json.loads(Path("data/strands/ear_bases.json").read_text())
    bases = {"ear_image_left": eb["ear_image_left_base"], "ear_image_right": eb["ear_image_right_base"]}
    ears = build(body, bases)
    overlap = ears["ear_image_left"].intersection(ears["ear_image_right"]).area
    res = {"about": "Prince's ears as their own parts (closed polygons, photo pixels), cut from the body "
                    "outline along the owner-approved base lines. Edges are pixel-precise "
                    "(tools/ear_edges.py); lashes and eyebrow whiskers are separate layers.",
           "photo": "data/photos/anchor_front.webp",
           "status": eb.get("status", ""),
           "checks": {"overlap_px": round(overlap, 4)},
           "parts": {k: {"area_px": round(v.area, 2),
                         "exterior": [[round(x, 3), round(y, 3)] for x, y in v.exterior.coords]}
                     for k, v in ears.items()}}
    Path("data/strands/parts_ears.json").write_text(json.dumps(res, indent=1))
    for k, v in ears.items():
        print(k, "area", round(v.area, 1), "bounds", tuple(round(b, 1) for b in v.bounds))
    return 0 if overlap < 1e-6 else 1


if __name__ == "__main__":
    sys.exit(main())
