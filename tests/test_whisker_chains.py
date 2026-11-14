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


def test_muzzle_ring_follows_the_crease_and_encloses_the_nose():
    """synthetic face: a raised disc (radius 150) with a darker crease at its edge, a dark nose in it"""
    from scipy import ndimage as ndi

    class _F:
        pass
    H, W = 700, 800
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    c = np.array([400.0, 380.0])
    r = np.hypot(xx - c[0], yy - c[1])
    rng = np.random.default_rng(0)
    g = 200 + 12 * np.exp(-((r - 120) / 40) ** 2) - 14 * np.exp(-((r - 150) / 8) ** 2) + rng.normal(0, 2, (H, W))
    nose = (np.abs(xx - c[0]) < 40) & (yy > c[1] - 70) & (yy < c[1] - 40)
    g[nose] = 90
    F = _F(); F.grey = g
    pads = {"landmarks": {"philtrum_x": c[0], "philtrum_top": c[1] - 20, "philtrum_bottom": c[1] + 20},
            "nose_mask": nose}
    ring, centre = wc.measure_muzzle(F, pads)
    rr = np.hypot(*(ring - c).T)
    assert np.median(np.abs(rr - 150)) < 4 and np.abs(rr - 150).max() < 12
    from matplotlib.path import Path as MPath
    assert MPath(ring).contains_points(np.c_[xx[nose], yy[nose]]).all()
