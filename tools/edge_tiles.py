"""Step 1 of docs/STRAND_PLAN.md: tile the edge band of the anchor photo.

Cuts the band around Prince's edge (from just inside where his fur is solid,
out to the last strand tip) into small overlapping square tiles, numbered in
order around him, writes the ledger, and proves every band pixel is in a tile.

Nothing here classifies anything. The rough body outline is used ONLY to find
where the edge band is.

Usage:
    python tools/edge_tiles.py [photo] [out_dir] [overview_png]
Defaults: data/photos/anchor_front.webp, data/strands, docs/images/edge_tiles_overview.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.measure import find_contours
from skimage.morphology import skeletonize

TILE = 64          # tile side, px
STEP = 40          # spacing of tiles along the outline, px (TILE - STEP = overlap)
INNER = 16         # how far inside the rough body outline the band reaches, px
PAD = 3            # background margin kept around every non-white pixel, px
WHITE = 254        # a pixel is "Prince" if its darkest channel is below this


def disk(r: int) -> np.ndarray:
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def largest(mask: np.ndarray) -> np.ndarray:
    lab, n = ndi.label(mask)
    if n == 0:
        return mask
    sizes = ndi.sum(mask, lab, range(1, n + 1))
    return lab == (int(np.argmax(sizes)) + 1)


def foreground(rgb: np.ndarray) -> np.ndarray:
    return rgb.min(axis=2) < WHITE


def rough_body(fg: np.ndarray) -> np.ndarray:
    """Rough solid body, only for locating the edge band. Not a classification."""
    return ndi.binary_fill_holes(largest(ndi.binary_opening(fg, disk(6))))


def edge_band(fg: np.ndarray, body: np.ndarray) -> np.ndarray:
    deep = ndi.binary_erosion(body, disk(INNER))
    near = ndi.binary_dilation(fg & ~deep, disk(PAD))
    return near & ~deep


def place(cx: float, cy: float, shape: tuple[int, int]) -> tuple[int, int, int, int]:
    h, w = shape
    x0 = int(round(cx)) - TILE // 2
    y0 = int(round(cy)) - TILE // 2
    x0 = min(max(x0, 0), w - TILE)
    y0 = min(max(y0, 0), h - TILE)
    return x0, y0, x0 + TILE, y0 + TILE


def outline_walk(body: np.ndarray) -> np.ndarray:
    """Points along the outer outline, starting at the top of his head and going
    toward image-right (his left), evenly spaced by STEP px of arc length."""
    contours = find_contours(body.astype(float), 0.5)
    c = max(contours, key=len)                     # (row, col) points
    xy = np.stack([c[:, 1], c[:, 0]], axis=1)
    start = int(np.argmin(xy[:, 1]))               # top-most point
    xy = np.roll(xy, -start, axis=0)
    # direction: make the walk go toward image-right first
    if xy[min(20, len(xy) - 1), 0] < xy[0, 0]:
        xy = xy[::-1]
        xy = np.roll(xy, 1, axis=0)
    seg = np.hypot(*np.diff(xy, axis=0).T)
    arc = np.concatenate([[0], np.cumsum(seg)])
    targets = np.arange(0, arc[-1], STEP)
    idx = np.searchsorted(arc, targets).clip(0, len(xy) - 1)
    return xy[idx]


def build_tiles(fg: np.ndarray):
    body = rough_body(fg)
    band = edge_band(fg, body)
    shape = fg.shape
    tiles = []
    covered = np.zeros(shape, bool)

    for i, (x, y) in enumerate(outline_walk(body), 1):
        x0, y0, x1, y1 = place(x, y, shape)
        tiles.append({"id": f"T{i:03d}", "kind": "outline", "x0": x0, "y0": y0, "x1": x1, "y1": y1})
        covered[y0:y1, x0:x1] = True

    # Extension tiles for anything the outline ring misses (outer fringe,
    # whiskers reaching far out). Grow outward from what's already covered.
    n_ext = 0
    while True:
        miss = band & ~covered
        if not miss.any():
            break
        dist = ndi.distance_transform_edt(~covered)
        dist[~miss] = np.inf
        y, x = np.unravel_index(int(np.argmin(dist)), shape)
        x0, y0, x1, y1 = place(x, y, shape)
        n_ext += 1
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        near = min((t for t in tiles if t["kind"] == "outline"),
                   key=lambda t: ((t["x0"] + t["x1"]) / 2 - cx) ** 2 + ((t["y0"] + t["y1"]) / 2 - cy) ** 2)
        tiles.append({"id": f"E{n_ext:03d}", "kind": "extension", "near": near["id"],
                      "x0": x0, "y0": y0, "x1": x1, "y1": y1})
        covered[y0:y1, x0:x1] = True
    return body, band, tiles


def uncovered(band: np.ndarray, tiles: list[dict]) -> int:
    cov = np.zeros(band.shape, bool)
    for t in tiles:
        cov[t["y0"]:t["y1"], t["x0"]:t["x1"]] = True
    return int((band & ~cov).sum())


def strand_estimate(fg: np.ndarray, body: np.ndarray) -> dict:
    """Rough count of strand-like pieces outside the rough body (skeleton
    segments between junctions). An ESTIMATE of the job size, not a result:
    overlapping hairs merge, and one hair can break into several pieces."""
    outside = fg & ~body
    sk = skeletonize(outside)
    nb = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    junction = sk & (nb >= 3)
    segs = sk & ~ndi.binary_dilation(junction, np.ones((3, 3), bool))
    lab, n = ndi.label(segs, structure=np.ones((3, 3), int))
    lengths = ndi.sum(segs, lab, range(1, n + 1)) if n else np.array([])
    return {"segments_ge_8px": int((lengths >= 8).sum()),
            "segments_ge_20px": int((lengths >= 20).sum()),
            "segments_ge_40px": int((lengths >= 40).sum())}


def overview(rgb: np.ndarray, tiles: list[dict], path: Path) -> None:
    img = Image.fromarray(rgb)
    d = ImageDraw.Draw(img)
    for t in tiles:
        col = (0, 170, 255) if t["kind"] == "outline" else (255, 140, 0)
        d.rectangle([t["x0"], t["y0"], t["x1"] - 1, t["y1"] - 1], outline=col, width=1)
    for t in tiles:
        n = int(t["id"][1:])
        if t["kind"] == "outline" and (n == 1 or n % 5 == 0):
            d.text((t["x0"] + 2, t["y0"] + 2), t["id"], fill=(0, 0, 160))
    img.save(path)


def main(argv: list[str]) -> int:
    photo = Path(argv[1]) if len(argv) > 1 else Path("data/photos/anchor_front.webp")
    out_dir = Path(argv[2]) if len(argv) > 2 else Path("data/strands")
    over = Path(argv[3]) if len(argv) > 3 else Path("docs/images/edge_tiles_overview.png")
    rgb = np.asarray(Image.open(photo).convert("RGB"))
    fg = foreground(rgb)
    body, band, tiles = build_tiles(fg)
    miss = uncovered(band, tiles)
    est = strand_estimate(fg, body)
    for t in tiles:
        t["status"] = "todo"
    ledger = {
        "about": "Step 1 of docs/STRAND_PLAN.md. Every tile of Prince's edge band, "
                 "in order around him (T = along the outline, starting at the top of "
                 "his head toward image-right = his left; E = extensions for the outer "
                 "fringe and whiskers, with the nearest outline tile). Status flow: "
                 "todo -> annotated -> self-checked -> owner-approved.",
        "photo": str(photo),
        "params": {"tile": TILE, "step": STEP, "inner": INNER, "pad": PAD, "white": WHITE},
        "band_pixels": int(band.sum()),
        "uncovered_band_pixels": miss,
        "strand_estimate": est,
        "tiles": tiles,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ledger.json").write_text(json.dumps(ledger, indent=1))
    over.parent.mkdir(parents=True, exist_ok=True)
    overview(rgb, tiles, over)
    n_out = sum(t["kind"] == "outline" for t in tiles)
    print(f"tiles: {len(tiles)} ({n_out} outline, {len(tiles) - n_out} extension)")
    print(f"band pixels: {int(band.sum())}, uncovered: {miss}")
    print(f"strand estimate: {est}")
    return 0 if miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
