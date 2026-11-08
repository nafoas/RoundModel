import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import body_outline as bo  # noqa: E402


def furry_disk():
    """Gray disk (r=120) with short fringe spikes all round and one long
    whisker, on pure white. The outline should be a smooth circle near r=120."""
    h = w = 600
    rgb = np.full((h, w, 3), 255, np.uint8)
    yy, xx = np.mgrid[:h, :w]
    r = np.hypot(xx - 300, yy - 300)
    rgb[r <= 120] = 170
    for ang in np.linspace(0, 2 * np.pi, 90, endpoint=False):    # fringe spikes, 10 px
        for s in np.linspace(118, 130, 30):
            x = int(300 + s * np.cos(ang)); y = int(300 + s * np.sin(ang)); rgb[y, x] = 150
    for s in np.linspace(110, 290, 400):                         # whisker going right
        rgb[int(300 + s * 0.15), int(300 + s)] = 100
    return rgb


def test_outline_is_smooth_circle_ignoring_whisker():
    bo.SENSITIVE_MAX_Y, bo.PEET_MIN_Y = -1000, 10000      # no faithful regions in this test
    a = bo.coverage(furry_disk())
    tck, _ = bo.fit_outline(a)
    c = bo.resample(bo.sample(tck, 4000), 1.0)
    r = np.hypot(c[:, 0] - 300, c[:, 1] - 300)
    assert 112 < r.min() and r.max() < 132           # near the disk edge, through the fringe
    assert r.max() - r.min() < 10                    # whisker didn't pull it out
    assert bo.turning(c).sum() < 3 * 2 * np.pi       # gentle: close to one full turn


def test_eye_mark_straddling_the_outline_ends_up_fully_inside():
    """A dark mark poking 4 px past a square outline must be merged in, exactly."""
    from matplotlib.path import Path as MPath
    h = w = 120
    rgb = np.full((h, w, 3), 255, np.uint8)
    rgb[20:100, 20:100] = 190                     # body: square 20..100
    rgb[50:54, 14:40] = 40                        # black mark poking out to x=14 (4 px tall)
    a = bo.coverage(rgb)
    square = np.array([[20, 20], [100, 20], [100, 100], [20, 100]], float)
    curve = bo.resample(np.vstack([square, square[:1]]), 0.5)[:-1]
    bo.EYE_BOXES = {"test": (5, 35, 60, 70)}
    fields = bo.eye_mark_fields(rgb, a)
    merged = bo.merge_marks(curve, fields)
    check = bo.mark_check(merged, fields)["test"]
    assert check["mark_pixels"] > 0
    assert check["mark_pixels_not_fully_inside"] == 0
    assert check["mark_area_outside_px"] == 0
    # and it didn't swallow the background far from the mark
    assert not MPath(merged).contains_point((10, 30))


def test_pixel_convention_edges_land_on_pixel_boundaries():
    """Project convention: pixel (c, r) covers [c, c+1) x [r, r+1). A crisp square
    filling pixels 20..99 must have its 50% edge exactly at x = 20 and x = 100."""
    a = np.zeros((120, 120))
    a[20:100, 20:100] = 1.0
    c = bo.level_contour(a, 0)
    assert abs(c[:, 0].min() - 20.0) < 0.05 and abs(c[:, 0].max() - 100.0) < 0.05
    assert abs(c[:, 1].min() - 20.0) < 0.05 and abs(c[:, 1].max() - 100.0) < 0.05


def test_lock_top_keeps_the_approved_top_exactly(tmp_path):
    """Approved = circle. New = same circle but dented inward near the top (like
    the eye hook). After locking rows < 200, the top must equal the approved."""
    import json
    t = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
    app = np.c_[300 + 150 * np.cos(t), 300 + 150 * np.sin(t)]
    new = app.copy()
    dent = (new[:, 1] < 190) & (np.abs(new[:, 0] - 250) < 30)
    new[dent, 1] += 14
    f = tmp_path / "top.json"
    f.write_text(json.dumps({"lock_row": 200, "hand_off_px": 40, "closed_curve": app.tolist()}))
    out = bo.lock_top(new, str(f))
    from scipy.spatial import cKDTree
    top = app[app[:, 1] < 200]
    assert cKDTree(out).query(top)[0].max() < 0.3
