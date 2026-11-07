"""Silhouette renderer: sphere-trace Prince's SDF from a camera.

Returns a *soft* silhouette in [0, 1]: ~1 inside him, ~0 outside, with a
smooth edge whose width is `tau` model units. The soft edge gives the
optimizer a useful signal; scoring also uses the hard (>0.5) version.
"""
from __future__ import annotations

import numpy as np

from .camera import Camera
from .model import Prince


def render_min_dist(prince: Prince, cam: Camera, steps: int = 64) -> np.ndarray:
    """Per pixel: smallest SDF value found along the ray (negative = hit)."""
    origin, dirs = cam.rays()
    n = len(dirs)
    lo, hi = prince.bounds()
    # ray / bounding-box intersection to limit marching
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / dirs
        t1 = (lo - origin) * inv
        t2 = (hi - origin) * inv
    tnear = np.max(np.minimum(t1, t2), axis=1)
    tfar = np.min(np.maximum(t1, t2), axis=1)
    hit_box = tfar > np.maximum(tnear, 0)
    best = np.full(n, 1e3)
    idx = np.nonzero(hit_box)[0]
    t = np.maximum(tnear[idx], 0)
    tf = tfar[idx]
    for _ in range(steps):
        if idx.size == 0:
            break
        p = origin + dirs[idx] * t[:, None]
        d = prince.sdf(p)
        best[idx] = np.minimum(best[idx], d)
        t = t + np.maximum(d * 0.8, 0.02)
        hit = d <= 1e-3
        best[idx[hit]] = -1.0  # solidly inside: avoids grey seams on hits
        keep = ~hit & (t < tf)
        idx, t, tf = idx[keep], t[keep], tf[keep]
    return best.reshape(cam.height, cam.width)


def render_silhouette(prince: Prince, cam: Camera, tau: float = 0.3,
                      steps: int = 64) -> np.ndarray:
    d = render_min_dist(prince, cam, steps)
    return 1.0 / (1.0 + np.exp(np.clip(d / tau, -50, 50)))


def render_shaded(prince: Prince, cam: Camera, steps: int = 96) -> np.ndarray:
    """Simple grey shaded image (H, W) for reports. 1 = background."""
    origin, dirs = cam.rays()
    n = len(dirs)
    t = np.zeros(n)
    lo, hi = prince.bounds()
    t[:] = max(np.linalg.norm(origin) - 40, 0)
    hit = np.zeros(n, bool)
    active = np.arange(n)
    for _ in range(steps):
        if active.size == 0:
            break
        p = origin + dirs[active] * t[active, None]
        d = prince.sdf(p)
        t[active] += np.maximum(d * 0.8, 0.01)
        h = d < 1e-3
        hit[active[h]] = True
        far = t[active] > np.linalg.norm(origin) + 40
        active = active[~h & ~far]
    img = np.ones(n)
    if hit.any():
        p = origin + dirs[hit] * t[hit, None]
        e = 0.05
        g = np.stack([
            prince.sdf(p + [e, 0, 0]) - prince.sdf(p - [e, 0, 0]),
            prince.sdf(p + [0, e, 0]) - prince.sdf(p - [0, e, 0]),
            prince.sdf(p + [0, 0, e]) - prince.sdf(p - [0, 0, e]),
        ], axis=1)
        nrm = g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        light = np.array([0.5, 0.4, 0.8])
        light /= np.linalg.norm(light)
        diffuse = np.clip(nrm @ light, 0, 1)
        facing = np.clip(-(nrm * dirs[hit]).sum(1), 0, 1)
        img[hit] = 0.25 + 0.55 * diffuse + 0.15 * facing
    return img.reshape(cam.height, cam.width)
