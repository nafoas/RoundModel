"""His whole shape as one closed surface, shaped by the other photos, the
master only regulating (owner, November 2026: from directly ahead many shapes
look the same, so never stick with one front guess; tasks/03 last section).

Start: the neutral hull (tools/fill_from_photos.py --no_front: carved from
all the photos' outlines, the master giving only its outline), smoothed.
Unknown: how far each surface point slides in or out along its starting
direction, solved coarse to fine (very smooth first, finer after).

Each photo, through its camera, his head turned as re-fitted
(checkpoints/cp6/head_poses):
- shape: where it sees the surface face-on, the surface's direction there
  should agree with that photo's normal map (checkpoints/cp5/maps);
- outline: no point of him may fall outside its outline of him; points on
  the model's own rim are drawn onto that outline.
Loafed photos count for his head only.
The master regulates only: every point inside his outline there, the rim on
it, and a gentle shading check (his white fur under the master's light,
checkpoints/cp5/maps/master_front_standing/light.json). No estimator's
normal map for the master is used.

usage: python tools/whole_head.py HULL_DIR OUT_DIR [--iters 250]
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
from fill_from_photos import POSES, STANDING, view_mask  # noqa: E402
from maps_model import camera, splat  # noqa: E402
from poisson_fuse import intrinsics  # noqa: E402
from refine_rim import laplacian  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MASTER = "master_front_standing"
VIEWS = ["sheet_02_front_3q", "sheet_08_front_3q_left", "sheet_03_right_profile", "sheet_07_left_profile",
         "sheet_09_top_down", "sheet_04_back_3q_right", "e_back_3q_left_high", "s01", "s18",
         "c02", "c21", "c08", "c10", "c09", "c26", "c03", "c12"]
T = lambda x: torch.as_tensor(np.asarray(x), dtype=torch.float64)  # noqa: E731


def vnormals(V, F):
    fn = torch.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]], dim=1)
    N = torch.zeros_like(V)
    for k in range(3):
        N = N.index_add(0, F[:, k], fn)
    return N / N.norm(dim=1, keepdim=True).clamp_min(1e-12)


def sample(img, uv, HW):
    g = torch.stack([uv[:, 0] / (HW[1] - 1) * 2 - 1, uv[:, 1] / (HW[0] - 1) * 2 - 1], -1)[None, None]
    return torch.nn.functional.grid_sample(img, g, align_corners=True, padding_mode="border")[0, :, 0].T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hull")
    ap.add_argument("out")
    ap.add_argument("--iters", type=int, default=250)
    ap.add_argument("--stages", default="300,60,12", help="smoothness per stage, coarse to fine")
    ap.add_argument("--w_shade", type=float, default=0.3)
    a = ap.parse_args()
    torch.set_num_threads(4)
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    V0, F0 = load_obj(Path(a.hull) / "head.obj")
    # smooth the hull's facets first (Taubin, does not shrink)
    L = laplacian(F0, len(V0)).tocsr()
    deg = np.asarray(L.diagonal())
    import scipy.sparse as sp
    Wn = sp.diags(1 / np.maximum(deg, 1)) @ (sp.diags(deg) - L)
    for _ in range(60):
        V0 = V0 + 0.5 * (Wn @ V0 - V0)
        V0 = V0 - 0.53 * (Wn @ V0 - V0)
    Vt, Ft = T(V0), torch.as_tensor(F0, dtype=torch.long)
    N0 = vnormals(Vt, Ft).detach()
    Lt = torch.sparse_coo_tensor(np.vstack(L.nonzero()), L.data, L.shape).coalesce()
    Lt = torch.sparse_coo_tensor(Lt.indices(), Lt.values().double(), Lt.shape)
    _, _, mpose = camera(MASTER)
    Rm = R.from_rotvec(mpose["rotvec"]).as_matrix()
    sm = np.asarray(mpose.get("shift_m", [0, 0, 0]))
    Vold0 = V0 + head_weight(V0)[:, None] * (((V0 - NECK_PIVOT - sm) @ Rm + NECK_PIVOT) - V0)
    hw = T(head_weight(Vold0))
    piv, Rm_t, sm_t = T(NECK_PIVOT), T(Rm), T(sm)

    def to_old(V):
        return V + hw[:, None] * (((V - piv - sm_t) @ Rm_t + piv) - V)

    views = []
    for name in [MASTER] + VIEWS:
        f, pp, Rc, pos = intrinsics(name) if name != MASTER else (None, None, None, None)
        if name == MASTER:
            from master_shell import master_intrinsics
            f, pp, Rc, pos, _ = master_intrinsics()
            pose = mpose
        else:
            _, _, pose = camera(name)
            if (POSES / f"{name}.json").exists():
                pose = json.loads((POSES / f"{name}.json").read_text())
        mask, head_only = view_mask(name)
        ne = ROOT / f"checkpoints/cp4/outlines/{name}.noears.png"
        if ne.exists():
            mask = np.asarray(Image.open(ne).convert("L")) > 127
        sd = (nd.distance_transform_edt(~mask) - nd.distance_transform_edt(mask)).astype(np.float64)
        v = dict(name=name, f=f, pp=T(pp), R=T(Rc), pos=T(pos), HW=mask.shape,
                 sd=T(sd)[None, None], head_only=head_only or (name not in STANDING and name != MASTER))
        Rv = R.from_rotvec(pose["rotvec"]).as_matrix() if pose else np.eye(3)
        v["Rv"], v["sv"] = T(Rv), T(np.asarray(pose.get("shift_m", [0, 0, 0])) if pose else np.zeros(3))
        if name == MASTER:
            lj = json.loads((ROOT / f"checkpoints/cp5/maps/{MASTER}/light.json").read_text())
            gray = np.asarray(Image.open(ROOT / "references/master/master_front_standing.webp").convert("L"), float) / 255
            fur = np.asarray(Image.open(ROOT / f"checkpoints/cp5/maps/{MASTER}/fur.png")) > 0
            v.update(gray=T(gray)[None, None], fur=T(fur.astype(float))[None, None],
                     L=T(lj["light_dir"]), amb=lj["ambient"], dirl=lj["directional"])
        else:
            Nn = np.load(ROOT / f"checkpoints/cp5/maps/{name}/normals.npy").astype(np.float64) * np.array([1, -1, -1])
            v["N"] = T((Nn.reshape(-1, 3) @ Rc).reshape(Nn.shape)).permute(2, 0, 1)[None]  # world, head as in that photo
        views.append(v)
        print("view", name, "head only" if v["head_only"] else "", flush=True)

    def in_view(V, v):
        Vo = to_old(V)
        return Vo + hw[:, None] * (((Vo - piv) @ v["Rv"].T + piv + v["sv"]) - Vo)

    vis_cache = {}

    def visible(Vv, v, Fnp):
        P = Vv.detach().numpy()
        Rc, pos, f, pp = v["R"].numpy(), v["pos"].numpy(), v["f"], v["pp"].numpy()

        def proj(Q):
            X = (Q - pos) @ Rc.T
            return f * X[:, :2] / X[:, 2:3] + pp, X[:, 2]
        uv, z = proj(P)
        (_,), zb = splat(P, Fnp, [np.zeros(len(P), np.int8)], proj, *v["HW"])
        px = np.clip(np.round(uv).astype(int), 0, [v["HW"][1] - 1, v["HW"][0] - 1])
        return torch.as_tensor(np.abs(z - zb[px[:, 1], px[:, 0]]) < 0.002)

    # his shape changes only through broad smooth bulges and dents (owner: no
    # spikes): each stage adds K bumps of radius r, centres spread over him
    from scipy.spatial import cKDTree
    tree = cKDTree(V0)
    bases, coefs = [], []

    def centres(K):
        idx = [0]
        dmin = np.linalg.norm(V0 - V0[0], axis=1)
        for _ in range(K - 1):
            i = int(np.argmax(dmin))
            idx.append(i)
            dmin = np.minimum(dmin, np.linalg.norm(V0 - V0[i], axis=1))
        return V0[idx]

    def disp():
        out = torch.zeros(len(V0), dtype=torch.float64)
        for B, c in zip(bases, coefs):
            out = out + B @ c
        return out
    for stage, (K, r) in enumerate([(60, 0.030), (300, 0.013)]):
        Cn = centres(K)
        dist = np.linalg.norm(V0[:, None, :] - Cn[None], axis=2)
        Bm = np.exp(-(dist / r) ** 2)
        Bm /= np.maximum(Bm.sum(1, keepdims=True), 1e-6)
        bases.append(T(Bm))
        c = torch.zeros(K, dtype=torch.float64, requires_grad=True)
        coefs.append(c)
        opt = torch.optim.Adam(coefs, lr=3e-4)
        lam = 0.0
        for it in range(a.iters + 1):
            d = disp()
            V = Vt + d[:, None] * N0
            if it % 25 == 0:
                vis_cache = {v["name"]: visible(in_view(V, v), v, F0) for v in views}
            loss = 0.0
            rep = {}
            for v in views:
                Vv = in_view(V, v)
                X = (Vv - v["pos"]) @ v["R"].T
                uv = v["f"] * X[:, :2] / X[:, 2:3] + v["pp"]
                s = sample(v["sd"], uv, v["HW"])[:, 0]  # + outside his outline (px)
                use = hw > 0.6 if v["head_only"] else torch.ones_like(hw, dtype=torch.bool)
                Nv = vnormals(Vv, Ft)
                sight = v["pos"] - Vv
                sight = sight / sight.norm(dim=1, keepdim=True)
                face = (Nv * sight).sum(1)
                vis = vis_cache[v["name"]] & use
                l_out = (torch.relu(s)[use] ** 2).mean() * 1e-2
                rim = vis & (face.abs() < 0.2) & (s.abs().detach() < 25)
                l_rim = torch.nn.functional.huber_loss(s[rim], torch.zeros_like(s[rim]), delta=8.0) * 1e-2 if rim.any() else 0.0
                lv = l_out + l_rim
                fw = vis & (face.detach() > 0.35)
                if v["name"] == MASTER:
                    nc = (Nv @ v["R"].T) * T([1, -1, -1])
                    pred = v["amb"] + v["dirl"] * (nc @ v["L"])
                    g = sample(v["gray"], uv, v["HW"])[:, 0]
                    fu = fw & (sample(v["fur"], uv, v["HW"])[:, 0] > 0.5)
                    l_sh = ((pred - g)[fu] ** 2).mean() * a.w_shade if fu.any() else 0.0
                    lv = lv + l_sh
                else:
                    nt = sample(v["N"], uv, v["HW"])
                    nt = nt / nt.norm(dim=1, keepdim=True).clamp_min(1e-9)
                    wgt = face.detach().clamp(0, 1) ** 2 * fw
                    l_n = ((1 - (Nv * nt).sum(1)) * wgt).sum() / wgt.sum().clamp_min(1)
                    lv = lv + l_n
                    rep[v["name"]] = round(float(l_n), 4)
                loss = loss + lv
            loss = loss + 5.0 * sum((cc ** 2).mean() for cc in coefs) * 1e3  # stay near the outline hull unless the photos say
            opt.zero_grad()
            loss.backward()
            opt.step()
            if it % 50 == 0:
                print(f"stage {stage} ({K} bumps, {r*1000:.0f} mm) it {it}: slide mm mean {d.abs().mean().item()*1000:.2f} "
                      f"max {d.abs().max().item()*1000:.2f}; normals off {np.mean(list(rep.values())):.4f}", flush=True)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", (Vt + disp()[:, None] * N0).detach().numpy(), F0)
    C.write_obj(out / "start.obj", V0, F0)


if __name__ == "__main__":
    main()
