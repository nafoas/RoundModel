import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import split_peets as sp  # noqa: E402


def line(a, b, n=50):
    return np.linspace(a, b, n)


def test_three_parts_tile_the_zone_exactly():
    """Body = square 0..100. Peet line at y=60 (joins reach the sides), dividers
    at x=30 and x=70 curving (one bows outward). Parts: left, middle, right."""
    t = np.linspace(0, 1, 400, endpoint=False)
    body = np.vstack([line((0, 0), (100, 0)), line((100, 0), (100, 100)),
                      line((100, 100), (0, 100)), line((0, 100), (0, 0))])
    peet_line = line((5, 60), (95, 60))
    cream_join = line((0, 60), (5, 60), 5)
    gray_join = line((95, 60), (100, 60), 5)
    ys = np.linspace(60, 100, 60)
    cream_div = np.c_[30 + 8 * np.sin(np.pi * (ys - 60) / 40), ys]      # bows right
    gray_div = np.c_[np.full_like(ys, 70.0), ys]
    zone, parts = sp.build(body, peet_line, cream_join, gray_join, cream_div, gray_div)
    assert abs(zone.area - 4000) < 1
    areas = {k: v.area for k, v in parts.items()}
    bow = np.trapezoid(8 * np.sin(np.pi * (ys - 60) / 40), ys)
    assert abs(areas["cream_peet_image_left"] - (30 * 40 + bow)) < 2
    assert abs(areas["gray_peet_image_right"] - 30 * 40) < 2
    assert abs(sum(areas.values()) - zone.area) < 1e-6
