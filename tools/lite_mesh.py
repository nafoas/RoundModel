"""A lighter copy of the model for camera solving (tools/solve_cams.py):
vertices merged on a 2 mm grid, collapsed triangles dropped.

usage: python tools/lite_mesh.py MODEL_DIR OUT_DIR [--grid 0.002]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--grid", type=float, default=0.002)
    a = ap.parse_args()
    V, F = load_obj(Path(a.inp) / "head.obj")
    key = np.round(V / a.grid).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    Vn = np.zeros((len(idx), 3))
    np.add.at(Vn, inv, V)
    Vn /= np.bincount(inv)[:, None]
    Fn = inv[F]
    Fn = Fn[(Fn[:, 0] != Fn[:, 1]) & (Fn[:, 1] != Fn[:, 2]) & (Fn[:, 0] != Fn[:, 2])]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", Vn, Fn)
    print(len(Vn), "vertices", len(Fn), "faces")


if __name__ == "__main__":
    main()
