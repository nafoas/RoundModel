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
