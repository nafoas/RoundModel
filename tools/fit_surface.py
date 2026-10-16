"""Checkpoint 2, stage 2: fit one smooth, closed surface to every wall at once.

Carving (assemble_walls.py) can only remove volume, so wherever two views
disagree it leaves a flat cut, and it can never put back something a single
view needs, like the master's ears. Here a closed surface, a sphere whose
radius varies with direction from his centre, is fitted to all the outlines
together:

  inside   every point of the surface must project inside each view's
           outline (nothing sticks out)
  cover    every point of each view's outline must be reached by the
           surface's projection (nothing is missing)
  round    neighbouring radii agree (where views disagree, Prince is round)
  mirror   his left and right sides match, softly

Views are weighted by tier, so the master dominates where they conflict.
Cameras start from assemble_walls.py and are refined together with the
surface (small turns, shifts and zoom, held near their starting values), so a
view that disagrees only because its camera was slightly off stops pulling
him out of shape. The master camera never moves; it anchors scale and pose.
The carved volume is only the starting shape.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R

ROOT = Path(__file__).resolve().parents[1]
CP1 = ROOT / "checkpoints/cp1"
CP2 = ROOT / "checkpoints/cp2"

# "cover": how strongly each view's outline must be reached by the surface
TIER_W = {"master": 40.0, "edited": 6.0, "sheet": 1.0}
# "inside" is much stricter for the master: nothing may stick out of his
# outline in the master view, whatever the other views want
INSIDE_W = {"master": 300.0, "edited": 6.0, "sheet": 1.0}
# Ears are thin flaps, modelled as their own geometry in Checkpoint 3. A
# closed body surface can't represent them: seen only from the front it
# smears them into a crest over his head. So the parts of each outline
# within EAR_RADIUS of an ear tip don't pull the body outward ("cover"),
# while "inside" still applies everywhere.
EAR_RADIUS = 0.032
SUBDIV = 5            # icosphere: 10242 vertices (~3 mm apart)
ITERS = 1500
W_INSIDE, W_COVER, W_ROUND, W_MIRROR, W_CAM = 1.0, 1.0, 1500.0, 5.0, 0.05


def icosphere(n):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
         (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11),
         (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    V = [np.array(p, float) / np.linalg.norm(p) for p in v]
    F = f
    for _ in range(n):
        cache, nf = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = V[a] + V[b]
                V.append(m / np.linalg.norm(m))
                cache[k] = len(V) - 1
            return cache[k]
        for a, b, c in F:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        F = nf
    return np.array(V), np.array(F)


def neighbours(F, n):
    nb = [set() for _ in range(n)]
    for a, b, c in F:
        nb[a] |= {b, c}
        nb[b] |= {a, c}
        nb[c] |= {a, b}
    rows, cols = [], []
    for i, s in enumerate(nb):
        for j in s:
            rows.append(i)
            cols.append(j)
    deg = np.array([len(s) for s in nb], float)
    return np.array(rows), np.array(cols), deg


def mask_path(vn, image):
    stem = Path(image).stem
    return CP1 / "masks" / (f"sheet_{stem}.outline.png" if vn.startswith("sheet_") else f"{stem}.outline.png")


def load_views(cams, ear_tips):
    views = []
    for vn, v in cams.items():
        m = np.asarray(Image.open(mask_path(vn, v["image"]))) > 0
        h, w = m.shape
        norm = max(h, w) / 100.0  # distances in % of image size
        sd = (distance_transform_edt(~m) - distance_transform_edt(m)) / norm
        cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=len)[:, 0, :].astype(float)
        c = c[np.linspace(0, len(c) - 1, 400).astype(int)]
        Rm = R.from_rotvec(v["rotvec_world_to_cam"]).as_matrix()
        for tip in ear_tips:
            Xc = (tip - np.array(v["camera_position_m"])) @ Rm.T
            uv = v["focal_px"] * Xc[:2] / Xc[2] + np.array([w, h]) / 2
            rad = v["focal_px"] * EAR_RADIUS / Xc[2]
            c = c[np.linalg.norm(c - uv, axis=1) > rad]
        views.append({
            "name": vn, "w": TIER_W[v["tier"]], "w_in": INSIDE_W[v["tier"]], "size": (w, h), "norm": norm,
            "R": torch.tensor(R.from_rotvec(v["rotvec_world_to_cam"]).as_matrix(), dtype=torch.float32),
            "cam": torch.tensor(v["camera_position_m"], dtype=torch.float32),
            "f": float(v["focal_px"]),
            "sd": torch.tensor(sd, dtype=torch.float32)[None, None],
            "contour": torch.tensor(c / norm, dtype=torch.float32),
            "fixed": v["tier"] == "master",
            "delta": torch.zeros(7, requires_grad=v["tier"] != "master"),
            "raw": v,
        })
    return views


def skew(w):
    z = torch.zeros((), dtype=w.dtype)
    return torch.stack([torch.stack([z, -w[2], w[1]]), torch.stack([w[2], z, -w[0]]),
                        torch.stack([-w[1], w[0], z])])


def camera(view):
    """Current camera of a view: its starting camera plus the learned nudge."""
    if view["fixed"]:
        return view["R"], view["cam"], view["f"]
    d = view["delta"]
    Rm = view["R"] @ torch.linalg.matrix_exp(skew(d[:3] * 0.05)).T
    return Rm, view["cam"] + d[3:6] * 0.02, view["f"] * torch.exp(d[6] * 0.05)


def project(view, X):
    Rm, cam, f = camera(view)
    Xc = (X - cam) @ Rm.T
    w, h = view["size"]
    u = f * Xc[:, 0] / Xc[:, 2] + w / 2
    v = f * Xc[:, 1] / Xc[:, 2] + h / 2
    return u, v


def sample_sd(view, u, v):
    w, h = view["size"]
    g = torch.stack([u / (w - 1) * 2 - 1, v / (h - 1) * 2 - 1], -1)[None, None]
    s = torch.nn.functional.grid_sample(view["sd"], g, align_corners=True, padding_mode="border")
    return s[0, 0, 0]


def init_radii(dirs, centre):
    vol = np.load(CP2 / "volume.npz")
    occ, vx, origin = vol["occupancy"], float(vol["voxel"]), vol["origin"]
    ts = np.arange(0.005, 0.2, 0.0005)
    r = np.zeros(len(dirs))
    for k in range(0, len(dirs), 4096):
        d = dirs[k:k + 4096]
        P = centre + d[:, None, :] * ts[None, :, None]
        idx = np.round((P - origin) / vx).astype(int)
        ok = np.all((idx >= 0) & (idx < np.array(occ.shape)), -1)
        inside = np.zeros(ok.shape, bool)
        ii = idx[ok]
        inside[ok] = occ[ii[:, 0], ii[:, 1], ii[:, 2]]
        last = np.where(inside.any(1), inside.shape[1] - 1 - np.argmax(inside[:, ::-1], 1), 0)
        r[k:k + 4096] = ts[last]
    return np.maximum(r, 0.01)


def main():
    torch.manual_seed(0)
    cj = json.loads((CP2 / "cameras.json").read_text())
    cams = cj["views"]
    ear_tips = [np.array(cj["points_3d"][k]) for k in ("ear_tip_R", "ear_tip_L")]
    views = load_views(cams, ear_tips)
    vol = np.load(CP2 / "volume.npz")
    occ_idx = np.argwhere(vol["occupancy"])
    centre = (occ_idx.mean(0) * float(vol["voxel"]) + vol["origin"])
    print("centre (cm)", (centre * 100).round(2))

    dirs, F = icosphere(SUBDIV)
    n = len(dirs)
    rows, cols, deg = neighbours(F, n)
    mirror = cKDTree(dirs).query(dirs * np.array([-1, 1, 1]))[1]
    r0 = init_radii(dirs, centre)

    D = torch.tensor(dirs, dtype=torch.float32)
    C = torch.tensor(centre, dtype=torch.float32)
    s = torch.tensor(np.log(r0), dtype=torch.float32, requires_grad=True)
    rows_t, cols_t = torch.tensor(rows), torch.tensor(cols)
    deg_t = torch.tensor(deg, dtype=torch.float32)
    mirror_t = torch.tensor(mirror)
    deltas = [v["delta"] for v in views if not v["fixed"]]
    opt = torch.optim.Adam([{"params": [s], "lr": 3e-3}, {"params": deltas, "lr": 2e-3}])
    wsum = sum(v["w"] for v in views)

    for it in range(ITERS + 1):
        X = C + D * torch.exp(s)[:, None]
        l_in = l_cov = 0.0
        for v in views:
            u, vv = project(v, X)
            out = torch.relu(sample_sd(v, u, vv))
            l_in = l_in + v["w_in"] * (out ** 2).mean()
            P = torch.stack([u, vv], 1) / v["norm"]
            dmin = torch.cdist(v["contour"], P).min(1).values
            l_cov = l_cov + v["w"] * (dmin ** 2).mean()
        l_in, l_cov = l_in / wsum, l_cov / wsum
        lap = s - torch.zeros(n).index_add(0, rows_t, s[cols_t]) / deg_t
        l_round = (lap ** 2).mean() * 1e3
        l_mirror = ((s - s[mirror_t]) ** 2).mean() * 1e2
        # cameras stay near where the landmarks and carving put them
        l_cam = sum((d ** 2).sum() for d in deltas) / len(deltas)
        loss = W_INSIDE * l_in + W_COVER * l_cov + W_ROUND * l_round + W_MIRROR * l_mirror + W_CAM * l_cam
        opt.zero_grad()
        loss.backward()
        opt.step()
        if it % 250 == 0:
            print(f"{it:5d} loss {loss.item():.4f} inside {l_in.item():.4f} cover {l_cov.item():.4f} "
                  f"round {l_round.item():.4f} mirror {l_mirror.item():.4f} cam {l_cam.item():.4f}", flush=True)

    X = (C + D * torch.exp(s)[:, None]).detach().numpy()
    # outward winding check
    a, b, c = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    nrm = np.cross(b - a, c - a)
    if np.mean(np.sum(nrm * (a - centre), 1)) < 0:
        F = F[:, [0, 2, 1]]
    with open(CP2 / "prince_cp2.obj", "w") as fh:
        fh.write("# Prince - Checkpoint 2 fitted surface (metres; +x his right, +y forward, +z up)\n")
        for p in X:
            fh.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        for t in F + 1:
            fh.write(f"f {t[0]} {t[1]} {t[2]}\n")
    ext = X.max(0) - X.min(0)
    vol_ml = np.abs(np.sum(np.einsum("ij,ij->i", a - centre, np.cross(b - centre, c - centre)))) / 6 * 1e6
    print("extent (cm) x/y/z", (ext * 100).round(1), "volume (ml)", round(vol_ml, 1))
    np.save(CP2 / "radii.npy", np.exp(s.detach().numpy()))
    cj = json.loads((CP2 / "cameras.json").read_text())
    for v in views:
        Rm, cam, f = camera(v)
        d = cj["views"][v["name"]]
        Rm = Rm.detach().numpy() if torch.is_tensor(Rm) else Rm
        cam = cam.detach().numpy() if torch.is_tensor(cam) else cam
        f = float(f.detach()) if torch.is_tensor(f) else float(f)
        d["rotvec_world_to_cam"] = R.from_matrix(Rm).as_rotvec().round(6).tolist()
        d["camera_position_m"] = np.asarray(cam).round(5).tolist()
        d["focal_px"] = round(f, 2)
        d["vertical_fov_deg"] = round(float(np.degrees(2 * np.arctan(d["size"][1] / 2 / f))), 2)
        rel = np.asarray(cam) - np.array([0, 0, 0.08])
        dist = np.linalg.norm(rel)
        d["azimuth_deg"] = round(float(np.degrees(np.arctan2(-rel[0], rel[1]))), 1)
        d["elevation_deg"] = round(float(np.degrees(np.arcsin(rel[2] / dist))), 1)
        d["distance_m"] = round(float(dist), 3)
    (CP2 / "cameras_fit.json").write_text(json.dumps(cj, indent=2))
    (CP2 / "fit_meta.json").write_text(json.dumps({
        "centre_m": centre.round(5).tolist(), "subdiv": SUBDIV, "iters": ITERS,
        "weights": {"inside": W_INSIDE, "cover": W_COVER, "round": W_ROUND, "mirror": W_MIRROR, "camera": W_CAM},
        "tier_weights": TIER_W, "inside_weights": INSIDE_W, "ear_radius_m": EAR_RADIUS, "extent_cm": (ext * 100).round(2).tolist(), "volume_ml": round(vol_ml, 1)}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
