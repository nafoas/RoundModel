"""Trace Prince's outline on the reference-sheet panels with a learned
background-removal model (rembg / IS-Net), which copes with the lamp,
the hand, and the saturated pink inside his ears far better than colour
thresholds. Panels are upscaled 4x before matting; the matte is averaged
back down and thresholded at 50% coverage, the same "dense fur" outline
definition used for the white-background references.
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("U2NET_HOME", str(ROOT / ".cache/u2net"))


def main(outdir, paths):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    session = new_session("isnet-general-use")
    summary = {}
    for p in paths:
        p = Path(p).resolve()
        im = Image.open(p).convert("RGB")
        big = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
        alpha = remove(big, session=session, only_mask=True)
        a = np.asarray(alpha.resize(im.size, Image.BOX)).astype(np.float32) / 255
        m = a > 0.5
        # drop whisker spikes thinner than ~3 px
        m = cv2.morphologyEx(m.astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) > 0
        n, lab, st, cen = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
        h, w = m.shape
        if n > 1:
            best = max(range(1, n), key=lambda i: st[i, 4] / (1 + np.hypot(cen[i][0] - w / 2, cen[i][1] - h / 2) / 50))
            m = lab == best
        ff = m.astype(np.uint8).copy()
        cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
        m = m | (ff == 0)
        name = "sheet_" + p.stem
        Image.fromarray((m * 255).astype(np.uint8)).save(outdir / f"{name}.outline.png")
        Image.fromarray((a * 255).astype(np.uint8)).save(outdir / f"{name}.matte.png")
        ys, xs = np.nonzero(m)
        summary[name] = {"source": str(p.relative_to(ROOT)),
                         "outline_bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]}
        print(name, summary[name]["outline_bbox"])
    (outdir / "summary_sheet.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
