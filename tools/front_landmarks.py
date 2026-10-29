"""His landmarks on the new front (tasks/03 step 2): the master's 2D
landmarks (eyes, nose tip, mouth split, front peets) placed on the front's
surface along their master rays. writes checkpoints/cp6/landmarks3d.json
(world frame = him as in the master).

usage: python tools/front_landmarks.py FRONT_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from master_shell import master_intrinsics  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    fd = Path(sys.argv[1])
    z = np.load(fd / "depth.npy")
    f, pp, Rc, pos, _ = master_intrinsics()
    L2 = json.loads((ROOT / "references/landmarks.json").read_text())["views"]["master_front_standing"]["points"]
    out = {}
    for k in ("eye_R", "eye_L", "nose_tip", "mouth_split", "peet_FR", "peet_FL"):
        u, v = L2[k]
        r = 6
        patch = z[int(v) - r:int(v) + r + 1, int(u) - r:int(u) + r + 1]
        zz = float(np.nanmedian(patch))
        if not np.isfinite(zz):  # a peet at the outline: nearest front depth
            ys, xs = np.nonzero(np.isfinite(z))
            i = np.argmin((xs - u) ** 2 + (ys - v) ** 2)
            zz, u, v = float(z[ys[i], xs[i]]), float(xs[i]), float(ys[i])
        ray = np.array([(u - pp[0]) / f, (v - pp[1]) / f, 1.0])
        out[k] = (pos + (ray * zz) @ Rc).tolist()
    (ROOT / "checkpoints/cp6").mkdir(exist_ok=True)
    (ROOT / "checkpoints/cp6/landmarks3d.json").write_text(json.dumps(
        {"note": "his landmarks on the new front (tools/front_landmarks.py): the master's 2D landmarks along their rays onto the front; world = him as in the master", **out}, indent=1))
    for k, p in out.items():
        print(k, np.round(np.asarray(p) * 1000, 1))


if __name__ == "__main__":
    main()
