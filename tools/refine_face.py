"""Checkpoint 3: shape his face, not just his outline.

Outlines can't see anything inside them, so the body's face region came out
as a forward-facing dome, and eyes placed on it faced forward. His eyes look
out to the side (about 55 deg from straight ahead, measured from how narrow
they appear in the master) and sit on near-vertical cheeks, with his
forehead and nose bridge rounding forward between them (that bridge is what
hides the inner edge of each eye in the master).

This pass reshapes the body surface to satisfy face geometry solved in 3D
from the face views (tools/solve_face.py), while every outline constraint
from the body fit still applies:

  eye sockets   a ring of surface points around each eye, in the plane
                facing the eye's direction; a point just in front of the eye
                must be outside the head, one just behind it inside
  nose, mouth   nose tip, nostril ends and mouth split lie on the surface

Everything is in the master pose (his head as the master shows it).
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import fit_surface as FS  # noqa: E402
import refine_body as RB  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CP2 = ROOT / "checkpoints/cp2"
CP3 = ROOT / "checkpoints/cp3"

EYE_OUT_DEG = 55.0   # eye direction: out to the side from straight ahead
EYE_UP_DEG = 8.0     # and slightly up
# Eye anatomy, sized from the master: the dark of his eye is ~11.5 mm across
# (76 px tall at ~33 cm; 45 px wide, foreshortened by the ~55 deg turn).
# With a 7 mm-radius eyeball, a 5.7 mm-radius lid opening puts the cornea
# ~2.9 mm proud of the lid line. The solved eye point is the front of the
# eye (what the photos show), so the lid ring sits 2.9 mm behind it.
EYE_RADIUS = 0.0070
RIM_RADIUS = 0.0057
EYE_PROUD = EYE_RADIUS - (EYE_RADIUS ** 2 - RIM_RADIUS ** 2) ** 0.5
ITERS = 2200
W_FACE = 0.25


def eye_axis(side, mpose):
    s = 1 if side == "R" else -1   # +x is his right
    a = np.array([s * np.sin(np.radians(EYE_OUT_DEG)) * np.cos(np.radians(EYE_UP_DEG)),
                  np.cos(np.radians(EYE_OUT_DEG)) * np.cos(np.radians(EYE_UP_DEG)),
                  np.sin(np.radians(EYE_UP_DEG))])
    return R.from_rotvec(mpose).apply(a)


def constraints(face):
    """(points, target signed distance in m, weight) for the face pass."""
    mpose = np.array(face["poses"]["master_front_standing"]["rotvec"])
    P = face["points_master_pose_m"]
    pts, tgt, wts = [], [], []
    eyes = {}
    for side in ("R", "L"):
        S = np.array(P[f"eye_{side}"])
        a = eye_axis(side, mpose)
        u = np.cross(a, [0, 0, 1.0])
        u /= np.linalg.norm(u)
        v = np.cross(a, u)
        rim_c = S - a * EYE_PROUD
        for t in np.linspace(0, 2 * np.pi, 16, endpoint=False):
            pts.append(rim_c + RIM_RADIUS * (np.cos(t) * u + np.sin(t) * v))
            tgt.append(0.0)
            wts.append(1.0)
        eyes[side] = {"surface_point": S.tolist(), "axis": a.tolist(), "rim_centre": rim_c.tolist(),
                      "eyeball_centre": (S - a * EYE_RADIUS).tolist(), "eyeball_radius_m": EYE_RADIUS,
                      "rim_radius_m": RIM_RADIUS, "proud_m": EYE_PROUD}
    for k in ("nose_tip", "nostril_R", "nostril_L", "mouth_split"):
        pts.append(np.array(P[k]))
        tgt.append(0.0)
        wts.append(1.5)
    return np.array(pts), np.array(tgt), np.array(wts), eyes


def main():
    torch.manual_seed(0)
    face = json.loads((CP3 / "face_solve.json").read_text())
    meta = json.loads((CP3 / "body_meta.json").read_text())
    centre = np.array(meta["centre_m"])
    dirs, F = FS.icosphere(meta["subdiv"])
    n = len(dirs)
    # the body as the body fit left it (before any face pass) is kept
    # separately; WARM=1 continues from the current face-shaped body
    import os
    base = CP3 / "body_radii_preface.npy"
    if not base.exists():
        np.save(base, np.load(CP3 / "body_radii.npy"))
    s0 = np.log(np.load(CP3 / ("body_radii.npy" if os.environ.get("WARM") else "body_radii_preface.npy")))

    cj = json.loads((CP2 / "cameras_fit.json").read_text())
    ears = [np.array(cj["points_3d"]["ear_tip_R"]), np.array(cj["points_3d"]["ear_tip_L"])]
    views = FS.load_views(cj["views"], ears, (), RB.PASS2_COVER_W, RB.PASS2_INSIDE_W, smooth=RB.OUTLINE_SMOOTH)
    views = [v for v in views if v["name"] not in RB.DROP_VIEWS]
    for v in views:
        v["fixed"] = True
        if v["name"] in RB.COVER_ONLY_VIEWS:
            v["w_in"] = 0.0

    cp, ct, cw, eyes = constraints(face)
    rel = cp - centre
    rn = np.linalg.norm(rel, axis=1)
    tree = cKDTree(dirs)
    sigma = 0.7 * np.median(tree.query(dirs, k=2)[0][:, 1])
    dist, idx = tree.query(rel / rn[:, None], k=16)
    kw = np.exp(-(dist / sigma) ** 2)
    kw /= kw.sum(1, keepdims=True)

    rows, cols, wts, wsum = FS.cotan_weights(dirs, F)
    rows_t, cols_t = torch.tensor(rows), torch.tensor(cols)
    w_t, wsum_t = torch.tensor(wts, dtype=torch.float32), torch.tensor(wsum, dtype=torch.float32)
    mirror_t = torch.tensor(cKDTree(dirs).query(dirs * np.array([-1, 1, 1]))[1])
    D = torch.tensor(dirs, dtype=torch.float32)
    C = torch.tensor(centre, dtype=torch.float32)
    idx_t, kw_t = torch.tensor(idx), torch.tensor(kw, dtype=torch.float32)
    rn_t, ct_t, cw_t = (torch.tensor(x, dtype=torch.float32) for x in (rn, ct, cw))

    s = torch.tensor(s0, dtype=torch.float32, requires_grad=True)
    opt = torch.optim.Adam([s], lr=1e-3)
    wsum_views = sum(v["w"] for v in views)
    for it in range(ITERS + 1):
        X = C + D * torch.exp(s)[:, None]
        sub = torch.randperm(n)[:RB.COVER_SAMPLE]
        l_in = l_cov = 0.0
        for v in views:
            u, vv = FS.project(v, X)
            l_in = l_in + v["w_in"] * (torch.relu(FS.sample_sd(v, u, vv)) ** 2).mean()
            Pp = torch.stack([u[sub], vv[sub]], 1) / v["norm"]
            l_cov = l_cov + v["w"] * (torch.cdist(v["contour"], Pp).min(1).values ** 2).mean()
        l_in, l_cov = l_in / wsum_views, l_cov / wsum_views
        r_at = (torch.exp(s)[idx_t] * kw_t).sum(1)
        sd = rn_t - r_at
        l_face = (cw_t * ((sd - ct_t) * 1000) ** 2).mean()
        lap = s - torch.zeros(n).index_add(0, rows_t, w_t * s[cols_t]) / wsum_t
        bilap = lap - torch.zeros(n).index_add(0, rows_t, w_t * lap[cols_t]) / wsum_t
        loss = (l_in + l_cov + W_FACE * l_face + RB.W_ROUND * (lap ** 2).mean() * 1e3
                + 2.0 * ((s - s[mirror_t]) ** 2).mean() * 1e2 + RB.PASS2_FAIR * (bilap ** 2).mean())
        opt.zero_grad()
        loss.backward()
        opt.step()
        if it % 150 == 0:
            rms = float(torch.sqrt((((sd - ct_t) * 1000) ** 2).mean()).detach())
            print(f"{it:4d} loss {loss.item():.4f} inside {l_in.item():.4f} cover {l_cov.item():.4f} "
                  f"fair {RB.PASS2_FAIR * (bilap ** 2).mean().item():.4f} "
                  f"face rms {rms:.2f} mm", flush=True)

    r = np.exp(s.detach().numpy())
    np.save(CP3 / "body_radii.npy", r)
    (CP3 / "face_shape.json").write_text(json.dumps({
        "eye_out_deg": EYE_OUT_DEG, "eye_up_deg": EYE_UP_DEG, "rim_radius_m": RIM_RADIUS,
        "eyeball_radius_m": EYE_RADIUS, "proud_m": EYE_PROUD, "eyes": eyes,
        "weight": W_FACE, "iters": ITERS}, indent=1))
    X = centre + dirs * r[:, None]
    with open(CP3 / "body.obj", "w") as fh:
        for p in X:
            fh.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        for t in F + 1:
            fh.write(f"f {t[0]} {t[1]} {t[2]}\n")


if __name__ == "__main__":
    main()
