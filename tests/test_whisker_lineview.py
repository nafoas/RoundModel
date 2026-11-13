"""Line view: finds a faint whisker along the direction field, ignores a crossing streak."""
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import face_whiskers as fw  # noqa: E402
import whisker_lineview as lv  # noqa: E402


def _scene(depth=4.0, seed=0):
    rng = np.random.default_rng(seed)
    H, W = 1000, 1100
    fur = 200 + ndi.gaussian_filter(rng.normal(0, 14, (H, W)), 1.0)
    ys, xs = np.mgrid[0:H, 0:W] + 0.5
    # faint whisker: y = 700 - 15 sin(pi (x-300)/500), x 300..600 (gently curved, ~horizontal)
    xc = np.clip(xs, 300, 600)
    yc = 700 - 15 * np.sin(np.pi * (xc - 300) / 500)
    d = np.abs(ys - yc)
    line = depth * np.exp(-d ** 2 / (2 * 1.3 ** 2)) * ((xs >= 300) & (xs <= 600))
    # a darker streak crossing it at 60 deg (not along the whisker directions)
    u = (xs - 450) * np.cos(np.radians(60)) + (ys - 690) * np.sin(np.radians(60))
    v = -(xs - 450) * np.sin(np.radians(60)) + (ys - 690) * np.cos(np.radians(60))
    streak = 2 * depth * np.exp(-v ** 2 / (2 * 1.3 ** 2)) * (np.abs(u) <= 60)
    img = np.clip(fur - line - streak, 0, 255)
    photo = np.repeat(img[..., None], 3, 2).astype(np.uint8)
    body = np.array([[150, 500], [950, 500], [950, 980], [150, 980], [150, 500]], float)
    field = [np.c_[np.linspace(200, 900, 50), np.full(50, 700.0)]]      # whiskers run ~horizontally here
    return photo, body, field


def test_line_view_finds_faint_whisker_and_ignores_crossing_streak():
    photo, body, field = _scene()
    L = lv.LineView(field, photo=photo, body=body, boxes=[])
    r = L.find(np.array([310.0, 700 - 15 * np.sin(np.pi * 10 / 500)]), 0.0, length=330, k0max=0.3)
    q, c = L.line_profile(r["q"])
    segs = lv.segments(dict(kind="interior", q=q, c=c))
    assert segs, "faint whisker not found"
    s, e = max(segs, key=lambda ab: ab[1] - ab[0])
    seg = q[s:e + 1]
    truth = 700 - 15 * np.sin(np.pi * (np.clip(seg[:, 0], 300, 600) - 300) / 500)
    assert np.median(np.abs(seg[:, 1] - truth)) < 0.6          # search path on the line (before photo fits)
    assert seg[0][0] < 330 and seg[-1][0] > 570                 # nearly its whole length
    # the streak: searching along it gives nothing (it crosses the whisker directions)
    t = np.array([np.cos(np.radians(60)), np.sin(np.radians(60))])
    r2 = L.find(np.array([450.0, 690.0]) - 50 * t, np.radians(60), length=100, k0max=0.1)
    q2, c2 = L.line_profile(r2["q"])
    assert not lv.segments(dict(kind="interior", q=q2, c=c2))
