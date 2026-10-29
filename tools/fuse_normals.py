"""His normals from every side, onto the model (docs/MEASURING.md, "Normals
from every side onto the model", steps 2-3).

Each model point is seen through each photo's own camera (his head turned
as he held it there). Where the point is visible there (not hidden behind
another part), inside his outline and away from its edge, the
photo's surface direction at that pixel is taken back to the world and to
his head at rest: one reading per photo.

The readings are blended into one target direction per point:
- the master counts most (MASTER_W); every other photo 1;
- a photo counts more where it sees the surface face-on (weight cos^2 of
  the angle between the model's surface and the line of sight; nothing
  beyond 70 deg);
- photos where his body is in another posture count for his head only;
- a reading more than 30 deg from the blend is dropped (he moved, his fur
  lay differently, or that scan misread him) and the blend is made again.
The normals almost always win over the model (owner): the target is his,
not a compromise with the current surface.

writes checkpoints/cp5/fused/: target.npy (per vertex, world, unit),
weight.npy, readings.npy (how many photos), spread.npy (deg, how much the
kept readings disagree), off.npy (deg, current model vs target), and
master.jpg / profile.jpg: the model through that camera, its current surface
direction | the target | the angle between (green 0, red 40+).

usage: python tools/fuse_normals.py MODEL_DIR VIEW [VIEW ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
from maps_model import camera, posed, splat, vertex_normals  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "checkpoints/cp5/fused"
MASTER_W = 4.0
DROP_DEG = 30.0


def head_only(view):
    p = ROOT / f"checkpoints/cp4/cams/{view}.json"
    return p.exists() and "his head" in json.loads(p.read_text()).get("relative_to", "")


def readings(V, F, view, Vocc, Focc):
    """Per vertex: the photo's surface direction (world, his head at rest) and its weight."""
    mp = ROOT / f"checkpoints/cp5/maps/{view}"
    Np = np.load(mp / "normals.npy").astype(float)
    # all of him (nose, mouth and eyes included: their surface counts too),
    # away from his outline, where fur is see-through
    fur = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{view}.png").convert("L")) > 127
    fur = nd.binary_erosion(fur, iterations=10)
    H, W = fur.shape
    proj, Rc, pose = camera(view)
    Vp, Vop = posed(V, pose), posed(Vocc, pose)
    (_,), zbuf = splat(Vop, Focc, [np.zeros(len(Vop), np.int8)], proj, H, W)
    uv, z = proj(Vp)
    px = np.round(uv).astype(int)
    ok = (px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < H) & (z > 0)
    pi = np.where(ok, px[:, 1], 0), np.where(ok, px[:, 0], 0)
    ok &= np.abs(z - zbuf[pi]) < 0.002  # not hidden
    ok &= fur[pi]
    Nm = vertex_normals(Vp, F)
    sight = proj.pos - Vp  # line of sight: from each point toward the camera
    sight /= np.linalg.norm(sight, axis=1, keepdims=True)
    c = np.einsum("ij,ij->i", Nm, sight)
    ok &= c > np.cos(np.radians(70))
    w = np.where(ok, c ** 2, 0.0)
    if view == "master_front_standing":
        w *= MASTER_W
    hw = head_weight(V)
    if head_only(view):
        w *= hw > 0.9
    n_cam = Np[pi] * np.array([1, -1, -1])  # photo frame (x right, y up, z to camera) -> camera (y down, z forward)
    n_world = n_cam @ Rc  # camera -> world
    if pose:  # back to his head at rest (head points only)
        Rh = R.from_rotvec(pose["rotvec"]).as_matrix()
        back = n_world @ Rh  # R^T n
        n_world = np.where((hw > 0.5)[:, None], back, n_world)
    n_world /= np.maximum(np.linalg.norm(n_world, axis=1, keepdims=True), 1e-9)
    return n_world, w


def blend(Ns, Ws):
    Ns, Ws = np.stack(Ns), np.stack(Ws)  # views x points (x 3)
    t = (Ws[..., None] * Ns).sum(0)
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    for _ in range(2):  # drop readings far from the blend, blend again
        ang = np.degrees(np.arccos(np.clip(np.einsum("vpi,pi->vp", Ns, t), -1, 1)))
        keep = (ang < DROP_DEG) | ((Ws > 0).sum(0) < 3)[None]
        Wk = Ws * keep
        t2 = (Wk[..., None] * Ns).sum(0)
        good = np.linalg.norm(t2, axis=1) > 1e-6
        t[good] = t2[good] / np.linalg.norm(t2[good], axis=1, keepdims=True)
    ang = np.degrees(np.arccos(np.clip(np.einsum("vpi,pi->vp", Ns, t), -1, 1)))
    spread = np.where(Wk.sum(0) > 0, (Wk * ang).sum(0) / np.maximum(Wk.sum(0), 1e-9), np.nan)
    return t, Wk.sum(0), (Wk > 0).sum(0), spread


