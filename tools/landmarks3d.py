"""His landmarks in 3D, from the master (docs/MEASURING.md step A).

The master is the authority: each master landmark (nose tip, mouth split)
is cast from the master camera onto the model (first surface hit), with his
head as he holds it in the master, then taken back to his head at rest.
The front peets the same way (bottom middle of each front peet; the head
pose does not reach them). The eyes come from checkpoints/cp4/eyes.json: the visible eye (what a photo
shows of it) is taken as the point half a radius in front of the eyeball's
centre along its axis. Ears are left out (they move between photos).

usage: python tools/landmarks3d.py MODEL_DIR  -> checkpoints/cp4/landmarks3d.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT  # noqa: E402


def ray_hit(o, d, V, F):
    A, B, Cc = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    e1, e2 = B - A, Cc - A
    p = np.cross(d, e2)
    det = e1 @ np.zeros(3) + np.einsum("ij,ij->i", e1, p)
    ok = np.abs(det) > 1e-14
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = o - A
    u = np.einsum("ij,ij->i", s, p) * inv
    q = np.cross(s, e1)
    v = (q @ d) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
    return o + d * t[hit].min() if hit.any() else None


def main():
    md = Path(sys.argv[1])
    V, F = load_obj(md / "head.obj")
    cam, _ = C.view_data("master_front_standing")
    pose = cam["pose"]
    Rm = R.from_rotvec(pose["rotvec"]).as_matrix()
    sh = np.asarray(pose["shift_m"])
    Vp = C.posed(V, pose)  # his head as in the master
    Rc = R.from_rotvec(cam["rot"]).as_matrix()
    o = np.asarray(cam["pos"])
    L2 = json.loads((C.ROOT / "references/landmarks.json").read_text())["views"]["master_front_standing"]["points"]
    out = {}
    for k in ("nose_tip", "mouth_split", "peet_FR", "peet_FL"):
        uv = np.asarray(L2[k], float)
        a = cam.get("align")
        d = np.r_[(uv - np.asarray(cam["pp"])) / cam["f"], 1.0] @ Rc
        d /= np.linalg.norm(d)
        P = ray_hit(o, d, Vp, F)
        if P is None:  # the ray passes just under/beside him (fur): nearest point of him to it
            q = Vp - o
            P = Vp[np.argmin(np.linalg.norm(q - np.outer(q @ d, d), axis=1))]
        if k.startswith("peet"):
            out[k] = P.tolist()  # the head pose does not reach his peets
        else:
            out[k] = ((P - NECK_PIVOT - sh) @ Rm + NECK_PIVOT).tolist()  # back to rest
    # his peets mirror images across his frame (the model is symmetric there;
    # a ray grazing the fur under one peet lands a little off)
    fr = json.loads((C.ROOT / "checkpoints/cp4/frame.json").read_text())
    n = np.array([np.cos(fr["turn_rad"]), np.sin(fr["turn_rad"]), 0.0])
    mir = lambda q: q - 2 * ((q - [fr["x_m"], 0, 0]) @ n) * n
    pr = (np.asarray(out["peet_FR"]) + mir(np.asarray(out["peet_FL"]))) / 2
    out["peet_FR"], out["peet_FL"] = pr.tolist(), mir(pr).tolist()
    E = json.loads((C.ROOT / "checkpoints/cp4/eyes.json").read_text())
    for s in ("R", "L"):
        c, ax, r = np.asarray(E[s]["centre"]), np.asarray(E[s]["axis"]), E[s]["radius"]
        out["eye_" + s] = (c + ax / np.linalg.norm(ax) * 0.5 * r).tolist()
    (C.ROOT / "checkpoints/cp4/landmarks3d.json").write_text(json.dumps(
        {"note": "his landmarks at rest (tools/landmarks3d.py): nose tip and mouth split cast from the master onto the model; eyes = visible eye, half a radius in front of the eyeball centre", **out}, indent=1))
    for k, v in out.items():
        print(k, np.round(np.asarray(v) * 1000, 1))


if __name__ == "__main__":
    main()
