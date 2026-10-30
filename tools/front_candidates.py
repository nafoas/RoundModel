"""New fronts for the master, from different estimators (owner: "make new
normals"; front only for now). Judged against docs/FEATURES.md, from the
front AND the side, before anything else is built.

Candidates (each gives a depth map of his front, inside his outline; the
surface's own normals follow from it):
- depthpro: Apple Depth Pro (metric depth, sharp detail), via transformers.
- marigold_depth: Marigold's depth model (prs-eth/marigold-depth-v1-1), via
  diffusers: a different model from the normals one that gave the mask.
- dav2: Depth Anything V2 Large (already made: checkpoints/cp5/maps).
Depth Pro's depth is in metres; the other two are relative, so their depth
(how far his face goes back) is matched to Depth Pro's over his outline (one
scale and one shift). All are then put at his distance (nose tip at the
master camera's depth for it, as step 1).

writes work/m/cand/<name>/head.obj, depth.npy (for tools/parts_sheet.py)
and checkpoints/cp6/front_candidates.jpg (photo | each, lit the same way).

usage: python tools/front_candidates.py
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from master_shell import master_intrinsics  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VIEW = "master_front_standing"
PHOTO = ROOT / "references/master/master_front_standing.webp"


def depthpro(img):
    import torch
    from transformers import DepthProForDepthEstimation, DepthProImageProcessorFast
    proc = DepthProImageProcessorFast.from_pretrained("apple/DepthPro-hf")
    model = DepthProForDepthEstimation.from_pretrained("apple/DepthPro-hf").eval()
    with torch.no_grad():
        out = model(**proc(images=img, return_tensors="pt"))
    post = proc.post_process_depth_estimation(out, target_sizes=[(img.height, img.width)])
    return post[0]["predicted_depth"].numpy().astype(float)


def marigold_depth(img):
    import torch
    from diffusers import MarigoldDepthPipeline
    pipe = MarigoldDepthPipeline.from_pretrained("prs-eth/marigold-depth-v1-1", torch_dtype=torch.float32)
    r = pipe(img, num_inference_steps=4, ensemble_size=4, processing_resolution=768,
             generator=torch.Generator().manual_seed(0))
    d = np.asarray(r.prediction[0], float).squeeze()  # 0 near .. 1 far (affine)
    return d


def match(rel, ref, m, inverse=False):
    """Scale and shift rel to ref over m (least squares); inverse: rel is nearness."""
    x = -rel[m] if inverse else rel[m]
    A = np.c_[x, np.ones(m.sum())]
    (s, t), *_ = np.linalg.lstsq(A, ref[m], rcond=None)
    return (-rel if inverse else rel) * s + t


def mesh_from_depth(z, f, pp, Rc, pos, out):
    H, W = z.shape
    v, u = np.mgrid[0:H, 0:W]
    ray = np.stack([(u - pp[0]) / f, (v - pp[1]) / f, np.ones((H, W))], -1)
    P = pos + (ray * z[..., None]) @ Rc
    ok = np.isfinite(z)
    idx = -np.ones((H, W), int)
    idx[ok] = np.arange(ok.sum())
    a, b, c, d = idx[:-1, :-1], idx[:-1, 1:], idx[1:, :-1], idx[1:, 1:]
    q = (a >= 0) & (b >= 0) & (c >= 0) & (d >= 0)
    F = np.vstack([np.c_[a[q], c[q], b[q]], np.c_[b[q], c[q], d[q]]])
    out.mkdir(parents=True, exist_ok=True)
    C.write_obj(out / "head.obj", P[ok], F)
    np.save(out / "depth.npy", z.astype(np.float32))
    return P


def shade(z, f, pp, Rc):
    H, W = z.shape
    v, u = np.mgrid[0:H, 0:W]
    Pc = np.stack([(u - pp[0]) / f * z, (v - pp[1]) / f * z, z], -1)
    n = np.cross(np.gradient(Pc, axis=1), np.gradient(Pc, axis=0))
    n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-12)
    L = np.array([-0.4, -0.5, -0.77])
    L /= np.linalg.norm(L)
    s = np.clip(-(n @ L), 0, 1) * 0.85 + 0.15
    return Image.fromarray((np.nan_to_num(s, nan=1.0) * 255).astype(np.uint8)).convert("RGB")


def main():
    img = Image.open(PHOTO).convert("RGB")
    f, pp, Rc, pos, _ = master_intrinsics()
    noears = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{VIEW}.noears.png").convert("L")) > 127
    m = nd.binary_erosion(noears, iterations=2)
    L2 = json.loads((ROOT / "references/landmarks.json").read_text())["views"][VIEW]["points"]
    nu, nv = np.asarray(L2["nose_tip"], int)
    z_nose = float(np.nanmedian(np.load(ROOT / "work/m/front/depth.npy")[nv - 3:nv + 4, nu - 3:nu + 4]))
    cands = {}
    dp = depthpro(img)
    cands["depthpro"] = dp
    print("depth pro: median depth", np.median(dp[m]), "m", flush=True)
    md = marigold_depth(img)
    cands["marigold_depth"] = match(md, dp, m)
    dav = np.load(ROOT / f"checkpoints/cp5/maps/{VIEW}/depth.npy").astype(float)
    cands["dav2"] = match(dav, dp, m, inverse=True)
    tiles = [("his photo", img.copy())]
    for name, z in cands.items():
        z = np.where(m, z, np.nan)
        z = z * (z_nose / np.nanmedian(z[nv - 3:nv + 4, nu - 3:nu + 4]))  # his distance
        zz = z.copy()
        zz[m] = nd.gaussian_filter(np.nan_to_num(z, nan=np.nanmedian(z)), 1.0)[m]  # pixel noise off
        mesh_from_depth(zz, f, pp, Rc, pos, ROOT / f"work/m/cand/{name}")
        rel = zz - z_nose
        print(f"{name}: depth behind his nose: eyes ~{np.nanmedian(rel[int(L2['eye_R'][1])-4:int(L2['eye_R'][1])+5, int(L2['eye_R'][0])-4:int(L2['eye_R'][0])+5])*1000:.0f} mm, "
              f"outline up to {np.nanmax(rel)*1000:.0f} mm", flush=True)
        tiles.append((name, shade(zz, f, pp, Rc)))
    T = 480
    sheet = Image.new("RGB", (len(tiles) * (T + 6), T + 30), "white")
    d = ImageDraw.Draw(sheet)
    for i, (nme, t) in enumerate(tiles):
        t.thumbnail((T, T))
        sheet.paste(t, (i * (T + 6), 30))
        d.text((i * (T + 6) + 4, 4), nme, fill=(0, 0, 0), font_size=22)
    sheet.save(ROOT / "checkpoints/cp6/front_candidates.jpg", quality=88)


if __name__ == "__main__":
    main()
