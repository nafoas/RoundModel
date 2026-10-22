"""How far the sculpt's outline is from his, on the stretches of outline that
belong to one part of the face, in each photo (head posed as he holds it
there). Reported in mm: + where the sculpt sticks out past him, - where it
falls short; and the mean distance either way.

usage: zone_score.py SCULPT_DIR [OUT.png]
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import HEAD_C, NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
# zones: boxes (x0, y0, x1, y1) in each full-size original
ZONES = {
    "sheet_03_right_profile": {"forehead (profile line, brow to nose)": (730, 330, 1030, 560)},
    "sheet_02_front_3q": {"far brow and eye (outline)": (150, 280, 330, 520)},
    "sheet_09_top_down": {"right side beside eye": (180, 850, 330, 1150),
                          "left side beside eye": (690, 850, 860, 1150)},
}


def main(d, out=None):
    d = Path(d)
    V, F = load_obj(d / "head.obj")
    cams = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
    poses = json.loads((ROOT / "checkpoints/cp3/head_poses.json").read_text())
    tiles, res = [], {}
    for view, zones in ZONES.items():
        cam = cams[view]
        Rc = R.from_rotvec(cam["rotvec_world_to_cam"]).as_matrix()
        cpos, f = np.array(cam["camera_position_m"]), cam["focal_px"]
        cx, cy = cam["principal_px"]
        p = poses[view]
        Rp, tp = R.from_rotvec(p["rotvec"]).as_matrix(), np.array(p["shift_m"])
        Vp = V + head_weight(V)[:, None] * (((V - NECK_PIVOT) @ Rp.T + NECK_PIVOT + tp) - V)
        Xc = (Vp - cpos) @ Rc.T
        P = np.stack([f * Xc[:, 0] / Xc[:, 2] + cx, f * Xc[:, 1] / Xc[:, 2] + cy], 1)
        photo = np.asarray(Image.open(ROOT / cam["image"]).convert("RGB")).copy()
        h, w = photo.shape[:2]
        fn = np.cross(Vp[F[:, 1]] - Vp[F[:, 0]], Vp[F[:, 2]] - Vp[F[:, 0]])
        front = np.einsum("ij,ij->i", fn, cpos - Vp[F[:, 0]]) > 0
        s = np.zeros((h, w), np.uint8)
        cv2.fillPoly(s, list(np.round(P[F[front]]).astype(np.int32)), 1)
        s = cv2.morphologyEx(s, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        m = np.asarray(Image.open(ROOT / f"checkpoints/cp3/orig_masks/{Path(cam['image']).stem}.mask.png")) > 0
        m = (cv2.GaussianBlur(m.astype(np.float32), (0, 0), 4) > 0.5).astype(np.uint8)
        # signed distance to the sculpt's outline: + outside the sculpt
        sd = cv2.distanceTransform(1 - s, cv2.DIST_L2, 5) - cv2.distanceTransform(s, cv2.DIST_L2, 5)
        ppm = f / ((HEAD_C - cpos) @ Rc.T)[2] / 1000  # px per mm at the head
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        C = np.vstack([c[:, 0] for c in cs])
        for name, (x0, y0, x1, y1) in zones.items():
            sel = (C[:, 0] >= x0) & (C[:, 0] < x1) & (C[:, 1] >= y0) & (C[:, 1] < y1)
            dd = -sd[C[sel, 1], C[sel, 0]] / ppm  # + : sculpt reaches past his outline
            res[f"{view}:{name}"] = (float(dd.mean()), float(np.abs(dd).mean()))
            cv2.rectangle(photo, (x0, y0), (x1, y1), (255, 200, 0), 2)
        if out:
            for mm, col in ((m, (235, 0, 60)), (s, (0, 110, 255))):
                cc, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                cv2.drawContours(photo, cc, -1, col, 3)
            allb = np.array(list(zones.values()))
            x0, y0 = allb[:, :2].min(0) - 60
            x1, y1 = allb[:, 2:].max(0) + 60
            t = Image.fromarray(photo[max(0, y0):y1, max(0, x0):x1])
            tiles.append(t.resize((round(t.width * 400 / t.height), 400)))
    for k, (sgn, ab) in res.items():
        print(f"{k:62s} sculpt {'past' if sgn > 0 else 'short of'} his outline by {abs(sgn):.1f} mm on average "
              f"(mean distance {ab:.1f} mm)")
    if out:
        W = sum(t.width for t in tiles) + 10 * len(tiles)
        o = Image.new("RGB", (W, 400), (255, 255, 255))
        x = 0
        for t in tiles:
            o.paste(t, (x, 0))
            x += t.width + 10
        o.save(out)
    (d / "zone_scores.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
