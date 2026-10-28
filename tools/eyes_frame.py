"""His eyes in his frame from the master (step B): moved with his head at
rest (checkpoints/cp4/head_poses_frame/delta.json), then made mirror images
across the frame plane (the right eye and the mirrored left averaged).

usage: python tools/eyes_frame.py  (rewrites checkpoints/cp4/eyes.json; the
previous one is kept as eyes.before_frame.json)
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = ROOT / "checkpoints/cp4/eyes.json"
    E = json.loads(p.read_text())
    keep = ROOT / "checkpoints/cp4/eyes.before_frame.json"
    if not keep.exists():
        keep.write_text(json.dumps(E, indent=1))
    else:
        E = json.loads(keep.read_text())
    fr = json.loads((ROOT / "checkpoints/cp4/frame.json").read_text())
    n = np.array([np.cos(fr["turn_rad"]), np.sin(fr["turn_rad"]), 0.0])
    o = np.array([fr["x_m"], 0, 0])
    mp = lambda q: q - 2 * ((q - o) @ n) * n
    mv = lambda v: v - 2 * (v @ n) * n
    dl = np.asarray(json.loads((ROOT / "checkpoints/cp4/head_poses_frame/delta.json").read_text())["delta_m"])
    cR, aR = np.asarray(E["R"]["centre"]) + dl, np.asarray(E["R"]["axis"])
    cL, aL = np.asarray(E["L"]["centre"]) + dl, np.asarray(E["L"]["axis"])
    c = (cR + mp(cL)) / 2
    a = aR + mv(aL)
    a /= np.linalg.norm(a)
    E["R"].update(centre=c.tolist(), axis=a.tolist())
    E["L"].update(centre=mp(c).tolist(), axis=mv(a).tolist())
    E["note"] += "; then made mirror images across his frame from the master (tools/eyes_frame.py, checkpoints/cp4/frame.json)"
    p.write_text(json.dumps(E, indent=1))
    for s in "RL":
        print(s, np.round(np.asarray(E[s]["centre"]) * 1000, 1))


if __name__ == "__main__":
    main()