def show(V, F, cur, tgt, view, name, wsum):
    mp = ROOT / f"checkpoints/cp5/maps/{view}/light.json"
    img = Image.open(ROOT / json.loads(mp.read_text())["photo"]).convert("RGB")
    W, H = img.size
    proj, Rc, pose = camera(view)
    Vp = posed(V, pose)
    to_photo = lambda N: (N @ Rc.T) * np.array([1, -1, -1])
    Rh = R.from_rotvec(pose["rotvec"]).as_matrix() if pose else np.eye(3)
    hw = head_weight(V)[:, None] > 0.5
    tgt_p = np.where(hw, tgt @ Rh.T, tgt)  # target turned with his head as in this photo
    has = (wsum > 0).astype(float)
    (a, b, h), z = splat(Vp, F, [to_photo(vertex_normals(Vp, F)), to_photo(tgt_p), has[:, None].repeat(3, 1)], proj, H, W)
    seen = np.isfinite(z)
    have = seen & (np.nan_to_num(h[..., 0]) > 0.5)

    def nimg(N, m):
        im = ((np.nan_to_num(N) * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
        im[~m] = 255
        return Image.fromarray(im)
    a_n = a / np.maximum(np.linalg.norm(np.nan_to_num(a), axis=-1, keepdims=True), 1e-9)
    b_n = b / np.maximum(np.linalg.norm(np.nan_to_num(b), axis=-1, keepdims=True), 1e-9)
    ang = np.degrees(np.arccos(np.clip((np.nan_to_num(a_n) * np.nan_to_num(b_n)).sum(-1), -1, 1)))
    s = (ang / 40).clip(0, 1)
    av = np.stack([255 * s, 255 * (1 - s), np.full_like(s, 60)], -1).astype(np.uint8)
    av[~have] = 255
    tiles = [img, nimg(a_n, seen), nimg(b_n, have), Image.fromarray(av)]
    names = ["his photo", "model now", "his normals from every side (target)", "model vs target (green 0, red 40+ deg)"]
    T = 460
    sheet = Image.new("RGB", (4 * (T + 6), T + 22), "white")
    d = ImageDraw.Draw(sheet)
    for i, (t, nme) in enumerate(zip(tiles, names)):
        t = t.copy()
        t.thumbnail((T, T))
        sheet.paste(t, (i * (T + 6), 22))
        d.text((i * (T + 6) + 4, 4), nme, fill=(0, 0, 0))
    sheet.save(OUT / f"{name}.jpg", quality=85)


def main():
    md = Path(sys.argv[1])
    V, F = load_obj(md / "head.obj")
    occ = [(V, F)] + [load_obj(e) for e in sorted(md.glob("eye_*.obj"))]
    Vocc = np.vstack([o[0] for o in occ])
    Focc = np.vstack([o[1] + sum(len(q[0]) for q in occ[:i]) for i, o in enumerate(occ)])
    Ns, Ws = [], []
    for view in sys.argv[2:]:
        n, w = readings(V, F, view, Vocc, Focc)
        Ns.append(n)
        Ws.append(w)
        print(view, "points read", int((w > 0).sum()), flush=True)
    t, wsum, cnt, spread = blend(Ns, Ws)
    cur = vertex_normals(V, F)
    off = np.degrees(np.arccos(np.clip((cur * t).sum(1), -1, 1)))
    OUT.mkdir(parents=True, exist_ok=True)
    for k, v in dict(target=t, weight=wsum, readings=cnt, spread=spread, off=off).items():
        np.save(OUT / f"{k}.npy", v)
    has = wsum > 0
    print(f"points with a target: {has.mean()*100:.0f}%; readings per point median {np.median(cnt[has]):.0f}; "
          f"spread median {np.nanmedian(spread[has]):.1f} deg; model vs target median {np.median(off[has]):.1f} deg", flush=True)
    show(V, F, cur, t, "master_front_standing", "master", wsum)
    if "sheet_03_right_profile" in sys.argv[2:]:
        show(V, F, cur, t, "sheet_03_right_profile", "profile", wsum)


if __name__ == "__main__":
    main()
