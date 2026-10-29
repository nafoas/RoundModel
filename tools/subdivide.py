"""A finer surface (docs/MEASURING.md, "Normals from every side", step 4):
every triangle split into four (edge midpoints), LEVELS times, so points are
about 1.5 mm / 2^LEVELS apart. The shape is not changed; only room is made
for fine form (nose split, creases).

usage: python tools/subdivide.py IN_DIR OUT_DIR [--levels 2]
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402


def split(V, F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), 1)
    uniq, inv = np.unique(E, axis=0, return_inverse=True)
    inv = inv.ravel()
    mid = len(V) + inv.reshape(3, -1).T  # midpoint index of edges (01, 12, 20) per face
    Vn = np.vstack([V, (V[uniq[:, 0]] + V[uniq[:, 1]]) / 2])
    a, b, c = F.T
    ab, bc, ca = mid.T
    Fn = np.vstack([np.c_[a, ab, ca], np.c_[ab, b, bc], np.c_[ca, bc, c], np.c_[ab, bc, ca]])
    return Vn, Fn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--levels", type=int, default=2)
    a = ap.parse_args()
    V, F = load_obj(Path(a.inp) / "head.obj")
    for _ in range(a.levels):
        V, F = split(V, F)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", V, F)
    for e in Path(a.inp).glob("eye_*.obj"):
        shutil.copy(e, out / e.name)
    for m in Path(a.inp).parent.glob(f"{Path(a.inp).name}.midline.json"):
        shutil.copy(m, out.parent / f"{out.name}.midline.json")
    el = np.linalg.norm(V[F[:, 0]] - V[F[:, 1]], axis=1)
    print(len(V), "points,", len(F), "triangles; edge median", round(float(np.median(el)) * 1000, 2), "mm")


if __name__ == "__main__":
    main()
