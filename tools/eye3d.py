"""His eyes in 3D, from hand traces in every photo at once.

Each eye: an eyeball (centre, radius) and the opening the fur leaves on it,
a closed curve on the ball: angle psi(phi) from the eye's axis, around the
axis (phi from 'up'), as a short Fourier series. What shows of the eye in a
photo is that cap, as seen from the photo's camera (front-facing part only),
inside his outline in that photo. Each photo has its own head pose (he holds
his head differently each time), fitted at the same time, held close to the
pose found from his outline; the master has none.

All traces are fitted together; the master counts double. Output:
checkpoints/cp3/eyes3d.json, and an overlay sheet.

usage: eye3d.py [ITERS] [OUT.png]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from sculpt import NECK_PIVOT  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEIGHT = {"master_front_standing": 2.0}
PART_W = {("sheet_02_front_3q", "eye_R"): 0.5, ("sheet_08_front_3q_left", "eye_R"): 0.5}
NF = 2  # Fourier terms of the opening


def cameras():
    m = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]["master_front_standing"]
    cams = {"master_front_standing": dict(image=m["image"], R=R.from_rotvec(m["rotvec_world_to_cam"]).as_matrix(),
                                          pos=np.array(m["camera_position_m"]), f=m["focal_px"],
                                          c=np.array(m["size"]) / 2)}
    for vn, v in json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"].items():
        cams[vn] = dict(image=v["image"], R=R.from_rotvec(v["rotvec_world_to_cam"]).as_matrix(),
                        pos=np.array(v["camera_position_m"]), f=v["focal_px"], c=np.array(v["principal_px"]))
    return cams


def eye_params(x, side):
    """x: per-eye vector [cx, cy, cz, r, yaw, pitch, roll, psi0, a1, b1, a2, b2]"""
    c = x[:3]
    r = x[3]
    s = 1 if side == "R" else -1
    yaw, pitch, roll = np.radians(x[4:7])
    ax = np.array([s * np.sin(yaw) * np.cos(pitch), np.cos(yaw) * np.cos(pitch), np.sin(pitch)])
    up = np.array([0, 0, 1.0]) - ax * ax[2]
    up /= np.linalg.norm(up)
    sd = np.cross(ax, up)
    # roll turns the opening about the axis
    up, sd = np.cos(roll) * up + np.sin(roll) * sd, -np.sin(roll) * up + np.cos(roll) * sd
    return c, r, ax, up, sd, x[7:]


def psi(phi, f):
    out = np.full_like(phi, np.radians(f[0]))
    for k in range(NF):
        out += np.radians(f[1 + 2 * k]) * np.cos((k + 1) * phi) + np.radians(f[2 + 2 * k]) * np.sin((k + 1) * phi)
    return np.clip(out, np.radians(10), np.radians(120))


def cap_mesh(x, side, nt=14, nphi=48):
    c, r, ax, up, sd, f = eye_params(x, side)
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    ps = psi(phi, f)
    t = np.linspace(0, 1, nt)[:, None] * ps[None, :]
    d = (np.cos(t)[..., None] * ax + np.sin(t)[..., None] * (np.cos(phi)[None, :, None] * up
                                                              + np.sin(phi)[None, :, None] * sd))
    P = c + r * d.reshape(-1, 3)
    N = d.reshape(-1, 3)
    tris = []
    for i in range(nt - 1):
        for j in range(nphi):
            a, b = i * nphi + j, i * nphi + (j + 1) % nphi
            cc, dd = a + nphi, b + nphi
            tris += [(a, cc, b), (b, cc, dd)]
    return P, N, np.array(tris)


def pose_apply(X, q):
    if q is None:
        return X
    Rm = R.from_rotvec(q[:3]).as_matrix()
    return (X - NECK_PIVOT) @ Rm.T + NECK_PIVOT + q[3:]


def visible_mask(x, side, cam, q, shape, box):
    P, N, T = cap_mesh(x, side)
    Pw = pose_apply(P, q)
    Nw = N if q is None else N @ R.from_rotvec(q[:3]).as_matrix().T
    Xc = (Pw - cam["pos"]) @ cam["R"].T
    uv = cam["f"] * Xc[:, :2] / Xc[:, 2:3] + cam["c"]
    front = np.einsum("ij,ij->i", Nw, cam["pos"] - Pw) > 0
    x0, y0, x1, y1 = box
    m = np.zeros((y1 - y0, x1 - x0), np.uint8)
    keep = front[T].all(1)
    if keep.any():
        cv2.fillPoly(m, list(np.round(uv[T[keep]] - [x0, y0]).astype(np.int32)), 1)
    return m


def main(iters=3000, out=None):
    cams = cameras()
    traces = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
    poses = json.loads((ROOT / "checkpoints/cp3/head_poses.json").read_text())
    log = json.loads((ROOT / "sculpt/head_log.json").read_text())
    jobs = []
    views = []
    for vn, parts in traces.items():
        if not isinstance(parts, dict):
            continue
        cam = cams[vn]
        stem = Path(cam["image"]).stem
        mp = ROOT / f"checkpoints/cp3/orig_masks/{stem}.mask.png"
        outline = (np.asarray(Image.open(mp)) > 0) if mp.exists() else None
        if vn != "master_front_standing":
            views.append(vn)
        for part, poly in parts.items():
            if not part.startswith("eye_"):
                continue
            poly = np.array(poly, np.int32)
            x, y, w, h = cv2.boundingRect(poly)
            m = max(w, h)
            box = (x - m, y - m, x + w + m, y + h + m)
            tm = np.zeros((box[3] - box[1], box[2] - box[0]), np.uint8)
            cv2.fillPoly(tm, [poly - [box[0], box[1]]], 1)
            om = None if outline is None else outline[box[1]:box[3], box[0]:box[2]].astype(np.uint8)
            jobs.append(dict(view=vn, side=part[-1], box=box, trace=tm, outline=om,
                             w=WEIGHT.get(vn, 1.0) * PART_W.get((vn, part), 1.0)))
    # start: current sculpt eyes, opening ~ current socket
    x0 = []
    for s in ("R", "L"):
        st = [e for e in log["steps"] if e["op"] == "eye" and e["side"] == s][0]
        ax = np.asarray(st["axis"]) / np.linalg.norm(st["axis"])
        yaw = np.degrees(np.arctan2(abs(ax[0]), ax[1]))
        pitch = np.degrees(np.arcsin(ax[2]))
        x0.append(np.r_[st["centre"], st["radius"], yaw, pitch, 0.0, 60.0, 0, 0, 0, 0])
    q0 = {v: (np.r_[poses[v]["rotvec"], poses[v]["shift_m"]] if v in poses else np.zeros(6)) for v in views}
    scale = np.r_[[0.001] * 3, 0.0005, 3, 3, 5, 5, 3, 3, 3, 3]

    def unpack(z):
        e = {s: x0[i] + z[i * 12:(i + 1) * 12] * scale for i, s in enumerate(("R", "L"))}
        q = {}
        for k, v in enumerate(views):
            dz = z[24 + 6 * k:30 + 6 * k]
            q[v] = q0[v] + np.r_[dz[:3] * 0.02, dz[3:] * 0.002]
        return e, q

    def cost(z, detail=False):
        e, q = unpack(z)
        tot, W, det = 0.0, 0.0, {}
        for j in jobs:
            m = visible_mask(e[j["side"]], j["side"], cams[j["view"]], q.get(j["view"]), j["trace"].shape, j["box"])
            if j["outline"] is not None:
                m &= j["outline"]
            iou = (m & j["trace"]).sum() / max(1, (m | j["trace"]).sum())
            tot += j["w"] * (1 - iou)
            W += j["w"]
            det[f"{j['view']}:eye_{j['side']}"] = iou
        c = tot / W
        # priors: poses stay near the outline poses; eyes near mirror images
        c += 0.002 * np.sum(z[24:] ** 2)
        mR, mL = e["R"], e["L"]
        c += 0.02 * (np.sum(((mR[:3] - mL[:3] * [-1, 1, 1]) / 0.004) ** 2) + ((mR[3] - mL[3]) / 0.001) ** 2) / 4
        c += 0.0005 * np.sum(z[:24] ** 2)
        return (c, det, e, q) if detail else c

    z = np.zeros(24 + 6 * len(views))
    c0, d0, _, _ = cost(z, True)
    print(f"start {c0:.4f} " + " ".join(f"{k.split(':')[0][6:14]}:{k[-1]} {v * 100:.0f}" for k, v in d0.items()), flush=True)
    for rnd in range(3):
        r = minimize(cost, z, method="Powell", options={"maxfev": iters, "xtol": 1e-3, "ftol": 1e-6})
        z = r.x
        c1, d1, e, q = cost(z, True)
        print(f"round {rnd}: {c1:.4f} " + " ".join(f"{k.split(':')[0][6:14]}:{k[-1]} {v * 100:.0f}" for k, v in d1.items()),
              flush=True)
    res = {"note": "eyes fitted to the hand traces in every photo at once (eye3d.py): centre, radius (m), facing yaw/pitch/roll (deg), and the lid opening psi(phi) = psi0 + a1 cos + b1 sin + a2 cos2 + b2 sin2 (deg) around the axis from 'up'",
           "eyes": {s: {"centre": e[s][:3].tolist(), "radius": float(e[s][3]), "yaw": float(e[s][4]),
                        "pitch": float(e[s][5]), "roll": float(e[s][6]), "opening": e[s][7:].tolist()} for s in e},
           "poses": {v: {"rotvec": q[v][:3].tolist(), "shift_m": q[v][3:].tolist()} for v in q},
           "overlap": d1}
    (ROOT / "checkpoints/cp3/eyes3d.json").write_text(json.dumps(res, indent=1))
    if out:
        tiles = []
        for j in jobs:
            cam = cams[j["view"]]
            m = visible_mask(e[j["side"]], j["side"], cam, q.get(j["view"]), j["trace"].shape, j["box"])
            if j["outline"] is not None:
                m &= j["outline"]
            ph = np.asarray(Image.open(ROOT / cam["image"]).convert("RGB"))[j["box"][1]:j["box"][3], j["box"][0]:j["box"][2]].copy()
            for mm, col in ((j["trace"], (235, 0, 60)), (m, (0, 110, 255))):
                cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(ph, cs, -1, col, 1)
            tiles.append(Image.fromarray(ph).resize((240, round(240 * ph.shape[0] / ph.shape[1]))))
        H = max(t.height for t in tiles)
        o = Image.new("RGB", (250 * len(tiles), H), (255, 255, 255))
        for i, t in enumerate(tiles):
            o.paste(t, (250 * i, 0))
        o.save(out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3000, sys.argv[2] if len(sys.argv) > 2 else None)
