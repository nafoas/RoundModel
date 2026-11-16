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
