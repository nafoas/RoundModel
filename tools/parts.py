"""Build Prince from his parts.

Each part is a soft rounded volume (an ellipsoid with a centre, radii and an
orientation); all parts are blended into one smooth surface with a smooth
union, so there are no seams. The parts file is a JSON list; a part can be
mirrored to his other side. The result is written as head.obj (the name the
existing renderers load) in the same world frame as the cameras: metres, +x
his right, +y forward, +z up.

usage: python tools/parts.py PARTS.json OUTDIR [--step 0.0012]

A part:
  {"name": "cheek", "centre": [x, y, z], "radii": [rx, ry, rz],
   "rot": [rx_deg, ry_deg, rz_deg],     # optional, XYZ euler, degrees
   "blend": 0.012,                      # how softly it melts into the rest
   "mirror": true,                      # also build it at -x
   "subtract": false}                   # carve instead of add (soft)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R
from skimage import measure


def ellipsoid_sdf(P, c, r, rot):
    """Approximate signed distance to an ellipsoid (good near the surface)."""
    q = (P - c) @ rot  # into the part's own axes
    k0 = np.linalg.norm(q / r, axis=1)
    k1 = np.linalg.norm(q / (r * r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def smin(a, b, k):
    """Smooth union: blends two distances over a width k."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def expand(parts):
    out = []
    for p in parts:
        if p.get("off"):
            continue
        out.append(p)
        if p.get("mirror"):
            m = dict(p)
            m["centre"] = [-p["centre"][0], p["centre"][1], p["centre"][2]]
            rx, ry, rz = p.get("rot", [0, 0, 0])
            m["rot"] = [rx, -ry, -rz]
            m["name"] = p["name"] + "_L"
            out.append(m)
    return out


def field(parts, P):
    d = None
    for p in parts:
        rot = R.from_euler("xyz", p.get("rot", [0, 0, 0]), degrees=True).as_matrix()
        di = ellipsoid_sdf(P, np.asarray(p["centre"], float), np.asarray(p["radii"], float), rot)
        if d is None:
            d = di
        elif p.get("subtract"):
            d = smax(d, -di, p.get("blend", 0.0))
        else:
            d = smin(d, di, p.get("blend", 0.0))
    return d


def build(parts, step):
    add = [p for p in parts if not p.get("subtract")]  # carving parts never grow him
    lo = np.min([np.asarray(p["centre"]) - max(p["radii"]) - 0.02 for p in add], axis=0)
    hi = np.max([np.asarray(p["centre"]) + max(p["radii"]) + 0.02 for p in add], axis=0)
    axes = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    G = np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)
    D = np.concatenate([field(parts, G[i:i + 400000]) for i in range(0, len(G), 400000)])
    D = D.reshape(len(axes[0]), len(axes[1]), len(axes[2]))
    V, F, _, _ = measure.marching_cubes(D, 0.0, spacing=(step, step, step))
    V += lo
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    F = F[np.linalg.norm(n, axis=1) > 1e-14]  # drop zero-area slivers
    return V, F  # skimage's winding already faces outward here


def write_obj(path, V, F):
    with open(path, "w") as f:
        f.write("".join(f"v {a:.6f} {b:.6f} {c:.6f}\n" for a, b, c in V))
        f.write("".join(f"f {a + 1} {b + 1} {c + 1}\n" for a, b, c in F))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts")
    ap.add_argument("out")
    ap.add_argument("--step", type=float, default=0.0012)
    a = ap.parse_args()
    data = json.loads(Path(a.parts).read_text())
    parts = expand(data["parts"])
    V, F = build(parts, a.step)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("eye_*.obj"):
        f.unlink()
    write_obj(out / "head.obj", V, F)
    for e in data.get("eyes", []):  # eyeballs as their own spheres
        u, v = np.meshgrid(np.linspace(0, np.pi, 24), np.linspace(0, 2 * np.pi, 48), indexing="ij")
        c, r = np.asarray(e["centre"]), e["radius"]
        P = np.stack([np.sin(u) * np.cos(v), np.sin(u) * np.sin(v), np.cos(u)], -1).reshape(-1, 3) * r + c
        n1, n2 = u.shape
        Fe = []
        for i in range(n1 - 1):
            for j in range(n2 - 1):
                a_, b_, c_, d_ = i * n2 + j, i * n2 + j + 1, (i + 1) * n2 + j, (i + 1) * n2 + j + 1
                Fe += [(a_, c_, b_), (b_, c_, d_)]
        write_obj(out / f"eye_{e['side']}.obj", P, np.array(Fe))
    print(f"{len(parts)} parts -> {len(V)} vertices; extent {V.min(0).round(3)} .. {V.max(0).round(3)}")


if __name__ == "__main__":
    sys.exit(main())
