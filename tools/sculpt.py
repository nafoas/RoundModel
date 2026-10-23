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
  bump    {"at", "radius", "height"}: soft swelling (or hollow if negative)
          along the surface normal
  crease  {"master_px_line", "width", "depth"}: soft groove along a line
          drawn on the master photo
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


def base_mesh(level=7):
    """Base body at icosphere level 7 (163,842 vertices, ~0.8 mm apart), its
    radii interpolated smoothly from the level-6 body fit. Fine enough for
    the eyelids and the nose."""
    meta = json.loads((ROOT / "checkpoints/cp3/body_meta.json").read_text())
    d6, _ = FS.icosphere(meta["subdiv"])
    r6 = np.load(ROOT / "checkpoints/cp3/body_radii_preface.npy")
    cache = ROOT / f"work/icosphere_{level}.npz"
    if cache.exists():
        z = np.load(cache)
        d, F = z["d"], z["F"]
    else:
        d, F = FS.icosphere(level)
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, d=d, F=F)
    from scipy.spatial import cKDTree
    dist, idx = cKDTree(d6).query(d, k=6)
    sig = np.median(cKDTree(d6).query(d6, k=2)[0][:, 1]) * 0.7
    w = np.exp(-(dist / sig) ** 2)
    r = (r6[idx] * w).sum(1) / w.sum(1)
    return np.array(meta["centre_m"]) + d * r[:, None], F


_AVG = {}


def neighbours(F, n):
    rows, cols, deg = FS.neighbours(F, n)
    return rows, cols, deg


def avg_op(rows, cols, deg):
    """Sparse operator giving each vertex the mean of its neighbours."""
    key = (len(deg), len(rows))
    if key not in _AVG:
        import scipy.sparse as sp
        _AVG[key] = sp.csr_matrix((1.0 / deg[rows], (rows, cols)), shape=(len(deg), len(deg)))
    return _AVG[key]


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


def normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return N / np.linalg.norm(N, axis=1, keepdims=True)


def densify(line, step_px):
    out = []
    for a, b in zip(line[:-1], line[1:]):
        a, b = np.array(a, float), np.array(b, float)
        n = max(1, int(np.linalg.norm(b - a) / step_px))
        out += [a + (b - a) * t for t in np.linspace(0, 1, n, endpoint=False)]
    out.append(np.array(line[-1], float))
    return out


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
            avg = avg_op(rows, cols, deg) @ D
            D = np.where(fixed[:, None], D, avg * step.get("decay", 0.97))
        # smooth the correction itself so neighbouring rim points move
        # together (moving each on its own leaves a ragged edge)
        for _ in range(step.get("smooth_iters", 25)):
            D = 0.5 * D + 0.5 * (avg_op(rows, cols, deg) @ D)
        # keep the move sideways: remove any part along the line of sight
        D -= np.einsum("ij,ij->i", D, view)[:, None] * view
        V = V + D * step.get("rate", 0.8)
    return V


HEAD_C = np.array([0.0, 0.065, 0.115])  # middle of the head, muzzle included
NECK_PIVOT = np.array([0.0, 0.02, 0.095])  # where the head turns on the neck


def head_weight(V):
    """1 on the head, fading to 0 on the body (the head is posed per photo)."""
    d = np.linalg.norm(V - HEAD_C, axis=1)
    x = np.clip((d - 0.058) / 0.03, 0, 1)
    return 1 - x * x * (3 - 2 * x)


