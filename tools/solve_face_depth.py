"""Depth of Prince's eyes behind his nose, with the master frozen.

The master fixes where each feature appears: each lies on the ray from the
master camera through its master pixel; only its depth along that ray is
open. Depth comes from direct ratios in photos taken from other directions,
which need no camera solve:

  side profiles   (eye-to-nose-tip horizontal gap) / (vertical gap)
                  = how far the eyes sit behind the nose, per unit of how
                    far they sit above it. The vertical gap also shows in the
                    master, so it converts the ratio to millimetres.
  top-down        (eye-line to nose-tip gap) / (distance between the eyes);
                  the eye spacing also shows in the master.

The nose tip sits on the body surface where the master ray meets it; the eyes
are then placed on their master rays at the depth the ratios give.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import brentq
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import build_features as BF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CP3 = ROOT / "checkpoints/cp3"
MASTER_PX = {"eye_R": (338, 467), "eye_L": (699, 442), "nose_tip": (546, 745)}

# pixel landmarks: eye centre, and the frontmost point of the muzzle
PROFILES = {
    "closeup 08 side profile (his right)": {"eye": (842, 545), "nose": (1042, 668)},
    "sheet 03 right profile": {"eye": (815, 460), "nose": (1003, 598)},
    "sheet 07 left profile": {"eye": (370, 410), "nose": (183, 525)},
}
TOP_DOWN = {"sheet 09 top-down": {"eye_R": (348, 1000), "eye_L": (672, 1005), "nose": (500, 1228)}}


def main():
    cj = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())
    master = BF.Cam(cj["views"]["master_front_standing"])
    body = BF.Body()
    body.r = np.load(CP3 / "body_radii_preface.npy")
    body.V = body.c + body.dirs * body.r[:, None]
    nose = master.hit(body, MASTER_PX["nose_tip"])
    rays = {k: master.ray(MASTER_PX[k]) for k in ("eye_R", "eye_L")}

    def eyes_at(t):
        return {k: master.pos + t * d for k, d in rays.items()}

    prof = {n: abs(p["nose"][0] - p["eye"][0]) / abs(p["nose"][1] - p["eye"][1]) for n, p in PROFILES.items()}
    td = {n: abs(p["nose"][1] - (p["eye_R"][1] + p["eye_L"][1]) / 2) / abs(p["eye_L"][0] - p["eye_R"][0])
          for n, p in TOP_DOWN.items()}
    r_prof = float(np.median(list(prof.values())))
    r_td = float(np.median(list(td.values())))

    def behind(t):
        e = eyes_at(t)
        return nose[1] - (e["eye_R"][1] + e["eye_L"][1]) / 2

    def above(t):
        e = eyes_at(t)
        return (e["eye_R"][2] + e["eye_L"][2]) / 2 - nose[2]

    def sep(t):
        e = eyes_at(t)
        return np.linalg.norm(e["eye_R"] - e["eye_L"])

    t0 = np.linalg.norm(nose - master.pos)
    t_prof = brentq(lambda t: behind(t) - r_prof * above(t), t0, t0 + 0.2)
    t_td = brentq(lambda t: behind(t) - r_td * sep(t), t0, t0 + 0.2)
    t = (t_prof + t_td) / 2
    e = eyes_at(t)
    res = {
        "_about": "Eye depth from profile and top-down ratios; master pixels fixed (points lie on master rays).",
        "ratios": {"profile_behind_over_above": prof, "topdown_behind_over_separation": td},
        "nose_tip_m": nose.round(5).tolist(),
        "estimates": {
            "from_profiles": {"eyes_behind_nose_mm": round(behind(t_prof) * 1000, 1),
                              "eye_separation_mm": round(sep(t_prof) * 1000, 1)},
            "from_top_down": {"eyes_behind_nose_mm": round(behind(t_td) * 1000, 1),
                              "eye_separation_mm": round(sep(t_td) * 1000, 1)}},
        "eye_R_m": e["eye_R"].round(5).tolist(), "eye_L_m": e["eye_L"].round(5).tolist(),
        "eyes_behind_nose_mm": round(behind(t) * 1000, 1), "eyes_above_nose_mm": round(above(t) * 1000, 1),
        "eye_separation_mm": round(sep(t) * 1000, 1),
        "previous_face_solve_behind_mm": None,
    }
    try:
        fs = json.loads((CP3 / "face_solve.json").read_text())["points_master_pose_m"]
        res["previous_face_solve_behind_mm"] = round((fs["nose_tip"][1] - (fs["eye_R"][1] + fs["eye_L"][1]) / 2) * 1000, 1)
    except Exception:
        pass
    # where the eyes sit relative to the body surface (negative = inside)
    res["eye_depth_vs_body_surface_mm"] = {k: round(float(body.sdf(v[None])[0] * 1000), 1) for k, v in e.items()}
    (CP3 / "face_depth.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
