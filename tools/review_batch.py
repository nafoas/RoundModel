"""Review sheets + measured fidelity check for a batch of outline tiles.

Usage: python tools/review_batch.py <batch_name> <first_tile> <last_tile>
  e.g. python tools/review_batch.py batch2 T021 T040

Writes docs/images/<batch_name>_outline_<n>.png (tiles at 4x with their
surroundings, outline in blue, tile in orange) and prints per-tile fidelity:

  cut    = solid body pixels (strand-free coverage >= 0.9) whose centres are
           OUTSIDE the outline by more than CUT_TOL px  -> the line cuts into him
  bulge  = pure-background pixels whose centres are INSIDE the outline by more
           than BULGE_TOL px                           -> the line swells into air
  smooth = the outline is smoother than the raw edge in this tile

Pixel convention: pixel (col, row) covers [col, col+1) x [row, row+1).
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

CUT_TOL = 1.0     # px
BULGE_TOL = 3.0   # px
SOLID = 0.9
CONTEXT, ZOOM, PER_SHEET = 110, 4, 10


def fidelity(tiles, curve, rgb, a_free):
    path, tree = MPath(curve), cKDTree(curve)
    mn = rgb.min(axis=2)
    out = {}
    for t in tiles:
        x0, y0, x1, y1 = t["x0"], t["y0"], t["x1"], t["y1"]
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        pts = np.c_[X.ravel(), Y.ravel()]
        inside = path.contains_points(pts).reshape(X.shape)
        dist = tree.query(pts)[0].reshape(X.shape)
        solid = a_free[y0:y1, x0:x1] >= SOLID
        bg = mn[y0:y1, x0:x1] >= bo.et.WHITE
        cut = solid & ~inside & (dist > CUT_TOL)
        bulge = bg & inside & (dist > BULGE_TOL)
        out[t["id"]] = {"cut_px": int(cut.sum()), "cut_max_px": round(float(dist[cut].max()), 2) if cut.any() else 0.0,
                        "bulge_px": int(bulge.sum()), "bulge_max_px": round(float(dist[bulge].max()), 2) if bulge.any() else 0.0}
    return out


def peet_line_check(curve):
    line = np.array(json.loads(Path("data/lines/peet_line.json").read_text())["sampled_curve"])
    inside = MPath(curve).contains_points(line)
    d = cKDTree(curve).query(line)[0]
    bad = (~inside) & (d > 1.0)
    return {"points": int(len(line)), "outside_by_more_than_1px": int(bad.sum()),
            "max_outside_px": round(float(d[~inside].max()), 2) if (~inside).any() else 0.0}


def sheets(name, tiles, curve, im):
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
                         (t["y1"] - y0) * ZOOM - 1], outline=(255, 90, 0), width=1)
            pts = [((x - x0) * ZOOM, (y - y0) * ZOOM) for x, y in curve]
            d.line(pts + [pts[0]], fill=(0, 170, 255), width=2)
            d.rectangle([0, 0, 52, 16], fill=(255, 255, 255)); d.text((4, 3), t["id"], fill=(0, 0, 0))
            r, col = divmod(i, 5)
            sheet.paste(c, (8 + col * (P + 8), 8 + r * (P + 8)))
        f = Path(f"docs/images/{name}_outline_{k // PER_SHEET + 1}.png")
        sheet.save(f); files.append(str(f))
    return files


def main(argv):
    name, first, last = argv[1], argv[2], argv[3]
    led = json.loads(Path("data/strands/ledger.json").read_text())
    ids = [t["id"] for t in led["tiles"]]
    tiles = led["tiles"][ids.index(first): ids.index(last) + 1]
    outline = json.loads(Path("data/strands/body_outline.json").read_text())
    curve = np.array(outline["sampled_curve"])
    im = Image.open("data/photos/anchor_front.webp").convert("RGB")
    rgb = np.asarray(im)
    a_free = bo.without_strands(bo.coverage(rgb))
    fid = fidelity(tiles, curve, rgb, a_free)
    rough = set(outline.get("tiles_where_not_smoother_than_raw", []))
    for t in tiles:
        f = fid[t["id"]]
        f["smoother_than_raw"] = t["id"] not in rough
        print(f'{t["id"]}: cut {f["cut_px"]} (max {f["cut_max_px"]} px)  bulge {f["bulge_px"]} '
              f'(max {f["bulge_max_px"]} px)  smoother {f["smoother_than_raw"]}')
    print("eye marks:", outline["eye_marks_check"])
    print("peet line:", peet_line_check(curve))
    print("sheets:", sheets(name, tiles, curve, im))
    Path(f"data/strands/fidelity_{name}.json").write_text(json.dumps(fid, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
