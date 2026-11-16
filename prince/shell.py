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
    depth_ratio: float = 1.0      # used only where a part's own depth is not given (0): front-to-back / side-to-side
    # owner, 2026-11-16: the face came out flat ("you kept the actual part where depth was important flat"). So the
    # head and body each have their OWN front-to-back depth, measured from the light on his fur (tools/depth_lines.py),
    # and his raised muzzle (the whisker pads, owner: "elevated mouf area") is its own rounded form on his face.
    body_c: float = 0.0           # body half-depth (cm); 0: body_w * depth_ratio
    head_c: float = 0.0           # head half-depth (cm); 0: head_w * depth_ratio
    muzzle_y: float = -2.0        # muzzle centre in the head's own frame: below the head centre (cm) ...
    muzzle_z: float = 3.5         # ... and forward of it (cm)
    muzzle_w: float = 0.0         # muzzle half-width (cm); 0: no muzzle
    muzzle_h: float = 1.5
    muzzle_c: float = 1.5         # muzzle half-depth (cm)
    muzzle_blend: float = 0.8     # how softly the muzzle joins the face (cm)

    FREE = ("body_x", "body_z", "body_w", "body_h", "head_x", "head_y", "head_z", "head_w", "head_h", "blend", "body_y")
    FREE_FACE = FREE + ("body_c", "head_c", "muzzle_y", "muzzle_z", "muzzle_w", "muzzle_h", "muzzle_c", "muzzle_blend")

    def head_rotation(self):
        return rot_y(np.radians(self.head_turn_deg)) @ rot_z(np.radians(self.head_tip_deg))

    def depths(self):
        return (self.body_c if self.body_c > 0 else self.body_w * self.depth_ratio,
                self.head_c if self.head_c > 0 else self.head_w * self.depth_ratio)

    def parts_sdf(self, P):
        """Distances to his body, and to his head (with its muzzle, if any), each on its own."""
        P = np.atleast_2d(P)
        bc, hc = self.depths()
        b = ellipsoid_sdf(P - [self.body_x, self.body_y, self.body_z], np.array([self.body_w, self.body_h, bc]))
        q = (P - [self.head_x, self.head_y, self.head_z]) @ self.head_rotation()      # into the head's own frame
        h = ellipsoid_sdf(q, np.array([self.head_w, self.head_h, hc]))
        if self.muzzle_w > 0:
            m = ellipsoid_sdf(q - [0.0, self.muzzle_y, self.muzzle_z], np.array([self.muzzle_w, self.muzzle_h, self.muzzle_c]))
            h = smooth_union(h, m, self.muzzle_blend)
        return b, h

    def sdf(self, P):
        P = np.atleast_2d(P)
        b, h = self.parts_sdf(P)
        return np.maximum(smooth_union(b, h, self.blend), -P[:, 1])     # nothing of him below the surface (y = 0)

    def vector(self, names=None):
        return np.array([getattr(self, k) for k in (names or self.FREE)], float)

    def with_vector(self, v, names=None):
        d = asdict(self); d.update(dict(zip(names or self.FREE, map(float, v))))
        return Shell(**d)

    def bounds(self, pad=1.0):
        bc, hc = self.depths()
        reach = max(self.head_w, self.head_h, hc) * 1.2 + (abs(self.muzzle_z) + self.muzzle_c if self.muzzle_w > 0 else 0)
        lo = np.array([min(self.body_x - self.body_w, self.head_x - reach) - pad, -pad,
                       min(self.body_z - bc, self.head_z - reach) - pad])
        hi = np.array([max(self.body_x + self.body_w, self.head_x + reach) + pad,
                       max(self.body_y + self.body_h, self.head_y + reach) + pad,
                       max(self.body_z + bc, self.head_z + reach) + pad])
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
