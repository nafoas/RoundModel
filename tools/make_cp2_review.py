"""Build the Checkpoint 2 review images from the clay renders.

Per view: the reference | the grey shape from the same camera, with the
photo's outline (red) and the shape's silhouette (blue) drawn over it |
a difference map (grey = agree, red = in the photo but not the shape,
blue = in the shape but not the photo). Plus the turntable sheet and
an agreement table. The master is always first.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from make_cp1_review import ORDER, font, mask_stem  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CP1 = ROOT / "checkpoints/cp1"
CP2 = ROOT / "checkpoints/cp2"


def on_white(rgba):
    a = rgba[..., 3:4].astype(np.float32) / 255
    return (rgba[..., :3] * a + 255 * (1 - a)).astype(np.uint8)


def ear_zone(view, ear_tips, radius, shape):
    """Disks around the projected ear tips: the ear parts of the outline,
    which the body deliberately leaves for Checkpoint 3."""
    from scipy.spatial.transform import Rotation as R
    z = np.zeros(shape, np.uint8)
    Rm = R.from_rotvec(view["rotvec_world_to_cam"]).as_matrix()
    for tip in ear_tips:
        Xc = (np.asarray(tip) - np.asarray(view["camera_position_m"])) @ Rm.T
        uv = view["focal_px"] * Xc[:2] / Xc[2] + np.array(view["size"]) / 2
        cv2.circle(z, (int(uv[0]), int(uv[1])), int(view["focal_px"] * radius / Xc[2]), 1, -1)
    return z > 0


def panel(vn, view, renders, ear_tips=(), ear_radius=0.0):
    ref = np.asarray(Image.open(ROOT / view["image"]).convert("RGB"))
    rgba = np.asarray(Image.open(renders / f"{vn}.png").convert("RGBA"))
    clay = on_white(rgba)
    sil = rgba[..., 3] > 127
    m = np.asarray(Image.open(CP1 / "masks" / f"{mask_stem(vn, view['image'])}.outline.png")) > 0
    th = max(1, round(max(ref.shape[:2]) / 450))
    ov = clay.copy()
    for mm, col in ((m, (235, 0, 60)), (sil, (0, 110, 255))):
        cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(ov, cs, -1, col, th)
    diff = np.full_like(ref, 255)
    diff[m & sil] = (170, 170, 170)
    diff[m & ~sil] = (235, 0, 60)
    diff[~m & sil] = (0, 110, 255)
    iou = float((m & sil).sum() / max(1, (m | sil).sum()))
    body = ~ear_zone(view, ear_tips, ear_radius, m.shape) if len(ear_tips) else np.ones_like(m)
    iou_body = float((m & sil & body).sum() / max(1, ((m | sil) & body).sum()))
    row = np.concatenate([ref, ov, diff], 1)
    im = Image.fromarray(row)
    if im.height < 700:
        k = 700 / im.height
        im = im.resize((round(im.width * k), 700), Image.LANCZOS)
    band = 70
    out = Image.new("RGB", (im.width, im.height + band), (255, 255, 255))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.text((10, im.height + 6), vn.replace("_", " "), fill=(0, 0, 0), font=font(26))
    d.text((10, im.height + 40),
           f"tier {view['tier']} | outline agreement {iou * 100:.1f}% (body only, ears excluded: {iou_body * 100:.1f}%)   "
           f"(red line = photo outline, blue line = assembled shape; right: red = photo only, blue = shape only)",
           fill=(70, 70, 70), font=font(17))
    return out, iou, iou_body


def main():
    renders = Path(sys.argv[1])
    cj = json.loads((CP2 / "cameras_fit.json").read_text())
    cams = cj["views"]
    meta = json.loads((CP2 / "fit_meta.json").read_text())
    ear_tips = [cj["points_3d"]["ear_tip_R"], cj["points_3d"]["ear_tip_L"]]
    rev = CP2 / "review"
    rev.mkdir(parents=True, exist_ok=True)
    table = {}
    for k, vn in enumerate(ORDER):
        im, iou, iou_body = panel(vn, cams[vn], renders, ear_tips, meta["ear_radius_m"])
        im.save(rev / f"{k:02d}_{vn}.png")
        table[vn] = {"outline_agreement": round(iou, 4), "body_only_agreement": round(iou_body, 4)}
        print(f"{vn:28s} {iou * 100:5.1f}%  body {iou_body * 100:5.1f}%")
    (CP2 / "agreement.json").write_text(json.dumps(table, indent=2))
    tt = sorted(renders.glob("turntable_*.png"))
    if tt:
        tiles = [on_white(np.asarray(Image.open(p).convert("RGBA"))) for p in tt]
        h, w = tiles[0].shape[:2]
        cols = 8
        rows = (len(tiles) + cols - 1) // cols
        sheet = np.full((rows * h, cols * w, 3), 255, np.uint8)
        for i, t in enumerate(tiles):
            sheet[(i // cols) * h:(i // cols + 1) * h, (i % cols) * w:(i % cols + 1) * w] = t
        Image.fromarray(sheet).resize((cols * w // 2, rows * h // 2), Image.LANCZOS).save(rev / "turntable_sheet.png")
        frames = [Image.fromarray(t).resize((w // 2, h // 2), Image.LANCZOS) for t in tiles]
        frames[0].save(rev / "turntable.gif", save_all=True, append_images=frames[1:], duration=120, loop=0)


if __name__ == "__main__":
    main()
