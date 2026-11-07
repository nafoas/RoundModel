"""Orbit camera looking at Prince.

yaw 0 = camera straight in front of his face (on +x), yaw 90 = viewing his
left side (+y). pitch > 0 = camera above, looking down. Image y goes down.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class Camera:
    yaw: float = 0.0          # degrees
    pitch: float = 10.0       # degrees
    roll: float = 0.0         # degrees
    dist: float = 60.0        # distance from target
    fov: float = 30.0         # vertical field of view, degrees
    target_z: float = 7.0     # height of the point the camera looks at
    shift_x: float = 0.0      # image-center offset, fraction of width
    shift_y: float = 0.0      # image-center offset, fraction of height
    width: int = 96
    height: int = 96

    # parameters the optimizer may refine for non-anchor views, with max deltas
    REFINABLE = {"yaw": 15.0, "pitch": 15.0, "roll": 8.0, "dist": 15.0,
                 "shift_x": 0.15, "shift_y": 0.15}

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)

    def resized(self, width, height):
        d = self.to_dict()
        d.update(width=width, height=height)
        return Camera(**d)

    def frame(self):
        """Camera position and orthonormal (right, up, forward) axes."""
        y, p, r = np.radians([self.yaw, self.pitch, self.roll])
        target = np.array([0.0, 0.0, self.target_z])
        pos = target + self.dist * np.array(
            [np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), np.sin(p)])
        fwd = target - pos
        fwd /= np.linalg.norm(fwd)
        right = np.cross(fwd, [0.0, 0.0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        c, s = np.cos(r), np.sin(r)
        right, up = c * right + s * up, -s * right + c * up
        return pos, right, up, fwd

    @property
    def focal(self):
        return 0.5 * self.height / np.tan(np.radians(self.fov) / 2)

    @property
    def center(self):
        return (0.5 * self.width + self.shift_x * self.width,
                0.5 * self.height + self.shift_y * self.height)

    def project(self, pts):
        """3D points (N,3) -> pixel coords (N,2) as (x right, y down)."""
        pos, right, up, fwd = self.frame()
        q = np.atleast_2d(pts) - pos
        zc = q @ fwd
        cx, cy = self.center
        u = cx + self.focal * (q @ right) / zc
        v = cy - self.focal * (q @ up) / zc
        return np.stack([u, v], axis=-1)

    def rays(self):
        """Origin (3,) and unit directions (H*W, 3) through pixel centers."""
        pos, right, up, fwd = self.frame()
        cx, cy = self.center
        xs = (np.arange(self.width) + 0.5 - cx) / self.focal
        ys = -(np.arange(self.height) + 0.5 - cy) / self.focal
        gx, gy = np.meshgrid(xs, ys)
        d = fwd + gx[..., None] * right + gy[..., None] * up
        d = d.reshape(-1, 3)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        return pos, d
