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


def test_anchor_camera_is_the_depth_models_camera():
    """Owner, 2026-11-17: "I agree with whatever the model says": the room's camera for this photo is MoGe-2's."""
    doc = load("data/cameras.json")
    cam = Camera.from_dict(doc["anchor_front"])
    placed = load("data/scene/visible_depth_moge2.json")["placed_in_the_room"]
    model = Camera.from_dict(placed["camera"])
    assert np.allclose(cam.C, model.C) and np.allclose(cam.R, model.R) and cam.f == model.f
    yaw, pitch, roll = cam.angles()
    assert abs(yaw) < 1e-6 and abs(roll) < 1e-6                 # straight on
    assert cam.C[1] > 0 and cam.C[2] > 0                         # above the surface, in front of his face
    eyes = (np.array(placed["landmarks_room_cm"]["eye_his_left"]) + np.array(placed["landmarks_room_cm"]["eye_his_right"])) / 2
    assert abs(eyes[1] - cam.C[1] - 0.5) < 0.01                  # owner: eye level, a tiny bit lower
    lm = load("data/strands/landmarks.json")["landmarks"]
    assert np.abs(cam.project([[0, 0, 0]])[0] - lm["floor_contact_midpoint"]["at_px"]).max() < 15   # origin under his peets
    size = doc["anchor_front"]["his_size_estimate_cm"]
    assert size["width"] == 15.5 and size["top_of_head"] >= 12.7  # approved width; above his adult floor
    assert abs(np.linalg.det(cam.R) - 1) < 1e-7


def test_the_six_inch_camera_is_kept_as_a_superseded_record():
    old = load("data/cameras.json")["anchor_front_six_inches_superseded"]
    assert old["status"].startswith("SUPERSEDED")
    assert old["his_size_estimate_cm"]["top_of_head"] == 12.7


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
