"""How well the visible eyes match his, from the master camera: renders the
sculpt with flat black eyes and compares what shows of each eyeball with the
hand-traced outline of the dark of his eye (checkpoints/cp3/master_eye_outlines.json).
usage: eye_score.py SCULPT_DIR [OUT.png]"""
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def score(d, out=None):
    d = Path(d)
    subprocess.run([sys.executable, str(ROOT / "tools/preview.py"), str(d / "head.obj"), str(d / "es.png"),
                    "--eyes", str(d / "eye_R.obj"), str(d / "eye_L.obj"), "--crop", "250", "330", "830", "900",
                    "--scale", "1", "--samples", "4", "--keep-raw", "--matte-eyes"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    img = np.asarray(Image.open(d / "es.raw.png").convert("RGBA")).astype(np.float32)
    dark = (img[..., :3].mean(2) < 80) & (img[..., 3] > 200)
    tr = json.loads((ROOT / "checkpoints/cp3/master_eye_outlines.json").read_text())
    res = {}
    for s in ("R", "L"):
        poly = np.array(tr[s], np.int32)
        m = np.zeros(dark.shape, np.uint8)
        cv2.fillPoly(m, [poly], 1)
        x0, y0, w, h = cv2.boundingRect(poly)
        zone = np.zeros_like(m)
        zone[y0 - 40:y0 + h + 40, x0 - 40:x0 + w + 40] = 1
        n, lab, st, _ = cv2.connectedComponentsWithStats((dark & (zone > 0)).astype(np.uint8))
        sc = np.zeros_like(m)
        if n > 1:
            sc = (lab == 1 + np.argmax(st[1:, 4])).astype(np.uint8)
        iou = (m & sc).sum() / max(1, (m | sc).sum())
        ys, xs = np.nonzero(sc)
        box = (xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None
        res[s] = {"iou": iou, "box": box, "photo_box": (x0, y0, x0 + w - 1, y0 + h - 1), "mask": sc, "photo": m}
    if out:
        ph = np.asarray(Image.open(ROOT / "references/master/master_front_standing.webp").convert("RGB")).copy()
        bg = img[..., :3] * (img[..., 3:4] / 255) + 228 * (1 - img[..., 3:4] / 255)
        ren = bg.astype(np.uint8).copy()
        for s in ("R", "L"):
            for im in (ph, ren):
                for mm, col in ((res[s]["photo"], (235, 0, 60)), (res[s]["mask"], (0, 110, 255))):
                    cs, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    cv2.drawContours(im, cs, -1, col, 1)
        tiles = []
        for s in ("R", "L"):
            x0, y0, x1, y1 = res[s]["photo_box"]
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            for im in (ph, ren):
                tiles.append(Image.fromarray(im[cy - 70:cy + 70, cx - 60:cx + 60]).resize((360, 420), Image.NEAREST))
        o = Image.new("RGB", (360 * 4 + 30, 420), (255, 255, 255))
        for i, t in enumerate(tiles):
            o.paste(t, (i * 360 + (i // 2) * 30, 0))
        o.save(out)
    return res


if __name__ == "__main__":
    r = score(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for s in ("R", "L"):
        print(f"{s}: overlap {r[s]['iou'] * 100:.0f}% | sculpt box {r[s]['box']} | photo box {r[s]['photo_box']}")
