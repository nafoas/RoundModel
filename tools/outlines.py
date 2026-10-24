"""His outline in the photos (traced with BiRefNet, a background-removal
segmentation model, run locally through rembg; whiskers removed after).

Older notes:
His outline in the photos the base shape is fitted to (tasks/02, base
shape step 1). Full-resolution masks for the photos with refined cameras.

Each sheet photo is traced at full size: a first estimate of his fur (bright
and nearly colourless, joined to him), refined by GrabCut on colour (sure fur
deep inside, sure background far outside). The master's own trace is
already full size.

usage: python tools/outlines.py [VIEW ...]  (one view per run keeps memory low) -> checkpoints/cp4/outlines/<view>.png (+ review sheet)
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "checkpoints/cp4/outlines"
PANEL_SCALE, PANEL_DX = 0.222, 7
SHEETS = {
    "sheet_02_front_3q": ("02_front_3q", "sheet_02_front_3q_right"),
    "sheet_03_right_profile": ("03_right_profile", "sheet_03_right_profile"),
    "sheet_04_back_3q_right": ("04_back_3q_right", "sheet_04_back_3q_right"),
    "sheet_07_left_profile": ("07_left_profile", "sheet_07_left_profile"),
    "sheet_08_front_3q_left": ("08_front_3q_left", "sheet_08_front_3q_left"),
    "sheet_09_top_down": ("09_top_down", "sheet_09_top_down"),
}


def fur(rgb, vmin=150):
    v = rgb.max(-1)
    sat = (v - rgb.min(-1)) / np.maximum(v, 1)
    return (v > vmin) & (sat < (0.22 if vmin >= 150 else 0.25))


def surely_not_fur(rgb):
    """Navy blanket and shadow (dark), brown couch and skin (saturated), the
    warm lamp-lit wall (bright but yellow: red well above blue)."""
    r, b = rgb[..., 0], rgb[..., 2]
    v = rgb.max(-1)
    sat = (v - rgb.min(-1)) / np.maximum(v, 1)
    return (v < 45) | (sat > 0.35) | ((r - b) > 30)


def largest(m):
    lab, n = nd.label(m)
    if n == 0:
        return m
    s = nd.sum(m, lab, range(1, n + 1))
    return nd.binary_fill_holes(lab == 1 + int(np.argmax(s)))


def birefnet_all():
    """Trace every fitted photo with BiRefNet (clean fur edge, whiskers mostly
    excluded); thin whisker spikes removed by a small opening."""
    from rembg import new_session, remove
    sess = new_session("birefnet-general")
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {"master_front_standing": ROOT / "references/master/master_front_standing.webp"}
    for view, (orig, _) in SHEETS.items():
        jobs[view] = ROOT / f"references/sheet_originals/{orig}.webp"
    import sys as _s
    only = [a for a in _s.argv[1:] if not a.startswith("--")]
    for view, src in jobs.items():
        if only and view not in only:
            continue
        al = np.asarray(remove(Image.open(src).convert("RGB"), session=sess, only_mask=True)) > 127
        disk = np.add.outer(np.arange(-6, 7) ** 2, np.arange(-6, 7) ** 2) <= 36
        m = largest(nd.binary_opening(al, structure=disk))
        Image.fromarray((m * 255).astype(np.uint8)).save(OUT / f"{view}.png")
        print(view, int(m.sum()), flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = np.asarray(Image.open(ROOT / "checkpoints/cp1/masks/master_front_standing.outline.png")) > 127
    Image.fromarray((m * 255).astype(np.uint8)).save(OUT / "master_front_standing.png")
    for view, (orig, panel) in SHEETS.items():
        rgb8 = np.asarray(Image.open(ROOT / f"references/sheet_originals/{orig}.webp").convert("RGB"))
        rgb = rgb8.astype(float)
        H, W = rgb.shape[:2]
        # his fur, lit or in shade (shaded fur under his body is a cool grey,
        # still nearly colourless and far brighter than the navy blanket)
        v = rgb.max(-1)
        sat = (v - rgb.min(-1)) / np.maximum(v, 1)
        cand = (v > 62) & (sat < 0.3) & ~surely_not_fur(rgb)
        core = largest(nd.binary_opening(fur(rgb), iterations=3))
        mask = cand & nd.binary_dilation(core, iterations=400)
        mask = nd.binary_opening(mask, iterations=3)
        lab, n = nd.label(mask)
        keep = np.unique(lab[core & mask])
        mask = np.isin(lab, keep[keep > 0])
        mask = largest(nd.binary_closing(np.pad(mask, 20), iterations=12)[20:-20, 20:-20])
        mask = nd.binary_opening(mask, iterations=2)
        Image.fromarray((mask * 255).astype(np.uint8)).save(OUT / f"{view}.png")
        print(view, W, H, int(mask.sum()))


if __name__ == "__main__":
    import sys
    birefnet_all() if "--colour" not in sys.argv else main()
