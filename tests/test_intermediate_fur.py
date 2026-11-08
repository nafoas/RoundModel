import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import body_outline as bo  # noqa: E402
import intermediate_fur as itf  # noqa: E402


def furry_disk():
    """Disk r=120 with a dense fringe of 1-px spikes 12 px long all round, and one
    long whisker reaching 150 px out to the right."""
    h = w = 700
    a = np.zeros((h, w))
    yy, xx = np.mgrid[:h, :w]
    a[np.hypot(xx - 350, yy - 350) <= 120] = 1.0
    for ang in np.linspace(0, 2 * np.pi, 400, endpoint=False):
        for s in np.linspace(120, 132, 40):
            a[int(350 + s * np.sin(ang)), int(350 + s * np.cos(ang))] = 1.0
    for s in np.linspace(120, 270, 600):
        a[int(350 + s * 0.1), int(350 + s)] = 1.0
    t = np.linspace(0, 2 * np.pi, 3000, endpoint=False)
    body = np.c_[350 + 120.5 * np.cos(t), 350 + 120.5 * np.sin(t)]
    return a, body


def test_outer_line_sits_at_the_fringe_tips_and_ignores_the_whisker():
    a, body = furry_disk()
    r = itf.reach(a, body)
    outer = itf.outer_line(body, r, a.shape)
    rad = np.hypot(outer[:, 0] - 350, outer[:, 1] - 350)
    assert 124 < np.median(rad) < 134           # around the fringe tips (120 + 12)
    assert rad.max() < 140                      # the whisker didn't drag it out
    from matplotlib.path import Path as MPath
    assert MPath(outer).contains_points(body).all()   # band never negative


def test_long_strands_masks_the_whisker_not_the_fringe():
    a, body = furry_disk()
    m = itf.long_strands(a, body)
    # whisker pixels far out (>= 40 px past the body) are masked
    assert m[int(350 + 220 * 0.1), int(350 + 220)] or m[int(350 + 220 * 0.1) + 1, int(350 + 220)]
    # short fringe spikes (12 px) on the left side are not
    assert not m[350, 350 - 126 : 350 - 120].any()
