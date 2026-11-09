"""Split Prince's body below the approved peet line into its three parts:
the cream peet (image left), the underfluff tuft, and the gray peet (image right).

Inputs (all owner-reviewed lines):
  data/strands/body_outline.json   body outline (closed)
  data/lines/peet_line.json        approved peet line (body above, peets/underfluff below)
  data/lines/peet_line_joins.json  short joins from the peet line's ends to the outline notches
  data/strands/peet_dividers.json  the two dividers (cream peet | tuft | gray peet)
Output: data/strands/parts_peets.json (closed sub-pixel polygons per part + checks).

Pixel convention: pixel (col, row) covers [col, col+1) x [row, row+1).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import split, unary_union


def load(path):
    return json.loads(Path(path).read_text())


def _out_dir(poly, end: np.ndarray, v: np.ndarray, d: float):
    """Direction from `end` that leaves `poly` within d px: the end direction v,
    or v rotated a little, whichever exits first."""
    from shapely.geometry import Point
    for deg in (0, 15, -15, 30, -30, 45, -45, 60, -60, 75, -75, 90, -90):
        r = np.radians(deg)
        w = np.array([v[0] * np.cos(r) - v[1] * np.sin(r), v[0] * np.sin(r) + v[1] * np.cos(r)])
        if not poly.buffer(1e-6).contains(Point(*(end + w * d))):
            return w
    raise RuntimeError(f"cannot find a way out of the region at {end}")


def extend(line: np.ndarray, poly, d: float = 3.0) -> np.ndarray:
    """Extend a polyline past both ends so it cleanly crosses the region's edge
    (ends lie on that edge; where a line meets it tangentially, the extension is
    turned slightly until it exits)."""
    k = min(4, len(line) - 1)
    a = line[0] - line[k]; b = line[-1] - line[-1 - k]
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    a = _out_dir(poly, line[0], a, d); b = _out_dir(poly, line[-1], b, d)
    return np.vstack([line[0] + a * d, line, line[-1] + b * d])


def split_once(poly: Polygon, line: np.ndarray):
    parts = split(poly, LineString(extend(line, poly)))
    geoms = sorted(parts.geoms, key=lambda g: -g.area)
    if len(geoms) < 2:
        raise RuntimeError("line did not split the region")
    return geoms


def build(body, peet_line, cream_join, gray_join, cream_div, gray_div):
    body_poly = Polygon(body).buffer(0)
    zone_line = np.vstack([cream_join, peet_line, gray_join[1:]])
    pieces = split_once(body_poly, zone_line)
    # the peet zone is the piece below the peet line (largest mean y)
    zone = max(pieces, key=lambda g: g.centroid.y)
    a, b = split_once(zone, cream_div)[:2]
    cream = min((a, b), key=lambda g: g.centroid.x)
    rest = max((a, b), key=lambda g: g.centroid.x)
    c, d = split_once(rest, gray_div)[:2]
    tuft = min((c, d), key=lambda g: g.centroid.x)
    gray = max((c, d), key=lambda g: g.centroid.x)
    return zone, {"cream_peet_image_left": cream, "underfluff_tuft": tuft, "gray_peet_image_right": gray}


def main() -> int:
    body = np.array(load("data/strands/body_outline.json")["sampled_curve"])
    peet_line = np.array(load("data/lines/peet_line.json")["sampled_curve"])
    joins = load("data/lines/peet_line_joins.json")
    cream_join = np.array(joins["cream_side"]["curve"])
    gray_join = np.array(joins["gray_side"]["curve"])
    div = load("data/strands/peet_dividers.json")
    cream_div = np.array(div["cream_peet_image_left__tuft"])
    gray_div = np.array(div["tuft__gray_peet_image_right"])
    zone, parts = build(body, peet_line, cream_join, gray_join, cream_div, gray_div)
    union = unary_union(list(parts.values()))
    overlap = sum(parts[a].intersection(parts[b]).area for a in parts for b in parts if a < b)
    checks = {"zone_area_px": round(zone.area, 2),
              "sum_of_parts_px": round(sum(p.area for p in parts.values()), 2),
              "gap_px": round(zone.difference(union).area, 4),
              "overlap_px": round(overlap, 4)}
    out = {"about": "Prince's parts below the approved peet line (step 3, peets). Closed polygons in "
                    "photo pixels. Each part is whole (METHOD 3b): the cream peet continues under the "
                    "tuft fur that covers its edge.",
           "photo": "data/photos/anchor_front.webp",
           "status": "self-checked; awaiting owner review (gray-side join is inferred)",
           "checks": checks,
           "parts": {k: {"area_px": round(v.area, 2),
                         "exterior": [[round(x, 3), round(y, 3)] for x, y in v.exterior.coords]}
                     for k, v in parts.items()}}
    Path("data/strands/parts_peets.json").write_text(json.dumps(out, indent=1))
    print(checks)
    for k, v in parts.items():
        print(k, "area", round(v.area, 1), "bounds", tuple(round(b, 1) for b in v.bounds))
    return 0 if checks["gap_px"] < 0.01 and checks["overlap_px"] < 0.01 else 1


if __name__ == "__main__":
    sys.exit(main())
