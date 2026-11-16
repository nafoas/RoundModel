"""The room and its cameras: every convention in prince/space.py, pinned down by a test."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prince.space import Camera, focal_px_from_35mm  # noqa: E402

W, H = 1098, 1433
F = focal_px_from_35mm(26.0, W, H)


def front(**kw):
    return Camera.orbit([0, 5, 0], 30.0, f=F, width=W, height=H, **kw)


def test_pixel_to_ray_and_back_is_exact():
    cam = Camera.orbit([1, 4, -2], 25.0, yaw_deg=20, pitch_deg=12, roll_deg=-4, f=F, width=W, height=H)
    uv = np.array([[0.5, 0.5], [549.0, 716.5], [1097.5, 1432.5], [300.25, 900.75]])
    for depth in (5.0, 25.0, 80.0):
        P = cam.point_at_depth(uv, np.full(len(uv), depth))
        assert np.allclose(cam.project(P), uv, atol=1e-9)
        assert np.allclose(cam.to_camera(P)[:, 2], depth)
    assert np.allclose(np.linalg.norm(cam.ray(uv), axis=1), 1)


def test_front_camera_his_left_is_picture_right_and_up_is_up():
    cam = front()
    c = cam.project([[0, 5, 0]])[0]
    assert np.allclose(c, [W / 2, H / 2])                       # the target is in the middle
    left = cam.project([[1, 5, 0]])[0]; up = cam.project([[0, 6, 0]])[0]; fwd = cam.project([[0, 5, 1]])[0]
    assert left[0] > c[0] and abs(left[1] - c[1]) < 1e-6        # his left (+X): picture right
    assert up[1] < c[1] and abs(up[0] - c[0]) < 1e-6            # up (+Y): picture up
    assert np.allclose(fwd, c)                                   # his forward points at the camera
    assert cam.C[2] > 0                                          # the camera stands in front of his face


def test_yaw_90_sees_his_left_side_with_his_face_to_the_picture_left():
    cam = Camera.orbit([0, 5, 0], 30.0, yaw_deg=90, f=F, width=W, height=H)
    assert cam.C[0] > 29.99                                      # camera on his left
    fwd = cam.project([[0, 5, 1]])[0]
    assert fwd[0] < W / 2                                         # his face points to the picture's left


def test_pitch_puts_the_camera_above_looking_down():
    cam = front(pitch_deg=30)
    assert cam.C[1] > 5 and cam.forward[1] < 0


def test_roll_turns_the_room_anticlockwise_in_the_picture():
    cam = front(roll_deg=10)
    up = cam.project([[0, 6, 0]])[0]
    assert up[0] < W / 2                                         # 'up' leans to the picture's left


def test_angles_round_trip():
    for yaw, pitch, roll in ((0, 0, 0), (35, 10, -6), (-120, -20, 3)):
        cam = Camera.orbit([0, 3, 1], 20.0, yaw_deg=yaw, pitch_deg=pitch, roll_deg=roll, f=F, width=W, height=H)
        assert np.allclose(cam.angles(), (yaw, pitch, roll), atol=1e-7)
        assert np.allclose(Camera.from_dict(cam.to_dict()).R, cam.R, atol=1e-7)
        assert np.allclose(cam.R @ cam.R.T, np.eye(3)) and abs(np.linalg.det(cam.R) - 1) < 1e-9   # no mirroring


def test_floor_hit_is_on_the_floor_and_on_the_ray():
    cam = front(pitch_deg=20)
    uv = np.array([[549.0, 1300.0], [200.0, 1200.0]])
    P = cam.hit_plane(uv)
    assert np.allclose(P[:, 1], 0, atol=1e-9)
    assert np.allclose(cam.project(P), uv, atol=1e-9)
    assert np.isnan(cam.hit_plane([[549.0, 10.0]])).all()        # a ray going up never meets the floor


def test_focal_from_35mm():
    assert abs(focal_px_from_35mm(43.2666, 3000, 2000) - np.hypot(3000, 2000)) < 0.01
