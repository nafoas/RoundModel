"""His ears as built leaves (docs/CARVING.md 14). Carving cannot make his
ears: they move independently and are held differently in each photo, so
the photos never agree and the carving cuts them to stubs.

Each ear is a thin, cupped leaf:
- its flat shape is his ear outline in the right profile, where the ear is
  seen nearly flat-on (outline minus the ear-less outline), back-projected
  onto the vertical plane through the ear's base (his head posed as there,
  then un-posed) and extended down into his head so the base is buried;
- thick, soft and rounded like his (about 7 mm with fur, rounded edges),
  flaring at the base into his head fur so there is no seam;
- cupped: the edges stand out toward his side, the opening facing outward;
- turned about the vertical so the opening faces forward-outward (`turn`,
  from the master's ear width against the profile's);
- tipped outward by `lean` degrees about its base (master: the ears lean out
  a little);
- the left ear is the mirror of the right across his midline.

usage: python tools/ears_leaf.py BODY_DIR OUT_DIR [--x 0.021] [--lean 12] [--cup 0.004] [--thick 0.003]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd
from scipy.spatial.transform import Rotation as R
from skimage import measure

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402

G = 0.0004  # grid of the leaf (m)


def unpose(P, pose):
    from sculpt import NECK_PIVOT
    if pose is None:
        return P
    Rm = R.from_rotvec(pose["rotvec"]).as_matrix()
    return (P - NECK_PIVOT - np.asarray(pose["shift_m"])) @ Rm + NECK_PIVOT


def ear_shape(view, x_plane):
    """(y, z) points of the ear, in the plane x = x_plane, un-posed."""
    C.NO_EARS = False
    cam, full = C.view_data(view)
    noe = np.asarray(Image.open(C.ROOT / f"checkpoints/cp4/outlines/{view}.noears.png")) > 127
    ear = full & ~noe
    lab, n = nd.label(ear)
    sz = nd.sum(ear, lab, range(1, n + 1))
    ear = lab == 1 + int(np.argmax(sz))
    ys, xs = np.nonzero(ear)
    uv = np.stack([xs, ys], 1).astype(float)
    # undo the per-photo alignment, then cast rays
    a = cam.get("align")
    if a:
        c = np.asarray(a["c"])
        th = np.radians(a["roll_deg"])
        Rm = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        q = uv - c - np.asarray(a["t"])
        q[:, 1] /= a.get("sy", 1.0)
        uv = (q / a["s"]) @ Rm + c
    Rc = R.from_rotvec(cam["rot"]).as_matrix()
    d = np.c_[(uv - np.asarray(cam["pp"])) / cam["f"], np.ones(len(uv))] @ Rc  # world ray directions
    o = np.asarray(cam["pos"])
    t = (x_plane - o[0]) / d[:, 0]
    P = o + t[:, None] * d
    return unpose(P, cam["pose"])[:, 1:], ear


def leaf_volume(yz, x0, args):
    lo = yz.min(0) - [0.004, 0.008]
    hi = yz.max(0) + 0.004
    ny, nz = np.ceil((hi - lo) / G).astype(int) + 1
    M = np.zeros((ny, nz), bool)
    ij = np.round((yz - lo) / G).astype(int)
    M[ij[:, 0], ij[:, 1]] = True
    M = nd.binary_closing(M, iterations=3)
    M = nd.binary_fill_holes(M)
    # bury the base: carry the bottom edge straight down 7 mm
    cols = np.nonzero(M.any(1))[0]
    for i in cols:
        zmin = np.nonzero(M[i])[0].min()
        M[i, max(zmin - int(0.007 / G), 0):zmin] = True
    M = nd.binary_opening(M, iterations=2)
    # a smooth outline (the traced edge is ragged with fur fringe)
    M = nd.gaussian_filter(M.astype(float), 0.0015 / G) > 0.5
    dist = nd.distance_transform_edt(M) * G
    yy = lo[0] + np.arange(ny) * G
    ymid = (yy[M.any(1)].min() + yy[M.any(1)].max()) / 2
    half_w = (yy[M.any(1)].max() - yy[M.any(1)].min()) / 2
    th = args.thick / 2 * np.sqrt(np.clip(dist / args.round, 0, 1))  # rounded edges (fur)
    # the base flares into his head fur (no seam where ear meets head)
    zz = lo[1] + np.arange(nz) * G
    zb = yz[:, 1].min()  # bottom of the ear as the photo shows it
    f = np.clip((zb + args.flare_h - zz) / args.flare_h, 0, 1)
    flare = f * f * (3 - 2 * f)  # smooth onset
    th = th + (args.flare / 2) * flare[None, :] * (M > 0)
    cup = args.cup * ((yy - ymid) / half_w) ** 2  # edges stand out toward his side
    pad = (args.thick + args.flare) / 2 + 0.002
    nx = int(np.ceil((args.cup + 2 * pad) / G)) + 1
    xs = x0 - pad + np.arange(nx) * G
    X = xs[:, None, None]
    Cx = x0 + cup[None, :, None]
    vol = (np.abs(X - Cx) < th[None, :, :]) & M[None, :, :]
    origin = np.array([xs[0], lo[0], lo[1]])
    return vol, origin


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("body")
    ap.add_argument("out")
    ap.add_argument("--x", type=float, default=0.021, help="ear base distance from his midline (m)")
    ap.add_argument("--lean", type=float, default=12.0)
    ap.add_argument("--cup", type=float, default=0.003)
    ap.add_argument("--turn", type=float, default=40.0, help="ear faces forward-outward by this (deg); master width vs profile width")
    ap.add_argument("--thick", type=float, default=0.007, help="ear thickness with fur (m)")
    ap.add_argument("--round", type=float, default=0.004, help="edge rounding width (m)")
    ap.add_argument("--flare", type=float, default=0.010, help="extra thickness at the base (m)")
    ap.add_argument("--flare_h", type=float, default=0.008, help="height of the base flare (m)")
    a = ap.parse_args()
    C.ALIGN = json.loads((C.ROOT / "checkpoints/cp4/view_align.json").read_text())
    pl = json.loads((C.ROOT / "checkpoints/cp4/midline.json").read_text())
    xe = pl["x_m"] + a.x  # his right ear (+x is his right)
    yz, _ = ear_shape("sheet_03_right_profile", xe)
    # the ear is turned to face forward-outward by `turn` deg; the profile saw
    # it foreshortened by cos(turn): widen it back along his length first
    yc = yz[:, 0].mean()
    yz = yz.copy()
    yz[:, 0] = yc + (yz[:, 0] - yc) / np.cos(np.radians(a.turn))
    vol, origin = leaf_volume(yz, xe, a)
    V, F, _, _ = measure.marching_cubes(np.pad(nd.gaussian_filter(vol.astype(float), 0.0012 / G), 2), 0.5, spacing=(G, G, G))
    V += origin - 2 * G
    F = F[:, ::-1]
    # lean outward about the base line (the bottom of the visible ear)
    base = np.array([xe, V[:, 1].mean(), np.percentile(V[:, 2], 25)])
    Rl = R.from_euler("y", a.lean, degrees=True).as_matrix()  # tips toward +x (his right)
    V = (V - base) @ Rl.T + base
    # turn about the vertical through its base: the opening faces forward-outward
    Rt = R.from_euler("z", a.turn, degrees=True).as_matrix()
    V = (V - base) @ Rt.T + base
    # mirror for his left ear across his midline
    nrm = np.array([np.cos(pl["turn_rad"]), np.sin(pl["turn_rad"]), 0.0])
    dd = (V - [pl["x_m"], 0, 0]) @ nrm
    Vm = V - 2 * dd[:, None] * nrm
    Fm = F[:, ::-1]
    Vb, Fb = load_obj(Path(a.body) / "head.obj")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    Vall = np.vstack([Vb, V, Vm])
    Fall = np.vstack([Fb, F + len(Vb), Fm + len(Vb) + len(V)])
    C.write_obj(out / "head.obj", Vall, Fall)
    C.write_obj(out / "ears.obj", np.vstack([V, Vm]), np.vstack([F, Fm + len(V)]))
    print("ear: width", round((V[:, 1].max() - V[:, 1].min()) * 1000, 1), "mm, height",
          round((V[:, 2].max() - V[:, 2].min()) * 1000, 1), "mm, top", round(V[:, 2].max() * 1000, 1), "mm")


if __name__ == "__main__":
    main()
