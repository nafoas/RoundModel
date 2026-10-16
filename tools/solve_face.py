"""Solve Prince's face in 3D from the face views.

His head is rigid, so the master and the head-turned / head-lowered /
toddling three-quarter photos are several looks at one face. One shared,
mirror-symmetric set of face points (eyes, nostril ends, nose tip, mouth
split) is solved together with each photo's head pose. The master's camera
is fixed (from Checkpoint 2), so the face lands in the same space as his
body. The nose tip is anchored on the body's front surface (the profiles
already fix how far forward his muzzle reaches), which removes the
depth-versus-turn ambiguity a few landmarks would otherwise leave.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import build_features as BF  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main():
    face = json.loads((ROOT / "references/face_landmarks.json").read_text())["views"]
    cams = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]
    master = BF.Cam(cams["master_front_standing"])
    body = BF.Body()
    f = master.f
    W, H = master.w, master.h
    nose0 = master.hit(body, face["master_front_standing"]["points"]["nose_tip"])
    head_centre = np.array([0.0, nose0[1] - 0.05, nose0[2]])  # pivot for head poses

    # parameters: eye (x,y,z) [R side, mirrored], nostril (x,y,z), nose (y,z) -> fixed at nose0, mouth (y,z)
    def points(p):
        ex, ey, ez, nx, ny, nz, my, mz = p[:8]
        return {"eye_R": np.array([ex, ey, ez]), "eye_L": np.array([-ex, ey, ez]),
                "nostril_R": np.array([nx, ny, nz]), "nostril_L": np.array([-nx, ny, nz]),
                "nose_tip": np.array([0.0, nose0[1], nose0[2]]), "mouth_split": np.array([0.0, my, mz])}

    # the master gets a head pose too: in the master photo his head is turned
    # and tilted slightly relative to his body (his eyes sit 210 px and
    # 151 px either side of his nose, one 25 px higher). The face itself is
    # symmetric; each photo, master included, shows it at its own small turn.
    views = ["master_front_standing"] + [k for k, v in face.items()
                                         if v["weight"] > 0 and k != "master_front_standing"]

    def project_view(P, pose):
        # head rotates about head_centre, then the master camera looks at it
        rot = R.from_rotvec(pose[:3])
        X = rot.apply(P - head_centre) + head_centre + pose[3:6]
        return master.project(X)

    def resid(p):
        pts = points(p)
        r = []
        for i, vn in enumerate(views):
            pose = p[8 + 6 * i: 14 + 6 * i]
            v = face[vn]
            for k, uv in v["points"].items():
                r.append(v["weight"] * (project_view(pts[k], pose) - np.array(uv)) / H * 100)
            # his head is attached: it turns, but barely shifts (~1 cm costs
            # as much as a 5% landmark miss)
            r.append(5.0 * pose[3:6] * 100)
        # face points sit at the surface of his head, not inside or behind
        # it (soft: the current body is only silhouette-accurate, so allow
        # a few mm either way; eyes sit just under the fur line)
        mpose = p[8:14]
        for k, target in (("eye_R", -0.002), ("eye_L", -0.002), ("nostril_R", 0.0), ("nostril_L", 0.0),
                          ("mouth_split", 0.0)):
            X = R.from_rotvec(mpose[:3]).apply(pts[k] - head_centre) + head_centre + mpose[3:6]
            r.append(np.atleast_1d(0.8 * (body.sdf(X[None])[0] - target) * 1000 / 3))
        return np.concatenate(r)

    # start: eyes on master rays, at the body surface
    eR = master.hit(body, face["master_front_standing"]["points"]["eye_R"])
    nR = master.hit(body, face["master_front_standing"]["points"]["nostril_R"])
    mo = master.hit(body, face["master_front_standing"]["points"]["mouth_split"])
    p0 = [eR[0], eR[1], eR[2], nR[0], nR[1], nR[2], mo[1], mo[2]]
    init_turn = {"master_front_standing": [0, 0, 0], "head_turn_left_mouth_closed": [0, 0, 0.3], "head_turn_right_mouth_open": [0, 0, -0.6],
                 "front_3q_left_toddle": [0, 0, -0.8], "front_head_lowered": [0.25, 0, 0]}
    for vn in views:
        p0 += init_turn.get(vn, [0, 0, 0]) + [0, 0, 0]
    sol = least_squares(resid, np.array(p0, float), loss="soft_l1")
    pts = points(sol.x)
    res = {"points_3d_m": {k: v.round(5).tolist() for k, v in pts.items()}, "head_pivot_m": head_centre.tolist(),
           "poses": {}, "rms_px": {}}
    for i, vn in enumerate(views):
        pose = sol.x[8 + 6 * i: 14 + 6 * i]
        e = [np.linalg.norm(project_view(pts[k], pose) - np.array(uv)) for k, uv in face[vn]["points"].items()]
        res["rms_px"][vn] = float(np.sqrt(np.mean(np.square(e))))
        eul = R.from_rotvec(pose[:3]).as_euler("xyz", degrees=True)
        res["poses"][vn] = {"rotvec": pose[:3].tolist(), "shift_m": pose[3:6].tolist(),
                            "pitch_roll_yaw_deg": eul.round(1).tolist()}
    # where the solved points sit relative to the current body surface
    mpose = sol.x[8:14]
    posed = {k: R.from_rotvec(mpose[:3]).apply(v - head_centre) + head_centre + mpose[3:6] for k, v in pts.items()}
    res["points_master_pose_m"] = {k: v.round(5).tolist() for k, v in posed.items()}
    res["depth_below_body_surface_mm"] = {k: float(-body.sdf(v[None])[0] * 1000) for k, v in posed.items()}
    out = ROOT / "checkpoints/cp3/face_solve.json"
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
