"""The underfluff tuft's fuzz: the faint, see-through haze of hair tips hanging
below the tuft's spike tips (owner, 2026-11-11: "it is simply his little fuzz,
part of the tuft ... it shouldn't be forgotten" when building him).

It is NOT added to the tuft's solid shape (that would make the tuft look bigger
and blockier); it's stored as the tuft's fuzz band: the region between the
tuft's lower edge and an outer line where the haze ends, between the peet
dividers. When he's built, the fuzz is rendered as soft, semi-transparent hair
tips; its opacity is the photo's fur coverage there.

Outer line: per column, how far below the tuft edge the fur coverage (long
strands removed, lightly averaged across columns) stays >= HAZE, smoothed into
a sub-pixel spline (no stair-steps). Writes data/strands/tuft_fuzz.json.
Usage: python tools/tuft_fuzz.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import UnivariateSpline
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402
import intermediate_fur as itf  # noqa: E402

HAZE = 0.10           # coverage at which the haze is considered to have ended
ACROSS_SIGMA = 2.0    # px, averaging across columns
SMOOTH_RMS = 1.0      # px, spline smoothing of the outer line
TAPER = 10.0          # px: the band closes smoothly to zero width at each divider end
OUT = Path("data/strands/tuft_fuzz.json")


def outer_line(a: np.ndarray, edge: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    xs = np.arange(int(np.ceil(edge[0, 0])), int(np.floor(edge[-1, 0])) + 1)
    aa = ndi.gaussian_filter1d(a, ACROSS_SIGMA, axis=1)
    ey, hy = [], []
    for x in xs:
        m = np.abs(edge[:, 0] - (x + 0.5)) < 0.6
        e = edge[m, 1].max() if m.any() else float(np.interp(x + 0.5, edge[:, 0], edge[:, 1]))
        col = aa[int(e):int(e) + 40, x]
        k = int(np.argmax(col < HAZE)) if (col < HAZE).any() else len(col)
        ey.append(e); hy.append(max(float(int(e) + k), e))
    xs = xs + 0.5
    ey, hy = np.array(ey), np.array(hy)
    u = np.clip(np.minimum(xs - edge[0, 0], edge[-1, 0] - xs) / TAPER, 0, 1)
    ramp = u * u * (3 - 2 * u)
    hy = ey + (hy - ey) * ramp
    pts_x = np.r_[edge[0, 0], xs, edge[-1, 0]]
    pts_y = np.r_[edge[0, 1], hy, edge[-1, 1]]
    w = np.r_[50.0, np.ones(len(xs)), 50.0]
    sp = UnivariateSpline(pts_x, pts_y, w=w, s=len(pts_x) * SMOOTH_RMS**2)
    fx = np.linspace(edge[0, 0], edge[-1, 0], 800)
    line = np.c_[fx, sp(fx)]
    line[0], line[-1] = edge[0], edge[-1]
    return line, xs, hy - ey


def main() -> int:
    rgb = np.asarray(Image.open("data/photos/anchor_front.webp").convert("RGB"))
    a = bo.coverage(rgb)
    body = np.array(json.loads(Path("data/strands/body_outline.json").read_text())["sampled_curve"])
    a = np.where(itf.long_strands(a, body), 0.0, a)
    edge = np.array(json.loads(Path("data/lines/tuft_edge_precise.json").read_text())["curve"])
    line, xs, depth = outer_line(a, edge)
    top = min(edge[:, 1].min(), line[:, 1].min()) - 30
    region = Polygon(np.vstack([line, [[line[-1, 0], top], [line[0, 0], top]]])).buffer(0)
    fuzz = region.difference(Polygon(body).buffer(0))
    if fuzz.geom_type == "MultiPolygon":
        parts = [g for g in fuzz.geoms if g.area > 0.5]
    else:
        parts = [fuzz]
    res = {"about": "The underfluff tuft's fuzz (owner 2026-11-11): faint see-through hair tips below the "
                    "tuft's spikes. Part of the tuft; not added to its solid shape. Include it when building "
                    "him, as soft semi-transparent tips whose opacity is the photo's fur coverage.",
           "belongs_to": "underfluff_tuft",
           "photo": "data/photos/anchor_front.webp",
           "status": "self-checked, awaiting owner review",
           "params": {"haze_coverage": HAZE, "across_sigma_px": ACROSS_SIGMA, "smooth_rms_px": SMOOTH_RMS,
                      "taper_px": TAPER},
           "depth_below_spike_edge_px": {"median": round(float(np.median(depth)), 2), "max": round(float(depth.max()), 2)},
           "area_px": round(sum(p.area for p in parts), 2),
           "outer_line": [[round(float(x), 3), round(float(y), 3)] for x, y in line],
           "regions": [[[round(x, 3), round(y, 3)] for x, y in p.exterior.coords] for p in parts]}
    OUT.write_text(json.dumps(res, indent=1))
    print("fuzz depth below the spike edge:", res["depth_below_spike_edge_px"], "| area", res["area_px"],
          "px² in", len(parts), "pieces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