def master_outline_points(V, F, master, px=4):
    """Vertices that are on the sculpt's actual outline from the master camera
    (edge-on to it and projecting onto the silhouette edge), not every
    sideways-facing point."""
    import cv2
    N = normals(V, F)
    mview = V - master.pos
    mview /= np.linalg.norm(mview, axis=1, keepdims=True)
    rim = np.abs(np.einsum("ij,ij->i", N, mview)) < 0.15
    uv = master.project(V)
    w, h = int(master.w), int(master.h)
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    front = np.einsum("ij,ij->i", fn, master.pos - V[F[:, 0]]) > 0
    sil = np.zeros((h, w), np.uint8)
    cv2.fillPoly(sil, list(np.round(uv[F[front]]).astype(np.int32)), 1)
    sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    edge = cv2.dilate(sil, np.ones((3, 3), np.uint8)) - cv2.erode(sil, np.ones((3, 3), np.uint8))
    near = cv2.dilate(edge, np.ones((2 * px + 1, 2 * px + 1), np.uint8)) > 0
    ui = np.clip(np.round(uv[:, 0]).astype(int), 0, w - 1)
    vi = np.clip(np.round(uv[:, 1]).astype(int), 0, h - 1)
    return rim & near[vi, ui]


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
            # the master is not perfectly symmetric (his head is slightly
            # turned): the mirrored copy may take its own values
            m.update(m.pop("mirror_overrides", {}))
            step = dict(step)
            step.pop("mirror_overrides", None)
            steps[-1] = step
            steps.append(m)
    # Cache: the mesh after each step is stored under a hash of every step up
    # to it, so changing a late step reuses all the work before it. Eye steps
    # only add objects, so they are replayed (cheap) rather than cached.
    import hashlib
    cache_dir = ROOT / "work/sculpt_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    # the code is part of the key too: changing how an op works must not
    # reuse meshes made the old way
    keys, hsh = [], hashlib.sha1(str(len(V)).encode() + Path(__file__).read_bytes())
    for st in steps:
        hsh.update(json.dumps(st, sort_keys=True).encode())
        keys.append(hsh.hexdigest()[:16])
    start = 0
    for i in range(len(steps) - 1, -1, -1):
        f = cache_dir / f"{keys[i]}.npy"
        if f.exists():
            V = np.load(f)
            start = i + 1
            break
    for st in steps[:start]:
        if st["op"] == "eye":
            ax_ = np.asarray(st["axis"], float)
            ax_ /= np.linalg.norm(ax_)
            c = np.asarray(st["centre"], float) if "centre" in st else np.asarray(st["front"], float) - ax_ * st["radius"]
            eyes[st["side"]] = {"centre": c.tolist(), "radius": st["radius"], "axis": ax_.tolist()}
    for si, step in enumerate(steps):
        if si < start:
            continue
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
            if "centre" in step:  # eyeball centre given directly (placed by measurement)
                c = np.asarray(step["centre"], float)
            else:
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
            perp = q - h[:, None] * ax_
            # elliptical opening: "rim_h" along the head (front-back),
            # "rim_v" up-down; an almond, as in his side-on photos
            up = np.array([0, 0, 1.0]) - ax_ * ax_[2]
            up /= np.linalg.norm(up)
            side = np.cross(ax_, up)
            rh, rv = step.get("rim_h", step["rim"]), step.get("rim_v", step["rim"])
            pu, ps = perp @ up, perp @ side
            ell = np.sqrt((ps / rh) ** 2 + (pu / rv) ** 2)  # 1 at the rim
            radial = ell * step["rim"]
            w = falloff(np.maximum(radial - step["rim"], 0), step["blend"]) * (h > 0)
            over = np.maximum((V - lid) @ ax_, 0)
            V -= (w * over)[:, None] * ax_[None, :]
            # outside the opening the fur wraps the eyeball: any surface that
            # would let the ball show through is pushed out to just cover it
            q = V - c
            dist = np.linalg.norm(q, axis=1)
            h = q @ ax_
            perp = q - h[:, None] * ax_
            ell = np.sqrt(((perp @ side) / rh) ** 2 + ((perp @ up) / rv) ** 2)
            cover = re + step.get("wrap", 0.0008)
            wrap = (ell > 1.0) & (dist < cover)
            V[wrap] = c + q[wrap] / dist[wrap, None] * cover
            # lids: where the fur lies below the eyeball outside the opening
            # (after seating the eye), raise it along the axis onto a shell just
            # over the ball, so the ball shows only through the opening, from
            # every direction
            if step.get("lids"):
                q = V - c
                h = q @ ax_
                perp = q - h[:, None] * ax_
                rho = np.linalg.norm(perp, axis=1)
                ell = np.sqrt(((perp @ side) / rh) ** 2 + ((perp @ up) / rv) ** 2)
                shell = np.sqrt(np.maximum(cover ** 2 - rho ** 2, 0))
                lid = (ell > 1.0) & (rho < cover) & (h > -re) & (h < shell)
                V[lid] += ((shell - h)[lid])[:, None] * ax_[None, :]
            # smooth the lid edge (pressed-back inside, wrapped outside meet
            # here and leave steps at mesh spacing), keeping the ball covered
            ring = (ell > 0.8) & (ell < step.get("edge_band", 1.35)) & (h > -re * 0.3)
            A = avg_op(rows, cols, deg)
            for _ in range(step.get("edge_smooth", 12)):
                V[ring] += 0.5 * ((A @ V)[ring] - V[ring])
                q = V - c
                dist = np.linalg.norm(q, axis=1)
                h = q @ ax_
                perp = q - h[:, None] * ax_
                ell = np.sqrt(((perp @ side) / rh) ** 2 + ((perp @ up) / rv) ** 2)
                inside = ring & (ell > 1.0) & (dist < cover)
                V[inside] = c + q[inside] / dist[inside, None] * cover
            # lid folds (after the edge smoothing, which would erode them):
            # just outside the opening, in front-above and
            # front-below, the fur stands out sideways (along the eye axis) to
            # `fold_up` / `fold_down` from the eye centre, so from the front
            # they hide the top and bottom of the eyeball while from the side
            # the whole round eye shows (profile: a fold arcs over the front of
            # the eye). Strongest in front-above/below, still present straight above/below; fades over
            # `fold_band` beyond the rim.
            if step.get("fold_up") or step.get("fold_down"):
                q = V - c
                h = q @ ax_
                perp = q - h[:, None] * ax_
                rho = np.linalg.norm(perp, axis=1)
                ell = np.sqrt(((perp @ side) / rh) ** 2 + ((perp @ up) / rv) ** 2)
                cphi = (perp @ side) * np.sign(side[1]) / np.maximum(rho, 1e-9)  # cos from forward
                sphi = (perp @ up) / np.maximum(rho, 1e-9)
                amp = np.where(sphi > 0, step.get("fold_up", 0.0), step.get("fold_down", 0.0))
                ang = np.abs(sphi) * np.sqrt(np.clip((cphi + 0.4) / 1.4, 0, 1))  # ~0.9 at 55 deg, 0.53 straight up
                fb = step.get("fold_band", 0.004)
                rise = step.get("fold_rise", 0.0015)
                dr = np.maximum(ell - 1.0, 0) * rh  # distance beyond the rim
                ramp = np.clip(dr / rise, 0, 1)
                ramp = ramp * ramp * (3 - 2 * ramp)  # rounded lip, not a wall
                w = ang * ramp * falloff(np.maximum(dr - rise, 0), fb) * (ell > 1.0) * (h > -re)
                target = amp * w
                raise_ = np.maximum(target - h, 0) * (w > 0)
                V += raise_[:, None] * ax_[None, :]
                # round it off, keeping the eyeball covered outside the opening
                zone = (w > 0.02) | ((ell > 0.9) & (dr < rise + fb) & (h > -re))
                for _ in range(step.get("fold_smooth", 12)):
                    V[zone] += 0.5 * ((A @ V)[zone] - V[zone])
                    q = V - c
                    dist = np.linalg.norm(q, axis=1)
                    h = q @ ax_
                    perp = q - h[:, None] * ax_
                    ell = np.sqrt(((perp @ side) / rh) ** 2 + ((perp @ up) / rv) ** 2)
                    inside = zone & (ell > 1.0) & (dist < cover)
                    V[inside] = c + q[inside] / dist[inside, None] * cover
            # lid roll: just inside the opening the lid tucks into the eye,
            # so the visible edge follows the smooth almond, not the mesh
            if step.get("tuck", 0):
                q = V - c
                dist = np.linalg.norm(q, axis=1)
                h = q @ ax_
                perp = q - h[:, None] * ax_
                ell = np.sqrt(((perp @ side) / rh) ** 2 + ((perp @ up) / rv) ** 2)
                band = (ell > 1.0 - step["tuck"]) & (ell <= 1.0) & (h > 0)
                V[band] = c + q[band] / dist[band, None] * (re - 0.0004)
        elif op == "eye_seat":
            # Seat the eyeball in the head: around the eye the fur is lowered
            # along the eye axis until, at the eyeball's rim, it sits `rim_h`
            # in front of the centre (near the equator: the eye bulges, close-ups
            # 02, 03, 09). The lowering is measured all round the rim and spread
            # smoothly over `reach` beyond it, so the face beside the eye is
            # gently narrower rather than dished.
            e = eyes[step["side"]]
            c, ax_, re = np.asarray(e["centre"]), np.asarray(e["axis"]), e["radius"]
            up = np.array([0, 0, 1.0]) - ax_ * ax_[2]
            up /= np.linalg.norm(up)
            side = np.cross(ax_, up)
            q = V - c
            h = q @ ax_
            perp = q - h[:, None] * ax_
            rho = np.linalg.norm(perp, axis=1)
            phi = np.arctan2(perp @ up, perp @ side)
            lateral = h > -0.3 * re
            ring = lateral & (rho > re) & (rho < re + 0.002)
            nb = 36
            bins = ((phi + np.pi) / (2 * np.pi) * nb).astype(int) % nb
            exc = np.zeros(nb)
            for b in range(nb):
                sel = ring & (bins == b)
                exc[b] = max(np.max(h[sel]) - step["rim_h"], 0) if sel.any() else 0
            # how far the fur may come down can differ round the eye: less in
            # front (toward the nose), above and below, where from the front
            # the fur covers the eyeball (master: a tall almond)
            bc = (np.arange(nb) + 0.5) / nb * 2 * np.pi - np.pi  # bin centre angle
            bu, bs = np.sin(bc), np.cos(bc) * np.sign(side[1])  # up, toward the nose
            md = step.get("max_drop", 1.0)
            caps = (np.maximum(bu, 0) ** 2 * step.get("max_drop_up", md)
                    + np.maximum(-bu, 0) ** 2 * step.get("max_drop_down", md)
                    + np.maximum(bs, 0) ** 2 * step.get("max_drop_front", md)
                    + np.maximum(-bs, 0) ** 2 * md)
            exc = np.minimum(exc, caps)
            # smooth round the rim (circular)
            for _ in range(3):
                exc = 0.25 * np.roll(exc, 1) + 0.5 * exc + 0.25 * np.roll(exc, -1)
            # interpolate per vertex (linear between bin centres)
            f = (phi + np.pi) / (2 * np.pi) * nb - 0.5
            i0 = np.floor(f).astype(int) % nb
            t = f - np.floor(f)
            ex_v = exc[i0] * (1 - t) + exc[(i0 + 1) % nb] * t
            # fade out just behind the eye's side instead of stopping dead
            # there (a hard stop leaves a crease across the brow)
            fb = step.get("back_fade", 0.0)
            if fb:
                hb = np.clip((h + 0.3 * re + fb) / fb, 0, 1)
                lateral = hb * hb * (3 - 2 * hb)
            w = falloff(np.maximum(rho - re, 0), step["reach"]) * lateral
            V -= (w * ex_v)[:, None] * ax_[None, :]
        elif op == "fair":
            # Replace a patch with the fairest surface (least bending) that
            # meets everything held: the patch edge, the lids right round each
            # eye, and the master outline. Removes ledges and cliffs over and
            # between the eyes without carving new ones. Solved directly (step-
            # by-step smoothing on this fine a mesh reaches only ~1 cm).
            import scipy.sparse as sp
            from scipy.sparse.linalg import spsolve
            d0 = np.linalg.norm(V - at, axis=1)
            region = d0 < step["radius"]
            hold = d0 > step["radius"] - step.get("edge", 0.004)
            for e in eyes.values():
                de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                hold |= de < step.get("hold_eyes", 0.003)
            hold |= master_outline_points(V, F, master)
            rid = np.nonzero(region)[0]
            Lf = avg_op(rows, cols, deg) - sp.identity(len(V), format="csr")
            Lr = Lf[rid][:, rid]
            # vertices just outside the region enter through the Laplacian
            Lout = Lf[rid][:, ~region]
            wdat = np.where(hold[rid], 1.0, step.get("keep", 1e-4))
            M_ = sp.diags(wdat) + step.get("stiffness", 1.0) * (Lr.T @ Lr)
            Mc = M_.tocsc()
            for k in range(3):
                rhs = wdat * V[rid, k] - step.get("stiffness", 1.0) * (Lr.T @ (Lout @ V[~region, k]))
                V[rid, k] = spsolve(Mc, rhs)
        elif op == "brow_cover":
            # The fold of fur over each eye, from where his photos show eye
            # and where they don't. In each photo (head posed as there):
            # fur in front of the eyeball where the photo shows eye moves back
            # (reveal); fur at the lid behind a part of the eyeball that the
            # photo does NOT show, but that is next to what it shows, comes
            # forward over it (cover). One smooth offset along the surface
            # normal (least bending), only round the eyes, fading to nothing.
            import cv2
            import scipy.sparse as sp
            from scipy.sparse.linalg import factorized
            from PIL import Image
            from scipy.spatial.transform import Rotation as Rot
            traces = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
            sidecams = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
            mcam = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]["master_front_standing"]
            A_ = avg_op(rows, cols, deg)
            hw = head_weight(V)
            for _ in range(step.get("rounds", 4)):
                N = normals(V, F)
                wsum = np.zeros(len(V))
                rhs = np.zeros(len(V))
                region = np.zeros(len(V), bool)
                for e in eyes.values():
                    region |= np.linalg.norm(V - np.asarray(e["centre"]), axis=1) < e["radius"] + step.get("reach", 0.014)
                for view, vw in step["views"].items():
                    if view == "master_front_standing":
                        c_ = mcam
                        Rc = Rot.from_rotvec(c_["rotvec_world_to_cam"]).as_matrix()
                        cpos, f, cc = np.array(c_["camera_position_m"]), c_["focal_px"], np.array(c_["size"]) / 2
                        Rp, tp, pv = np.eye(3), np.zeros(3), NECK_PIVOT
                    else:
                        c_ = sidecams[view]
                        Rc = Rot.from_rotvec(c_["rotvec_world_to_cam"]).as_matrix()
                        cpos, f, cc = np.array(c_["camera_position_m"]), c_["focal_px"], np.array(c_["principal_px"])
                        pp = json.loads((ROOT / f"checkpoints/cp3/head_poses_parts/{view}.json").read_text())
                        Rp, tp = Rot.from_rotvec(pp["rotvec"]).as_matrix(), np.array(pp["shift_m"])
                        pv = np.array(pp.get("pivot", NECK_PIVOT))
                    Vp = V + hw[:, None] * (((V - pv) @ Rp.T + pv + tp) - V)
                    Np = N @ Rp.T
                    Xc = (Vp - cpos) @ Rc.T
                    uv = f * Xc[:, :2] / Xc[:, 2:3] + cc
                    vdir = Vp - cpos
                    tv = np.linalg.norm(vdir, axis=1)
                    vdir /= tv[:, None]
                    cosn = np.maximum(np.abs(np.einsum("ij,ij->i", Np, vdir)), 0.25)
                    for side, e in eyes.items():
                        poly = traces.get(view, {}).get("eye_" + side)
                        if poly is None:
                            continue
                        P = np.array(poly, np.int32)
                        x0, y0 = P.min(0) - 60
                        x1, y1 = P.max(0) + 60
                        tm = np.zeros((y1 - y0, x1 - x0), np.uint8)
                        cv2.fillPoly(tm, [P - [x0, y0]], 1)
                        ring = cv2.dilate(tm, np.ones((2 * vw.get("ring_px", 20) + 1,) * 2, np.uint8))
                        ui = np.round(uv[:, 0]).astype(int) - x0
                        vi = np.round(uv[:, 1]).astype(int) - y0
                        inb = (ui >= 0) & (vi >= 0) & (ui < x1 - x0) & (vi < y1 - y0)
                        ui, vi = np.clip(ui, 0, x1 - x0 - 1), np.clip(vi, 0, y1 - y0 - 1)
                        shown = inb & (tm[vi, ui] > 0)
                        nearring = inb & (ring[vi, ui] > 0)
                        cp = (np.asarray(e["centre"]) - pv) @ Rp.T + pv + tp
                        oc = cpos - cp
                        bq = vdir @ oc
                        disc = bq ** 2 - (oc @ oc - e["radius"] ** 2)
                        hit = disc > 0
                        tnear = -bq - np.sqrt(np.maximum(disc, 0))
                        de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                        local = region & (de > 0.0002) & (de < step.get("reach", 0.014))
                        m = step.get("margin", 0.0004)
                        reveal = local & hit & shown & (tv < tnear + m)
                        cover = local & hit & ~shown & nearring & (tv > tnear - m) & (de < step.get("lid_band", 0.004))
                        w_ = vw.get("weight", 1.0)
                        wsum += w_ * reveal + w_ * vw.get("cover_w", 1.0) * cover
                        rhs += w_ * reveal * (-np.clip((tnear - tv + m) / cosn, 0, 0.006) * 1000)
                        rhs += w_ * vw.get("cover_w", 1.0) * cover * (np.clip((tv - tnear + m) / cosn, 0, 0.006) * 1000)
                rid = np.nonzero(region)[0]
                Lr = (A_ - sp.identity(len(V), format="csr"))[rid][:, rid]
                edge = np.zeros(len(V))
                for e in eyes.values():
                    de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                    edge = np.maximum(edge, (de > step.get("reach", 0.014) - 0.002).astype(float))
                b = np.where(wsum > 0, rhs / np.maximum(wsum, 1e-9), 0)
                M_ = (sp.diags(wsum[rid] + 10.0 * edge[rid] + 1e-7) + step.get("stiffness", 30.0) * (Lr.T @ Lr)).tocsc()
                t = np.zeros(len(V))
                t[rid] = factorized(M_)(wsum[rid] * b[rid])
                V = V + (t / 1000 * step.get("rate", 1.0))[:, None] * N
                print(f"brow_cover: reveal/cover points {int((rhs < 0).sum())}/{int((rhs > 0).sum())}, "
                      f"moves {t.min():.2f}..{t.max():.2f} mm", file=sys.stderr)
        elif op == "brow_contour":
            # The brow and forehead fur standing in front of each eye, seen
            # edge-on from an angle, is what bounds his visible eye in the
            # master, three-quarters and top-down (the profile shows the whole
            # eye, so his lid does not cover it). In each such photo (head
            # posed as there) the model's outline points in front of the
            # eyeball are moved sideways in that photo's picture plane onto
            # the edge of his visible eye; all photos' moves combine into one
            # smooth local change.
            import cv2
            import scipy.sparse as sp
            from scipy.sparse.linalg import factorized
            from scipy.spatial.transform import Rotation as Rot
            traces = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
            sidecams = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
            mcam = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]["master_front_standing"]
            A_ = avg_op(rows, cols, deg)
            hw = head_weight(V)
            reach = step.get("reach", 0.016)
            region = np.zeros(len(V), bool)
            for e in eyes.values():
                region |= np.linalg.norm(V - np.asarray(e["centre"]), axis=1) < e["radius"] + reach
            rid = np.nonzero(region)[0]
            Lr = (A_ - sp.identity(len(V), format="csr"))[rid][:, rid]
            edge = np.zeros(len(V))
            for e in eyes.values():
                de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                edge = np.maximum(edge, ((de > reach - 0.003) & (de < reach)).astype(float))
            for rnd in range(step.get("rounds", 5)):
                N = normals(V, F)
                D = np.zeros_like(V)
                wsum = np.zeros(len(V))
                for view, vw in step["views"].items():
                    if view == "master_front_standing":
                        Rc = Rot.from_rotvec(mcam["rotvec_world_to_cam"]).as_matrix()
                        cpos, f, cc = np.array(mcam["camera_position_m"]), mcam["focal_px"], np.array(mcam["size"]) / 2
                        Rp, tp, pv = np.eye(3), np.zeros(3), NECK_PIVOT
                    else:
                        c_ = sidecams[view]
                        Rc = Rot.from_rotvec(c_["rotvec_world_to_cam"]).as_matrix()
                        cpos, f, cc = np.array(c_["camera_position_m"]), c_["focal_px"], np.array(c_["principal_px"])
                        pp = json.loads((ROOT / f"checkpoints/cp3/head_poses_parts/{view}.json").read_text())
                        Rp, tp = Rot.from_rotvec(pp["rotvec"]).as_matrix(), np.array(pp["shift_m"])
                        pv = np.array(pp.get("pivot", NECK_PIVOT))
                    Vp = V + hw[:, None] * (((V - pv) @ Rp.T + pv + tp) - V)
                    Np = N @ Rp.T
                    Xc = (Vp - cpos) @ Rc.T
                    uv = f * Xc[:, :2] / Xc[:, 2:3] + cc
                    vdir = Vp - cpos
                    tv = np.linalg.norm(vdir, axis=1)
                    vdir /= tv[:, None]
                    rim = np.abs(np.einsum("ij,ij->i", Np, vdir)) < step.get("rim_cos", 0.2)
                    for side, e in eyes.items():
                        poly = traces.get(view, {}).get("eye_" + side)
                        if poly is None:
                            continue
                        P = np.array(poly, np.int32)
                        x0, y0 = P.min(0) - 80
                        x1, y1 = P.max(0) + 80
                        W_, H_ = x1 - x0, y1 - y0
                        tm = np.zeros((H_, W_), np.uint8)
                        cv2.fillPoly(tm, [P - [x0, y0]], 1)
                        sdist = (cv2.distanceTransform(1 - tm, cv2.DIST_L2, 5)
                                 - cv2.distanceTransform(tm, cv2.DIST_L2, 5))  # + outside his eye
                        gy, gx = np.gradient(cv2.GaussianBlur(sdist, (0, 0), 2))
                        cp = (np.asarray(e["centre"]) - pv) @ Rp.T + pv + tp
                        oc = cpos - cp
                        bq = vdir @ oc
                        disc = bq ** 2 - (oc @ oc - e["radius"] ** 2)
                        tnear = -bq - np.sqrt(np.maximum(disc, 0))
                        # the eyeball's disc in this photo (where an outline point
                        # in front of it bounds what shows of the eye)
                        Xe = (cp - cpos) @ Rc.T
                        ue = f * Xe[:2] / Xe[2] + cc
                        re_px = f * e["radius"] / Xe[2]
                        ui = np.round(uv[:, 0]).astype(int) - x0
                        vi = np.round(uv[:, 1]).astype(int) - y0
                        inb = (ui >= 1) & (vi >= 1) & (ui < W_ - 1) & (vi < H_ - 1)
                        ui, vi = np.clip(ui, 0, W_ - 1), np.clip(vi, 0, H_ - 1)
                        in_disc = np.linalg.norm(uv - ue, axis=1) < re_px * 1.05
                        de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                        sel = (region & rim & inb & in_disc & (disc > 0) & (tv < tnear) & (de > 0.0003)
                               & (de < reach - 0.003))
                        if not sel.any():
                            continue
                        g = np.stack([gx[vi, ui], gy[vi, ui]], 1)
                        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
                        move_px = -sdist[vi, ui][:, None] * g  # onto his eye's edge
                        move_px = np.clip(move_px, -step.get("max_px", 25), step.get("max_px", 25))
                        mm = Xc[:, 2] / f  # metres per px at the point
                        mc = np.c_[move_px * mm[:, None], np.zeros(len(V))] @ Rc  # camera -> world (posed)
                        mw = mc @ Rp  # posed -> head frame
                        w_ = vw.get("weight", 1.0)
                        D[sel] += w_ * mw[sel]
                        wsum[sel] += w_
                Dm = np.where(wsum[:, None] > 0, D / np.maximum(wsum, 1e-9)[:, None], 0)
                wt = np.minimum(wsum, 4.0) + 10.0 * edge
                M_ = (sp.diags(wt[rid] + 1e-7) + step.get("stiffness", 300.0) * (Lr.T @ Lr)).tocsc()
                solve = factorized(M_)
                Ds = np.zeros_like(V)
                for k in range(3):
                    Ds[rid, k] = solve(wt[rid] * Dm[rid, k])
                V = V + Ds * step.get("rate", 0.7)
                print(f"brow_contour round {rnd}: {int((wsum > 0).sum())} outline points, "
                      f"mean asked {np.linalg.norm(Dm[wsum > 0], axis=1).mean() * 1000:.2f} mm, "
                      f"max move {np.linalg.norm(Ds, axis=1).max() * 1000:.2f} mm", file=sys.stderr)
        elif op == "line_contour":
            # A stretch of his outline in some photos (part_traces lines, e.g.
            # the forehead): in each photo (head posed as there) the model's
            # outline points next to his line move sideways in that photo's
            # picture plane onto his line; all photos combine into one broad
            # smooth change over `region` (a ball round `at`), the fur round
            # each eye held.
            import cv2
            import scipy.sparse as sp
            from scipy.sparse.linalg import factorized
            from scipy.spatial.transform import Rotation as Rot
            traces = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
            sidecams = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
            A_ = avg_op(rows, cols, deg)
            hw = head_weight(V)
            d0 = np.linalg.norm(V - np.asarray(step["at"]), axis=1)
            region = d0 < step["radius"]
            hold = (d0 > step["radius"] - 0.004).astype(float)
            for e in eyes.values():
                hold = np.maximum(hold, (np.linalg.norm(V - np.asarray(e["centre"]), axis=1)
                                         < e["radius"] + step.get("hold_eyes", 0.003)).astype(float))
            rid = np.nonzero(region)[0]
            Lr = (A_ - sp.identity(len(V), format="csr"))[rid][:, rid]
            for rnd in range(step.get("rounds", 6)):
                N = normals(V, F)
                D = np.zeros_like(V)
                wsum = np.zeros(len(V))
                for view, vw in step["views"].items():
                    c_ = sidecams[view]
                    Rc = Rot.from_rotvec(c_["rotvec_world_to_cam"]).as_matrix()
                    cpos, f, cc = np.array(c_["camera_position_m"]), c_["focal_px"], np.array(c_["principal_px"])
                    pp = json.loads((ROOT / f"checkpoints/cp3/head_poses_parts/{view}.json").read_text())
                    Rp, tp = Rot.from_rotvec(pp["rotvec"]).as_matrix(), np.array(pp["shift_m"])
                    pv = np.array(pp.get("pivot", NECK_PIVOT))
                    Vp = V + hw[:, None] * (((V - pv) @ Rp.T + pv + tp) - V)
                    Np = N @ Rp.T
                    Xc = (Vp - cpos) @ Rc.T
                    uv = f * Xc[:, :2] / Xc[:, 2:3] + cc
                    vdir = Vp - cpos
                    vdir /= np.linalg.norm(vdir, axis=1, keepdims=True)
                    rim = np.abs(np.einsum("ij,ij->i", Np, vdir)) < step.get("rim_cos", 0.25)
                    # only the model's actual outline in this photo
                    W_, H_ = int(cc[0] * 2) + 400, int(cc[1] * 2) + 400
                    fn = np.cross(Vp[F[:, 1]] - Vp[F[:, 0]], Vp[F[:, 2]] - Vp[F[:, 0]])
                    front = np.einsum("ij,ij->i", fn, cpos - Vp[F[:, 0]]) > 0
                    sil = np.zeros((H_, W_), np.uint8)
                    cv2.fillPoly(sil, list(np.round(uv[F[front]]).astype(np.int32)), 1)
                    sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
                    edge = cv2.dilate(sil, np.ones((3, 3), np.uint8)) - cv2.erode(sil, np.ones((3, 3), np.uint8))
                    near_edge = cv2.dilate(edge, np.ones((9, 9), np.uint8)) > 0
                    ui = np.clip(np.round(uv[:, 0]).astype(int), 0, W_ - 1)
                    vi = np.clip(np.round(uv[:, 1]).astype(int), 0, H_ - 1)
                    on_outline = rim & near_edge[vi, ui] & region
                    a_, b_ = vw.get("range", [0, None])
                    L_ = np.array(traces[view][step["line"]], float)[a_:b_]
                    # densify his line and find each outline point's nearest
                    seg = []
                    for k in range(len(L_) - 1):
                        n_ = max(2, int(np.linalg.norm(L_[k + 1] - L_[k]) / 2))
                        seg.append(L_[k] + (L_[k + 1] - L_[k]) * np.linspace(0, 1, n_, endpoint=False)[:, None])
                    seg.append(L_[-1:])
                    Ld = np.vstack(seg)
                    idx = np.nonzero(on_outline)[0]
                    if len(idx) == 0:
                        continue
                    dd = np.linalg.norm(uv[idx, None, :] - Ld[None, :, :], axis=2)
                    k = np.argmin(dd, axis=1)
                    dist = dd[np.arange(len(idx)), k]
                    # not past either end of his line
                    inner = (k > 0) & (k < len(Ld) - 1) & (dist < vw.get("near_px", 70))
                    idx, k = idx[inner], k[inner]
                    move_px = Ld[k] - uv[idx]
                    mm = Xc[idx, 2] / f
                    mc = np.c_[move_px * mm[:, None], np.zeros(len(idx))] @ Rc
                    mw = mc @ Rp
                    w_ = vw.get("weight", 1.0)
                    D[idx] += w_ * mw
                    wsum[idx] += w_
                if step.get("symmetric"):
                    # his face is symmetric: each point also takes its mirror
                    # partner's request (x -> -x)
                    from scipy.spatial import cKDTree
                    if rnd == 0 or "mir_idx" not in dir():
                        mir_idx = cKDTree(V).query(V * np.array([-1, 1, 1]))[1]
                    Dmir = D[mir_idx] * np.array([-1, 1, 1])
                    D = D + Dmir
                    wsum = wsum + wsum[mir_idx]
                Dm = np.where(wsum[:, None] > 0, D / np.maximum(wsum, 1e-9)[:, None], 0)
                wt = np.minimum(wsum, 4.0) + 10.0 * hold
                M_ = (sp.diags(wt[rid] + 1e-7) + step.get("stiffness", 5000.0) * (Lr.T @ Lr)).tocsc()
                solve = factorized(M_)
                Ds = np.zeros_like(V)
                for kk in range(3):
                    Ds[rid, kk] = solve(wt[rid] * Dm[rid, kk])
                V = V + Ds * step.get("rate", 0.7)
                print(f"line_contour {step['line']} round {rnd}: {int((wsum > 0).sum())} outline points, "
                      f"mean asked {np.linalg.norm(Dm[wsum > 0], axis=1).mean() * 1000:.2f} mm, "
                      f"max move {np.linalg.norm(Ds, axis=1).max() * 1000:.2f} mm", file=sys.stderr)
        elif op == "midline_swell":
            # His forehead/bridge line in the profiles is his midline. The gap
            # between his line and the model's midline is measured along the
            # midline in each profile (head posed as there), averaged over the
            # profiles, smoothed along the line, and applied as one broad
            # swelling centred on the midline that fades evenly to the sides
            # (and away from the eyes), outward from a centre inside the head.
            import cv2
            from scipy.spatial.transform import Rotation as Rot
            traces = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
            sidecams = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
            hw = head_weight(V)
            cen = np.asarray(step["centre"])
            th_v = np.arctan2(V[:, 2] - cen[2], V[:, 1] - cen[1])
            mid = np.abs(V[:, 0]) < 0.002
            samples = []
            for view, vw in step["views"].items():
                c_ = sidecams[view]
                Rc = Rot.from_rotvec(c_["rotvec_world_to_cam"]).as_matrix()
                cpos, f, cc = np.array(c_["camera_position_m"]), c_["focal_px"], np.array(c_["principal_px"])
                pp = json.loads((ROOT / f"checkpoints/cp3/head_poses_parts/{view}.json").read_text())
                Rp, tp = Rot.from_rotvec(pp["rotvec"]).as_matrix(), np.array(pp["shift_m"])
                pv = np.array(pp.get("pivot", NECK_PIVOT))
                Vp = V + hw[:, None] * (((V - pv) @ Rp.T + pv + tp) - V)
                Xc = (Vp - cpos) @ Rc.T
                uv = f * Xc[:, :2] / Xc[:, 2:3] + cc
                W_, H_ = int(cc[0] * 2) + 400, int(cc[1] * 2) + 400
                fn = np.cross(Vp[F[:, 1]] - Vp[F[:, 0]], Vp[F[:, 2]] - Vp[F[:, 0]])
                front = np.einsum("ij,ij->i", fn, cpos - Vp[F[:, 0]]) > 0
                sil = np.zeros((H_, W_), np.uint8)
                cv2.fillPoly(sil, list(np.round(uv[F[front]]).astype(np.int32)), 1)
                sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
                sd = cv2.distanceTransform(1 - sil, cv2.DIST_L2, 5) - cv2.distanceTransform(sil, cv2.DIST_L2, 5)
                a_, b_ = vw.get("range", [0, None])
                Lp = np.array(traces[view][step["line"]], float)[a_:b_]
                midi = np.nonzero(mid)[0]
                for pnt in Lp:
                    x_, y_ = int(round(pnt[0])), int(round(pnt[1]))
                    gap_px = sd[y_, x_]  # + : his line outside the model
                    k = midi[np.argmin(np.linalg.norm(uv[midi] - pnt, axis=1))]
                    pmm = f / Xc[k, 2] / 1000
                    samples.append((th_v[k], gap_px / pmm / 1000, vw.get("weight", 1.0)))
            S_ = np.array(samples)
            bw = step.get("bandwidth", 0.12)

            def gap_at(th):
                wk = np.exp(-0.5 * ((th[:, None] - S_[None, :, 0]) / bw) ** 2) * S_[None, :, 2]
                g = (wk * S_[None, :, 1]).sum(1) / np.maximum(wk.sum(1), 1e-9)
                # taper beyond the measured stretch
                lo, hi = S_[:, 0].min(), S_[:, 0].max()
                t_ = np.clip(np.minimum(th - lo + bw, hi + bw - th) / bw, 0, 1)
                return np.clip(g, -step.get("max_in", 0.003), step.get("max_out", 0.01)) * t_ * t_ * (3 - 2 * t_)

            g_v = gap_at(th_v)
            lat = np.exp(-0.5 * (V[:, 0] / step.get("sigma_x", 0.018)) ** 2)
            fade = np.ones(len(V))
            for e in eyes.values():
                de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                x_ = np.clip((de - step.get("hold_eyes", 0.003)) / step.get("eye_fade", 0.006), 0, 1)
                fade = np.minimum(fade, x_ * x_ * (3 - 2 * x_))
            radial = np.c_[np.zeros(len(V)), np.cos(th_v), np.sin(th_v)]
            facing = (V[:, 1] > cen[1]) | (V[:, 2] > cen[2])
            if step.get("along_normal"):
                # swell outward along the surface (no shearing of sideways-
                # facing fur, which folds it)
                radial = normals(V, F)
            V = V + (g_v * lat * fade * facing)[:, None] * radial
            order = np.argsort(S_[:, 0])
            print("midline_swell gaps (deg, mm): " + " ".join(f"{np.degrees(a):.0f}:{b * 1000:+.1f}" for a, b, _ in S_[order]),
                  file=sys.stderr)
        elif op == "eye_ring":
            pass  # recorded here, made in main() from the finished head
        elif op == "bump":
            # soft swelling (height > 0) or hollow (< 0) along the surface normal
            N = normals(V, F)
            w = falloff(np.linalg.norm(V - at, axis=1), step["radius"])
            V += (w * step["height"])[:, None] * N
        elif op == "crease":
            # soft groove along a line of master pixels, projected onto the
            # surface; depth along the surface normal, profile smooth across
            N = normals(V, F)
            pts = [master.hit(V, F, px) for px in densify(step["master_px_line"], 4)]
            P = np.array(pts)
            d = np.min(np.linalg.norm(V[:, None, :] - P[None, :, :], axis=2), axis=1)
            w = falloff(d, step["width"])
            depth = np.full(len(V), step["depth"])
            V -= (w * depth)[:, None] * N
        elif op == "fit_outline":
            V = fit_outline(V, F, rows, cols, deg, master, step)
        elif op == "smooth":
            w = falloff(np.linalg.norm(V - at, axis=1), step["radius"]) * step.get("strength", 0.5)
            for _ in range(step.get("iters", 3)):
                V += w[:, None] * (avg_op(rows, cols, deg) @ V - V)
        else:
            raise ValueError(op)
        np.save(cache_dir / f"{keys[si]}.npy", V)
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
    # eye-ring: his dark lid margin round each eye (a Dwarf Hotot's ring), the
    # band of lid just outside the lid opening; written as its own thin mesh so
    # it renders dark, like his
    socks = [st for st in log["steps"] if st["op"] == "socket"]
    for st in log["steps"]:
        if st["op"] != "eye_ring":
            continue
        for side in ("R", "L"):
            if side not in eyes:
                continue
            e = eyes[side]
            c, re = np.asarray(e["centre"]), e["radius"]
            ax_ = np.asarray(e["axis"]) / np.linalg.norm(e["axis"])
            sk = dict(socks[-1])
            if side == "L":
                sk.update(sk.get("mirror_overrides", {}))
            rim = sk["rim"]
            w = st.get("width_" + side, st["width"])
            # a smooth band: even angles round the eye, from just inside the
            # lid edge out to rim + w; each point is placed on the head's
            # surface by casting from the eye centre outward
            up = np.array([0, 0, 1.0]) - ax_ * ax_[2]
            up /= np.linalg.norm(up)
            sd = np.cross(ax_, up)
            phis = np.linspace(0, 2 * np.pi, 96, endpoint=False)
            rhos = np.linspace(rim - st.get("inner", 0.0004), rim + w, 5)
            near = np.linalg.norm((V[F].mean(1)) - c, axis=1) < re + 0.006
            A0, B0, C0 = V[F[near, 0]], V[F[near, 1]], V[F[near, 2]]
            e1, e2 = B0 - A0, C0 - A0
            P = np.zeros((len(rhos), len(phis), 3))
            for i, rr in enumerate(rhos):
                for j, ph in enumerate(phis):
                    hh = np.sqrt(max(re ** 2 - min(rr, re * 0.999) ** 2, 0))
                    dvec = ax_ * hh + rr * (np.cos(ph) * up + np.sin(ph) * sd)
                    dvec /= np.linalg.norm(dvec)
                    pv = np.cross(dvec, e2)
                    det = np.einsum("ij,ij->i", e1, pv)
                    ok = np.abs(det) > 1e-14
                    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
                    s_ = c - A0
                    u = np.einsum("ij,ij->i", s_, pv) * inv
                    qq = np.cross(s_, e1)
                    v_ = (qq @ dvec) * inv
                    t = np.einsum("ij,ij->i", e2, qq) * inv
                    hit = ok & (u >= 0) & (v_ >= 0) & (u + v_ <= 1) & (t > re * 0.9)
                    tt = t[hit].min() if hit.any() else re
                    # hug the lid: where the fur stands further out than
                    # `hug`, the ring lies tucked under it, on the eyeball
                    tt = min(max(tt, re), re + st.get("hug", 0.0015))
                    P[i, j] = c + dvec * (tt + 0.00012)
            nr, nphi = P.shape[:2]
            Fr = []
            for i in range(nr - 1):
                for j in range(nphi):
                    a_, b_ = i * nphi + j, i * nphi + (j + 1) % nphi
                    Fr += [(a_, b_, a_ + nphi), (b_, b_ + nphi, a_ + nphi)]
            write_obj(out / f"ring_{side}.obj", P.reshape(-1, 3), np.array(Fr))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
