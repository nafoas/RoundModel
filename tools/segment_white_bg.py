"""Trace Prince's outlines on the white-background (edited) references.

For each image this produces three masks:
  fringe  - everything that is Prince, including the wispy outer hairs (whiskers removed)
  outline - the body outline: where fur is dense enough to read as his surface
  whiskers - thin dark strands outside the outline, kept separately for later

The background in the edited set is pure white, so anything measurably
darker than white and connected to Prince is Prince.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def load_rgb(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def largest_component(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    if n <= 1:
        return mask
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return lab == k


def fill_holes(mask):
    m = mask.astype(np.uint8)
    h, w = m.shape
    ff = m.copy()
    pad = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(ff, pad, (0, 0), 1)
    return (m | (1 - ff)).astype(bool)


def segment(rgb):
    # "darkness" = how far below pure white the darkest channel is
    dark = 255.0 - rgb.min(axis=2)

    # anything visibly not-background
    any_fg = dark > 6

    # whiskers and single wisps are thin; an opening with a disc wider than
    # them removes them while keeping the fluffy body
    k5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    k15 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    k31 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))

    body_seed = largest_component(cv2.morphologyEx(any_fg.astype(np.uint8), cv2.MORPH_OPEN, k15) > 0)
    body_seed = fill_holes(body_seed)

    # fringe: foreground within reach of the body, minus thin strands
    near_body = cv2.dilate(body_seed.astype(np.uint8), k31) > 0
    fringe = any_fg & near_body
    fringe = cv2.morphologyEx(fringe.astype(np.uint8), cv2.MORPH_OPEN, k5) > 0
    fringe = fill_holes(largest_component(fringe | body_seed))

    # outline: dense fur. Use local coverage of foreground: where most
    # pixels in a neighbourhood are fur, the surface reads as solid.
    cov = cv2.blur(any_fg.astype(np.float32), (21, 21))
    outline = (cov > 0.5) & fringe
    outline = cv2.morphologyEx(outline.astype(np.uint8), cv2.MORPH_OPEN, k15) > 0
    outline = fill_holes(largest_component(outline))
    # keep the outline a smooth, single shape
    outline = cv2.morphologyEx(outline.astype(np.uint8), cv2.MORPH_CLOSE, k15) > 0

    whiskers = any_fg & ~cv2.dilate(fringe.astype(np.uint8), k5).astype(bool)
    whiskers = cv2.morphologyEx(whiskers.astype(np.uint8), cv2.MORPH_OPEN,
                                np.ones((1, 1), np.uint8)) > 0
    return fringe, outline, whiskers


def main(paths, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    summary = {}
    for p in paths:
        p = Path(p).resolve()
        rgb = load_rgb(p)
        fringe, outline, whiskers = segment(rgb)
        name = p.stem
        for tag, m in (("fringe", fringe), ("outline", outline), ("whiskers", whiskers)):
            Image.fromarray((m * 255).astype(np.uint8)).save(outdir / f"{name}.{tag}.png")
        ys, xs = np.nonzero(outline)
        summary[name] = {
            "source": str(p.relative_to(ROOT)),
            "size": [int(rgb.shape[1]), int(rgb.shape[0])],
            "outline_bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "outline_area_px": int(outline.sum()),
            "fringe_area_px": int(fringe.sum()),
        }
        print(name, summary[name]["outline_bbox"])
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[2:], sys.argv[1])
