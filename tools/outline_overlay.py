"""Outline of the sculpt (blue) over his outline in a full-size sheet original
(red), from that view's refined camera; cropped around the head.
usage: outline_overlay.py SCULPT_DIR VIEW OUT.png [--half 0.07]"""
import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from refine_side_cameras import load_obj  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def silhouette(V, F, cam, h, w):
    Rm = __import__("scipy.spatial.transform", fromlist=["Rotation"]).Rotation.from_rotvec(
        cam["rotvec_world_to_cam"]).as_matrix()
    c, f = np.array(cam["camera_position_m"]), cam["focal_px"]
    cx, cy = cam["principal_px"]
    Xc = (V - c) @ Rm.T
    P = np.stack([f * Xc[:, 0] / Xc[:, 2] + cx, f * Xc[:, 1] / Xc[:, 2] + cy], 1)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    front = np.einsum("ij,ij->i", fn, c - V[F[:, 0]]) > 0
    img = np.zeros((h, w), np.uint8)
    cv2.fillPoly(img, list(np.round(P[F[front]]).astype(np.int32)), 1)
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    ff = img.copy()
    cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
    return (img | (1 - ff)) > 0, P, f, Xc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sculpt_dir")
    ap.add_argument("view")
    ap.add_argument("out")
    ap.add_argument("--half", type=float, default=0.07)
    a = ap.parse_args()
    cam = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"][a.view]
    photo = np.asarray(Image.open(ROOT / cam["image"]).convert("RGB")).copy()
    h, w = photo.shape[:2]
    m = np.asarray(Image.open(ROOT / f"work/orig/{Path(cam['image']).stem}.mask.png")) > 0
    m = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 4) > 0.5
    V, F = load_obj(Path(a.sculpt_dir) / "head.obj")
    s, P, f, Xc = silhouette(V, F, cam, h, w)
    for mm, col in ((m, (235, 0, 60)), (s, (0, 110, 255))):
        cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(photo, cs, -1, col, 3)
    # crop around the head: the projection of the face centre
    dj = json.loads((ROOT / "checkpoints/cp3/face_depth.json").read_text())
    X = (np.array(dj["eye_R_m"]) + np.array(dj["eye_L_m"])) / 4 + np.array(dj["nose_tip_m"]) / 2
    i = np.argmin(np.linalg.norm(V - X, axis=1))
    u, v, z = P[i, 0], P[i, 1], Xc[i, 2]
    r = a.half * f / z
    Image.fromarray(photo).crop((int(u - r), int(v - r), int(u + r), int(v + r))).resize((640, 640)).save(a.out)


if __name__ == "__main__":
    main()
