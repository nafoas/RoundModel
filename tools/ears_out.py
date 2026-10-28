"""His outlines without the ears (docs/CARVING.md section 10). The ears are
built as their own geometry; left in the outlines, the front and side
photos carve a slab at ear height between them (the flat plate with ridges
seen from above). An ear is what a round opening of about a tenth of his
size removes from the top third of his outline (the ears are narrower than
that, his head is not). Writes <view>.noears.png next to each outline."""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as nd

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402

OUT = C.ROOT / "checkpoints/cp4/outlines"


def remove_ears(m, frac=0.11, top=0.33):
    ys, xs = np.nonzero(m)
    h, w = ys.max() - ys.min(), xs.max() - xs.min()
    r = max(3, int(frac * max(h, w)))
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    pad = r + 5
    mp = np.pad(m.astype(np.uint8), pad)
    op = cv2.morphologyEx(mp, cv2.MORPH_OPEN, k)[pad:-pad, pad:-pad].astype(bool)
    band = np.zeros_like(m)
    band[:ys.min() + int(top * h)] = True
    ears = m & ~op & band
    lab, n = nd.label(ears)
    if n:
        sz = nd.sum(ears, lab, range(1, n + 1))
        ears = np.isin(lab, [i + 1 for i, s in enumerate(sz) if s > 0.003 * m.sum()])
    out = m & ~ears
    # cutting an ear out leaves a notch where its base met the head (in the
    # side and back photos, right behind his head); his head runs smoothly
    # there under the ear. Close it with a large round tool in the top band.
    # Closing cannot regrow the ear (it only fills hollows of the ear-less
    # outline), so the ear's own area may be filled too.
    rc = max(3, int(0.08 * max(h, w)))
    kc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rc + 1, 2 * rc + 1))
    pc = rc + 5
    closed = cv2.morphologyEx(np.pad(out.astype(np.uint8), pc), cv2.MORPH_CLOSE, kc)[pc:-pc, pc:-pc].astype(bool)
    out = out | (closed & band)
    # soften the cut where each ear met the head
    out = cv2.morphologyEx(out.astype(np.uint8), cv2.MORPH_OPEN,
                           cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)
    return out, ears


def main():
    C.ALIGN = {}
    tiles = []
    for name in C.VIEWS:
        if name == "sheet_09_top_down":  # from above the ears lie inside his outline
            continue
        cam, m = C.view_data(name)
        out, ears = remove_ears(m)
        Image.fromarray((out * 255).astype(np.uint8)).save(OUT / f"{name}.noears.png")
        ys, xs = np.nonzero(m)
        im = np.zeros(m.shape + (3,), np.uint8)
        im[m] = (200, 200, 200)
        im[ears] = (255, 0, 0)
        t = Image.fromarray(im[max(ys.min() - 20, 0):ys.max() + 20, max(xs.min() - 20, 0):xs.max() + 20])
        t.thumbnail((300, 300))
        tiles.append(t)
        print(name, int(ears.sum()))
    o = Image.new("RGB", (4 * 305, 2 * 305))
    for i, t in enumerate(tiles):
        o.paste(t, ((i % 4) * 305, (i // 4) * 305))
    o.save(OUT / "_ears.png")


if __name__ == "__main__":
    main()
