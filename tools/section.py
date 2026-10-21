"""Quick plot of the sculpt seen from above, as horizontal slices through
the head at eye and nose height, with the measured eyes and nose tip.
usage: section.py VERTS.npy OUT.png"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(vpath, out):
    V = np.load(vpath)
    V0 = np.load(ROOT / "work/sc/verts0.npy") if (ROOT / "work/sc/verts0.npy").exists() else None
    dj = json.loads((ROOT / "checkpoints/cp3/face_depth.json").read_text())
    eR, eL, nose = (np.array(dj[k]) for k in ("eye_R_m", "eye_L_m", "nose_tip_m"))
    fig, ax = plt.subplots(figsize=(6, 6))
    for z, c, lab in (((eR[2] + eL[2]) / 2, "#2a78d6", "eye level"), (nose[2], "#eb6834", "nose level")):
        for VV, alpha, suffix in ((V0, 0.25, " (start)"), (V, 1.0, "")):
            if VV is None:
                continue
            s = VV[np.abs(VV[:, 2] - z) < 0.0015]
            ax.plot(s[:, 0] * 100, s[:, 1] * 100, ".", ms=2, color=c, alpha=alpha, label=lab + suffix)
    ax.plot([eR[0] * 100, eL[0] * 100], [eR[1] * 100, eL[1] * 100], "ko", label="eyes (measured)")
    ax.plot([nose[0] * 100], [nose[1] * 100], "k^", label="nose tip")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="lower center")
    ax.set_xlabel("x cm (+ his right)")
    ax.set_ylabel("y cm (+ forward)")
    ax.set_xlim(8, -8)
    ax.set_ylim(-4, 11)
    fig.savefig(out, dpi=100)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
