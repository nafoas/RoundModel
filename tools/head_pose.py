"""Separate pose from shape: his head is not held exactly the same in every
photo. For one full-size sheet original, the sculpt's head alone (blended
into the body below the neck) is turned and shifted rigidly until its outline
and eyes best match the photo. What still disagrees after that is shape.

usage: head_pose.py SCULPT_DIR VIEW OUT.png
prints the head turn found and the agreement before/after; OUT.png shows his
outline (red), the posed sculpt's outline (blue), his eye centres (red +) and
the posed sculpt's eye centres (blue +)."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from refine_side_cameras import load_obj  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
from sculpt import HEAD_C, NECK_PIVOT as PIVOT, head_weight  # noqa: E402
# his eye centres (black of the eye) and the ears to leave out, per original
LANDMARK_W = 0.01
# eyes help fix the pose (a round head turns without changing its outline),
# weakly, with large turns penalised, so a wrong eye still shows in the scores
USE_EYES = True
MARKS = {
    "sheet_03_right_profile": {"eyes": {"R": (814, 465)}, "ears": [(480, 160, 700, 420)]},
    "sheet_07_left_profile": {"eyes": {"L": (370, 410)}, "ears": [(560, 210, 720, 390)]},
    "sheet_09_top_down": {"eyes": {"R": (346, 990), "L": (679, 1004)}, "points": {"nose_v": ((500, 1222), (545, 748))}, "ears": [(380, 600, 700, 820)]},
    # the far eye's centre is hidden behind his outline: only the near eye;
    # "points": photo px -> the same point's master px (on the sculpt)
    "sheet_02_front_3q": {"eyes": {"L": (610, 405)}, "points": {"nose_v": ((383, 690), (545, 748))},
                          "ears": [(400, 150, 520, 220), (600, 130, 740, 300)]},
}


def main(d, view, out):
    d = Path(d)
    V, F = load_obj(d / "head.obj")
    log = json.loads((ROOT / "sculpt/head_log.json").read_text())
    eyes = {}
    for st in log["steps"]:
        if st["op"] == "eye":
            eyes[st["side"]] = np.array(st["centre"])
    if "L" not in eyes:
        eyes["L"] = eyes["R"] * np.array([-1, 1, 1])
    # the part of each eyeball that can show: inside the lid opening (the cap
    # in front of the lid plane). An eye's mark in a photo is the middle of
    # what shows of it, which for a sideways-facing eye is far from its centre.
    caps = {}
    for st in log["steps"]:
        if st["op"] == "eye":
            ax = np.asarray(st["axis"], float)
            ax /= np.linalg.norm(ax)
            sock = [x for x in log["steps"] if x["op"] == "socket"]
            proud = sock[-1]["proud"] if sock else 0.003
            rng = np.random.default_rng(0)
            P = rng.normal(size=(4000, 3))
            P /= np.linalg.norm(P, axis=1, keepdims=True)
            P = P[P @ ax > (st["radius"] - proud) / st["radius"]]
            caps[st["side"]] = (np.asarray(st["centre"]) + P * st["radius"], P)
    if MARKS[view].get("points"):
        from sculpt import Master
        mst = Master()
        for k, (_, mpx) in MARKS[view]["points"].items():
            eyes[k] = mst.hit(V, F, mpx)
    cam = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"][view]
    Rc = R.from_rotvec(cam["rotvec_world_to_cam"]).as_matrix()
    cpos, f = np.array(cam["camera_position_m"]), cam["focal_px"]
    cx, cy = cam["principal_px"]
    photo = np.asarray(Image.open(ROOT / cam["image"]).convert("RGB")).copy()
    h, w = photo.shape[:2]
    m = np.asarray(Image.open(ROOT / "checkpoints/cp3/orig_masks" / f"{Path(cam['image']).stem}.mask.png")) > 0
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 4) > 0.5
    marks = MARKS[view]

    def proj(X):
        Xc = (X - cpos) @ Rc.T
        return np.stack([f * Xc[..., 0] / Xc[..., 2] + cx, f * Xc[..., 1] / Xc[..., 2] + cy], -1), Xc[..., 2]

    # zone: around the head's projection, ears left out
    hc, hz = proj(HEAD_C)
    rad = 0.075 * f / hz
    zone = np.zeros((h, w), bool)
    cv2.circle(zone.view(np.uint8), tuple(int(v) for v in hc), int(rad), 1, -1)
    zone = zone.view(bool)
    for x0, y0, x1, y1 in marks["ears"]:
        zone[y0:y1, x0:x1] = False
    wt = head_weight(V)

    def posed(q):
        Rm = R.from_rotvec(q[:3] * 0.1).as_matrix()
        t = q[3:] * 0.01
        Vh = (V - PIVOT) @ Rm.T + PIVOT + t
        E = {s: (e - PIVOT) @ Rm.T + PIVOT + t for s, e in eyes.items()}
        # visible middle of each eye: cap points facing the camera
        for s_, (P, Nn) in caps.items():
            Pp = (P - PIVOT) @ Rm.T + PIVOT + t
            facing = np.einsum("ij,ij->i", Nn @ Rm.T, cpos - Pp) > 0
            if facing.sum() > 10:
                E["vis_" + s_] = Pp[facing]
        return V + wt[:, None] * (Vh - V), E

    fn0 = None

    def sil(Vp):
        P, z = proj(Vp)
        fn = np.cross(Vp[F[:, 1]] - Vp[F[:, 0]], Vp[F[:, 2]] - Vp[F[:, 0]])
        front = np.einsum("ij,ij->i", fn, cpos - Vp[F[:, 0]]) > 0
        img = np.zeros((h, w), np.uint8)
        cv2.fillPoly(img, list(np.round(P[F[front]]).astype(np.int32)), 1)
        img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        ff = img.copy()
        cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
        return (img | (1 - ff)) > 0

    px_per_mm = f / hz / 1000

    def cost(q, parts=False):
        Vp, E = posed(q)
        s = sil(Vp)
        iou = (s & m & zone).sum() / max(1, ((s | m) & zone).sum())
        errs = []
        for k, v in (marks["eyes"].items() if USE_EYES else []):
            if "vis_" + k in E:
                uvv = proj(E["vis_" + k])[0].mean(0)
            else:
                uvv = proj(E[k])[0]
            errs.append(np.linalg.norm(uvv - np.array(v)) / px_per_mm)
        for k, (px, _) in marks.get("points", {}).items():
            errs.append(np.linalg.norm(proj(E[k])[0] - np.array(px)) / px_per_mm)
        eye_err = np.mean(errs) if errs else 0.0  # mm
        # landmarks (eyes, nose) are the surest thing in a photo: weighted
        # so 1 mm off costs as much as 2% of outline agreement
        c = (1 - iou) + LANDMARK_W * eye_err + 0.01 * np.sum(q[:3] ** 2) + 0.01 * np.sum(q[3:] ** 2)
        return (c, iou, eye_err) if parts else c

    q0 = np.zeros(6)
    c0, iou0, e0 = cost(q0, True)
    r = minimize(cost, q0, method="Powell", options={"maxfev": 1500, "xtol": 1e-3, "ftol": 1e-6})
    c1, iou1, e1 = cost(r.x, True)
    rot = R.from_rotvec(r.x[:3] * 0.1)
    print(f"{view}: head outline {iou0 * 100:.1f}% -> {iou1 * 100:.1f}% | eye off by {e0:.1f} -> {e1:.1f} mm | "
          f"head turn {np.degrees(np.linalg.norm(r.x[:3] * 0.1)):.1f} deg about "
          f"{np.round(r.x[:3] / max(1e-9, np.linalg.norm(r.x[:3])), 2)}, shift {np.round(r.x[3:] * 10, 1)} mm")
    Vp, E = posed(r.x)
    s = sil(Vp)
    # where they differ: red = only his photo, blue = only the posed sculpt
    ph_only, sc_only = m & ~s & zone, s & ~m & zone
    photo[ph_only] = (photo[ph_only] * 0.3 + np.array([235, 0, 60]) * 0.7).astype(np.uint8)
    photo[sc_only] = (photo[sc_only] * 0.3 + np.array([0, 110, 255]) * 0.7).astype(np.uint8)
    cs, _ = cv2.findContours(zone.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(photo, cs, -1, (255, 255, 0), 1)
    for k, v in marks["eyes"].items():
        cv2.drawMarker(photo, tuple(int(a) for a in v), (235, 0, 60), cv2.MARKER_CROSS, 30, 3)
        cv2.drawMarker(photo, tuple(int(a) for a in proj(E[k])[0]), (0, 110, 255), cv2.MARKER_CROSS, 30, 3)
    x0, y0 = int(hc[0] - rad * 1.1), int(hc[1] - rad * 1.1)
    crop = Image.fromarray(photo).crop((x0, y0, x0 + int(2.2 * rad), y0 + int(2.2 * rad))).resize((560, 560))
    crop.save(out)
    res = {"view": view, "rotvec": (r.x[:3] * 0.1).tolist(), "shift_m": (r.x[3:] * 0.01).tolist(),
           "iou_before": iou0, "iou_after": iou1, "eye_mm_before": e0, "eye_mm_after": e1}
    p = ROOT / "checkpoints/cp3/head_poses.json"
    allr = json.loads(p.read_text()) if p.exists() else {}
    allr[view] = res
    p.write_text(json.dumps(allr, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
