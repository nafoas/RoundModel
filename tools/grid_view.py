"""Make an upscaled, gridded copy of (part of) a reference image, labelled in
original pixel coordinates, so landmarks can be placed precisely by eye.

usage: grid_view.py IMAGE OUT [x0 y0 x1 y1] [--scale N] [--step N]
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("out")
    ap.add_argument("box", nargs="*", type=int)
    ap.add_argument("--scale", type=int, default=3)
    ap.add_argument("--step", type=int, default=10)
    a = ap.parse_args()

    im = Image.open(a.image).convert("RGB")
    x0, y0, x1, y1 = a.box if a.box else (0, 0, im.width, im.height)
    s = a.scale
    c = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    major = a.step * 5
    for gx in range((x0 // a.step + 1) * a.step, x1, a.step):
        X = (gx - x0) * s
        d.line([(X, 0), (X, c.height)], fill=(0, 255, 0) if gx % major == 0 else (0, 110, 0), width=1)
        if gx % major == 0:
            d.text((X + 2, 2), str(gx), fill=(255, 0, 0))
    for gy in range((y0 // a.step + 1) * a.step, y1, a.step):
        Y = (gy - y0) * s
        d.line([(0, Y), (c.width, Y)], fill=(0, 255, 0) if gy % major == 0 else (0, 110, 0), width=1)
        if gy % major == 0:
            d.text((2, Y + 2), str(gy), fill=(255, 0, 0))
    c.save(a.out)


if __name__ == "__main__":
    main()
