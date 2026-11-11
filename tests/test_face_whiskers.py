"""Face whisker search: finds a faint curved line on fur-like noise, to sub-pixel."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import face_whiskers as fw  # noqa: E402


def _scene(depth=8.0, seed=0):
    rng = np.random.default_rng(seed)
    H, W = 260, 360
    from scipy import ndimage as ndi
    fur = 200 + ndi.gaussian_filter(rng.normal(0, 14, (H, W)), 1.0)   # fur-like speckle
    # a gently curved whisker: y = 130 - 20*sin(pi*x/600), from x=20 to x=300, dark by `depth`
    ys, xs = np.mgrid[0:H, 0:W] + 0.5
    xc = np.clip(xs, 20, 300)
    yc = 130 - 20 * np.sin(np.pi * xc / 600)
    d = np.abs(ys - yc) / np.sqrt(1 + (20 * np.pi / 600 * np.cos(np.pi * xc / 600)) ** 2)
    line = depth * np.exp(-d ** 2 / (2 * 1.2 ** 2)) * ((xs >= 20) & (xs <= 300))
    img = np.clip(fur - line, 0, 255)
    photo = np.repeat(img[..., None], 3, 2).astype(np.uint8)
    body = np.array([[5, 5], [355, 5], [355, 255], [5, 255], [5, 5]], float)   # whole frame is "face"
    return photo, body


import pytest


@pytest.mark.parametrize("seed", [0, 2, 3, 4])
def test_finds_faint_curved_line(seed):
    photo, body = _scene(seed=seed)
    f = fw.Face(photo, body, boxes=[])
    x0 = 30.0; y0 = 130 - 20 * np.sin(np.pi * x0 / 600)
    slope = -20 * np.pi / 600 * np.cos(np.pi * x0 / 600)
    th = np.arctan2(slope, 1.0) - np.deg2rad(12)       # entry direction off by 12 deg (the cheek bend)
    r = f.find(np.array([x0, y0]), th, length=300)
    assert r["cut"] is not None
    ie, a, b = r["cut"]
    out = f.finish(r["q"], a, b)
    pts = out["centreline"]
    truth = 130 - 20 * np.sin(np.pi * pts[:, 0] / 600)
    err = np.abs(pts[:, 1] - truth)
    # the line is only ~2x the fur speckle: along its length it is placed to a
    # fraction of a pixel; in the last ~12 px at each end (data on one side only,
    # and where it fades) to within ~2 px
    inner = err[12:-12]
    assert np.median(inner) < 0.25 and inner.max() < 0.8
    assert err.max() < 2.5
    # ends where the line ends (x = 300), not on into plain fur; with the line only
    # 2x the fur's speckle, where exactly it fades is uncertain by up to ~20 px
    assert 278 <= pts[-1][0] <= 308


def test_plain_fur_gives_nothing():
    photo, body = _scene(depth=0.0, seed=1)
    f = fw.Face(photo, body, boxes=[])
    found = sum(f.find(np.array([30.0, y]), 0.0, length=240)["cut"] is not None for y in (60.0, 130.0, 200.0))
    assert found == 0
