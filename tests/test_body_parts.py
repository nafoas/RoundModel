"""Body parts: the path search follows a known valley; lines are carried on to the outline;
no new region overrules an approved part."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import body_parts as bp  # noqa: E402


def test_dp_path_follows_a_valley_smoothly():
    xs = np.arange(0, 200.0); Y = np.arange(0, 100.0)
    true = 50 + 20 * np.sin(xs / 40)
    rng = np.random.default_rng(0)
    cost = np.array([-np.exp(-((Y - t) / 3) ** 2) + rng.normal(0, 0.2, len(Y)) for t in true])
    path = bp.dp_path(cost, Y, range(-3, 4), step_cost=0.3)
    assert np.median(np.abs(Y[path] - true)) < 2


def test_to_outline_stops_at_the_edge():
    class _F:
        @staticmethod
        def sdist(p):
            return 100.0 - np.hypot(p[0], p[1])        # a disc of radius 100
    seg = bp.to_outline(_F, np.array([0.0, 0.0]), np.array([1.0, 0.0]))
    assert abs(seg[-1][0] - 100) <= 1


def test_leak_check_catches_a_region_inside_an_approved_part():
    H, W = 1433, 1098                                  # the anchor photo
    masks = bp.approved_masks(H, W)
    reg = np.zeros((H, W), np.uint8)
    for (f, k), m in masks.items():
        reg[m] = bp.part_code(f, k)
    assert not any(bp.leaks(reg).values())
    (f, k), m = next((fk, m) for fk, m in masks.items() if "gray_peet" in fk[1])
    r, c = np.argwhere(m)[len(np.argwhere(m)) // 2]
    reg[r, c] = 3                                      # one undercarriage pixel inside his grey peet
    assert bp.leaks(reg)[k] == 1
