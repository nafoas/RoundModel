"""What the anchor photo sees of him, and how far away it is: every ray cut at a measured distance.

Owner's plan (2026-11-16): "Have it invent absolutely nothing." Every area of him is governed by exactly one
photo (later photos will cover other areas, with no overlap). From THIS photo: the depth of ONLY what is
visible, nothing else; shown like the rays in the room, "each ray ... brought to the exact distance calculated",
so the rays show his surface. Don't model him.

How:
- Two independent depth models, each given the photo exactly as it is, each giving one distance per pixel:
  Depth Pro (Apple, apple/DepthPro-hf) and MoGe-2 (Microsoft, Ruicheng/moge-2-vitl-normal). Each also
  estimates the camera's lens itself.
- For every pixel of him (inside his outline, data/strands/body_outline.json): the ray from OUR anchor camera
  (data/cameras.json) through that pixel, cut at that model's distance from its camera to that pixel.
  No smoothing, no filling, no merging the two models: each is kept and shown on its own.
- Checks they were NOT given, reported only (never used to change anything): the distance to his nose
  (owner: about six inches), the lens each model estimated vs ours, his width.

Usage: python tools/visible_depth.py -> data/scene/visible_depth_<model>.png (+ .json),
       docs/images/space/visible_depth_*.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prince.space import Camera  # noqa: E402

OUT_IMG = ROOT / "docs/images/space"
MODELS = {"depthpro": "apple/DepthPro-hf", "moge2": "Ruicheng/moge-2-vitl-normal"}


def load(p):
    return json.loads((ROOT / p).read_text())


def him_mask(H, W):
    """Pixels of him: inside his body outline (his ears and peets included; whiskers and wisps outside it are not)."""
    from matplotlib.path import Path as MP
    outline = np.array(load("data/strands/body_outline.json")["sampled_curve"])
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    return MP(outline).contains_points(np.c_[xx.ravel(), yy.ravel()]).reshape(H, W)


def run_depthpro(img):
    """Depth Pro: distance (m) from its camera to every pixel, and its own lens estimate."""
    import torch
    from transformers import AutoImageProcessor, DepthProForDepthEstimation
    proc = AutoImageProcessor.from_pretrained(MODELS["depthpro"])
    model = DepthProForDepthEstimation.from_pretrained(MODELS["depthpro"]).eval()
    inputs = proc(images=img, return_tensors="pt")
    with torch.no_grad():
        out = model(**inputs)
    post = proc.post_process_depth_estimation(out, target_sizes=[(img.height, img.width)])[0]
    z = post["predicted_depth"].float().numpy()                   # metres along its camera's axis
    f = float(post["focal_length"])                               # pixels, for this picture's size
    H, W = z.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    X = (xx - W / 2) / f * z; Y = (yy - H / 2) / f * z
    dist = np.sqrt(X * X + Y * Y + z * z)                          # straight-line distance to each pixel's spot
    return dict(distance_m=dist, focal_px=f, fov_deg=float(post.get("field_of_view", np.nan)))


def run_moge2(img):
    """MoGe-2: a 3D point (m) for every pixel in its own camera, and its own lens estimate."""
    import torch
    from moge.model.v2 import MoGeModel
    model = MoGeModel.from_pretrained(MODELS["moge2"]).eval()
    t = torch.tensor(np.asarray(img, dtype=np.float32) / 255.0).permute(2, 0, 1)
    with torch.no_grad():
        out = model.infer(t)
    P = out["points"].numpy()                                       # (H, W, 3) metres, its camera
    K = out["intrinsics"].numpy()                                   # normalised: fx in picture widths
    dist = np.linalg.norm(P, axis=-1)
    return dict(distance_m=dist, focal_px=float(K[0, 0] * img.width), valid=out["mask"].numpy().astype(bool))


def save_distance(name, dist_cm, mask):
    """Distance map as a 16-bit picture (units of 0.01 cm = 0.1 mm; 0 = not him)."""
    a = np.where(mask & np.isfinite(dist_cm), np.clip(np.round(dist_cm * 100), 1, 65535), 0).astype(np.uint16)
    Image.fromarray(a).save(ROOT / f"data/scene/visible_depth_{name}.png")


def checks(name, dist_cm, mask, cam, lm, focal_px):
    """Things the model was not told, reported only."""
    H, W = mask.shape
    nose = np.array(lm["nose_y_centre"]["at_px"]).astype(int)
    win = dist_cm[nose[1] - 3:nose[1] + 4, nose[0] - 3:nose[0] + 4]
    out = dict(nose_distance_cm=round(float(np.nanmedian(win)), 2), owner_remembered_cm=15.24,
               lens_px_model=round(focal_px, 1), lens_px_room_camera=round(cam.f, 1))
    # his width: the 3D distance between his outline's left and right ends at its widest row
    cam_doc = load("data/cameras.json")["anchor_front"]["widest_outline_px"]
    y = int(cam_doc["y"])
    row = np.flatnonzero(mask[y])
    if len(row):
        l_px, r_px = np.array([row[0] + 4.5, y + 0.5]), np.array([row[-1] - 3.5, y + 0.5])
        pl = cam.C + cam.ray([l_px])[0] * dist_cm[y, int(l_px[0])]
        pr = cam.C + cam.ray([r_px])[0] * dist_cm[y, int(r_px[0])]
        out["width_at_widest_outline_cm"] = round(float(np.linalg.norm(pl - pr)), 2)
    vals = dist_cm[mask]
    out["distance_range_cm"] = [round(float(np.nanpercentile(vals, 1)), 2), round(float(np.nanpercentile(vals, 99)), 2)]
    return out


def main() -> int:
    img = Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB")
    W, H = img.size
    cam = Camera.from_dict(load("data/cameras.json")["anchor_front"])
    lm = load("data/strands/landmarks.json")["landmarks"]
    mask = him_mask(H, W)
    results = {}
    for name, fn in (("depthpro", run_depthpro), ("moge2", run_moge2)):
        t0 = time.time()
        r = fn(img)
        dist_cm = r["distance_m"] * 100.0
        save_distance(name, dist_cm, mask)
        c = checks(name, dist_cm, mask, cam, lm, r["focal_px"])
        c["seconds"] = round(time.time() - t0, 1)
        if "valid" in r:
            c["model_says_invalid_px_of_him"] = int((mask & ~r["valid"]).sum())
        meta = dict(about=__doc__.split("\n\n")[0], model=MODELS[name], photo="data/photos/anchor_front.webp",
                    file=f"data/scene/visible_depth_{name}.png",
                    units="16-bit: distance from the camera to each pixel of him, in 0.01 cm; 0 = not him",
                    rays="the room's anchor camera (data/cameras.json): each pixel's ray, cut at this distance",
                    pixels_of_him=int(mask.sum()), checks_not_given_to_the_model=c,
                    invented="nothing: no smoothing, filling or merging; only what this photo sees")
        (ROOT / f"data/scene/visible_depth_{name}.json").write_text(json.dumps(meta, indent=1))
        results[name] = (dist_cm, c)
        print(name, json.dumps(c))
    d1, d2 = results["depthpro"][0], results["moge2"][0]
    diff = (d1 - d2)[mask]
    print("the two models, distance difference over his pixels (cm): median %.2f, middle 90%% %.2f to %.2f"
          % (np.median(diff), np.percentile(diff, 5), np.percentile(diff, 95)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
