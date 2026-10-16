"""Checkpoint 3, step 1: refine the body the features attach to.

Starts from the Checkpoint 2 surface, at four times the vertex density
(40,962 vertices, ~1.5 mm apart), and fits again with the master given far
more say: its outline must be reached almost exactly, not just mostly. The
other views keep the shape honest in depth but carry less weight, which
also stops their small disagreements from creasing his back.

Ears are left out of the body's outline-matching here; they are built as
their own geometry next, so the body shouldn't bulge toward them. Peets are
not left out: his lower skirt covers them, so the body keeps tracing the
master's bottom outline and the peets are pads mostly inside it.
Cameras are held where Checkpoint 2 left them.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).parent))
import fit_surface as FS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CP2 = ROOT / "checkpoints/cp2"
CP3 = ROOT / "checkpoints/cp3"

SUBDIV = 6
ITERS = 900
COVER_W = {"master": 200.0, "edited": 6.0, "sheet": 0.5}
INSIDE_W = {"master": 2000.0, "edited": 6.0, "sheet": 0.5}
W_ROUND, W_MIRROR = 1500.0 * 8, 5.0   # x8: same roundness per mm on the finer mesh, a little looser
# Fairness: penalise changes in curvature, not curvature. A round body has
# steady curvature and costs nothing; a crease is a curvature spike. Holding
# the surface tightly inside the master's outline otherwise folds it along
# that outline's edge.
W_FAIR = 1.2e8
COVER_SAMPLE = 12000
# Views that look from almost the master's direction. Each one clips the
# surface along nearly the same line as the master but outlines him a little
# differently (another photo, the real rather than the edited Prince), and
# the difference folds the surface down his sides. The master speaks for
# that direction (deferential rule): the sheet's straight-front photo is
# left out of the body fit, and its three-quarter photos may push the
# surface out (they carry his muzzle's depth) but never clip it.
DROP_VIEWS = {"sheet_01_front"}
COVER_ONLY_VIEWS = {"sheet_02_front_3q", "sheet_08_front_3q_left"}
OUTLINE_SMOOTH = 0.004  # ~6 px on the master: follow the fur's envelope, not single hairs
# Second pass. Where the other views want him to bulge past the master's
# outline, pass 1 clips the surface and leaves a ridge along the master's
# outline edge. Pass 2 keeps the master strict, makes fairness strong and
# gives the other views only a light say, so the surface rounds over and
# meets the master's outline tangentially, as a smooth body does.
PASS2_ITERS = 700
PASS2_COVER_W = {"master": 200.0, "edited": 1.0, "sheet": 0.1}
PASS2_INSIDE_W = {"master": 2000.0, "edited": 3.0, "sheet": 0.25}
PASS2_FAIR = 2.4e9


def optimise(views, D, C, graph, s_init, iters, lr, w_fair):
    rows_t, cols_t, w_t, wsum_t, mirror_t = graph
    n = len(D)
    s = torch.tensor(s_init, dtype=torch.float32, requires_grad=True)
    opt = torch.optim.Adam([s], lr=lr)
    wsum = sum(v["w"] for v in views)
    for it in range(iters + 1):
        X = C + D * torch.exp(s)[:, None]
        sub = torch.randperm(n)[:COVER_SAMPLE]
        l_in = l_cov = 0.0
        for v in views:
            u, vv = FS.project(v, X)
            out = torch.relu(FS.sample_sd(v, u, vv))
            l_in = l_in + v["w_in"] * (out ** 2).mean()
            P = torch.stack([u[sub], vv[sub]], 1) / v["norm"]
            dmin = torch.cdist(v["contour"], P).min(1).values
            l_cov = l_cov + v["w"] * (dmin ** 2).mean()
        l_in, l_cov = l_in / wsum, l_cov / wsum
        lap = s - torch.zeros(n).index_add(0, rows_t, w_t * s[cols_t]) / wsum_t
        l_round = (lap ** 2).mean() * 1e3
        l_mirror = ((s - s[mirror_t]) ** 2).mean() * 1e2
        bilap = lap - torch.zeros(n).index_add(0, rows_t, w_t * lap[cols_t]) / wsum_t
        l_fair = (bilap ** 2).mean()
        loss = l_in + l_cov + W_ROUND * l_round + W_MIRROR * l_mirror + w_fair * l_fair
        opt.zero_grad()
        loss.backward()
        opt.step()
        if it % 150 == 0:
            print(f"{it:5d} loss {loss.item():.4f} inside {l_in.item():.4f} cover {l_cov.item():.4f} "
                  f"round {l_round.item():.5f} mirror {l_mirror.item():.4f} fair {w_fair * l_fair.item():.4f}",
                  flush=True)
    return np.exp(s.detach().numpy())


def main():
    torch.manual_seed(0)
    cj = json.loads((CP2 / "cameras_fit.json").read_text())
    meta = json.loads((CP2 / "fit_meta.json").read_text())
    centre = np.array(meta["centre_m"])
    P3 = cj["points_3d"]
    ears = [np.array(P3["ear_tip_R"]), np.array(P3["ear_tip_L"])]
    views = FS.load_views(cj["views"], ears, (), COVER_W, INSIDE_W, smooth=OUTLINE_SMOOTH)
    views = [v for v in views if v["name"] not in DROP_VIEWS]
    for v in views:
        v["fixed"] = True
        if v["name"] in COVER_ONLY_VIEWS:
            v["w_in"] = 0.0

    d5, _ = FS.icosphere(5)
    r5 = np.load(CP2 / "radii.npy")
    dirs, F = FS.icosphere(SUBDIV)
    dist, idx = cKDTree(d5).query(dirs, k=3)
    w = 1 / np.maximum(dist, 1e-9)
    r0 = np.exp((np.log(r5[idx]) * w).sum(1) / w.sum(1))

    n = len(dirs)
    rows, cols, wts, wsum = FS.cotan_weights(dirs, F)
    mirror = cKDTree(dirs).query(dirs * np.array([-1, 1, 1]))[1]
    D = torch.tensor(dirs, dtype=torch.float32)
    C = torch.tensor(centre, dtype=torch.float32)
    graph = (torch.tensor(rows), torch.tensor(cols), torch.tensor(wts, dtype=torch.float32),
             torch.tensor(wsum, dtype=torch.float32), torch.tensor(mirror))

    if os.environ.get("PRINCE_SKIP_PASS1") and (CP3 / "body_radii_pass1.npy").exists():
        r1 = np.load(CP3 / "body_radii_pass1.npy")
    else:
        r1 = optimise(views, D, C, graph, np.log(r0), ITERS, 1.5e-3, W_FAIR)
        np.save(CP3 / "body_radii_pass1.npy", r1)
    for v in views:
        v["w"] = PASS2_COVER_W[v["raw"]["tier"]]
        v["w_in"] = 0.0 if v["name"] in COVER_ONLY_VIEWS else PASS2_INSIDE_W[v["raw"]["tier"]]
    r2 = optimise(views, D, C, graph, np.log(r1), PASS2_ITERS, 1e-3, PASS2_FAIR)
    s = torch.tensor(np.log(r2))
    X = (C + D * torch.exp(s)[:, None]).numpy()
    a, b, c = X[F[:, 0]], X[F[:, 1]], X[F[:, 2]]
    if np.mean(np.sum(np.cross(b - a, c - a) * (a - centre), 1)) < 0:
        F = F[:, [0, 2, 1]]
    CP3.mkdir(parents=True, exist_ok=True)
    np.save(CP3 / "body_radii.npy", np.exp(s.numpy()))
    with open(CP3 / "body.obj", "w") as fh:
        fh.write("# Prince - Checkpoint 3 refined body (no ears/peets/features)\n")
        for p in X:
            fh.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        for t in F + 1:
            fh.write(f"f {t[0]} {t[1]} {t[2]}\n")
    (CP3 / "body_meta.json").write_text(json.dumps({
        "centre_m": centre.tolist(), "subdiv": SUBDIV, "iters": ITERS, "cover_weights": COVER_W,
        "inside_weights": INSIDE_W, "round": W_ROUND, "mirror": W_MIRROR, "fair": W_FAIR,
        "pass2": {"iters": PASS2_ITERS, "cover_weights": PASS2_COVER_W, "inside_weights": PASS2_INSIDE_W,
                  "fair": PASS2_FAIR}, "outline_smooth": OUTLINE_SMOOTH,
        "dropped_views": sorted(DROP_VIEWS), "cover_only_views": sorted(COVER_ONLY_VIEWS),
        "ear_radius_m": FS.EAR_RADIUS}, indent=2))
    print("extent (cm)", ((X.max(0) - X.min(0)) * 100).round(1))


if __name__ == "__main__":
    main()
