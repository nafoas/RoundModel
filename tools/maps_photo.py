"""Maps from his photos (docs/MEASURING.md step C), inside his outline only.

For each photo:
1. Surface direction (normals) from a single-image estimator: Marigold
   normals (prs-eth/marigold-normals-v1-1, through diffusers; DSINE, the
   plan's first choice, needs code fetched from GitHub, which this
   environment does not allow). Several runs averaged (ensemble) so fur
   texture does not show as bumps. Camera frame: x right, y up, z toward
   the camera.
2. Relative depth from Depth Anything V2 (Large), for ordering only (what
   is nearer), not size.
3. His fur: inside his outline, bright and nearly colourless (eyes, nose,
   inner ears and deep shadow left out). One colour all over, so its
   brightness depends on which way it faces and the light.
4. The light: a low-order light (ambient + one direction; first-order
   spherical harmonics) fitted to his fur brightness against the normals.
   The fit's leftover (brightness the light and those normals don't
   explain) is a second, independent read of his surface: where it is
   large, the estimated normals and his shading disagree.

writes checkpoints/cp5/maps/<view>/ normals.npy (float16, HxWx3), depth.npy,
fur.png, light.json, and review.jpg (photo | normals | depth | shading
leftover), each to be checked by eye on the photo before use.

usage: python tools/maps_photo.py VIEW [VIEW ...]   (view names as in
checkpoints/cp4/outlines/, e.g. master_front_standing, c25, s01)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "checkpoints/cp5/maps"


def photo_of(view):
    if view == "master_front_standing":
        return ROOT / "references/master/master_front_standing.webp"
    L = json.loads((ROOT / "checkpoints/cp4/cams/landmarks2d.json").read_text())
    if view in L:
        return ROOT / L[view]["photo"]
    if view.startswith("sheet_"):  # sheet_02_front_3q -> references/sheet_originals/02_front_3q.webp
        p = ROOT / f"references/sheet_originals/{view[6:]}.webp"
        if p.exists():
            return p
    raise SystemExit(f"no photo known for {view}")


def fur_mask(rgb, outline):
    v = rgb.max(-1)
    sat = (v - rgb.min(-1)) / np.maximum(v, 1)
    fur = outline & (sat < 0.28) & (v > 90)  # his bib has a lavender cast: still fur
    # keep away from the outline itself (fur edge is translucent, mixed with background)
    fur &= nd.binary_erosion(outline, iterations=6)
    return nd.binary_opening(fur, iterations=2)


def fit_light(gray, N, m):
    """I = a + b . n over his fur (first-order spherical harmonics)."""
    A = np.c_[np.ones(m.sum()), N[m]]
    coef, *_ = np.linalg.lstsq(A, gray[m], rcond=None)
    pred = np.zeros_like(gray)
    pred[m] = A @ coef
    d = coef[1:] / max(np.linalg.norm(coef[1:]), 1e-9)
    return coef, d, pred


def colour_normals(N, m):
    im = ((N * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    im[~m] = 255
    return Image.fromarray(im)


def main():
    import torch
    from diffusers import MarigoldNormalsPipeline
    from transformers import pipeline
    torch.set_num_threads(4)
    normals_pipe = MarigoldNormalsPipeline.from_pretrained("prs-eth/marigold-normals-v1-1", torch_dtype=torch.float32)
    depth_pipe = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-Large-hf", device="cpu")
    for view in sys.argv[1:]:
        src = photo_of(view)
        img = Image.open(src).convert("RGB")
        rgb = np.asarray(img).astype(float)
        H, W = rgb.shape[:2]
        outline = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{view}.png").convert("L")) > 127
        r = normals_pipe(img, num_inference_steps=4, ensemble_size=4, processing_resolution=768,
                         generator=torch.Generator().manual_seed(0))
        N = np.asarray(r.prediction[0], float)[:H, :W]
        N /= np.maximum(np.linalg.norm(N, axis=-1, keepdims=True), 1e-9)
        D = np.asarray(depth_pipe(img)["predicted_depth"], float)
        if D.shape != (H, W):
            D = np.asarray(Image.fromarray(D.astype(np.float32)).resize((W, H), Image.BILINEAR))
        fur = fur_mask(rgb, outline)
        gray = rgb.mean(-1) / 255.0
        coef, ldir, pred = fit_light(gray, N, fur)
        resid = np.where(fur, gray - pred, 0.0)
        r2 = 1 - (resid[fur] ** 2).mean() / gray[fur].var()
        out = OUT / view
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "normals.npy", N.astype(np.float16))
        np.save(out / "depth.npy", D.astype(np.float32))
        Image.fromarray((fur * 255).astype(np.uint8)).save(out / "fur.png")
        (out / "light.json").write_text(json.dumps({
            "photo": str(src.relative_to(ROOT)),
            "frame": "camera: x right, y up, z toward the camera",
            "light_dir": np.round(ldir, 3).tolist(),
            "ambient": round(float(coef[0]), 3), "directional": round(float(np.linalg.norm(coef[1:])), 3),
            "shading_explained": round(float(r2), 3),
            "note": "his fur brightness = ambient + directional * (normal . light_dir), fitted over his fur. From a front view nearly all fur faces the camera, so the light's z (toward the camera) is not pinned: read its x (right) and y (up) only"}, indent=1))
        # review: photo | normals | depth | shading leftover (red: brighter than the light
        # and normals predict, blue: darker)
        T = 520
        ph = img.copy()
        nm = colour_normals(N, outline)
        dd = np.where(outline, D, np.nan)
        lo, hi = np.nanpercentile(dd, 2), np.nanpercentile(dd, 98)
        dv = ((np.nan_to_num((dd - lo) / max(hi - lo, 1e-9), nan=0)).clip(0, 1) * 255).astype(np.uint8)
        dv = np.where(outline, dv, 255).astype(np.uint8)
        dimg = Image.fromarray(np.stack([dv] * 3, -1))
        s = (resid / 0.15).clip(-1, 1)
        rv = np.full((H, W, 3), 255, np.uint8)
        rv[..., 0] = np.where(s < 0, 255 * (1 + s), 255).astype(np.uint8)
        rv[..., 1] = (255 * (1 - np.abs(s))).astype(np.uint8)
        rv[..., 2] = np.where(s > 0, 255 * (1 - s), 255).astype(np.uint8)
        rv[~fur] = (235, 235, 235)
        rv[~outline] = 255
        tiles = [ph, nm, dimg, Image.fromarray(rv)]
        for t in tiles:
            t.thumbnail((T, T))
        sheet = Image.new("RGB", (4 * (T + 6), T), "white")
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * (T + 6), 0))
        sheet.save(out / "review.jpg", quality=85)
        print(view, "light dir", np.round(ldir, 2), "shading explained", round(float(r2), 2), flush=True)


if __name__ == "__main__":
    main()
