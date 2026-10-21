"""Side view of the sculpt: vertical slices through the head (y forward, z up)
at the midline and through each eye, before and after, with the measured
eyes and nose. usage: profile_plot.py VERTS.npy OUT.png"""
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
    V0 = np.load(ROOT / "work/sc/verts0.npy")
    dj = json.loads((ROOT / "checkpoints/cp3/face_depth.json").read_text())
    eR, nose = np.array(dj["eye_R_m"]), np.array(dj["nose_tip_m"])
    fig, ax = plt.subplots(figsize=(6, 6))
    for x, c, lab in ((0.0, "#2a78d6", "midline"), (eR[0], "#eb6834", "through right eye"),
                      (eR[0] / 2, "#1baf7a", "halfway")):
        for VV, al, suf in ((V0, 0.25, " (start)"), (V, 1.0, "")):
            s = VV[(np.abs(VV[:, 0] - x) < 0.0015) & (VV[:, 1] > 0)]
            ax.plot(s[:, 1] * 100, s[:, 2] * 100, ".", ms=2, color=c, alpha=al, label=lab + suf)
    ax.plot([eR[1] * 100], [eR[2] * 100], "ko", label="right eye (measured)")
    ax.plot([nose[1] * 100], [nose[2] * 100], "k^", label="nose tip")
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc="lower left")
    ax.set_xlabel("y cm (+ forward)")
    ax.set_ylabel("z cm (up)")
    ax.set_xlim(0, 12)
    ax.set_ylim(4, 18)
    fig.savefig(out, dpi=100)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
