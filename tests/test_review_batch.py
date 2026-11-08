import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import review_batch as rb  # noqa: E402


def setup():
    rgb = np.full((200, 200, 3), 255, np.uint8)
    rgb[50:150, 50:150] = 180                      # body: pixels 50..149 -> [50, 150)
    a_free = np.zeros((200, 200)); a_free[50:150, 50:150] = 1.0
    tile = {"id": "X", "x0": 30, "y0": 30, "x1": 170, "y1": 170}
    return rgb, a_free, tile


def square(lo, hi, step=0.5):
    s = np.arange(lo, hi, step)
    return np.vstack([np.c_[s, np.full_like(s, lo)], np.c_[np.full_like(s, hi), s],
                      np.c_[s[::-1] + step, np.full_like(s, hi)], np.c_[np.full_like(s, lo), s[::-1] + step]])


def test_exact_outline_is_clean():
    rgb, a, t = setup()
    f = rb.fidelity([t], square(50, 150), rgb, a)["X"]
    assert f["cut_px"] == 0 and f["bulge_px"] == 0


def test_shrunken_outline_reports_cut():
    rgb, a, t = setup()
    f = rb.fidelity([t], square(53, 147), rgb, a)["X"]
    assert f["cut_px"] > 0 and f["cut_max_px"] > 2


def test_swollen_outline_reports_bulge():
    rgb, a, t = setup()
    f = rb.fidelity([t], square(46, 154), rgb, a)["X"]
    assert f["bulge_px"] > 0 and f["cut_px"] == 0


def test_line_out_in_the_fringe_is_flagged():
    """Body 50..149 with a 12 px fringe of thin spikes; a line drawn through the
    middle of the fringe must be flagged, a line on the body edge must not."""
    rgb, a, t = setup()
    for x in range(52, 148, 4):                    # spikes along the top edge, rows 38..49
        rgb[38:50, x] = 120
    f_on = rb.fidelity([t], square(50, 150), rgb, a)["X"]
    f_mid = rb.fidelity([t], square(44, 156), rgb, a)["X"]
    assert f_on["fringe_in_px"] == 0
    assert f_mid["fringe_in_px"] > 0 and f_mid["fringe_in_max_px"] > 2
