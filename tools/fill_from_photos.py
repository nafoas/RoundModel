"""Step 2 of tasks/03_from_master_front.md: the rest of him filled in from
the other photos, the master's front never moved.

A block of cubes bigger than him (world frame = him as in the master).
- The master is a hard rule: a cube is cut if it is in front of his front
  surface (step 1, work/m/front/depth.npy) or outside his outline in the
  master (ears left out: they come later).
- Every other photo with a reliable camera carves gently, as before
  (docs/CARVING.md): a cube is cut where two photos say it is outside his
  outline by more than their tolerance, or one says so by more than 1.5x.
  A photo says nothing about cubes outside its own frame (close-ups).
  Photos where his body is in another posture carve his head only.
- His head in each photo: that photo's head pose (solved against the old
  model's frame) re-expressed from the master's: each cube is first taken
  from the master's head pose back to that frame, then posed as in the photo.
- Surface by marching cubes, relaxed; then every point the master sees is
  placed exactly on his front (along its master ray), so the front is the
  step-1 front.

usage: python tools/fill_from_photos.py FRONT_DIR OUT_DIR [--step 0.001]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd
from scipy.ndimage import map_coordinates
from scipy.spatial.transform import Rotation as R
from skimage import measure

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from maps_model import camera, posed, splat  # noqa: E402
from master_shell import master_intrinsics  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MASTER = "master_front_standing"
# photo: tolerance (px in that photo)
VIEWS = {"sheet_09_top_down": 3, "sheet_03_right_profile": 6, "sheet_07_left_profile": 10,
         "sheet_02_front_3q": 8, "sheet_08_front_3q_left": 8, "sheet_04_back_3q_right": 8,
         "sheet_05_back": 2, "sheet_06_back_3q_left": 2, "s01": 6, "s18": 6,
         "e_back_3q_left_high": 8, "c02": 12, "c21": 12, "c08": 10, "c10": 10, "c09": 12,
         "c26": 12, "c03": 12, "c14": 12, "c12": 12, "s11": 10, "s17": 10}


def unpose(P, pose):
    """From his head as in the master back to the old model's frame."""
    if not pose:
        return P
    Rm = R.from_rotvec(pose["rotvec"]).as_matrix()
    Q = (P - NECK_PIVOT - np.asarray(pose["shift_m"])) @ Rm + NECK_PIVOT
    hw = head_weight(P)[:, None]
    return P + hw * (Q - P)


