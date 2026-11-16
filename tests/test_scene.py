"""The anchor camera in the room, the landmarks and the rays (tools/landmarks.py, tools/scene.py outputs)."""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prince.space import Camera  # noqa: E402


def load(p):
    return json.loads((ROOT / p).read_text())


def test_anchor_camera_is_placed_as_the_owner_remembers_the_shot():
    doc = load("data/cameras.json")["anchor_front"]
    cam = Camera.from_dict(doc)
    lm = load("data/strands/landmarks.json")["landmarks"]
    assert np.allclose(cam.project([[0, 0, 0]])[0], lm["floor_contact_midpoint"]["at_px"], atol=1e-3)
    assert cam.C[1] > 0 and cam.C[2] > 0                       # above the surface, in front of his face
    yaw, pitch, roll = cam.angles()
    assert abs(yaw) < 1e-6 and abs(roll) < 1e-6                # straight on
    assert -2.0 <= pitch <= 0.0                                  # level, or tilted up a touch (owner)
    assert abs(cam.cx - lm["nose_y_centre"]["at_px"][0]) < 1e-6  # aimed at his face, not the picture's centre
    nose = cam.ray([lm["nose_y_centre"]["at_px"]])[0]
    nose_pt = cam.C + 15.24 * nose                               # owner: roughly six inches away
    assert abs(nose_pt[1] - doc["nose_height_cm"]) < 0.01
    eyes = (np.array(lm["eye_his_left"]["at_px"]) + np.array(lm["eye_his_right"]["at_px"])) / 2
    up = np.degrees(np.arcsin(cam.ray([eyes])[0][1]))
    assert 0.0 < up < 4.0                                        # his eyes a touch above the camera
    assert abs(np.linalg.det(cam.R) - 1) < 1e-7


def test_landmarks_are_named_by_his_side():
    lm = load("data/strands/landmarks.json")["landmarks"]
    for a, b in (("eye_his_left", "eye_his_right"), ("ear_tip_his_left", "ear_tip_his_right"),
                 ("peet_bottom_his_left", "peet_bottom_his_right"), ("mouth_corner_his_left", "mouth_corner_his_right")):
        assert lm[a]["at_px"][0] > lm[b]["at_px"][0]             # his left = the picture's right
        assert lm[a]["mirror_of"] == b and lm[b]["mirror_of"] == a


def test_every_saved_ray_lands_back_on_its_pixel():
    cam = Camera.from_dict(load("data/cameras.json")["anchor_front"])
    rays = load("data/scene/anchor_rays.json")
    for e in rays["sets"] + rays["landmarks"]:
        uv = np.array(e["picture_px"]); d = np.array(e["directions_room"])
        assert np.allclose(np.linalg.norm(d, axis=1), 1, atol=1e-5)
        P = cam.C + d * (30.0 / (d @ cam.forward))[:, None]
        assert np.abs(cam.project(P) - uv).max() < 0.02
        assert np.allclose(np.array(e["directions_camera"]) @ cam.R, d, atol=2e-6)
