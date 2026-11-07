import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import edge_tiles as et  # noqa: E402


def synthetic():
    """A gray disk (the 'body') with a long thin 'whisker' reaching far out."""
    h, w = 400, 400
    rgb = np.full((h, w, 3), 255, np.uint8)
    yy, xx = np.mgrid[:h, :w]
    rgb[(xx - 200) ** 2 + (yy - 200) ** 2 <= 90 ** 2] = 180
    for t in np.linspace(0, 1, 400):                      # whisker: 1 px wide line
        x = int(285 + t * 105); y = int(200 - t * 150)
        rgb[y, x] = 120
    return rgb


def test_every_band_pixel_is_in_a_tile():
    fg = et.foreground(synthetic())
    body, band, tiles = et.build_tiles(fg)
    assert band.sum() > 0
    assert et.uncovered(band, tiles) == 0


def test_whisker_tip_is_covered():
    fg = et.foreground(synthetic())
    _, _, tiles = et.build_tiles(fg)
    tip_x, tip_y = 389, 51
    assert any(t["x0"] <= tip_x < t["x1"] and t["y0"] <= tip_y < t["y1"] for t in tiles)


def test_tiles_are_in_bounds_unique_and_ordered():
    fg = et.foreground(synthetic())
    _, _, tiles = et.build_tiles(fg)
    ids = [t["id"] for t in tiles]
    assert len(ids) == len(set(ids))
    outline = [t for t in tiles if t["kind"] == "outline"]
    assert [t["id"] for t in outline] == [f"T{i:03d}" for i in range(1, len(outline) + 1)]
    for t in tiles:
        assert 0 <= t["x0"] < t["x1"] <= 400 and 0 <= t["y0"] < t["y1"] <= 400
        assert t["x1"] - t["x0"] == et.TILE and t["y1"] - t["y0"] == et.TILE


def test_uncovered_detects_a_gap():
    band = np.zeros((100, 100), bool); band[50, 50] = True
    assert et.uncovered(band, []) == 1
