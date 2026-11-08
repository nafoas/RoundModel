"""Intermediate fur: the band between Prince's body line and the general edge
of his fringe (owner, 2026-11-08: "the little intermediate fur gets its own
colour"). Its inner edge is the body outline; this tool finds the OUTER edge,
where the dense fringe ends and only individual wisps/whiskers carry on.

How: walk outward from the body line along its normal and measure fur
coverage; average it ALONG the edge over a short stretch (so one long hair or a
whisker barely counts, but the dense fringe does); the fringe reaches as far as
that averaged density stays >= DENSITY. That reach is smoothed along the edge,
and the outer line is the boundary of {points within reach of the body}, so it
can't loop or cross the body line.

Below the approved peet line the band belongs to the peets and the underfluff
tuft (their own steps), not to the intermediate fur.

Usage: python tools/intermediate_fur.py   (writes data/strands/intermediate_fur.json)
Pixel convention: pixel (col, row) covers [col, col+1) x [row, row+1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import find_contours

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402

DENSITY = 0.18        # fringe continues while the along-edge averaged coverage is at least this
ALONG_SIGMA = 12.0    # px: averaging along the edge (one hair ~ 2 px wide counts for little)
REACH_SIGMA = 8.0     # px: smoothing of the reach along the edge
MAX_REACH = 45.0      # px
STEP = 0.5            # px
# Long straight strands (whiskers, long wisps) are removed before measuring the
# fringe: where many fan out together they would otherwise look like fringe.
STRAND_RIDGE = 0.05   # ridge-filter threshold
STRAND_MIN_LEN = 35   # px: fringe spikes are ~10-20 px, whiskers/long wisps 40-200 px
STRAND_MIN_REACH = 20 # px: the strand must reach at least this far past the body line
STRAND_DILATE = 2     # px


def long_strands(a: np.ndarray, body: np.ndarray) -> np.ndarray:
    """Mask of long straight strands outside the body (whiskers, long wisps)."""
    from skimage.draw import line as draw_line
    from skimage.filters import sato
    from skimage.transform import probabilistic_hough_line
    h, w = a.shape
    yy, xx = np.mgrid[:h, :w]
    inb = MPath(body).contains_points(np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]).reshape(h, w)
    ridge = sato(a, sigmas=(1, 2), black_ridges=False)
    segs = probabilistic_hough_line((ridge > STRAND_RIDGE) & ~inb, threshold=10,
                                    line_length=STRAND_MIN_LEN, line_gap=3, rng=0)
    tree = cKDTree(body)
    mask = np.zeros((h, w), bool)
    for (x0, y0), (x1, y1) in segs:
        rr, cc = draw_line(y0, x0, y1, x1)
        if tree.query(np.c_[cc + 0.5, rr + 0.5])[0].max() >= STRAND_MIN_REACH:
            mask[rr, cc] = True
    return ndi.binary_dilation(mask, iterations=STRAND_DILATE) & ~inb


def outward_normals(c: np.ndarray) -> np.ndarray:
    d = np.roll(c, -1, axis=0) - np.roll(c, 1, axis=0)
    n = np.c_[d[:, 1], -d[:, 0]]
    n /= np.linalg.norm(n, axis=1)[:, None]
    probe = MPath(c).contains_points((c + 2 * n)[::40])
    return -n if probe.mean() > 0.5 else n


def reach(a: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Per body-line point: how far (px) the dense fringe reaches outward."""
    n = outward_normals(c)
    t = np.arange(0, MAX_REACH + STEP, STEP)
    P = c[:, None, :] + n[:, None, :] * t[None, :, None]           # N x T x 2
    # coverage sampled at those points (pixel centres at +0.5)
    M = ndi.map_coordinates(a, [P[..., 1].ravel() - 0.5, P[..., 0].ravel() - 0.5],
                            order=1, mode="constant").reshape(P.shape[:2])
    sig = ALONG_SIGMA / STEP                                        # spacing of c is 0.5 px
    Ms = ndi.gaussian_filter1d(M, sig, axis=0, mode="wrap")
    below = Ms < DENSITY
    first = np.where(below.any(axis=1), below.argmax(axis=1), len(t) - 1)
    r = t[first]
    return ndi.gaussian_filter1d(r, REACH_SIGMA / STEP, mode="wrap")


