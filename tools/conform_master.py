"""The model bent to take his front from the master's normals (docs/
MEASURING.md, "Correction (owner)"), keeping its own surface so his sides,
back and top stay round (tools/master_shell.py extruded along the master's
rays and made walls; this replaces it).

His front surface comes from the master's normal map alone
(master_shell.integrate: perspective normal integration, one scale per piece
from the model). Then, in rounds, on the model's own surface:
- every point the master sees inside his outline is to move along its master
  ray onto his front surface;
- every point on the model's outline in the master (side-on to the camera)
  is to move in or out to his outline there;
- these moves are spread into one smooth field over the whole surface
  (data where the master sees him, gentle bending elsewhere), so his sides,
  back and top follow without walls or ridges;
- moves are taken back to his head at rest (the master's head pose).
Finally the surface is made finer (0.3 mm) and every front point placed
exactly on his front surface, so the detail from the normals is kept in
full.

usage: python tools/conform_master.py MODEL_DIR OUT_DIR [--rounds 8] [--smooth 20]
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from PIL import Image
from scipy import ndimage as nd
from scipy.ndimage import map_coordinates
from scipy.sparse.linalg import factorized
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from maps_model import camera, posed, splat, vertex_normals  # noqa: E402
from master_shell import integrate, master_intrinsics  # noqa: E402
from refine_rim import laplacian  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import head_weight  # noqa: E402
from subdivide import split  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VIEW = "master_front_standing"


def his_front(V, F, proj, pose, H, W, k=2):
    f, pp, Rc, pos, _ = master_intrinsics()
    Np = np.load(ROOT / f"checkpoints/cp5/maps/{VIEW}/normals.npy").astype(float)
    noears = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{VIEW}.noears.png").convert("L")) > 127
    omega = nd.binary_erosion(noears, iterations=2)
    lz = integrate(Np * np.array([1, -1, -1]), omega, f, pp, k)
    (_,), zf = splat(posed(V, pose), F, [np.zeros(len(V), np.int8)], proj, H, W)
    zf_k = zf[::k, ::k]
    lab, n = nd.label(np.isfinite(lz))
    out = np.full_like(lz, np.nan)
    for c in range(1, n + 1):
        m = lab == c
        both = m & np.isfinite(zf_k)
        if both.sum() >= 200:
            out[m] = np.exp(lz[m] + np.median(np.log(zf_k[both]) - lz[both]))
    zs = np.asarray(Image.fromarray(np.nan_to_num(out, nan=0).astype(np.float32)).resize((W, H), Image.BILINEAR))
    ok = (np.asarray(Image.fromarray((np.isfinite(out) * 255).astype(np.uint8)).resize((W, H), Image.NEAREST)) > 0) & omega
    return np.where(ok, zs, 0.0), ok, noears, pos


def to_rest(V, delta, pose):
    if not pose:
        return delta
    hw = head_weight(V)[:, None]
    Rh = R.from_rotvec(pose["rotvec"]).as_matrix()
    return hw * (delta @ Rh) + (1 - hw) * delta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("out")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--smooth", type=float, default=20.0)
    ap.add_argument("--levels", type=int, default=2)
    a = ap.parse_args()
    md, out = Path(a.model), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    body = md / "head.obj"
    V, F = load_obj(body)
    # the ears are built leaves: kept apart, not bent
    if (md / "ears.obj").exists():
        Ve, Fe = load_obj(md / "ears.obj")
        nb = len(V) - len(Ve)
        if nb > 0 and np.allclose(V[nb:], Ve):
            V, F = V[:nb], F[(F < nb).all(1)]
    else:
        Ve, Fe = np.zeros((0, 3)), np.zeros((0, 3), int)
    cam, _ = C.view_data(VIEW)
    pose = cam["pose"]
    proj, _, _ = camera(VIEW)
    H, W = (np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{VIEW}.png")).shape)[:2]
    zs, valid, noears, pos = his_front(V, F, proj, pose, H, W)
    sd = nd.distance_transform_edt(~noears) - nd.distance_transform_edt(noears)  # + outside him
    L = laplacian(F, len(V)).tocsc()
    for r in range(a.rounds):
        Vp = posed(V, pose)
        uv, z = proj(Vp)
        (_,), zb = splat(Vp, F, [np.zeros(len(V), np.int8)], proj, H, W)
        px = np.clip(np.round(uv).astype(int), 0, [W - 1, H - 1])
        seen = np.abs(z - zb[px[:, 1], px[:, 0]]) < 0.0015
        Np_ = vertex_normals(Vp, F)
        ray = Vp - pos
        ray /= np.linalg.norm(ray, axis=1, keepdims=True)
        facing = -np.einsum("ij,ij->i", Np_, ray)
        zt = map_coordinates(zs, [uv[:, 1], uv[:, 0]], order=1)
        vv = map_coordinates(valid.astype(float), [uv[:, 1], uv[:, 0]], order=1)
        front = seen & (vv > 0.99) & (zt > 0) & (facing > 0.2)
        d = np.zeros_like(V)
        w = np.zeros(len(V))
        d[front] = ((Vp - pos) * (zt / np.maximum(z, 1e-9) - 1)[:, None])[front]
        w[front] = 1.0
        # the model's outline in the master: in or out to his outline
        rim = seen & (np.abs(facing) < 0.25)
        s = map_coordinates(sd, [uv[:, 1], uv[:, 0]], order=1)
        mm_px = z / cam["f"]
        n_img = Np_ - np.einsum("ij,ij->i", Np_, ray)[:, None] * ray  # normal across the line of sight
        n_img /= np.maximum(np.linalg.norm(n_img, axis=1, keepdims=True), 1e-9)
        mv = (-s * mm_px)[:, None] * n_img
        d[rim & ~front] = mv[rim & ~front]
        w[rim & ~front] = 1.0
        d = to_rest(V, d, pose)
        # one smooth field: data where given, gentle bending elsewhere
        Wd = sp.diags(w)
        solve = factorized((Wd + a.smooth * (L @ L) + 1e-9 * sp.eye(len(V))).tocsc())
        D = np.stack([solve(w * d[:, i]) for i in range(3)], 1)
        V = V + D
        print(f"round {r}: front points {front.sum()}, outline points {(rim & ~front).sum()}, "
              f"move mm mean {np.linalg.norm(D, axis=1).mean()*1000:.2f} max {np.linalg.norm(D, axis=1).max()*1000:.2f}", flush=True)
    # finer, then every front point exactly on his front surface
    for _ in range(a.levels):
        V, F = split(V, F)
    Vp = posed(V, pose)
    uv, z = proj(Vp)
    (_,), zb = splat(Vp, F, [np.zeros(len(V), np.int8)], proj, H, W)
    px = np.clip(np.round(uv).astype(int), 0, [W - 1, H - 1])
    seen = np.abs(z - zb[px[:, 1], px[:, 0]]) < 0.0008
    zt = map_coordinates(zs, [uv[:, 1], uv[:, 0]], order=1)
    vv = map_coordinates(valid.astype(float), [uv[:, 1], uv[:, 0]], order=1)
    snap = seen & (vv > 0.99) & (zt > 0) & (np.abs(zt - z) < 0.002)
    d = np.zeros_like(V)
    d[snap] = ((Vp - pos) * (zt / np.maximum(z, 1e-9) - 1)[:, None])[snap]
    V = V + to_rest(V, d, pose)
    print(f"fine surface: {len(V)} points; {snap.sum()} placed exactly on his front", flush=True)
    C.write_obj(out / "head.obj", np.vstack([V, Ve]), np.vstack([F, Fe + len(V)]))
    for e in md.glob("eye_*.obj"):
        shutil.copy(e, out / e.name)
    if len(Ve):
        C.write_obj(out / "ears.obj", Ve, Fe)


if __name__ == "__main__":
    main()
