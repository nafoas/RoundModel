import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import wisps as w  # noqa: E402


def truth_strand(sigma=0.9, opacity=0.7):
    t = np.linspace(0, 1, 400)
    x = 40 + 80 * t
    y = 60 + 18 * np.sin(2.2 * t) + 6 * t ** 2          # gently curved hair
    cl = np.c_[x, y]
    return {"centreline": cl, "sigma": np.full(len(cl), sigma), "opacity": np.full(len(cl), opacity)}


def test_trace_recovers_centre_width_opacity_and_full_length():
    rng = np.random.default_rng(0)
    st = truth_strand()
    a = w.render((130, 170), [st], ss=8) + rng.normal(0, 0.01, (130, 170))
    cl = st["centreline"]
    tan = np.gradient(cl, axis=0); n = np.c_[-tan[:, 1], tan[:, 0]]; n /= np.linalg.norm(n, axis=1)[:, None]
    seed = (cl + 1.2 * n)[40:-40:10]                          # 1.2 px off, ~15 px short at each end
    res = w.trace(a, seed)
    got = res["centreline"]
    core = cl[20:-20]
    d = cKDTree(got).query(core)[0]
    assert d.max() < 0.2, d.max()                              # sub-pixel centre
    assert abs(np.median(res["sigma"]) - 0.9) < 0.15
    assert abs(np.median(res["opacity"]) - 0.7) < 0.08
    assert np.hypot(*(got[0] - cl[0])) < 4 and np.hypot(*(got[-1] - cl[-1])) < 4   # ends found


def test_render_matches_its_own_input_profile():
    st = truth_strand(sigma=1.0, opacity=0.8)
    a = w.render((130, 170), [st], ss=8)
    assert 0.7 < a.max() <= 0.81
