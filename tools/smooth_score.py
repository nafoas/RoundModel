"""How smooth the fur round the eyes and over the forehead is: the sharpest
bends (umbrella Laplacian, mm) among surface points within `reach` of the eyes'
midpoint, leaving out the lid right at each eye (1.5 mm), as the 95th
percentile and the maximum. Walls, notches and flaps show up here even when
every outline matches.
usage: smooth_score.py SCULPT_DIR"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import sculpt as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def score(d, log=None):
    d = Path(d)
    V = np.load(d / "verts.npy")
    _, F = S.base_mesh()
    rows, cols, deg = S.neighbours(F, len(V))
    A = S.avg_op(rows, cols, deg)
    lap = np.linalg.norm(A @ V - V, axis=1) * 1000
    L = json.loads((Path(log) if log else ROOT / "sculpt/head_log.json").read_text())
    eyes = [x for x in L["steps"] if x["op"] == "eye"]
    cs = [np.asarray(e["centre"]) for e in eyes]
    mid = (cs[0] + cs[1]) / 2
    sel = np.linalg.norm(V - mid, axis=1) < 0.045
    sel &= V[:, 1] > mid[1] - 0.025  # the face side of the head
    for e in eyes:
        sel &= np.linalg.norm(V - np.asarray(e["centre"]), axis=1) > e["radius"] + 0.0015
    return float(np.percentile(lap[sel], 95)), float(lap[sel].max())


if __name__ == "__main__":
    p95, mx = score(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"bend round eyes and forehead: 95th percentile {p95:.3f} mm, sharpest {mx:.3f} mm")
