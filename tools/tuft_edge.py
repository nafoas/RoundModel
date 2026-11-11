"""Pixel-precise lower edge of the underfluff tuft between Prince's peets,
spike tips included (guide #1: tufts are FLUFF, tips included; the tuft is a
sensitive area, METHOD 3).

The edge is the 50% fur-coverage level at the photo's own resolution (no blur),
long strands removed first, smoothed only enough to remove pixel stair-steps,
between the bottom ends of the two owner-approved peet dividers.
Writes data/lines/tuft_edge_precise.json; tools/body_outline.py splices it in.

Usage: python tools/tuft_edge.py
Pixel convention: pixel (col, row) covers [col, col+1) x [row, row+1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402
import ear_edges as ee  # noqa: E402
import intermediate_fur as itf  # noqa: E402

OUT = Path("data/lines/tuft_edge_precise.json")


def short_stretch(c: np.ndarray, start, end) -> np.ndarray:
    t = cKDTree(c)
    i, j = t.query(start)[1], t.query(end)[1]
    n = len(c)
    fwd = c[[(i + k) % n for k in range((j - i) % n + 1)]]
    bwd = c[[(i - k) % n for k in range((i - j) % n + 1)]]
    return fwd if len(fwd) < len(bwd) else bwd


def main() -> int:
    rgb = np.asarray(Image.open("data/photos/anchor_front.webp").convert("RGB"))
    a = bo.coverage(rgb)
    body = np.array(json.loads(Path("data/strands/body_outline.json").read_text())["sampled_curve"])
    div = json.loads(Path("data/strands/peet_dividers.json").read_text())
    start = np.array(div["cream_peet_image_left__tuft"][-1])
    end = np.array(div["tuft__gray_peet_image_right"][-1])
    strands = itf.long_strands(a, body)
    c = ee.precise_contour(a, strands)
    s = short_stretch(c, start, end)
    raw = s.copy()
    s, bridged = ee.bridge_stubs(s, strands)
    s = ee.smooth(s)
    d = cKDTree(s).query(raw)[0]
    gaps = [round(float(cKDTree(c).query(p)[0]), 3) for p in (start, end)]
    res = {"about": "Pixel-precise lower edge of the underfluff tuft (spike tips included), between the "
                    "bottom ends of the approved peet dividers. Spliced into the body outline by "
                    "tools/body_outline.py.",
           "photo": "data/photos/anchor_front.webp",
           "status": "self-checked, awaiting owner review",
           "divider_ends_to_precise_edge_px": gaps,
           "whisker_roots_bridged": bridged,
           "distance_to_raw_edge_px": {"median": round(float(np.median(d)), 3), "max": round(float(d.max()), 3)},
           "curve": [[round(float(x), 3), round(float(y), 3)] for x, y in s]}
    OUT.write_text(json.dumps(res, indent=1))
    print("divider ends to the precise edge (px):", gaps)
    print("distance to raw edge:", res["distance_to_raw_edge_px"], "| bridged:", bridged)
    print("from", s[0].round(1), "to", s[-1].round(1), "| lowest point y", s[:, 1].max().round(1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
