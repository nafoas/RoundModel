"""Whiskers traced to the pad: own bend kept when it reaches the pad; smallest extra bend when it
doesn't; nothing inferred when the seen end is already at the pad."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import whisker_chains as wc  # noqa: E402

PAD = dict(lateral=[np.array([100.0, 0.0]), np.array([100.0, 200.0])],
           outline=np.array([[100, 0], [100, 200], [140, 200], [140, 0]], float))


def test_seg_cross():
    q = wc.seg_cross(np.array([0.0, 0.0]), np.array([10.0, 10.0]), np.array([0.0, 10.0]), np.array([10.0, 0.0]))
    assert np.allclose(q, [5, 5])
    assert wc.seg_cross(np.array([0.0, 0.0]), np.array([1.0, 1.0]), np.array([5.0, 0.0]), np.array([6.0, 0.0])) is None


def test_own_bend_kept_when_it_reaches_the_pad():
    pts, k, k_own = wc.path_to_pad(np.array([0.0, 100.0]), np.array([1.0, 0.0]), np.radians(0.05), PAD)
    assert k == k_own
    assert abs(pts[-1][0] - 100.0) < 1e-6 and len(pts) <= 101


def test_smallest_extra_bend_when_it_misses():
    # heading up and away: must bend to reach the edge, and it reaches it exactly
    pts, k, k_own = wc.path_to_pad(np.array([0.0, 100.0]), np.array([np.cos(-1.2), np.sin(-1.2)]), 0.0, PAD)
    assert pts is not None and abs(pts[-1][0] - 100.0) < 0.5 and k > 0


def test_nothing_inferred_at_the_pad():
    pts, k, _ = wc.path_to_pad(np.array([97.0, 50.0]), np.array([1.0, 0.0]), 0.0, PAD)
    assert len(pts) == 1


def test_pad_outline_follows_the_lip_line_and_reaches_the_nostrils():
    """synthetic muzzle: a dark lip line y = 820 + 0.15 |x - 548| from x 420 to 680 on speckled fur,
    a dark nose above; the outline must run along the lip line and up to both nostril wing tips"""
    from scipy import ndimage as ndi

    class _F:
        pass
    H, W = 1000, 1100
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    rng = np.random.default_rng(0)
    g = 200 + ndi.gaussian_filter(rng.normal(0, 6, (H, W)), 1.0)
    lip_y = 820 + 0.15 * np.abs(xx - 548)
    g -= 25 * np.exp(-((yy - lip_y) / 2.5) ** 2) * (np.abs(xx - 548) <= 130)
    nose = (np.abs(xx - 548) < 80 - 0.9 * (yy - 690)) & (yy > 690) & (yy < 760)
    g[nose] = 90
    F = _F(); F.grey = g
    pads = {"nose_mask": nose, "landmarks": {
        "philtrum_x": 548.0, "philtrum_top": 760.0, "philtrum_bottom": 815.0,
        "nostril_wing_left": np.array([470.0, 692.0]), "nostril_wing_right": np.array([626.0, 692.0])}}
    ring, centre, info = wc.measure_muzzle(F, pads)
    low = ring[(ring[:, 1] > 800) & (np.abs(ring[:, 0] - 548) < 110)]
    err = np.abs(low[:, 1] - (820 + 0.15 * np.abs(low[:, 0] - 548)))
    assert len(low) > 50 and np.median(err) < 1.5
    for k in ("image_left", "image_right"):
        assert abs(info[k]["lip_corner"][0] - 548) > 100          # followed the lip line out to near its end
    assert min(np.hypot(*(ring - [470.0, 692.0]).T)) < 4 and min(np.hypot(*(ring - [626.0, 692.0]).T)) < 4


def test_inward_continuation_keeps_its_own_bend():
    """a line on a circle, ordered root -> tip: continuing past its root end with its own bend stays on
    the same circle (the bug: the bend's sign was flipped, bending it the other way)"""
    c, r = np.array([300.0, 300.0]), 250.0
    a = np.linspace(-0.2, 0.5, 200)
    line = c + r * np.c_[np.cos(a), np.sin(a)]                     # root at a = -0.2, tip at a = 0.5
    k = wc.own_curvature(line[::-1])
    ext = wc.arc_to(line[0], -wc.tangent(line, False), k, 100)
    wrong = wc.arc_to(line[0], -wc.tangent(line, False), -k, 100)
    assert np.abs(np.hypot(*(ext - c).T) - r).max() < 3.0           # (direction estimated over 10 px)
    assert np.abs(np.hypot(*(wrong - c).T) - r).max() > 20.0
