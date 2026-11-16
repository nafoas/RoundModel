"""A rough, parametric shell of Prince for the depth lines (3D grounding step 5). NOT the model.

Rule 1 (CLAUDE.md): the shell is never built from his outline. It is a simple parametric shape, and his outline
only MEASURES it: its parameters are adjusted until its silhouette through the anchor camera matches his.

Shape: his body (an ellipsoid resting on the surface he sits on) and his head (an ellipsoid, turned and tipped as
measured in tools/facing.py), joined by a smooth blend (he has almost no neck). Both are symmetric about their own
midlines. Front-to-back depth is not visible in one front photo: ASSUMED round (each as deep as it is wide) until
the owner says otherwise or a side photo shows it.

Room coordinates as prince/space.py: cm; floor y = 0; +X his left, +Y up, +Z his forward.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def ellipsoid_sdf(q, r):
    """Approximate signed distance (cm) to an axis-aligned ellipsoid with semi-axes r, at local points q (N, 3).
    Negative inside. (The 'k0 * (k0 - 1) / k1' bound: exact on spheres, close elsewhere.)"""
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    # at the very centre the bound is 0/0: there the distance to the surface is the shortest semi-axis
    return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -np.min(r))


def smooth_union(a, b, k):
    """Smooth minimum of two distances with blend width k (cm): a soft join instead of a crease."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


@dataclass
class Shell:
    body_x: float = 0.0       # body centre, left-right (cm)
    body_z: float = -6.0      # body centre, front-back (cm)
    body_w: float = 7.5       # body half-width (cm); its half-depth = body_w * depth_ratio (ASSUMED round: 1)
    body_h: float = 6.0       # body half-height (cm)
    body_y: float = 6.0       # body centre height; <= body_h: a loaf sits INTO the surface (the clip at y = 0 flattens
                              # his underside), never floating above it
    head_x: float = 0.0
    head_y: float = 9.0
    head_z: float = -2.0
    head_w: float = 5.5       # head half-width; half-depth = head_w * depth_ratio
    head_h: float = 4.5
    blend: float = 2.0        # how softly head and body join (cm)
    head_turn_deg: float = 0.0    # + toward his left (tools/facing.py)
    head_tip_deg: float = 0.0     # + his left side up
    depth_ratio: float = 1.0      # front-to-back / side-to-side: ASSUMED round

    FREE = ("body_x", "body_z", "body_w", "body_h", "head_x", "head_y", "head_z", "head_w", "head_h", "blend", "body_y")

    def head_rotation(self):
        return rot_y(np.radians(self.head_turn_deg)) @ rot_z(np.radians(self.head_tip_deg))

    def parts_sdf(self, P):
        P = np.atleast_2d(P)
        b = ellipsoid_sdf(P - [self.body_x, self.body_y, self.body_z],
                          np.array([self.body_w, self.body_h, self.body_w * self.depth_ratio]))
        q = (P - [self.head_x, self.head_y, self.head_z]) @ self.head_rotation()      # into the head's own frame
        h = ellipsoid_sdf(q, np.array([self.head_w, self.head_h, self.head_w * self.depth_ratio]))
        return b, h

    def sdf(self, P):
        P = np.atleast_2d(P)
        b, h = self.parts_sdf(P)
        return np.maximum(smooth_union(b, h, self.blend), -P[:, 1])     # nothing of him below the surface (y = 0)

    def vector(self):
        return np.array([getattr(self, k) for k in self.FREE], float)

    def with_vector(self, v):
        d = asdict(self); d.update(dict(zip(self.FREE, map(float, v))))
        return Shell(**d)

    def bounds(self, pad=1.0):
        lo = np.array([min(self.body_x - self.body_w, self.head_x - self.head_w * 1.5) - pad, -pad,
                       min(self.body_z - self.body_w * self.depth_ratio, self.head_z - self.head_w * 1.5) - pad])
        hi = np.array([max(self.body_x + self.body_w, self.head_x + self.head_w * 1.5) + pad,
                       max(self.body_y + self.body_h, self.head_y + self.head_h * 1.5) + pad,
                       max(self.body_z + self.body_w * self.depth_ratio, self.head_z + self.head_w * 1.5) + pad])
        return lo, hi


def trace(shell: Shell, origin, dirs, steps=96, t0=0.0, t1=60.0):
    """Sphere-trace rays from origin: (first-hit distance or inf, smallest distance seen along each ray)."""
    n = len(dirs); t = np.full(n, float(t0)); best = np.full(n, np.inf); hit = np.full(n, np.inf)
    alive = np.ones(n, bool)
    for _ in range(steps):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        d = shell.sdf(origin + dirs[idx] * t[idx, None])
        best[idx] = np.minimum(best[idx], d)
        done = d < 1e-3
        hit[idx[done]] = t[idx[done]]
        t[idx] += np.maximum(d * 0.9, 0.01)
        alive[idx[done | (t[idx] > t1)]] = False
    return hit, best
