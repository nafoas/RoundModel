"""Pixel-precise outline over the top of Prince's head: both ears, the dip
between them, and down past each ear's base (owner, 2026-11-09: "go pixel by
pixel, including all the little notches, kinks, and the base on the left,
because they're his little ears").

The edge is the 50% level of his fur coverage at the photo's own resolution
(no blur), with long strands (whiskers) removed first, so it follows every
notch and kink. Only two things are changed:
  - whisker roots: where a whisker leaves the ear, the few px of stub left
    after removing the whisker are bridged (whiskers are their own layer; the
    ear continues under them, METHOD 3b);
  - pixel stair-steps: a spline with at most SMOOTH_RMS px RMS deviation.

Writes data/lines/top_of_head_precise.json; tools/body_outline.py splices it in.
Usage: python tools/ear_edges.py
Pixel convention: pixel (col, row) covers [col, col+1) x [row, row+1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import splev, splprep
from scipy.spatial import cKDTree
from skimage.measure import find_contours

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402
import intermediate_fur as itf  # noqa: E402

START = (361.5, 306.0)    # just below the hook at the ear base (image left), where the precise edge meets the old outline (0.2 px)
END = (719.0, 316.5)      # below the ear (image right), where the precise edge meets the old outline (0.1 px)
SMOOTH_RMS = 0.25         # px
STUB_RADIUS = 3.0         # px around a whisker root that is bridged
OUT = Path("data/lines/top_of_head_precise.json")


def precise_contour(a: np.ndarray, strands: np.ndarray) -> np.ndarray:
    a2 = np.where(strands, 0.0, a)
    cs = find_contours(a2, bo.LEVEL)
    c = max(cs, key=len)
    return np.stack([c[:, 1] + 0.5, c[:, 0] + 0.5], axis=1)


def stretch(c: np.ndarray, start, end) -> np.ndarray:
    """The part of closed contour c between the points nearest start and end
    that goes over the top (smaller mean y)."""
    t = cKDTree(c)
    i, j = t.query(start)[1], t.query(end)[1]
    n = len(c)
    fwd = c[[(i + k) % n for k in range((j - i) % n + 1)]]
    bwd = c[[(i - k) % n for k in range((i - j) % n + 1)]]
    return fwd if fwd[:, 1].mean() < bwd[:, 1].mean() else bwd


def bridge_stubs(s: np.ndarray, strands: np.ndarray) -> tuple[np.ndarray, list]:
    """Replace stretches touching a whisker root by a cubic Hermite between the
    clean points on either side."""
    root = ndi.binary_dilation(strands, iterations=int(np.ceil(STUB_RADIUS)))
    r = np.round(s[:, 1] - 0.5).astype(int), np.round(s[:, 0] - 0.5).astype(int)
    bad = root[r]
    spans, i = [], 0
    while i < len(s):
        if bad[i]:
            j = i
            while j + 1 < len(s) and bad[j + 1]:
                j += 1
            spans.append((max(i - 1, 0), min(j + 1, len(s) - 1)))
            i = j + 1
        else:
            i += 1
    out, last = [], 0
    for a, b in spans:
        out.append(s[last:a + 1])
        p0, p1 = s[a], s[b]
        k = 4
        t0 = s[a] - s[max(a - k, 0)]; t1 = s[min(b + k, len(s) - 1)] - s[b]
        L = np.hypot(*(p1 - p0))
        t0 = t0 / (np.hypot(*t0) + 1e-9) * L; t1 = t1 / (np.hypot(*t1) + 1e-9) * L
        t = np.linspace(0, 1, max(int(L * 4), 4))[1:-1, None]
        h = (2 * t**3 - 3 * t**2 + 1) * p0 + (t**3 - 2 * t**2 + t) * t0 + (-2 * t**3 + 3 * t**2) * p1 + (t**3 - t**2) * t1
        out.append(h)
        last = b
    out.append(s[last:])
    return np.vstack(out), [[s[a].round(2).tolist(), s[b].round(2).tolist()] for a, b in spans]


def smooth(s: np.ndarray) -> np.ndarray:
    s = bo.resample(s, 0.5)
    tck, _ = splprep([s[:, 0], s[:, 1]], s=len(s) * SMOOTH_RMS**2)
    x, y = splev(np.linspace(0, 1, len(s) * 2), tck)
    out = bo.resample(np.c_[x, y], 0.25)
    out[0], out[-1] = s[0], s[-1]
    return out


def main() -> int:
    rgb = np.asarray(Image.open("data/photos/anchor_front.webp").convert("RGB"))
    a = bo.coverage(rgb)
    body = np.array(json.loads(Path("data/strands/body_outline.json").read_text())["sampled_curve"])
    strands = itf.long_strands(a, body)
    c = precise_contour(a, strands)
    s = stretch(c, START, END)
    raw = s.copy()
    s, bridged = bridge_stubs(s, strands)
    s = smooth(s)
    d = cKDTree(s).query(raw)[0]
    root = ndi.binary_dilation(strands, iterations=int(np.ceil(STUB_RADIUS)))
    away = ~root[np.round(raw[:, 1] - 0.5).astype(int), np.round(raw[:, 0] - 0.5).astype(int)]
    res = {
        "about": "Pixel-precise outline over the top of his head (both ears, the dip, past each ear's base), "
                 "owner 2026-11-09. Spliced into the body outline by tools/body_outline.py.",
        "photo": "data/photos/anchor_front.webp",
        "status": "self-checked, awaiting owner review",
        "params": {"level": bo.LEVEL, "blur_px": 0, "smooth_rms_px": SMOOTH_RMS, "stub_radius_px": STUB_RADIUS,
                   "start_near": START, "end_near": END},
        "whisker_roots_bridged": bridged,
        "distance_to_raw_edge_px": {"median": round(float(np.median(d[away])), 3),
                                    "max": round(float(d[away].max()), 3)},
        "curve": [[round(float(x), 3), round(float(y), 3)] for x, y in s],
    }
    OUT.write_text(json.dumps(res, indent=1))
    print("whisker roots bridged:", bridged)
    print("distance to the raw photo edge (away from whisker roots):", res["distance_to_raw_edge_px"])
    print("points", len(s), "from", s[0].round(1), "to", s[-1].round(1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
