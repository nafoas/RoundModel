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


def test_whisker_follows_its_own_line_beside_a_neighbour_and_through_a_crossing():
    """Whisker A runs alongside whisker B (3 px apart) for 40 px, and a third
    hair crosses A at right angles. Started from A's free end, the trace must
    stay on A along the side-by-side stretch and carry on past the crossing."""
    t = np.linspace(0, 1, 600)
    A = {"centreline": np.c_[20 + 160 * t, 40 + 0 * t], "sigma": np.full(600, 0.8), "opacity": np.full(600, 0.8)}
    B = {"centreline": np.c_[100 + 80 * t, 43 + 0 * t], "sigma": np.full(600, 0.8), "opacity": np.full(600, 0.8)}
    C = {"centreline": np.c_[60 + 0 * t, 20 + 40 * t], "sigma": np.full(600, 0.8), "opacity": np.full(600, 0.8)}
    a = w.render((80, 200), [A, B, C], ss=8)
    seed = A["centreline"][20:120:5]                     # x 25..40, the free end left of the crossing
    res = w.retrace_whisker(a, seed)
    cl = res["centreline"]
    assert cl[:, 0].max() > 170                          # got through the crossing and the side-by-side stretch
    on_A = np.abs(cl[:, 1] - 40.0)
    assert np.percentile(on_A, 95) < 0.6, np.percentile(on_A, 95)   # never switched to B (3 px away)
