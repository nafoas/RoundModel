"""The rough shell (prince/shell.py) and its fit (tools/depth_lines.py)."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prince.shell import Shell, ellipsoid_sdf, smooth_union, trace  # noqa: E402


def test_ellipsoid_distance_is_exact_on_a_sphere_and_signed():
    q = np.array([[3.0, 0, 0], [0, 1.0, 0], [0, 0, -2.0]])
    assert np.allclose(ellipsoid_sdf(q, np.array([2.0, 2.0, 2.0])), [1.0, -1.0, 0.0])
    assert ellipsoid_sdf(np.array([[0.0, 0, 0]]), np.array([3.0, 1.0, 2.0]))[0] < 0


def test_smooth_union_is_never_above_the_plain_union():
    a = np.linspace(-2, 2, 41); b = a[::-1]
    assert (smooth_union(a, b, 1.5) <= np.minimum(a, b) + 1e-12).all()
    assert np.allclose(smooth_union(a, b, 0.0), np.minimum(a, b))


def test_nothing_of_him_goes_below_the_surface():
    sh = Shell(body_y=2.0, body_h=6.0)                 # a body sitting deep into the surface
    assert (sh.sdf(np.c_[np.zeros(5), -np.linspace(0.1, 3, 5), np.full(5, sh.body_z)]) > 0).all()


def test_tracing_meets_a_ball_where_it_should():
    sh = Shell(body_x=0, body_z=0, body_w=2, body_h=2, body_y=5, head_y=50, head_w=0.5, head_h=0.5, blend=0.0)
    hit, _ = trace(sh, np.array([0.0, 5.0, 20.0]), np.array([[0.0, 0.0, -1.0]]), t0=1)
    assert abs(hit[0] - 18.0) < 0.01


def test_the_fitted_shell_matches_his_outline_and_his_nose():
    doc = json.loads((ROOT / "data/scene/shell.json").read_text())
    assert doc["fit"]["iou_scored"] >= 0.95
    assert abs(doc["fit"]["nose_off_surface_cm"]) < 0.1
    sh = Shell(**doc["shell"])
    assert sh.body_y <= sh.body_h + 1e-9                 # sits on (or into) the surface, never floating
    assert sh.head_y > sh.body_y                          # his head above the middle of his body
