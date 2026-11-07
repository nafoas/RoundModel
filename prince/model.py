"""Parametric model of Prince.

Prince is described by a small set of named numbers (PARAMS). From those we
build a signed distance field (SDF): negative inside him, positive outside.
Everything is smooth unions of ellipsoids, so he stays round by construction.

Coordinates: x forward (toward nose), y = Prince's left, z up, ground z = 0.
Units are roughly centimeters.

This file never looks at photos. The model is built only from parameters.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Param:
    name: str
    default: float
    lo: float
    hi: float
    doc: str


PARAMS: list[Param] = [
    # Body: the loaf
    Param("body_len", 8.2, 6.0, 14.0, "half-length of body, front to back"),
    Param("body_wid", 7.5, 5.0, 11.0, "half-width of body"),
    Param("body_hgt", 6.5, 4.0, 10.0, "half-height of body ellipsoid"),
    Param("body_cz", 6.0, 3.0, 10.0, "height of body center above ground"),
    Param("ground_blend", 0.8, 0.1, 2.0, "softness of flattening where he sits on the ground"),
    # Head: blended into body with a big radius = 'barely a neck'
    Param("head_rx", 4.5, 3.0, 7.0, "head half-depth (front-back)"),
    Param("head_ry", 4.8, 3.0, 7.0, "head half-width"),
    Param("head_rz", 4.3, 3.0, 7.0, "head half-height"),
    Param("head_x", 7.0, 3.0, 12.0, "head center, forward of body center"),
    Param("head_z", 9.5, 5.0, 15.0, "head center height above ground"),
    Param("neck_blend", 3.0, 0.5, 6.0, "how smoothly head flows into body (bigger = less neck)"),
    # Ears: tiny, symmetric
    Param("ear_len", 1.6, 0.8, 6.0, "ear half-length, base to tip axis"),
    Param("ear_wid", 1.1, 0.5, 2.5, "ear half-width"),
    Param("ear_thk", 0.5, 0.2, 1.2, "ear half-thickness"),
    Param("ear_x", -0.8, -3.0, 2.0, "ear base x offset from head center"),
    Param("ear_y", 2.0, 0.5, 4.0, "ear base sideways offset from head midline"),
    Param("ear_zf", 0.8, 0.4, 1.0, "ear base height as fraction of head_rz"),
    Param("ear_tilt", 30.0, -10.0, 70.0, "ear tilt backward, degrees"),
    Param("ear_splay", 15.0, -10.0, 50.0, "ear splay outward, degrees"),
    Param("ear_blend", 0.6, 0.1, 1.5, "how smoothly ears join head"),
    # Front feet: small, mostly under the body
    Param("ff_len", 1.8, 0.8, 3.0, "front foot half-length"),
    Param("ff_rad", 1.0, 0.5, 2.0, "front foot half-width/height"),
    Param("ff_x", 6.0, 0.0, 12.0, "front foot x position"),
    Param("ff_y", 2.5, 1.0, 5.0, "front foot sideways offset"),
    # Hind feet
    Param("hf_len", 3.0, 1.5, 5.0, "hind foot half-length"),
    Param("hf_rad", 1.3, 0.6, 2.5, "hind foot half-width/height"),
    Param("hf_x", -4.5, -12.0, 0.0, "hind foot x position"),
    Param("hf_y", 3.8, 1.5, 6.0, "hind foot sideways offset"),
    Param("foot_blend", 0.8, 0.1, 2.0, "how smoothly feet join body"),
    # Tail
    Param("tail_r", 1.8, 0.8, 3.0, "tail radius"),
    Param("tail_dx", 0.4, -1.0, 2.0, "tail center offset behind the body's back edge"),
    Param("tail_z", 4.5, 2.0, 9.0, "tail height above ground"),
    # Face landmarks (do not change shape; used for landmark scoring)
    Param("eye_az", 38.0, 15.0, 65.0, "eye angle sideways from straight forward, degrees"),
    Param("eye_el", 15.0, -10.0, 40.0, "eye angle above head center, degrees"),
    Param("nose_el", -12.0, -40.0, 10.0, "nose angle below head center, degrees"),
]

NAMES = [p.name for p in PARAMS]
INDEX = {n: i for i, n in enumerate(NAMES)}
LOWER = np.array([p.lo for p in PARAMS])
UPPER = np.array([p.hi for p in PARAMS])
DEFAULT = np.array([p.default for p in PARAMS])

LANDMARKS = [
    "eye_l", "eye_r", "nose", "ear_tip_l", "ear_tip_r",
    "ear_base_l", "ear_base_r", "tail", "foot_fl", "foot_fr",
]


def to_dict(vec) -> dict[str, float]:
    return {n: float(v) for n, v in zip(NAMES, vec)}


def from_dict(d: dict) -> np.ndarray:
    """Build a parameter vector; missing names fall back to defaults."""
    vec = DEFAULT.copy()
    for k, v in d.items():
        if k not in INDEX:
            raise KeyError(f"unknown parameter {k!r}")
        vec[INDEX[k]] = v
    return vec


def clip(vec) -> np.ndarray:
    return np.clip(np.asarray(vec, float), LOWER, UPPER)


def save(vec, path):
    with open(path, "w") as f:
        json.dump(to_dict(vec), f, indent=2)


def load(path) -> np.ndarray:
    with open(path) as f:
        return from_dict(json.load(f))


# ---------------------------------------------------------------- SDF pieces

def _sd_ellipsoid(p, r):
    """Approximate SDF of an axis-aligned ellipsoid with radii r at origin."""
    k0 = np.linalg.norm(p / r, axis=-1)
    k1 = np.linalg.norm(p / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def _smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def _smax(a, b, k):
    return -_smin(-a, -b, k)


def _rot_x(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _rot_y(deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


class Prince:
    """A concrete Prince built from a parameter vector."""

    def __init__(self, vec):
        self.vec = clip(vec)
        P = to_dict(self.vec)
        self.P = P
        self.body_c = np.array([0.0, 0.0, P["body_cz"]])
        self.body_r = np.array([P["body_len"], P["body_wid"], P["body_hgt"]])
        self.head_c = np.array([P["head_x"], 0.0, P["head_z"]])
        self.head_r = np.array([P["head_rx"], P["head_ry"], P["head_rz"]])
        self.ear_r = np.array([P["ear_wid"], P["ear_thk"], P["ear_len"]])
        # ears: local frame has the long axis along +z (local y = thickness)
        # Ear faces forward, so width is along x, thickness along y.
        self.ears = []
        for side in (+1, -1):  # +1 = left (y+), -1 = right
            base = self.head_c + np.array(
                [P["ear_x"], side * P["ear_y"], P["ear_zf"] * P["head_rz"]])
            R = _rot_x(-side * P["ear_splay"]) @ _rot_y(-P["ear_tilt"])
            center = base + R @ np.array([0, 0, P["ear_len"]])
            tip = base + R @ np.array([0, 0, 2 * P["ear_len"]])
            self.ears.append((base, R, center, tip))
        self.feet = []
        for x, y, ln, rad in ((P["ff_x"], P["ff_y"], P["ff_len"], P["ff_rad"]),
                              (P["hf_x"], P["hf_y"], P["hf_len"], P["hf_rad"])):
            for side in (+1, -1):
                self.feet.append((np.array([x, side * y, rad]),
                                  np.array([ln, rad, rad])))
        self.tail_c = np.array([-P["body_len"] - P["tail_dx"], 0.0, P["tail_z"]])

    # -- shape
    def sdf(self, p):
        P = self.P
        p = np.asarray(p, float)
        d = _sd_ellipsoid(p - self.body_c, self.body_r)
        head = _sd_ellipsoid(p - self.head_c, self.head_r)
        d = _smin(d, head, P["neck_blend"])
        ears = None
        for _, R, c, _ in self.ears:
            local = (p - c) @ R  # == R^T (p - c) for row vectors
            e = _sd_ellipsoid(local, self.ear_r)
            ears = e if ears is None else np.minimum(ears, e)
        d = _smin(d, ears, P["ear_blend"])
        feet = None
        for c, r in self.feet:
            f = _sd_ellipsoid(p - c, r)
            feet = f if feet is None else np.minimum(feet, f)
        d = _smin(d, feet, P["foot_blend"])
        tail = np.linalg.norm(p - self.tail_c, axis=-1) - P["tail_r"]
        d = _smin(d, tail, 0.5)
        # flat where he sits: cut everything below the ground
        d = _smax(d, -p[..., 2], P["ground_blend"])
        return d

    # -- landmarks (3D)
    def _head_surface(self, az_deg, el_deg):
        az, el = np.radians(az_deg), np.radians(el_deg)
        u = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
        return self.head_c + u * self.head_r

    def landmarks(self) -> dict[str, np.ndarray]:
        P = self.P
        (bl, _, _, tl), (br, _, _, tr) = self.ears
        ff_l, ff_r = self.feet[0], self.feet[1]
        return {
            "eye_l": self._head_surface(P["eye_az"], P["eye_el"]),
            "eye_r": self._head_surface(-P["eye_az"], P["eye_el"]),
            "nose": self._head_surface(0.0, P["nose_el"]),
            "ear_tip_l": tl, "ear_tip_r": tr,
            "ear_base_l": bl, "ear_base_r": br,
            "tail": self.tail_c - np.array([P["tail_r"], 0, 0]),
            "foot_fl": ff_l[0] + np.array([ff_l[1][0], 0, 0]),
            "foot_fr": ff_r[0] + np.array([ff_r[1][0], 0, 0]),
        }

    def bounds(self):
        """Axis-aligned box that safely contains him."""
        lo = np.array([-self.P["body_len"] - 6, -14.0, -0.5])
        hi = np.array([self.P["head_x"] + self.P["head_rx"] + 6, 14.0,
                       self.P["head_z"] + self.P["head_rz"] + 2 * self.P["ear_len"] + 4])
        return lo, hi

    # -- export
    def mesh(self, resolution=0.25):
        """Marching-cubes mesh (trimesh.Trimesh)."""
        import trimesh
        from skimage.measure import marching_cubes
        lo, hi = self.bounds()
        axes = [np.arange(lo[i], hi[i] + resolution, resolution) for i in range(3)]
        grid = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1)
        vol = self.sdf(grid.reshape(-1, 3)).reshape(grid.shape[:3])
        verts, faces, normals, _ = marching_cubes(vol, 0.0, spacing=(resolution,) * 3)
        verts += lo
        return trimesh.Trimesh(verts, faces[:, ::-1], vertex_normals=-normals, process=True)
