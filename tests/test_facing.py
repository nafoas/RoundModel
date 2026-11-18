"""How he faces (tools/facing.py): a known turn and tip are recovered from mirror pairs, with the right signs."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from prince.space import Camera  # noqa: E402
import facing as fc  # noqa: E402


def test_a_known_turn_and_tip_come_back_from_mirror_pairs():
    turn, tip = np.radians(7.0), np.radians(4.0)
    # his head frame: +X his left, +Y up, +Z his forward; mirror pairs (x, y, z) and (-x, y, z)
    half = np.array([[1.8, 2.0, -1.5], [0.7, 0.2, 0.8], [0.5, -1.0, 0.5], [1.2, -1.3, 0.1], [0.4, 3.5, -1.0], [2.0, 3.0, -2.0]])
    R = np.array([[np.cos(turn), 0, np.sin(turn)], [0, 1, 0], [-np.sin(turn), 0, np.cos(turn)]]) @ \
        np.array([[np.cos(tip), -np.sin(tip), 0], [np.sin(tip), np.cos(tip), 0], [0, 0, 1]])
    centre = np.array([0.0, 7.0, 0.0])
    left = centre + half @ R.T; right = centre + (half * [-1, 1, 1]) @ R.T
    cam = Camera.orbit(centre, 13.0, pitch_deg=-1.0, f=1428.0, width=1098, height=1433, cx=548.0, cy=482.0)
    pairs = list(zip(cam.project(left), cam.project(right)))
    X, misfit = fc.left_right_axis(cam, pairs)
    t, p = fc.turn_tip(X)
    assert abs(t - 7.0) < 0.05 and abs(p - 4.0) < 0.05            # turned toward his left, his left side up
    assert misfit.max() < 0.01
    assert cam.project([left[0]])[0][0] > cam.project([right[0]])[0][0]   # his left shows on the picture's right


def test_head_read_from_his_measured_surface():
    """data/scene/facing.json: the head as read from the depth model's surface (tools/facing.py from_surface)."""
    import json
    doc = json.loads((ROOT / "data/scene/facing.json").read_text())
    h, old = doc["head"], doc["head_photo_only"]
    readings = list(h["turn_readings_deg"].values())
    assert len(readings) == 5 and h["turned_deg"] == round(float(np.median(readings)), 1)   # the middle reading
    X = np.array(h["left_right_axis_room"])
    assert abs(np.linalg.norm(X) - 1) < 1e-3
    t, p = fc.turn_tip(X)
    assert abs(t - h["turned_deg"]) < 0.1 and abs(p - h["tipped_deg"]) < 0.1
    for tip in h["tip_per_pair_deg"].values():             # two independent ways to read his tip agree (a 3D pair's
        assert abs(tip - old["tipped_deg"]) < 2.0          # tip needs a unit direction: 19 deg came from a raw one)
    assert set(h["left_out"]) == {"mouth corners", "ear bases (inner and outer)"}
    assert "nod" in h and "eyes_middle_to_nose_slopes_below_level_deg" in h["nod"]