def view_mask(name):
    p = ROOT / f"checkpoints/cp4/cams/{name}.json"
    if p.exists():
        m = ROOT / f"checkpoints/cp4/outlines/{name}.png"
        head_only = "his head" in json.loads(p.read_text()).get("relative_to", "")
        return np.asarray(Image.open(m).convert("L")) > 127, head_only
    _, mask = C.view_data(name)
    return mask, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("front")
    ap.add_argument("out")
    ap.add_argument("--step", type=float, default=0.001)
    ap.add_argument("--votes", type=int, default=2)
    ap.add_argument("--hard", type=float, default=1.5)
    a = ap.parse_args()
    fd, out = Path(a.front), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    zfront = np.load(fd / "depth.npy")
    Vf, Ff = load_obj(fd / "head.obj")
    f, pp, Rc, pos, mpose = master_intrinsics()
    noears = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{MASTER}.noears.png").convert("L")) > 127
    Hm, Wm = noears.shape
    # the block: his front's width and height, and well back of it
    lo = np.array([Vf[:, 0].min() - 0.015, Vf[:, 1].max() - 0.20, Vf[:, 2].min() - 0.015])
    hi = np.array([Vf[:, 0].max() + 0.015, Vf[:, 1].max() + 0.005, Vf[:, 2].max() + 0.03])
    axes = [np.arange(lo[i], hi[i], a.step) for i in range(3)]
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    print("cubes", tuple(len(x) for x in axes), flush=True)
    # master: hard
    Xc = (G - pos) @ Rc.T
    uv = f * Xc[:, :2] / Xc[:, 2:3] + pp
    inside_m = map_coordinates(noears.astype(float), [uv[:, 1], uv[:, 0]], order=1, cval=0) > 0.5
    zf = map_coordinates(np.nan_to_num(zfront, nan=0), [uv[:, 1], uv[:, 0]], order=0, cval=0)
    keep = inside_m & (zf > 0) & (Xc[:, 2] >= zf)
    print("master keeps", int(keep.sum()), flush=True)
    votes = np.zeros(len(G), np.int16)
    hard = np.zeros(len(G), bool)
    Gold = unpose(G, mpose)
    hwG = head_weight(Gold)
    for name, tol in VIEWS.items():
        try:
            proj, _, pose = camera(name)
            mask, head_only = view_mask(name)
        except Exception as e:  # noqa: BLE001
            print("skip", name, e)
            continue
        H, W = mask.shape
        sd = nd.distance_transform_edt(~mask) - nd.distance_transform_edt(mask)  # + outside him (px)
        idx = np.nonzero(keep)[0]
        uvv, z = proj(posed(Gold[idx], pose))
        inframe = (uvv[:, 0] >= 2) & (uvv[:, 0] < W - 2) & (uvv[:, 1] >= 2) & (uvv[:, 1] < H - 2) & (z > 0)
        s = map_coordinates(sd, [uvv[:, 1], uvv[:, 0]], order=1, cval=-1e3)
        out_ = inframe & (s > tol)
        if head_only:
            out_ &= hwG[idx] > 0.9
        votes[idx[out_]] += 1
        hard[idx[inframe & (s > a.hard * tol) & ((not head_only) | (hwG[idx] > 0.9))]] = True
        print(f"{name}: says outside {out_.sum()}", flush=True)
    cut = (votes >= a.votes) | hard
    vol = (keep & ~cut).reshape(tuple(len(x) for x in axes))
    vol = nd.binary_fill_holes(vol)
    lab, n = nd.label(vol)
    if n > 1:
        vol = lab == 1 + int(np.argmax(nd.sum(vol, lab, range(1, n + 1))))
    print("him", int(vol.sum()), "cubes", flush=True)
    np.save(out / "volume.npy", vol)
    fv = nd.gaussian_filter(vol.astype(np.float32), 1.2)
    V, F, _, _ = measure.marching_cubes(np.pad(fv, 2), 0.5, spacing=(a.step,) * 3)
    V += lo - 2 * a.step
    F = F[:, ::-1]
    # the master's front exactly: points the master sees, near his front, along their ray onto it
    uvq = (f * ((V - pos) @ Rc.T)[:, :2] / ((V - pos) @ Rc.T)[:, 2:3]) + pp
    zq = ((V - pos) @ Rc.T)[:, 2]
    proj_m, _, _ = camera(MASTER)

    def proj_new(P):  # master camera, him as in the master (no pose)
        X = (P - pos) @ Rc.T
        return f * X[:, :2] / X[:, 2:3] + pp, X[:, 2]
    (_,), zb = splat(V, F, [np.zeros(len(V), np.int8)], proj_new, Hm, Wm)
    px = np.clip(np.round(uvq).astype(int), 0, [Wm - 1, Hm - 1])
    seen = np.abs(zq - zb[px[:, 1], px[:, 0]]) < 2 * a.step
    zt = map_coordinates(np.nan_to_num(zfront, nan=0), [uvq[:, 1], uvq[:, 0]], order=1, cval=0)
    snap = seen & (zt > 0) & (np.abs(zt - zq) < 4 * a.step)
    V[snap] = pos + (V[snap] - pos) * (zt[snap] / zq[snap])[:, None]
    C.write_obj(out / "head.obj", V, F)
    print(f"surface {len(V)} points; {snap.sum()} placed exactly on his front", flush=True)


if __name__ == "__main__":
    main()
