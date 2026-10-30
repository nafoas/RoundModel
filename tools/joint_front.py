"""His front solved jointly from several angles (owner: make the normals from
multiple angles with respect to both; face first: master, both three-
quarters, both profiles). Judged against docs/FEATURES.md.

Unknown: his depth along every master pixel (1/K resolution), so his outline
and look from the front stay the master's. Start: Depth Pro's front
(work/m/cand/depthproc). Every round, the surface's own normals are compared
- with Depth Pro's surface directions in the master (weight W_MASTER);
- in each other photo (sheet 02, 08, 03, 07), with that photo's normal map
  (checkpoints/cp5/maps) where the photo sees the point face-on, through
  its camera, his head turned as re-fitted (checkpoints/cp6/head_poses);
  in the loafed profiles only his head counts;
and a light smoothness on log depth. All at once (Adam, PyTorch, CPU).
Then the change in depth is spread to Depth Pro's full-resolution front.

writes work/m/joint/<name>/head.obj, depth.npy; prints the agreement per photo.

usage: python tools/joint_front.py [--iters 400] [--k 4]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from scipy import ndimage as nd
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from fill_from_photos import POSES  # noqa: E402
from front_candidates import mesh_from_depth  # noqa: E402
from maps_model import camera  # noqa: E402
from master_shell import master_intrinsics  # noqa: E402
from poisson_fuse import intrinsics  # noqa: E402
from sculpt import NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MASTER = "master_front_standing"
OTHERS = {"sheet_02_front_3q": True, "sheet_08_front_3q_left": True,
          "sheet_03_right_profile": False, "sheet_07_left_profile": False}  # True: standing like the master
W_MASTER = 1.0


def Rm_(pose):
    return R.from_rotvec(pose["rotvec"]).as_matrix() if pose else np.eye(3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=400)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--smooth", type=float, default=0.02)
    ap.add_argument("--out", default="work/m/joint/j1")
    a = ap.parse_args()
    torch.set_num_threads(4)
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    f, pp, Rc, pos, mpose = master_intrinsics()
    z_full = np.load(ROOT / "work/m/cand/depthproc/depth.npy").astype(float)
    H, W = z_full.shape
    k = a.k
    zk = z_full[::k, ::k]
    m = np.isfinite(zk)
    m = nd.binary_erosion(m, iterations=1)
    h, w = zk.shape
    vv, uu = np.mgrid[0:h, 0:w]
    ray = np.stack([(uu * k - pp[0]) / f, (vv * k - pp[1]) / f, np.ones((h, w))], -1)
    T = lambda x: torch.tensor(x, dtype=torch.float64)  # noqa: E731
    ray_t, Rc_t, pos_t = T(ray), T(Rc), T(pos)
    lz0 = np.log(np.where(m, zk, np.nanmedian(zk)))
    lz = torch.nn.Parameter(T(lz0))
    m_t = torch.tensor(m)

    def points(lz):
        return pos_t + (ray_t * torch.exp(lz)[..., None]) @ Rc_t  # world, him as in the master

    def normals(P):
        du = P[:, 1:, :] - P[:, :-1, :]
        dv = P[1:, :, :] - P[:-1, :, :]
        n = torch.cross(dv[:, :-1], du[:-1, :], dim=-1)  # facing the camera
        return n / n.norm(dim=-1, keepdim=True).clamp_min(1e-12)
    # the master's target: Depth Pro's own surface directions (fixed)
    with torch.no_grad():
        P0 = points(T(lz0))
        n_master = normals(P0)
    # head weight (fixed, from the start shape) in the old frame the cameras live in
    P0n = P0.numpy().reshape(-1, 3)
    Rmm = Rm_(mpose)
    sm = np.asarray(mpose.get("shift_m", [0, 0, 0])) if mpose else np.zeros(3)
    hw0 = head_weight(P0n)
    Pold0 = P0n + hw0[:, None] * (((P0n - NECK_PIVOT - sm) @ Rmm + NECK_PIVOT) - P0n)
    hw = torch.tensor(head_weight(Pold0).reshape(h, w))
    views = []
    for name, standing in OTHERS.items():
        fv, ppv, Rv, posv = intrinsics(name)
        _, _, pose = camera(name)
        if (POSES / f"{name}.json").exists():
            pose = json.loads((POSES / f"{name}.json").read_text())
        Nv = np.load(ROOT / f"checkpoints/cp5/maps/{name}/normals.npy").astype(np.float32) * np.array([1, -1, -1], np.float32)
        Nv_world = (Nv.reshape(-1, 3) @ Rv).reshape(Nv.shape)  # camera -> world (head as in that photo)
        mask = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{name}.png").convert("L")) > 127
        mask = nd.binary_erosion(mask, iterations=8)
        views.append(dict(name=name, f=fv, pp=T(ppv), R=T(Rv), pos=T(posv), pose=pose, standing=standing,
                          N=torch.tensor(Nv_world).permute(2, 0, 1)[None].double(),
                          mask=torch.tensor(mask.astype(np.float64))[None, None], HW=mask.shape))
    Rm_t = T(Rmm)
    sm_t = T(sm)
    piv = T(NECK_PIVOT)

    def to_view(P, v):
        """Him as in the master -> old frame -> his head as in photo v."""
        hwv = hw[:P.shape[0], :P.shape[1], None]
        Pold = P + hwv * (((P - piv - sm_t) @ Rm_t + piv) - P)
        Rv_ = T(Rm_(v["pose"]))
        sv = T(np.asarray(v["pose"].get("shift_m", [0, 0, 0]))) if v["pose"] else T(np.zeros(3))
        Pv = Pold + hwv * (((Pold - piv) @ Rv_.T + piv + sv) - Pold)
        return Pv, Rv_

    def sample(img, uv, HW):
        g = torch.stack([uv[..., 0] / (HW[1] - 1) * 2 - 1, uv[..., 1] / (HW[0] - 1) * 2 - 1], -1)[None]
        return torch.nn.functional.grid_sample(img, g, align_corners=True)[0]

    opt = torch.optim.Adam([lz], lr=2e-3)
    mi = m_t[:-1, :-1] & m_t[1:, :-1] & m_t[:-1, 1:]
    for it in range(a.iters + 1):
        opt.zero_grad()
        P = points(lz)
        n = normals(P)
        loss_m = ((1 - (n * n_master).sum(-1)) * mi).sum() / mi.sum()
        loss = W_MASTER * loss_m
        report = {"master": float(loss_m)}
        Pc = P[:-1, :-1]
        for v in views:
            Pv, Rv_ = to_view(Pc, v)
            X = (Pv - v["pos"]) @ v["R"].T
            uv = v["f"] * X[..., :2] / X[..., 2:3] + v["pp"]
            # his surface direction in that photo, back to him as in the master (head turned back)
            nv = sample(v["N"], uv, v["HW"]).permute(1, 2, 0)
            hwv = (hw[:-1, :-1] > 0.5)[..., None]
            nv = torch.where(hwv, nv @ Rv_ @ Rm_t.T, nv)
            nv = nv / nv.norm(dim=-1, keepdim=True).clamp_min(1e-9)
            inside = sample(v["mask"], uv, v["HW"])[0] > 0.5
            sight = v["pos"] - Pv
            sight = sight / sight.norm(dim=-1, keepdim=True)
            n_v = torch.where(hwv, n @ Rm_t @ Rv_.T, n)  # surface as in that photo
            face = (n_v * sight).sum(-1).detach()
            wgt = (face.clamp(0, 1) ** 2) * inside * mi * (face > 0.3)
            if not v["standing"]:
                wgt = wgt * (hw[:-1, :-1] > 0.6)
            lv = ((1 - (n * nv).sum(-1)) * wgt).sum() / wgt.sum().clamp_min(1)
            loss = loss + lv
            report[v["name"]] = float(lv)
        lap = (lz[1:-1, 1:-1] * 4 - lz[:-2, 1:-1] - lz[2:, 1:-1] - lz[1:-1, :-2] - lz[1:-1, 2:])
        loss = loss + a.smooth * 1e4 * (lap[m_t[1:-1, 1:-1]] ** 2).mean()
        loss.backward()
        with torch.no_grad():
            lz.grad[~m_t] = 0
        opt.step()
        if it % 50 == 0:
            print(it, {k_: round(v_, 4) for k_, v_ in report.items()}, flush=True)
    # the change, spread to Depth Pro's full-resolution front
    dl = (lz.detach().numpy() - lz0) * m
    dl_full = np.asarray(Image.fromarray(dl.astype(np.float32)).resize((W, H), Image.BILINEAR))
    z_new = z_full * np.exp(dl_full)
    out = ROOT / a.out
    mesh_from_depth(np.where(np.isfinite(z_full), z_new, np.nan), f, pp, Rc, pos, out)
    print("depth change: median", np.nanmedian(np.abs(z_new - z_full)) * 1000, "mm, max", np.nanmax(np.abs(z_new - z_full)) * 1000, "mm")


if __name__ == "__main__":
    main()
