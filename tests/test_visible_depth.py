"""His surface as each depth model measured it, placed in the room with that model's own camera
(tools/visible_depth.py outputs)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from prince.space import Camera  # noqa: E402

MODELS = ("depthpro", "moge2")


def load(p):
    return json.loads((ROOT / p).read_text())


@pytest.mark.parametrize("name", MODELS)
def test_each_model_keeps_its_own_lens_and_aims_straight_on(name):
    meta = load(f"data/scene/visible_depth_{name}.json")
    cam = meta["placed_in_the_room"]["camera"]
    assert cam["focal_px"] == pytest.approx(meta["lens_px"], abs=1e-3)                  # its own lens, not ours
    W, H = cam["image_size_px"]
    assert cam["principal_point_px"] == pytest.approx([W / 2, H / 2])                  # as the model assumes
    assert abs(cam["yaw_deg"]) < 1e-6 and abs(cam["roll_deg"]) < 1e-6                  # straight on


@pytest.mark.parametrize("name", MODELS)
def test_placed_as_approved_and_remembered(name):
    pl = load(f"data/scene/visible_depth_{name}.json")["placed_in_the_room"]
    assert pl["his_eyes_above_camera_cm"] == pytest.approx(0.5, abs=0.01)             # owner: eye level, a tiny bit lower
    assert abs(pl["peet_bottoms_cm"]["his_right"] + pl["peet_bottoms_cm"]["his_left"]) < 0.02   # surface through their middle
    lm = pl["landmarks_room_cm"]
    mid = (np.array(lm["peet_bottom_his_right"]) + np.array(lm["peet_bottom_his_left"])) / 2
    assert np.allclose(mid, 0, atol=0.01)                                              # origin under their middle


@pytest.mark.parametrize("name", MODELS)
def test_every_point_sits_on_its_own_pixel_and_he_is_his_approved_width(name):
    import visible_depth as vd
    cam, P, meta = vd.room_points(name)
    H, W = P.shape[:2]
    ys, xs = np.nonzero(np.isfinite(P[..., 0]))
    pick = np.random.default_rng(1).choice(len(ys), 500, replace=False)
    uv = cam.project(P[ys[pick], xs[pick]])
    assert np.abs(uv - np.c_[xs[pick] + 0.5, ys[pick] + 0.5]).max() < 1e-3           # the ray through that very pixel
    Pc = (P - cam.C) @ cam.R.T                                                          # back in the camera's frame
    widest_y = int(load("data/cameras.json")["anchor_front"]["widest_outline_px"]["y"])
    width = vd.width_across(Pc, vd.him_mask(H, W), widest_y)
    assert width == pytest.approx(vd.WIDTH_CM, abs=0.01)


def test_the_two_models_are_never_merged():
    a = load("data/scene/visible_depth_depthpro.json")["placed_in_the_room"]["camera"]
    b = load("data/scene/visible_depth_moge2.json")["placed_in_the_room"]["camera"]
    assert a["focal_px"] != b["focal_px"] and a["position_cm"] != b["position_cm"]
    for d in (a, b):
        Camera.from_dict(d)                                                             # each a complete camera
