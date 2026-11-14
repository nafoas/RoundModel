"""Whole-length follow (the real acceptance step, side-by-side test included): bridges a faint
gap in a whisker and ends where it ends; adds nothing from plain fur."""
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import face_whiskers as fw  # noqa: E402
import whisker_fulllength as wf  # noqa: E402
import whisker_lineview as lv  # noqa: E402


class _Here:                      # runs the "pool" jobs in this process
    map = staticmethod(lambda f, xs: list(map(f, xs)))


def _scene(seed=0):
    rng = np.random.default_rng(seed)
    H, W = 1000, 1100
    fur = 200 + ndi.gaussian_filter(rng.normal(0, 10, (H, W)), 1.0)
    ys, xs = np.mgrid[0:H, 0:W] + 0.5
    yc = 700 - 20 * np.sin(np.pi * (np.clip(xs, 300, 700) - 300) / 800)
    on = (xs >= 300) & (xs <= 700) & ~((xs >= 480) & (xs <= 505))      # 25 px gap at x 480-505
    depth = np.where(xs < 480, 6.0, 4.0)                                   # fainter after the gap
    line = depth * np.exp(-(ys - yc) ** 2 / (2 * 1.3 ** 2)) * on
    photo = np.repeat(np.clip(fur - line, 0, 255)[..., None], 3, 2).astype(np.uint8)
    body = np.array([[150, 500], [950, 500], [950, 980], [150, 980], [150, 500]], float)
    field = [np.c_[np.linspace(200, 900, 50), np.full(50, 700.0)]]
    return photo, body, field


def _truth(x):
    return 700 - 20 * np.sin(np.pi * (np.clip(x, 300, 700) - 300) / 800)


def _follow_all(V, start_line):
    doc = {"whiskers": [{"id": "t", "centreline": start_line.tolist()}]}
    done, added = {("t", "outline")}, np.zeros((0, 2))
    for _ in range(4):
        acc = wf.follow_round(V, doc, _Here, done)
        if not acc:
            break
        for wid, side, q, m in acc:
            added = np.vstack([added, q])
            doc["whiskers"][0]["centreline"] = np.vstack([doc["whiskers"][0]["centreline"], q]).tolist()
    return added


def test_follow_bridges_gap_and_ends_at_the_end():
    photo, body, field = _scene()
    V = lv._L = wf.CombinedView(field, photo=photo, body=body, boxes=[])
    xs = np.arange(300.0, 420.0)
    added = _follow_all(V, np.c_[xs, _truth(xs)])
    assert len(added) and added[-1][0] > 660, "did not follow across the gap to near the end (x = 700)"
    assert added[-1][0] < 715, "ran on past the end into plain fur"
    assert np.median(np.abs(added[:, 1] - _truth(added[:, 0]))) < 0.8


def test_follow_from_plain_fur_adds_nothing():
    photo, body, field = _scene(seed=1)
    V = lv._L = wf.CombinedView(field, photo=photo, body=body, boxes=[])
    for y in (560.0, 620.0, 850.0):
        xs = np.arange(250.0, 300.0)                 # a short "whisker" ending in plain fur
        line = np.c_[xs, np.full(len(xs), y)]
        assert len(_follow_all(V, line)) == 0
