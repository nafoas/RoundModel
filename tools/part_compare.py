"""Step 3: compare each part of his face with the model's, per photo, from
the lines of part_traces.json (his) and model_lines.json (the model's).
Closed parts (eye, socket): size (width x height along the shape's own axes,
mm), orientation (tilt of the long axis, deg), position (centre offset, mm,
which carries depth: a part that sits deeper or further out lands elsewhere),
and shape overlap after aligning centres (shape alone). Open lines
(forehead, muzzle, ridge): mean distance from his line to the model's (mm),
signed (+ = the model sits outside his line, toward the camera's edge).
usage: part_compare.py   (writes checkpoints/cp3/part_compare.json, prints a table)"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from part_score import cameras  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def shape_stats(P):
    P = np.asarray(P, float)
    m = cv2.moments(P.astype(np.float32).reshape(-1, 1, 2))
    c = np.array([m["m10"] / m["m00"], m["m01"] / m["m00"]])
    cov = np.array([[m["mu20"], m["mu11"]], [m["mu11"], m["mu02"]]]) / m["m00"]
    w, v = np.linalg.eigh(cov)
    major = v[:, 1]
    ang = np.degrees(np.arctan2(major[0], -major[1]))  # tilt of long axis from vertical, + leaning right at top
    ang = (ang + 90) % 180 - 90
    q = (P - c) @ v
    size = np.ptp(q, axis=0)[::-1]  # long, short
    return c, ang, size


def overlap_centred(A, B):
    A, B = np.asarray(A, float), np.asarray(B, float)
    ca, cb = A.mean(0), B.mean(0)
    off = np.array([200.0, 200.0])
    ma = np.zeros((400, 400), np.uint8)
    mb = np.zeros((400, 400), np.uint8)
    cv2.fillPoly(ma, [np.round(A - ca + off).astype(np.int32)], 1)
    cv2.fillPoly(mb, [np.round(B - cb + off).astype(np.int32)], 1)
    return (ma & mb).sum() / max(1, (ma | mb).sum())


def main():
    T = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
    M = json.loads((ROOT / "checkpoints/cp3/model_lines.json").read_text())
    cams = cameras()
    out = {}
    for view, parts in M.items():
        c = cams[view]
        Rc = R.from_rotvec(c["rotvec"]).as_matrix()
        z = ((np.array([0, 0.06, 0.125]) - np.asarray(c["pos"])) @ Rc.T)[2]
        pmm = c["f"] / z / 1000
        for part, mline in parts.items():
            his = T[view][part]
            kind = part.split("_")[0]
            key = f"{view}:{part}"
            if kind in ("eye", "socket"):
                ch, ah, sh = shape_stats(his)
                cm, am, sm = shape_stats(mline)
                out[key] = {"size_his_mm": (sh / pmm).round(1).tolist(), "size_model_mm": (sm / pmm).round(1).tolist(),
                            "tilt_his_deg": round(float(ah), 1), "tilt_model_deg": round(float(am), 1),
                            "centre_offset_mm": ((cm - ch) / pmm).round(1).tolist(),
                            "shape_overlap": round(float(overlap_centred(his, mline)), 3)}
            else:
                H_ = np.asarray(his, float)
                Mm = np.asarray(mline, float)
                d = np.array([np.min(np.linalg.norm(Mm - p, axis=1)) for p in H_]) / pmm
                out[key] = {"mean_dist_mm": round(float(d.mean()), 1), "max_dist_mm": round(float(d.max()), 1)}
    (ROOT / "checkpoints/cp3/part_compare.json").write_text(json.dumps(out, indent=1))
    for k, v in out.items():
        if "size_his_mm" in v:
            print(f"{k:38s} size his {v['size_his_mm']} model {v['size_model_mm']} mm | tilt his {v['tilt_his_deg']:+.0f} "
                  f"model {v['tilt_model_deg']:+.0f} deg | centre off {v['centre_offset_mm']} mm | shape {v['shape_overlap']*100:.0f}%")
        else:
            print(f"{k:38s} line distance mean {v['mean_dist_mm']} mm, max {v['max_dist_mm']} mm")


if __name__ == "__main__":
    main()
