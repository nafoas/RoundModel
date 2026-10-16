"""Build the Checkpoint 3 review images: the grey form with his features.

Lead image: the master next to the grey form from the master's exact
camera, then a face close-up at the same framing, then outline agreement
for every wall view, then a turntable. Grey clay is composited on a soft
grey background (on pure white his highlit head edge disappears).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from make_cp1_review import ORDER, font, mask_stem  # noqa: E402
from make_cp2_review import on_white  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CP1 = ROOT / "checkpoints/cp1"
CP2 = ROOT / "checkpoints/cp2"
CP3 = ROOT / "checkpoints/cp3"
BG = 228
FACE_BOX = (240, 160, 860, 900)  # master pixels: ears to chin


def label(img, title, sub):
    band = 74
    out = Image.new("RGB", (img.width, img.height + band), (255, 255, 255))
    out.paste(img, (0, 0))
    d = ImageDraw.Draw(out)
    d.text((10, img.height + 6), title, fill=(0, 0, 0), font=font(26))
    d.text((10, img.height + 42), sub, fill=(70, 70, 70), font=font(17))
    return out


def agreement(view, rgba):
    m = np.asarray(Image.open(CP1 / "masks" / f"{mask_stem(view[0], view[1]['image'])}.outline.png")) > 0
    sil = rgba[..., 3] > 127
    return m, sil, float((m & sil).sum() / max(1, (m | sil).sum()))


def main():
    renders = Path(sys.argv[1])
    cams = json.loads((CP2 / "cameras_fit.json").read_text())["views"]
    rev = CP3 / "review"
    rev.mkdir(parents=True, exist_ok=True)
    table = {}

    # lead: master side by side, and the face close-up
    ref = np.asarray(Image.open(ROOT / cams["master_front_standing"]["image"]).convert("RGB"))
    rgba = np.asarray(Image.open(renders / "master_front_standing.png").convert("RGBA"))
    clay = on_white(rgba, BG)
    m, sil, iou = agreement(("master_front_standing", cams["master_front_standing"]), rgba)
    table["master_front_standing"] = round(iou, 4)
    ov = clay.copy()
    for mm, col in ((m, (235, 0, 60)), (sil, (0, 110, 255))):
        cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(ov, cs, -1, col, 3)
    label(Image.fromarray(np.concatenate([ref, clay, ov], 1)), "master front standing: photo | grey form | outlines",
          f"same camera, angle and distance as the master | outline agreement {iou * 100:.1f}% "
          f"(red = photo outline, blue = grey form; the photo's outline follows individual hairs, the form follows the fur's envelope)"
          ).save(rev / "00_master.png")
    x0, y0, x1, y1 = FACE_BOX
    face = np.concatenate([ref[y0:y1, x0:x1], clay[y0:y1, x0:x1]], 1)
    label(Image.fromarray(face).resize((face.shape[1] * 2 // 1, face.shape[0] * 2 // 1), Image.LANCZOS),
          "face close-up, master framing", "photo | grey form (eyes shown dark so their placement and size can be judged)"
          ).save(rev / "01_master_face.png")

    tiles = []
    for vn in ORDER[1:]:
        p = renders / f"{vn}.png"
        if not p.exists():
            continue
        rgba = np.asarray(Image.open(p).convert("RGBA"))
        ref = np.asarray(Image.open(ROOT / cams[vn]["image"]).convert("RGB"))
        m, sil, iou = agreement((vn, cams[vn]), rgba)
        table[vn] = round(iou, 4)
        clay = on_white(rgba, BG)
        for mm, col in ((m, (235, 0, 60)), (sil, (0, 110, 255))):
            cs, _ = cv2.findContours(mm.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(clay, cs, -1, col, max(1, round(max(ref.shape[:2]) / 450)))
        im = Image.fromarray(np.concatenate([ref, clay], 1))
        im = im.resize((round(im.width * 520 / im.height), 520), Image.LANCZOS)
        tiles.append(label(im, vn.replace("_", " "), f"tier {cams[vn]['tier']} | outline agreement {iou * 100:.1f}%"))
    if tiles:
        cols = 2
        w = max(t.width for t in tiles)
        h = max(t.height for t in tiles)
        sheet = Image.new("RGB", (cols * w, ((len(tiles) + 1) // cols) * h), (255, 255, 255))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % cols) * w, (i // cols) * h))
        sheet.save(rev / "02_all_views.png")

    tt = sorted(renders.glob("turntable_*.png"))
    if tt:
        frames = [Image.fromarray(on_white(np.asarray(Image.open(p).convert("RGBA")), BG)) for p in tt]
        w, h = frames[0].size
        frames = [f.resize((w // 2, h // 2), Image.LANCZOS) for f in frames]
        frames[0].save(rev / "03_turntable.gif", save_all=True, append_images=frames[1:], duration=120, loop=0)
        cols = 8
        rows = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * frames[0].width, rows * frames[0].height), (BG, BG, BG))
        for i, f in enumerate(frames):
            sheet.paste(f, ((i % cols) * f.width, (i // cols) * f.height))
        sheet.save(rev / "03_turntable_sheet.png")
    (CP3 / "agreement.json").write_text(json.dumps(table, indent=2))
    for k, v in table.items():
        print(f"{k:28s} {v * 100:5.1f}%")


if __name__ == "__main__":
    main()