def outer_line(c: np.ndarray, r: np.ndarray, shape) -> np.ndarray:
    """Boundary of {p : distance from p to the body line <= reach at the nearest
    body point} together with the body itself."""
    h, w = shape
    xs0, ys0 = np.floor(c.min(0) - MAX_REACH - 4).astype(int)
    xs1, ys1 = np.ceil(c.max(0) + MAX_REACH + 4).astype(int)
    xs0, ys0, xs1, ys1 = max(xs0, 0), max(ys0, 0), min(xs1, w), min(ys1, h)
    ss = 2                                                           # half-pixel grid
    X, Y = np.meshgrid(np.arange(xs0, xs1, 1 / ss) + 0.25, np.arange(ys0, ys1, 1 / ss) + 0.25)
    pts = np.c_[X.ravel(), Y.ravel()]
    dist, idx = cKDTree(c).query(pts)
    inside = MPath(c).contains_points(pts)
    f = np.where(inside, 1.0, r[idx] - dist).reshape(X.shape)
    f = ndi.gaussian_filter(f, 0.5)
    cs = find_contours(f, 0.0)
    cc = max(cs, key=len)
    xy = np.stack([xs0 + cc[:, 1] / ss + 0.25, ys0 + cc[:, 0] / ss + 0.25], axis=1)
    keep = bo.SMOOTH_RMS
    bo.SMOOTH_RMS = 0.5
    try:
        tck, _ = bo.fit_smooth(xy)
    finally:
        bo.SMOOTH_RMS = keep
    out = bo.resample(bo.sample(tck, 8000), 0.5)
    return bo.resample(np.vstack([out, out[:1]]), 0.5)[:-1]


def main() -> int:
    rgb = np.asarray(Image.open("data/photos/anchor_front.webp").convert("RGB"))
    a = bo.coverage(rgb)
    body = np.array(json.loads(Path("data/strands/body_outline.json").read_text())["sampled_curve"])
    strands = long_strands(a, body)
    r = reach(np.where(strands, 0.0, a), body)
    outer = outer_line(body, r, a.shape)
    # checks
    d_out = cKDTree(outer).query(body)[0]
    inside_outer = MPath(outer).contains_points(body)
    above = bo.peet_weight(body) < 0.5
    raw = bo.resample(bo.level_contour(a, 0.0), 1.0)
    res = {
        "about": "Intermediate fur (owner 2026-11-08): band between the body line "
                 "(data/strands/body_outline.json) and this outer line, ABOVE the approved "
                 "peet line. Below the peet line the band belongs to the peets / underfluff.",
        "photo": "data/photos/anchor_front.webp",
        "status": "first pass, self-checked per batch; awaiting owner review",
        "params": {"density": DENSITY, "along_sigma_px": ALONG_SIGMA, "reach_sigma_px": REACH_SIGMA,
                   "max_reach_px": MAX_REACH, "long_strands_removed": {"min_len_px": STRAND_MIN_LEN,
                   "min_reach_px": STRAND_MIN_REACH, "masked_px": int(strands.sum())}},
        "band_width_px_above_peet_line": {"min": round(float(r[above].min()), 2),
                                          "median": round(float(np.median(r[above])), 2),
                                          "max": round(float(r[above].max()), 2)},
        "body_line_points_outside_outer": int((~inside_outer & (d_out > 0.5)).sum()),
        "turning_rad": {"raw_edge": round(float(bo.turning(raw).sum()), 1),
                        "outer_line": round(float(bo.turning(outer).sum()), 1)},
        "outer_sampled_curve": [[round(float(x), 3), round(float(y), 3)] for x, y in outer],
        "reach_per_body_point": [round(float(v), 2) for v in r],
    }
    Path("data/strands/intermediate_fur.json").write_text(json.dumps(res, indent=1))
    print("band width above peet line:", res["band_width_px_above_peet_line"])
    print("body line points outside the outer line:", res["body_line_points_outside_outer"])
    print("turning:", res["turning_rad"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
