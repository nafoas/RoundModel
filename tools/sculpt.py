"""Sculpt Prince's head step by step, reproducibly.

The sculpt is a list of small operations in a JSON log, applied in order to
the base body (the silhouette-fitted body from Checkpoint 3, before any face
pass). Each step is meant to be checked against the references right after
it is added (tools/preview.py), so the log is also the record of how his
face was shaped.

Operations
  eye     {"side", "centre", "radius", "axis"}: an eyeball (separate object)
  grab    {"at", "move", "radius"}: move the surface near a point by a vector,
          with smooth falloff (like a sculpting grab brush)
  section {"z", "half_height", "front", "k", "power"}: pull the front of the
          head back toward the curve y = front - k |x|^power (seen from above), in a band of
          heights around z
  socket  {"side", "proud", "rim", "blend"}: the eye's opening, facing out
          along the eye's axis; cornea stands `proud` beyond the lid
  smooth  {"at", "radius", "strength", "iters"}: relax the surface locally

Any step with "mirror": true is also applied mirrored to his other side.

Points are metres (+x his right, +y forward, +z up). "at" may also be given
as {"master_px": [u, v]}: the point where the master camera's ray through
that pixel meets the current surface, so steps can be placed by pointing at
the master.

usage: sculpt.py LOG.json OUTDIR
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fit_surface as FS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def base_mesh():
    meta = json.loads((ROOT / "checkpoints/cp3/body_meta.json").read_text())
    d, F = FS.icosphere(meta["subdiv"])
    r = np.load(ROOT / "checkpoints/cp3/body_radii_preface.npy")
    return np.array(meta["centre_m"]) + d * r[:, None], F


def neighbours(F, n):
    rows, cols, deg = FS.neighbours(F, n)
    return rows, cols, deg


class Master:
    def __init__(self):
        from scipy.spatial.transform import Rotation as R
        v = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]["master_front_standing"]
        self.R = R.from_rotvec(v["rotvec_world_to_cam"]).as_matrix()
        self.pos = np.array(v["camera_position_m"])
        self.f = v["focal_px"]
        self.w, self.h = v["size"]

    def ray(self, px):
        d = np.array([(px[0] - self.w / 2) / self.f, (px[1] - self.h / 2) / self.f, 1.0]) @ self.R
        return d / np.linalg.norm(d)

    def project(self, X):
        Xc = (np.atleast_2d(X) - self.pos) @ self.R.T
        return np.stack([self.f * Xc[:, 0] / Xc[:, 2] + self.w / 2, self.f * Xc[:, 1] / Xc[:, 2] + self.h / 2], 1)

    def hit(self, V, F, px):
        """First intersection of the master ray through px with the mesh."""
        o, d = self.pos, self.ray(px)
        a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
        e1, e2 = b - a, c - a
        p = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, p)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        s = o - a
        u = np.einsum("ij,ij->i", s, p) * inv
        q = np.cross(s, e1)
        v = (q @ d) * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        good = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0)
        if not good.any():
            raise ValueError(f"master ray through {px} misses the mesh")
        return o + d * t[good].min()


def falloff(dist, radius):
    x = np.clip(dist / radius, 0, 1)
    return (1 - x * x) ** 2  # smooth bump, 1 at centre, 0 at radius


def midline(V):
    sel = (np.abs(V[:, 0]) < 0.003) & (V[:, 1] > 0)
    z, y = V[sel, 2], V[sel, 1]
    o = np.argsort(z)
    return lambda q: np.interp(q, z[o], y[o])


def fit_outline(V, F, rows, cols, deg, master, step):
    """Make the master-view silhouette match his traced outline.

    Silhouette (rim) points are moved sideways in the master's image plane,
    never along the master's line of sight, by their distance to the traced
    outline; the move is spread smoothly into the nearby surface. Parts of
    the outline that belong to features built separately (ears, peets) are
    excluded by boxes in master pixels."""
    import cv2
    from PIL import Image
    mask = np.asarray(Image.open(ROOT / "checkpoints/cp1/masks/master_front_standing.outline.png")) > 0
    # follow the smooth envelope of his fur, not individual tufts (those
    # come from the fur itself later)
    sig = step.get("outline_soften_px", 0)
    if sig:
        mask = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), sig) > 0.5
    h, w = mask.shape
    sd = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5) - \
        cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)  # + outside, - inside (px)
    gy, gx = np.gradient(cv2.GaussianBlur(sd, (0, 0), 1.5))
    excl = np.zeros_like(mask)
    for x0, y0, x1, y1 in step.get("exclude", []):
        excl[y0:y1, x0:x1] = True
    n = len(V)
    for _ in range(step.get("iters", 6)):
        fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        N = np.zeros_like(V)
        for k in range(3):
            np.add.at(N, F[:, k], fn)
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        view = V - master.pos
        dist = np.linalg.norm(view, axis=1)
        view /= dist[:, None]
        rim = np.abs(np.einsum("ij,ij->i", N, view)) < 0.12
        uv = master.project(V)
        ui = np.clip(np.round(uv[:, 0]).astype(int), 0, w - 1)
        vi = np.clip(np.round(uv[:, 1]).astype(int), 0, h - 1)
        rim &= ~excl[vi, ui]
        # signed distance to his outline (px): move rim points by it, inward
        # if outside (+), outward if inside (-), along the outline's normal
        g = np.stack([gx[vi, ui], gy[vi, ui]], 1)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
        move_px = -sd[vi, ui][:, None] * g
        Rm = master.R
        right, down = Rm[0], Rm[1]
        move = (move_px[:, :1] * right + move_px[:, 1:] * down) * (dist / master.f)[:, None]
        D = np.zeros_like(V)
        D[rim] = move[rim]
        fixed = rim.copy()
        # spread the rim moves into the nearby surface (harmonic fill)
        for _ in range(step.get("spread", 40)):
            avg = np.zeros_like(D)
            np.add.at(avg, rows, D[cols])
            avg /= deg[:, None]
            D = np.where(fixed[:, None], D, avg * step.get("decay", 0.97))
        # smooth the correction itself so neighbouring rim points move
        # together (moving each on its own leaves a ragged edge)
        for _ in range(step.get("smooth_iters", 25)):
            avg = np.zeros_like(D)
            np.add.at(avg, rows, D[cols])
            D = 0.5 * D + 0.5 * avg / deg[:, None]
        # keep the move sideways: remove any part along the line of sight
        D -= np.einsum("ij,ij->i", D, view)[:, None] * view
        V = V + D * step.get("rate", 0.8)
    return V


def apply(log, V, F, master):
    V0 = V.copy()
    V = V.copy()
    n = len(V)
    rows, cols, deg = neighbours(F, n)
    eyes = {}
    steps = []
    for step in log["steps"]:
        steps.append(step)
        if step.get("mirror"):
            m = dict(step)
            m.pop("mirror")
            flip = np.array([-1, 1, 1.0])
            for k in ("at", "move", "centre", "axis"):
                if k in m and not isinstance(m[k], dict):
                    m[k] = (np.asarray(m[k]) * flip).tolist()
            if "side" in m:
                m["side"] = {"R": "L", "L": "R"}[m["side"]]
            steps.append(m)
    for step in steps:
        op = step["op"]
        at = step.get("at")
        if isinstance(at, dict) and "master_px" in at:
            at = master.hit(V, F, at["master_px"])
        at = None if at is None else np.asarray(at, float)
        if op == "eye":
            # "front" is the visible front of the eye (the measured point on
            # the master ray); the eyeball sits behind it along its axis
            ax_ = np.asarray(step["axis"], float)
            ax_ /= np.linalg.norm(ax_)
            c = np.asarray(step["front"], float) - ax_ * step["radius"]
            eyes[step["side"]] = {"centre": c.tolist(), "radius": step["radius"], "axis": ax_.tolist()}
        elif op == "grab":
            w = falloff(np.linalg.norm(V - at, axis=1), step["radius"])
            V += w[:, None] * np.asarray(step["move"], float)
        elif op == "section":
            # pull the front of the head back toward a target curve seen from
            # above, y = front - k * x**2, inside a smooth band of heights;
            # only moves points that stick out in front of the curve, and only
            # along y (away from the master camera, so the master outline holds)
            z0, hz = step["z"], step["half_height"]
            hz_below = step.get("half_height_below", hz)
            dz = V[:, 2] - z0
            wz = np.where(dz >= 0, falloff(np.abs(dz), hz), falloff(np.abs(dz), hz_below))
            if step["front"] == "midline":
                # keep his profile: the curve's front follows the starting
                # midline at every height
                front = midline(V0)(V[:, 2])
            else:
                front = step["front"]
            ax_ = np.abs(V[:, 0])
            if "curve" in step:
                # explicit outline seen from above: [x, drop behind the front]
                # pairs for one side, mirrored; smooth (monotone) between them
                from scipy.interpolate import PchipInterpolator
                cx, cd = np.array(step["curve"], float).T
                target = front - PchipInterpolator(cx, cd, extrapolate=True)(np.minimum(ax_, cx[-1]))
            else:
                # power 2 = even curve; higher = broad flat front turning back
                # more sharply toward the sides
                target = front - step["k"] * ax_ ** step.get("power", 2)
            # past x_cap (just beyond the eyes) the pull fades out gradually:
            # the side of the head back there is already behind the eyes, and
            # a hard stop leaves a flat forward-facing wall
            wz = wz * falloff(np.maximum(ax_ - step.get("x_cap", 1.0), 0), step.get("x_fade", 0.012))
            excess = np.maximum(V[:, 1] - target, 0) * (V[:, 1] > step.get("min_y", 0.0))
            V[:, 1] -= wz * excess * step.get("strength", 1.0)
        elif op == "socket":
            # The opening the eye sits in faces OUT along the eye's own axis
            # (sideways), never forward. Around the eye, surface points in
            # front of the lid plane (measured along the eye axis) are pressed
            # back along the axis to it; the press fades out beyond the rim.
            e = eyes[step["side"]]
            c, ax_, re = np.asarray(e["centre"]), np.asarray(e["axis"]), e["radius"]
            lid = c + ax_ * (re - step["proud"])  # lid plane: cornea stands `proud` beyond it
            q = V - c
            h = q @ ax_
            radial = np.linalg.norm(q - h[:, None] * ax_, axis=1)
            w = falloff(np.maximum(radial - step["rim"], 0), step["blend"]) * (h > 0)
            over = np.maximum((V - lid) @ ax_, 0)
            V -= (w * over)[:, None] * ax_[None, :]
        elif op == "fit_outline":
            V = fit_outline(V, F, rows, cols, deg, master, step)
        elif op == "smooth":
            w = falloff(np.linalg.norm(V - at, axis=1), step["radius"]) * step.get("strength", 0.5)
            for _ in range(step.get("iters", 3)):
                avg = np.zeros_like(V)
                np.add.at(avg, rows, V[cols])
                avg /= deg[:, None]
                V += w[:, None] * (avg - V)
        else:
            raise ValueError(op)
    return V, eyes


def sphere(c, r, n=40):
    u, v = np.meshgrid(np.linspace(0, np.pi, n), np.linspace(0, 2 * np.pi, 2 * n, endpoint=False), indexing="ij")
    P = np.stack([np.sin(u) * np.cos(v), np.sin(u) * np.sin(v), np.cos(u)], -1).reshape(-1, 3) * r + c
    F = []
    m = 2 * n
    for i in range(n - 1):
        for j in range(m):
            a, b, cc, d = i * m + j, i * m + (j + 1) % m, (i + 1) * m + j, (i + 1) * m + (j + 1) % m
            F += [(a, cc, b), (b, cc, d)]
    return P, np.array(F)


def write_obj(path, V, F):
    with open(path, "w") as fh:
        for p in V:
            fh.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        for t in F + 1:
            fh.write(f"f {t[0]} {t[1]} {t[2]}\n")


def main(log_path, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    log = json.loads(Path(log_path).read_text())
    V, F = base_mesh()
    V, eyes = apply(log, V, F, Master())
    write_obj(out / "head.obj", V, F)
    for side, e in eyes.items():
        P, Fe = sphere(np.array(e["centre"]), e["radius"])
        write_obj(out / f"eye_{side}.obj", P, Fe)
    np.save(out / "verts.npy", V)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
