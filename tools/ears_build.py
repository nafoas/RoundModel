"""His ears (docs/CARVING.md 14). Carved the same way as his body: the
block carved with the ears left in his outlines (carve.py --ears), minus
the ear-less carving (dilated a little so only what stands above his head
is taken), above his head only. Made symmetric about his body midline
(checkpoints/cp4/midline.json), meshed, and joined to the body mesh.

usage: python tools/ears_build.py EARS_CARVE_DIR BODY_CARVE_DIR BODY_MODEL_DIR OUT_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as nd

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402


def main():
    ed, bd, md, out = map(Path, sys.argv[1:5])
    ev, bv = np.load(ed / "volume.npy"), np.load(bd / "volume.npy")
    meta = json.loads((ed / "carve.json").read_text())
    step, o = meta["step"], np.array(meta["origin"])
    axes = [o[i] + step * np.arange(ev.shape[i]) for i in range(3)]
    Z = axes[2][None, None, :]
    ear = ev & ~nd.binary_dilation(bv, iterations=2) & (Z > 0.13)
    # only what lies in his ears as the master shows them (the outline minus
    # the ear-less outline, a little widened): not the head top between them
    from PIL import Image
    C.NO_EARS = False
    cam, full = C.view_data("master_front_standing")
    noe = np.asarray(Image.open(C.ROOT / "checkpoints/cp4/outlines/master_front_standing.noears.png")) > 127
    em = nd.binary_dilation(full & ~noe, iterations=6)
    idx = np.argwhere(ear)
    P = o + idx * step
    uv = np.round(C.project(C.posed(P, cam["pose"]), cam)).astype(int)
    H, W = em.shape
    ok = (uv[:, 0] >= 0) & (uv[:, 0] < W) & (uv[:, 1] >= 0) & (uv[:, 1] < H)
    inear = np.zeros(len(P), bool)
    inear[ok] = em[uv[ok, 1], uv[ok, 0]]
    ear[tuple(idx[~inear].T)] = False
    ear = nd.binary_opening(ear, iterations=1)
    lab, n = nd.label(ear)
    sz = nd.sum(ear, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sz) if s > 0.15 * sz.max()]
    ear = np.isin(lab, keep)
    print("ear pieces", len(keep), "cubes", int(ear.sum()))
    # symmetric about his body midline
    pl = json.loads((C.ROOT / "checkpoints/cp4/midline.json").read_text())
    nrm = np.array([np.cos(pl["turn_rad"]), np.sin(pl["turn_rad"]), 0.0])
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    d = (G - [pl["x_m"], 0, 0]) @ nrm
    Gm = G - 2 * d[:, None] * nrm
    sdf = nd.distance_transform_edt(~ear) - nd.distance_transform_edt(ear)
    sm = nd.map_coordinates(sdf, ((Gm - o) / step).T, order=1, mode="nearest").reshape(ear.shape)
    ear = (sdf + sm) / 2 < 0
    # reach down into the body so they join without a gap
    ear = ear | (nd.binary_dilation(ear, iterations=2) & bv & (Z > 0.13))
    Ve, Fe = C.mesh(ear, axes, step, smooth_iters=20)
    Vb, Fb = load_obj(md / "head.obj")
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", np.vstack([Vb, Ve]), np.vstack([Fb, Fe + len(Vb)]))
    C.write_obj(out / "ears.obj", Ve, Fe)
    print("ears: extent", Ve.min(0).round(3), Ve.max(0).round(3))


if __name__ == "__main__":
    main()
