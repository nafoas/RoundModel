"""Prince's 3D space: the room he sits in, and cameras looking at him.

THE ROOM (owner, 2026-11-16: ground him in a real 3D space before any sculpting)
- Units: centimetres.
- Floor: the flat plane y = 0. He rests on it; nothing of him goes below it.
- Axes (right-handed), named from HIS point of view:
    +X = his left   (in the front photo: the picture's right)
    +Y = up
    +Z = his forward (the way his face points)
- Origin: on the floor, in his midline plane (x = 0, the plane that splits him into left and right),
  under the front of his peets (the midpoint of where his two peets meet the floor).

CAMERAS
- A pinhole camera: a position C in the room, a rotation R (room -> camera), and a lens: focal length f
  (pixels, square pixels) and principal point (cx, cy) (pixels).
- Camera frame: x = picture right, y = picture down, z = the way the camera looks.
- Picture coordinates as everywhere in this project: x right, y down, pixel (c, r) covers
  [c, c+1) x [r, r+1), so its centre is (c + 0.5, r + 0.5).
- Every pixel is a RAY from the camera, never a point on a flat sheet: `ray()` turns picture points into
  directions from C; only a depth along that ray makes a point in the room.
- Orbit placement (same words as docs/PLAN.md): yaw 0 = camera straight in front of his face (on +Z),
  yaw 90 = camera on his left (+X); pitch > 0 = camera above, looking down; roll > 0 = the camera turned
  clockwise about the way it looks, so the room appears turned anticlockwise in the picture.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FULL_FRAME_DIAGONAL_MM = float(np.hypot(36.0, 24.0))     # 35 mm-equivalent focal lengths refer to this


def focal_px_from_35mm(f35_mm: float, width: int, height: int) -> float:
    """Focal length in pixels for a 35 mm-equivalent focal length, if the picture is the whole frame."""
    return f35_mm * float(np.hypot(width, height)) / FULL_FRAME_DIAGONAL_MM


def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


@dataclass
class Camera:
    """Pinhole camera in the room. R maps room directions to camera directions; C is its position."""
    R: np.ndarray
    C: np.ndarray
    f: float
    cx: float
    cy: float
    width: int
    height: int

    # ---- placement
    @classmethod
    def orbit(cls, target, distance, yaw_deg=0.0, pitch_deg=0.0, roll_deg=0.0, *, f, width, height,
              cx=None, cy=None):
        """Camera `distance` cm from `target`, looking at it from direction (yaw, pitch), turned by roll."""
        y, p, r = np.radians([yaw_deg, pitch_deg, roll_deg])
        back = np.array([np.sin(y) * np.cos(p), np.sin(p), np.cos(y) * np.cos(p)])  # target -> camera
        C = np.asarray(target, float) + distance * back
        return cls.look(C, target, roll_deg=roll_deg, f=f, width=width, height=height, cx=cx, cy=cy)

    @classmethod
    def look(cls, C, target, roll_deg=0.0, *, f, width, height, cx=None, cy=None, up=(0.0, 1.0, 0.0)):
        """Camera at C looking at target, picture 'up' as close to the room's up as possible, then roll."""
        C = np.asarray(C, float); z = np.asarray(target, float) - C; z = z / np.linalg.norm(z)
        x = np.cross(-np.asarray(up, float), z)            # picture right = down x forward (x = y cross z)
        if np.linalg.norm(x) < 1e-9:                        # looking straight up/down: pick room +X
            x = np.array([1.0, 0.0, 0.0])
        x = x / np.linalg.norm(x); yv = np.cross(z, x)      # picture down
        R = np.stack([x, yv, z])                            # rows: camera axes in room coordinates
        R = rot_z(np.radians(roll_deg)).T @ R               # roll: turn the camera about its own z
        return cls(R=R, C=C, f=float(f), cx=float(width / 2 if cx is None else cx),
                   cy=float(height / 2 if cy is None else cy), width=int(width), height=int(height))

    # ---- the camera's own axes, in room coordinates
    @property
    def right(self):
        return self.R[0]

    @property
    def down(self):
        return self.R[1]

    @property
    def forward(self):
        return self.R[2]

    # ---- room <-> picture
    def to_camera(self, P):
        return (np.atleast_2d(np.asarray(P, float)) - self.C) @ self.R.T

    def project(self, P):
        """Room points (N, 3) -> picture points (N, 2). Points behind the camera give NaN."""
        q = self.to_camera(P)
        z = np.where(q[:, 2] > 1e-9, q[:, 2], np.nan)
        return np.c_[self.cx + self.f * q[:, 0] / z, self.cy + self.f * q[:, 1] / z]

    def ray_camera(self, uv):
        """Picture points (N, 2) -> unit directions in the camera frame (depend only on the lens)."""
        uv = np.atleast_2d(np.asarray(uv, float))
        d = np.c_[(uv[:, 0] - self.cx) / self.f, (uv[:, 1] - self.cy) / self.f, np.ones(len(uv))]
        return d / np.linalg.norm(d, axis=1, keepdims=True)

    def ray(self, uv):
        """Picture points (N, 2) -> unit directions in the room, from C."""
        return self.ray_camera(uv) @ self.R

    def point_at_depth(self, uv, depth):
        """The room point on each pixel's ray at `depth` cm along the camera's viewing axis."""
        d = self.ray(uv); dz = d @ self.forward
        return self.C + d * (np.asarray(depth, float).reshape(-1, 1) / dz[:, None])

    def hit_plane(self, uv, normal=(0.0, 1.0, 0.0), offset=0.0):
        """Where each pixel's ray meets the plane n . P = offset (default: the floor). NaN if never."""
        n = np.asarray(normal, float); d = self.ray(uv)
        den = d @ n; t = (offset - self.C @ n) / np.where(np.abs(den) > 1e-12, den, np.nan)
        t = np.where(t > 0, t, np.nan)
        return self.C + d * t[:, None]

    # ---- lens and pose as numbers
    def angles(self):
        """(yaw, pitch, roll) in degrees, in the orbit sense above."""
        z = self.forward
        pitch = float(np.degrees(np.arcsin(np.clip(-z[1], -1, 1))))
        yaw = float(np.degrees(np.arctan2(-z[0], -z[2])))
        ref = Camera.look(self.C, self.C + z, f=self.f, width=self.width, height=self.height)
        roll = float(np.degrees(np.arctan2(ref.down @ self.right, ref.right @ self.right)))
        return yaw, pitch, roll

    def to_dict(self):
        yaw, pitch, roll = self.angles()
        return dict(position_cm=np.round(self.C, 4).tolist(), rotation_room_to_camera=np.round(self.R, 8).tolist(),
                    focal_px=round(self.f, 4), principal_point_px=[round(self.cx, 4), round(self.cy, 4)],
                    image_size_px=[self.width, self.height],
                    yaw_deg=round(yaw, 4), pitch_deg=round(pitch, 4), roll_deg=round(roll, 4),
                    fov_horizontal_deg=round(float(np.degrees(2 * np.arctan(self.width / 2 / self.f))), 3),
                    fov_vertical_deg=round(float(np.degrees(2 * np.arctan(self.height / 2 / self.f))), 3))

    @classmethod
    def from_dict(cls, d):
        return cls(R=np.array(d["rotation_room_to_camera"], float), C=np.array(d["position_cm"], float),
                   f=d["focal_px"], cx=d["principal_point_px"][0], cy=d["principal_point_px"][1],
                   width=d["image_size_px"][0], height=d["image_size_px"][1])
