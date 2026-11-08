"""Review sheets + measured checks for a batch of intermediate-fur tiles.

Usage: python tools/review_fur.py <batch_name> <first_tile> <last_tile>

Sheets: docs/images/<batch>_fur_<n>.png, each tile at 4x with its surroundings:
body line (blue), outer edge of the intermediate fur (orange), approved peet line
(magenta; below it the band belongs to the peets/underfluff, not this class).

Per tile (band above the peet line only):
  width     = band width min / median / max along the body line in the tile (px)
  captured  = share of fur within 30 px outside the body line that lies inside
              the band (the rest is long single hairs: wisps/whiskers)
  smoother  = outer line is smoother than the raw photo edge in this tile
  peet_zone = the tile is entirely below the peet line (not this class)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from PIL import Image, ImageDraw
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402

CONTEXT, ZOOM, PER_SHEET = 110, 4, 10


def itf_reserved_row():
    import intermediate_fur as itf
    return itf.RESERVED_ROW


def checks(tiles, body, outer, reach, a):
    pb, po = MPath(body), MPath(outer)
    tree_b = cKDTree(body)
    raw = bo.resample(bo.level_contour(a, 0.0), 1.0)
    above_body = bo.peet_weight(body) < 0.5
    res = {}
    for t in tiles:
        x0, y0, x1, y1 = t["x0"], t["y0"], t["x1"], t["y1"]
        on = (body[:, 0] >= x0) & (body[:, 0] < x1) & (body[:, 1] >= y0) & (body[:, 1] < y1)
        sel = on & above_body
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        pts = np.c_[X.ravel(), Y.ravel()]
        in_b = pb.contains_points(pts); in_o = po.contains_points(pts)
        d = tree_b.query(pts)[0]
        above = bo.peet_weight(pts) < 0.5
        ring = ~in_b & (d <= 30) & above
        fur = a[y0:y1, x0:x1].ravel()
        tot = fur[ring].sum()
        r = {"peet_zone": bool(on.any() and not sel.any()),
             "reserved_ears_eyes": bool(on.any() and np.mean(body[on, 1] < itf_reserved_row()) > 0.5)}
        if sel.any():
            w = reach[sel]
            r.update({"width_min": round(float(w.min()), 1), "width_median": round(float(np.median(w)), 1),
                      "width_max": round(float(w.max()), 1)})
        r["captured"] = round(float(fur[ring & in_o].sum() / tot), 2) if tot > 1 else None
        r_out, r_raw = bo.roughness_in_box(outer, (x0, y0, x1, y1)), bo.roughness_in_box(raw, (x0, y0, x1, y1))
        r["smoother_than_raw"] = bool(r_out == 0 or r_out < r_raw)
        res[t["id"]] = r
    return res


def sheets(name, tiles, curves, im):
    W, H = im.size
    P = CONTEXT * ZOOM
    files = []
    for k in range(0, len(tiles), PER_SHEET):
        sub = tiles[k:k + PER_SHEET]
        rows = (len(sub) + 4) // 5
        sheet = Image.new("RGB", (5 * P + 6 * 8, rows * P + (rows + 1) * 8), (255, 255, 255))
        for i, t in enumerate(sub):
            cx, cy = (t["x0"] + t["x1"]) // 2, (t["y0"] + t["y1"]) // 2
            x0 = max(0, min(W - CONTEXT, cx - CONTEXT // 2)); y0 = max(0, min(H - CONTEXT, cy - CONTEXT // 2))
            c = im.crop((x0, y0, x0 + CONTEXT, y0 + CONTEXT)).resize((P, P), Image.LANCZOS)
            d = ImageDraw.Draw(c)
            d.rectangle([(t["x0"] - x0) * ZOOM, (t["y0"] - y0) * ZOOM, (t["x1"] - x0) * ZOOM - 1,
                         (t["y1"] - y0) * ZOOM - 1], outline=(255, 210, 160), width=1)
            for curve, col, closed in curves:
                pts = [((x - x0) * ZOOM, (y - y0) * ZOOM) for x, y in curve]
                d.line(pts + ([pts[0]] if closed else []), fill=col, width=2)
            d.rectangle([0, 0, 52, 16], fill=(255, 255, 255)); d.text((4, 3), t["id"], fill=(0, 0, 0))
            r, col = divmod(i, 5)
            sheet.paste(c, (8 + col * (P + 8), 8 + r * (P + 8)))
        f = Path(f"docs/images/{name}_fur_{k // PER_SHEET + 1}.png")
        sheet.save(f); files.append(str(f))
    return files


def main(argv):
    name, first, last = argv[1], argv[2], argv[3]
    led = json.loads(Path("data/strands/ledger.json").read_text())
    ids = [t["id"] for t in led["tiles"]]
    tiles = led["tiles"][ids.index(first): ids.index(last) + 1]
    body = np.array(json.loads(Path("data/strands/body_outline.json").read_text())["sampled_curve"])
    fur = json.loads(Path("data/strands/intermediate_fur.json").read_text())
    outer = np.array(fur["outer_sampled_curve"]); reach = np.array(fur["reach_per_body_point"])
    pl = np.array(json.loads(Path("data/lines/peet_line.json").read_text())["sampled_curve"])
    im = Image.open("data/photos/anchor_front.webp").convert("RGB")
    a = bo.coverage(np.asarray(im))
    res = checks(tiles, body, outer, reach, a)
    for k, v in res.items():
        print(k, v)
    print("sheets:", sheets(name, tiles, [(body, (0, 170, 255), True), (outer, (255, 140, 0), True),
                                         (pl, (200, 0, 200), False)], im))
    Path(f"data/strands/fur_{name}.json").write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
