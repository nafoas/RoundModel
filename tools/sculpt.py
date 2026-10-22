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


def smooth_field(sel, a, b, region, rows, cols, deg, lam, clip, anchor=None, anchor_w=1.0):
    """Scalar field t (on `region`, 0 outside) minimising
    sum_sel (a t - b)^2 + lam |L t|^2, L the mesh Laplacian (neighbour mean
    minus self); b clipped to +-clip."""
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    n = len(region)
    idx = np.full(n, -1)
    rid = np.nonzero(region)[0]
    idx[rid] = np.arange(len(rid))
    A = avg_op(rows, cols, deg)
    Lfull = A - sp.identity(n, format="csr")
    L = Lfull[rid][:, rid]  # outside the region t = 0
    w = np.zeros(len(rid))
    rhs = np.zeros(len(rid))
    s_ = sel[rid]
    aa, bb = a[rid][s_], np.clip(b[rid][s_], -clip, clip)
    w[s_] = aa * aa
    rhs[s_] = aa * bb
    if anchor is not None:
        w += anchor[rid] * anchor_w
    M = sp.diags(w + 1e-6) + lam * (L.T @ L)
    t = np.zeros(n)
    t[rid] = spsolve(M.tocsc(), rhs)
    return t


def fit_view(V, F, rows, cols, deg, master, step, eyes=None):
    """Make his outline in another photo match, without touching the master.

    His head is held a little differently in each photo, so the head is first
    posed as found by head_pose.py (`pose`: rotvec and shift, applied about
    the neck). Silhouette points in that photo are then moved only along the
    master camera's line of sight (invisible from the master), by whatever
    amount shifts them onto his outline there; points where such a move
    hardly shifts the outline are left alone. Moves are spread smoothly."""
    import cv2
    from PIL import Image
    from scipy.spatial.transform import Rotation as Rot
    cam = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"][step["view"]]
    Rc = Rot.from_rotvec(cam["rotvec_world_to_cam"]).as_matrix()
    cpos, f = np.array(cam["camera_position_m"]), cam["focal_px"]
    cx, cy = cam["principal_px"]
    mask = np.asarray(Image.open(ROOT / "checkpoints/cp3/orig_masks" / (Path(cam["image"]).stem + ".mask.png"))) > 0
    mask = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), step.get("outline_soften_px", 4)) > 0.5
    h, w = mask.shape
    sd = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5) - \
        cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    gy, gx = np.gradient(cv2.GaussianBlur(sd, (0, 0), 1.5))
    excl = np.zeros_like(mask)
    for x0, y0, x1, y1 in step.get("exclude", []):
        excl[y0:y1, x0:x1] = True
    Rp = Rot.from_rotvec(step["pose"]["rotvec"]).as_matrix()
    tp = np.array(step["pose"]["shift_m"])
    hw = head_weight(V)
    A = avg_op(rows, cols, deg)

    def posed(X):
        return X + hw[:, None] * (((X - NECK_PIVOT) @ Rp.T + NECK_PIVOT + tp) - X)

    def proj(X):
        Xc = (X - cpos) @ Rc.T
        return np.stack([f * Xc[:, 0] / Xc[:, 2] + cx, f * Xc[:, 1] / Xc[:, 2] + cy], 1), Xc[:, 2]

    for _ in range(step.get("iters", 6)):
        Vp = posed(V)
        N = normals(Vp, F)
        view = Vp - cpos
        view /= np.linalg.norm(view, axis=1, keepdims=True)
        rim = np.abs(np.einsum("ij,ij->i", N, view)) < 0.12
        uv, z = proj(Vp)
        ui = np.clip(np.round(uv[:, 0]).astype(int), 0, w - 1)
        vi = np.clip(np.round(uv[:, 1]).astype(int), 0, h - 1)
        rim &= ~excl[vi, ui] & (hw > step.get("min_head", 0.3))
        if "zones" in step:
            inz = np.zeros(len(V), bool)
            for x0, y0, x1, y1 in step["zones"]:
                inz |= (ui >= x0) & (ui < x1) & (vi >= y0) & (vi < y1)
            rim &= inz
        # only rim points on the sculpt's actual outline in this photo (not
        # rims hidden behind it, e.g. round the eyes)
        fn = np.cross(Vp[F[:, 1]] - Vp[F[:, 0]], Vp[F[:, 2]] - Vp[F[:, 0]])
        front = np.einsum("ij,ij->i", fn, cpos - Vp[F[:, 0]]) > 0
        sil = np.zeros((h, w), np.uint8)
        cv2.fillPoly(sil, list(np.round(uv[F[front]]).astype(np.int32)), 1)
        sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        # fill enclosed gaps (folded lids leave small holes in the fill that
        # would otherwise count as outline inside the face)
        ff = sil.copy()
        cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
        sil = sil | (1 - ff)
        edge = cv2.dilate(sil, np.ones((3, 3), np.uint8)) - cv2.erode(sil, np.ones((3, 3), np.uint8))
        near_edge = cv2.dilate(edge, np.ones((7, 7), np.uint8)) > 0
        rim &= near_edge[vi, ui]
        g = np.stack([gx[vi, ui], gy[vi, ui]], 1)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
        want = -sd[vi, ui]  # px along g (outward +)
        # the direction each point may move: along the master's line of
        # sight (never changes the master view), or, with `free`, for points
        # well away from the master outline, straight toward/away from this
        # photo's outline (a point not on the master outline can move
        # sideways without changing it)
        mdir = V - master.pos
        mdir /= np.linalg.norm(mdir, axis=1, keepdims=True)
        if step.get("free"):
            Nm = normals(V, F)
            facing = np.abs(np.einsum("ij,ij->i", Nm, mdir))
            wf = np.clip((facing - 0.25) / 0.2, 0, 1)
            # photo in-plane direction g, in the head's own (unposed) frame
            gw = (g[:, :1] * Rc[0] + g[:, 1:] * Rc[1]) @ Rp
            gw -= np.einsum("ij,ij->i", gw, view @ Rp)[:, None] * (view @ Rp)
            gw /= np.maximum(np.linalg.norm(gw, axis=1, keepdims=True), 1e-9)
            # sign: along mdir as before; for free points pick the photo
            # direction (move along it changes the outline most)
            mdir = (1 - wf)[:, None] * mdir * np.sign(np.einsum("ij,ij->i", mdir, gw) + 1e-12)[:, None] + wf[:, None] * gw
            mdir /= np.maximum(np.linalg.norm(mdir, axis=1, keepdims=True), 1e-9)
        eps = 1e-4
        uv2, _ = proj(posed(V + eps * mdir))
        lever = np.einsum("ij,ij->i", (uv2 - uv) / eps, g)  # px per metre along g
        full = f / z
        ok = rim & (np.abs(lever) > step.get("min_lever", 0.35) * full)
        # one smooth move field over the head (thin plate): as close as it can
        # get to what the outline points ask for, while bending as little as
        # possible, so it cannot leave steps or stripes. In mm.
        # the fur right round each eye (the lids) stays put
        anchor = None
        if eyes:
            anchor = np.zeros(len(V))
            for e in eyes.values():
                de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                # firm at the lid, fading to free over `hold_eyes` (a hard
                # edge to the hold leaves a notch where it ends)
                anchor = np.maximum(anchor, falloff(np.maximum(de, 0), step.get("hold_eyes", 0.012)))
        t = smooth_field(ok, lever / full, want / (full / 1000), hw > 0.02, rows, cols, deg,
                         step.get("stiffness", 3e4), step.get("max_want_mm", 8),
                         anchor=anchor, anchor_w=1.0) / 1000
        # the move field is smooth; so is the direction field it moves along
        Ds = (t * step.get("rate", 0.6))[:, None] * mdir
        if step.get("free"):
            # directions differ point to point; smooth the moves themselves
            for _ in range(step.get("move_smooth", 40)):
                Ds = 0.5 * Ds + 0.5 * (A @ Ds)
        V = V + Ds
    return V


def fit_multi(V, F, rows, cols, deg, master, step, eyes=None):
    """The head's outline in every listed photo at once (master included),
    each photo with his head posed as there. Every point on the sculpt's
    outline in a photo asks to move along its surface normal by whatever
    brings that outline onto his; one smooth offset field (least bending)
    answers all of them together, weighted per photo. No photo is held
    fixed; the master just counts more."""
    import cv2
    import scipy.sparse as sp
    from scipy.sparse.linalg import spsolve
    from PIL import Image
    from scipy.spatial.transform import Rotation as Rot
    side_cams = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
    poses = json.loads((ROOT / step.get("poses_file", "checkpoints/cp3/eyes3d.json")).read_text())["poses"]
    hw = head_weight(V)
    region = hw > 0.02
    if step.get("eyes_only_reach") and eyes:
        # a local pass round the eyes (lids, brow, the fur between them)
        region = np.zeros(len(V), bool)
        for e in eyes.values():
            region |= np.linalg.norm(V - np.asarray(e["centre"]), axis=1) < e["radius"] + step["eyes_only_reach"]
    rid = np.nonzero(region)[0]
    A = avg_op(rows, cols, deg)
    Lf = (A - sp.identity(len(V), format="csr"))[rid][:, rid]
    LtL = (Lf.T @ Lf).tocsc()
    views = []
    for v in step["views"]:
        name = v["view"]
        if name == "master_front_standing":
            cam = dict(R=master.R, pos=master.pos, f=master.f, c=np.array([master.w / 2, master.h / 2]))
            mpath = ROOT / step.get("master_mask", "checkpoints/cp3/master_head_outline.png")
            soft = 7
        else:
            c = side_cams[name]
            cam = dict(R=Rot.from_rotvec(c["rotvec_world_to_cam"]).as_matrix(), pos=np.array(c["camera_position_m"]),
                       f=c["focal_px"], c=np.array(c["principal_px"]))
            mpath = ROOT / "checkpoints/cp3/orig_masks" / (Path(c["image"]).stem + ".mask.png")
            soft = 4
        mask = np.asarray(Image.open(mpath)) > 0
        mask = cv2.GaussianBlur(mask.astype(np.float32), (0, 0), soft) > 0.5
        h, w = mask.shape
        sd = cv2.distanceTransform((~mask).astype(np.uint8), cv2.DIST_L2, 5) - \
            cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
        gy, gx = np.gradient(cv2.GaussianBlur(sd, (0, 0), 1.5))
        excl = np.zeros_like(mask)
        for x0, y0, x1, y1 in v.get("exclude", []):
            excl[y0:y1, x0:x1] = True
        pose = poses.get(name)
        Rp = np.eye(3) if pose is None else Rot.from_rotvec(pose["rotvec"]).as_matrix()
        tp = np.zeros(3) if pose is None else np.array(pose["shift_m"])
        tr = {}
        if step.get("eye_traces") and eyes:
            parts = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text()).get(name, {})
            for pn, poly in parts.items():
                if pn.startswith("eye_") and pn[-1] in eyes:
                    tm = np.zeros((h, w), np.uint8)
                    cv2.fillPoly(tm, [np.array(poly, np.int32)], 1)
                    tr[pn[-1]] = tm > 0
        views.append(dict(cam=cam, sd=sd, gx=gx, gy=gy, excl=excl, Rp=Rp, tp=tp, w=v.get("weight", 1.0), h=h, wd=w,
                          traces=tr, name=name))
    report = []
    for it in range(step.get("iters", 4)):
        N = normals(V, F)
        wsum = np.zeros(len(V))
        rhs = np.zeros(len(V))
        report = []
        for vw in views:
            cam, Rp, tp = vw["cam"], vw["Rp"], vw["tp"]
            Vp = V + hw[:, None] * (((V - NECK_PIVOT) @ Rp.T + NECK_PIVOT + tp) - V)
            Np = N @ Rp.T
            Xc = (Vp - cam["pos"]) @ cam["R"].T
            uv = cam["f"] * Xc[:, :2] / Xc[:, 2:3] + cam["c"]
            h, w = vw["h"], vw["wd"]
            fnn = np.cross(Vp[F[:, 1]] - Vp[F[:, 0]], Vp[F[:, 2]] - Vp[F[:, 0]])
            front = np.einsum("ij,ij->i", fnn, cam["pos"] - Vp[F[:, 0]]) > 0
            sil = np.zeros((h, w), np.uint8)
            cv2.fillPoly(sil, list(np.round(uv[F[front]]).astype(np.int32)), 1)
            # the eyes are part of his outline too (from above and in three-
            # quarter they make the edge themselves)
            eye_disks = []
            for e in (eyes or {}).values():
                cp = (np.asarray(e["centre"]) - NECK_PIVOT) @ Rp.T + NECK_PIVOT + tp
                Xe = (cp - cam["pos"]) @ cam["R"].T
                ue = cam["f"] * Xe[:2] / Xe[2] + cam["c"]
                re_px = cam["f"] * e["radius"] / Xe[2]
                cv2.circle(sil, (int(round(ue[0])), int(round(ue[1]))), int(round(re_px)), 1, -1)
                eye_disks.append((cp, e["radius"]))
            sil = cv2.morphologyEx(sil, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            ff = sil.copy()
            cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1)
            sil = sil | (1 - ff)
            edge = cv2.dilate(sil, np.ones((3, 3), np.uint8)) - cv2.erode(sil, np.ones((3, 3), np.uint8))
            near = cv2.dilate(edge, np.ones((7, 7), np.uint8)) > 0
            vdir = Vp - cam["pos"]
            vdir /= np.linalg.norm(vdir, axis=1, keepdims=True)
            ui = np.clip(np.round(uv[:, 0]).astype(int), 0, w - 1)
            vi = np.clip(np.round(uv[:, 1]).astype(int), 0, h - 1)
            rim = (np.abs(np.einsum("ij,ij->i", Np, vdir)) < 0.15) & near[vi, ui] & ~vw["excl"][vi, ui] & (hw > 0.3)
            g = np.stack([vw["gx"][vi, ui], vw["gy"][vi, ui]], 1)
            g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-6)
            want = -vw["sd"][vi, ui]  # px, along g
            eps = 1e-4
            Xc2 = (Vp + eps * Np - cam["pos"]) @ cam["R"].T
            uv2 = cam["f"] * Xc2[:, :2] / Xc2[:, 2:3] + cam["c"]
            lever = np.einsum("ij,ij->i", (uv2 - uv) / eps, g) / 1000  # px per mm
            ok = rim & (np.abs(lever) > 0.3 * cam["f"] / Xc[:, 2] / 1000)
            b = np.clip(want / np.where(ok, lever, 1), -step.get("max_mm", 6), step.get("max_mm", 6))
            wv = vw["w"] * ok
            wsum += wv
            rhs += wv * b
            # where this photo shows his eye, no fur in front of it; where
            # the eyeball would show but the photo shows fur, fur covers it
            if vw["traces"]:
                tv = np.linalg.norm(Vp - cam["pos"], axis=1)
                facing = np.einsum("ij,ij->i", Np, -vdir) > 0.05
                cosn = np.maximum(np.einsum("ij,ij->i", Np, -vdir), 0.2)
                for side, tmask in vw["traces"].items():
                    e = eyes[side]
                    cp = (np.asarray(e["centre"]) - NECK_PIVOT) @ Rp.T + NECK_PIVOT + tp
                    oc = cam["pos"] - cp
                    bq = np.einsum("ij,j->i", vdir, oc)
                    disc = bq ** 2 - (oc @ oc - e["radius"] ** 2)
                    hit = disc > 0
                    tnear = -bq - np.sqrt(np.maximum(disc, 0))
                    shown = tmask[vi, ui]
                    ring = cv2.dilate(tmask.astype(np.uint8), np.ones((25, 25), np.uint8)) > 0
                    de_ = np.linalg.norm(V - np.asarray(e["centre"]), axis=1)
                    # fur tucked under the eyeball (inside the opening) is left alone
                    near_eye = (de_ < e["radius"] + 0.012) & (de_ > e["radius"])
                    occl = hit & shown & facing & (tv < tnear) & near_eye
                    cov = hit & ~shown & ring[vi, ui] & (tv > tnear) & near_eye & (hw > 0.3)
                    we = step.get("eye_weight", 1.0) * vw["w"]
                    bo = -np.clip((tnear - tv + 0.0004) / cosn * 1000, 0, 4)
                    bc = np.clip((tv - tnear + 0.0004) / cosn * 1000, 0, 4)
                    wsum += we * occl + we * cov
                    rhs += we * occl * bo + we * cov * bc
            report.append(float(np.mean(np.abs(want[ok]) / (cam["f"] / Xc[ok, 2] / 1000))) if ok.any() else 0.0)
        # each outline point asks for an offset b (mm) with weight w
        sel = wsum[rid] > 0
        bavg = np.where(wsum > 0, rhs / np.maximum(wsum, 1e-9), 0)
        M = sp.diags(wsum[rid] + 1e-6) + step.get("stiffness", 3e3) * LtL
        t = np.zeros(len(V))
        t[rid] = spsolve(M.tocsc(), wsum[rid] * bavg[rid])
        V = V + (t / 1000 * step.get("rate", 1.0))[:, None] * N
        print(f"fit_multi iter {it}: mean outline distance per view (mm) " + " ".join(f"{x:.2f}" for x in report),
              file=sys.stderr)
    return V


def eye_frame(e):
    """Axis and the two directions round it ('up' turned by the eye's roll),
    as in eye3d.py."""
    ax_ = np.asarray(e["axis"], float)
    ax_ = ax_ / np.linalg.norm(ax_)
    up = np.array([0, 0, 1.0]) - ax_ * ax_[2]
    up /= np.linalg.norm(up)
    sd = np.cross(ax_, up)
    rl = np.radians(e.get("roll", 0.0) or 0.0)
    return ax_, np.cos(rl) * up + np.sin(rl) * sd, -np.sin(rl) * up + np.cos(rl) * sd


def opening_angle(phi, f):
    out = np.full_like(phi, np.radians(f[0]))
    for k in range((len(f) - 1) // 2):
        out += np.radians(f[1 + 2 * k]) * np.cos((k + 1) * phi) + np.radians(f[2 + 2 * k]) * np.sin((k + 1) * phi)
    return np.clip(out, np.radians(10), np.radians(120))


def smooth_disp(D, w, region, rows, cols, deg, lam):
    """Smooth displacement field: near D where w > 0, least bending elsewhere,
    zero outside `region`."""
    import scipy.sparse as sp
    from scipy.sparse.linalg import factorized
    rid = np.nonzero(region)[0]
    A = avg_op(rows, cols, deg)
    L = (A - sp.identity(len(w), format="csr"))[rid][:, rid]
    M = (sp.diags(w[rid] + 1e-7) + lam * (L.T @ L)).tocsc()
    solve = factorized(M)
    out = np.zeros_like(D)
    for k in range(3):
        out[rid, k] = solve(w[rid] * D[rid, k])
    return out


def fair_shape(V, target, w, region, rows, cols, deg, lam):
    """Smoothest surface (least bending of the shape) over `region` meeting
    `target` where w > 0; vertices outside the region stay put."""
    import scipy.sparse as sp
    from scipy.sparse.linalg import factorized
    rid = np.nonzero(region)[0]
    A = avg_op(rows, cols, deg)
    Lf = A - sp.identity(len(V), format="csr")
    Lr, Lo = Lf[rid][:, rid], Lf[rid][:, ~region]
    M = (sp.diags(w[rid] + 1e-9) + lam * (Lr.T @ Lr)).tocsc()
    solve = factorized(M)
    out = V.copy()
    for k in range(3):
        out[rid, k] = solve(w[rid] * target[rid, k] - lam * (Lr.T @ (Lo @ V[~region, k])))
    return out


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
            f.touch()
            start = i + 1
            break
    for st in steps[:start]:
        if st["op"] == "eye":
            ax_ = np.asarray(st["axis"], float)
            ax_ /= np.linalg.norm(ax_)
            c = np.asarray(st["centre"], float) if "centre" in st else np.asarray(st["front"], float) - ax_ * st["radius"]
            eyes[st["side"]] = {"centre": c.tolist(), "radius": st["radius"], "axis": ax_.tolist(),
                                "opening": st.get("opening"), "roll": st.get("roll", 0.0)}
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
            eyes[step["side"]] = {"centre": c.tolist(), "radius": step["radius"], "axis": ax_.tolist(),
                                  "opening": step.get("opening"), "roll": step.get("roll", 0.0)}
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
            hold |= master_outline_points(V, F, master, px=step.get("outline_px", 4))
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
        elif op == "lid_fur":
            # Fur above (hood) and below (cheek) the eye stands out sideways,
            # along the eye axis: from the front it hides the top and bottom
            # of the eyeball, from the side the whole round eye still shows
            # (photos: a tall almond from the front, a full disc side-on).
            # Thickness `hood` straight above, `cheek` straight below, fading
            # smoothly toward the front and back corners (|sin|^1.5) and away
            # from the rim (rises over `rise`, fades over `band`); relaxed after.
            e = eyes[step["side"]]
            c, ax_, re = np.asarray(e["centre"]), np.asarray(e["axis"]), e["radius"]
            up = np.array([0, 0, 1.0]) - ax_ * ax_[2]
            up /= np.linalg.norm(up)
            side = np.cross(ax_, up)
            q = V - c
            h = q @ ax_
            perp = q - h[:, None] * ax_
            rho = np.linalg.norm(perp, axis=1)
            sphi = (perp @ up) / np.maximum(rho, 1e-9)
            amp = np.where(sphi > 0, step["hood"], step["cheek"]) * np.abs(sphi) ** 1.5
            if step.get("brow"):
                # brow: fur rising toward the nose and up, where the brow
                # meets the bridge (top-down and master: the eye's front edge
                # is tucked into fur, not standing proud of a notch)
                cphi = (perp @ side) * np.sign(side[1]) / np.maximum(rho, 1e-9)  # toward the nose
                b = np.radians(step.get("brow_deg", 45))
                cosd = cphi * np.cos(b) + sphi * np.sin(b)
                amp = amp + step["brow"] * np.maximum(cosd, 0) ** 2
            rim = step.get("rim", re)
            dr = rho - rim
            x = np.clip(dr / step.get("rise", 0.002), 0, 1)
            radial = x * x * (3 - 2 * x) * falloff(np.maximum(dr - step.get("rise", 0.002), 0), step.get("band", 0.008))
            radial *= np.clip((h + 0.5 * re) / (0.5 * re), 0, 1)  # only the side of the head the eye is on
            dh = amp * radial
            V += dh[:, None] * ax_[None, :]
            w = 0.5 * (dh > 1e-5)
            A_ = avg_op(rows, cols, deg)
            for _ in range(step.get("relax", 6)):
                V += w[:, None] * (A_ @ V - V)
        elif op == "lids3d":
            # Lids from the eye's 3D opening (eye3d.py). On the eyeball,
            # within the opening, the eye shows: fur there tucks just under
            # the ball. The lid edge lies on the ball along the opening.
            # Outside the opening the fur covers the ball (at least `cover`
            # over it). All met by one smooth displacement (least bending),
            # fading to nothing `reach` beyond the ball.
            e = eyes[step["side"]]
            c, re = np.asarray(e["centre"]), e["radius"]
            ax_, up, sd = eye_frame(e)
            cover, tuck = step.get("cover", 0.0006), step.get("tuck", 0.0005)
            band = np.radians(step.get("band_deg", 4))
            for _ in range(step.get("rounds", 3)):
                q = V - c
                d = np.linalg.norm(q, axis=1)
                u = q / d[:, None]
                th = np.arccos(np.clip(u @ ax_, -1, 1))
                ph = np.arctan2(u @ sd, u @ up)
                # the lid's edge band sits just outside the fitted opening, so
                # the eye shows over the whole opening
                ps = opening_angle(ph, e["opening"]) + np.radians(step.get("shift_deg", 0.0))
                near = d < re + step.get("near", 0.004)
                # one smooth rule for the fur's height over the ball, by angle
                # from the lid edge s = theta - psi: tucked under well inside,
                # on the ball at the edge, thickening slowly outside; blended
                # smoothly across +-band (no hard classes, so no stair steps
                # or pinches at the corners)
                sang = th - ps
                x_ = np.clip((sang + band) / (2 * band), 0, 1)
                sm = x_ * x_ * (3 - 2 * x_)
                outside_lvl = re + cover + step.get("thick", 0.0) * np.degrees(np.maximum(sang, 0))
                outside_lvl = np.minimum(outside_lvl, re + step.get("thick_max", 0.004))
                lvl = (1 - sm) * (re - tuck) + sm * outside_lvl
                # inside the opening the fur must be at most lvl; outside at least
                need = np.where(sm < 0.5, d > lvl, d < lvl) & near
                target = V.copy()
                target[need] = c + u[need] * lvl[need, None]
                w = need * (1.0 + 3.0 * (1 - np.abs(2 * sm - 1)))  # firmest at the edge
                if step.get("drape"):
                    # the fur round the eye becomes the smoothest surface (least
                    # bending of the shape itself) that meets the lids, keeps
                    # off the eyeball and joins the head at `reach`
                    region = d < re + step["reach"]
                    w[region & (d > re + step["reach"] - 0.002)] = 10.0
                    target[w == 10.0] = V[w == 10.0]
                    Vf = fair_shape(V, target, w, region, rows, cols, deg, step.get("stiffness", 1.0))
                    # blend into the untouched head gradually toward the edge
                    # (a hard edge leaves a ring crease)
                    xb = np.clip((d - re) / step["reach"], 0, 1)
                    wb = np.clip((1 - xb) / 0.5, 0, 1)
                    wb = wb * wb * (3 - 2 * wb)
                    V = V + wb[:, None] * (Vf - V)
                else:
                    D = smooth_disp(target - V, w, d < re + step.get("reach", 0.012), rows, cols, deg,
                                    step.get("stiffness", 30.0))
                    V = V + D
        elif op == "fill_dents":
            # Fur is full and rounded: over the brow and forehead there are no
            # valleys. The smoothest surface over the area (lids and the
            # area's edge held) gives, for each point, how far it lies below
            # that; that depth is itself smoothed (so the fill is one soft
            # swell, never per-point), kept outward only, and applied along
            # the surface normal. Repeated a few times.
            dist0 = np.linalg.norm(V - np.asarray(step["at"]), axis=1)
            region = dist0 < step["radius"]
            hold = dist0 > step["radius"] - step.get("edge", 0.004)
            for e in eyes.values():
                hold |= np.linalg.norm(V - np.asarray(e["centre"]), axis=1) < e["radius"] + step.get("keep_lid", 0.0015)
            w = hold.astype(float) * 10.0
            xb = np.clip(dist0 / step["radius"], 0, 1)
            wb = np.clip((1 - xb) / 0.5, 0, 1)
            wb = wb * wb * (3 - 2 * wb)
            for _ in range(step.get("rounds", 4)):
                Vf = fair_shape(V, V, w, region, rows, cols, deg, 1.0)
                N = normals(V, F)
                depth = np.maximum(np.einsum("ij,ij->i", Vf - V, N), 0) * region * ~hold
                # one smooth swell
                Dz = smooth_disp(np.c_[depth, np.zeros((len(V), 2))], (depth > 0).astype(float), region,
                                 rows, cols, deg, step.get("swell_stiffness", 30.0))[:, 0]
                Dz = np.maximum(Dz, 0) * wb
                Ns = smooth_disp(N, np.ones(len(V)), region, rows, cols, deg, 3.0)
                Ns[~region] = N[~region]
                Ns /= np.maximum(np.linalg.norm(Ns, axis=1, keepdims=True), 1e-9)
                V = V + (Dz * step.get("rate", 1.0))[:, None] * Ns
        elif op == "despike":
            # single points standing out from their neighbours near the eyes
            # (mesh-level spikes) are pulled back into the surface
            A_ = avg_op(rows, cols, deg)
            near = np.zeros(len(V), bool)
            for e in eyes.values():
                near |= np.linalg.norm(V - np.asarray(e["centre"]), axis=1) < e["radius"] + step.get("reach", 0.012)
            for _ in range(step.get("iters", 10)):
                lap = A_ @ V - V
                spk = near & (np.linalg.norm(lap, axis=1) > step.get("limit", 0.0004))
                V[spk] += 0.6 * lap[spk]
        elif op == "convexify":
            # Fur over the forehead and brow makes no hollows. In thin slices
            # across the head (constant y), each point under the slice's
            # convex outline moves out to it, in the slice plane; points on
            # the outline do not move, so the outline from the front and from
            # above stays exactly as it was. The fur round each eye is left
            # alone. Moves are then made smooth along the head.
            from scipy.spatial import ConvexHull
            y0, y1 = step["y"]
            zmin = step["z_min"]
            free = (V[:, 1] > y0) & (V[:, 1] < y1) & (V[:, 2] > zmin)
            held = np.zeros(len(V), bool)
            for e in eyes.values():
                held |= np.linalg.norm(V - np.asarray(e["centre"]), axis=1) < e["radius"] + step.get("hold_eyes", 0.003)
            D = np.zeros_like(V)
            w = np.zeros(len(V))
            dy = step.get("slab", 0.0015)
            for yc in np.arange(y0, y1, dy):
                sl = np.nonzero((V[:, 1] >= yc) & (V[:, 1] < yc + dy) & (V[:, 2] > zmin - 0.01))[0]
                if len(sl) < 10:
                    continue
                P2 = V[sl][:, [0, 2]]
                use = ~held[sl]
                if use.sum() < 10:
                    continue
                hull = ConvexHull(P2[use])
                eq = hull.equations  # n.x + d <= 0 inside
                dist = P2 @ eq[:, :2].T + eq[:, 2]  # negative inside
                k = np.argmax(dist, axis=1)  # nearest face (least negative)
                gap = -dist[np.arange(len(sl)), k]
                nrm = eq[k, :2]
                mv = free[sl] & ~held[sl] & (gap > 0)
                D[sl[mv], 0] = nrm[mv, 0] * gap[mv]
                D[sl[mv], 2] = nrm[mv, 1] * gap[mv]
                w[sl[mv]] = 1.0
                w[sl[free[sl] & ~mv]] = 1.0  # stays
            # the fill fades in gradually away from each eye (a hard edge to
            # the held band leaves a fold)
            if step.get("fade_eyes"):
                fade = np.ones(len(V))
                for e in eyes.values():
                    de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                    x_ = np.clip((de - step.get("hold_eyes", 0.003)) / step["fade_eyes"], 0, 1)
                    fade = np.minimum(fade, x_ * x_ * (3 - 2 * x_))
                D *= fade[:, None]
            # held lids, and his outline from the front, pin the move at zero
            w[held] = 4.0
            mo = master_outline_points(V, F, master, px=step.get("outline_px", 2))
            D[mo] = 0
            w[mo] = 4.0
            region = free | held
            Ds = smooth_disp(D, w, np.ones(len(V), bool), rows, cols, deg, step.get("stiffness", 3.0))
            V = V + Ds * step.get("rate", 1.0)
        elif op == "relax":
            # Round off ridges and corners without shrinking (Taubin: a
            # smoothing step, then a slightly larger un-shrinking step). Full
            # strength in the middle of the area, fading to its edge and to
            # the lids round each eye; his outline from the front held.
            A_ = avg_op(rows, cols, deg)
            w = falloff(np.linalg.norm(V - at, axis=1), step["radius"])
            for e in eyes.values():
                de = np.linalg.norm(V - np.asarray(e["centre"]), axis=1) - e["radius"]
                x_ = np.clip((de - step.get("hold_eyes", 0.002)) / step.get("fade_eyes", 0.006), 0, 1)
                w = w * x_ * x_ * (3 - 2 * x_)
            if step.get("hold_outline", True):
                w = w * ~master_outline_points(V, F, master, px=2)
            lam, mu = step.get("lam", 0.5), step.get("mu", -0.53)
            for _ in range(step.get("iters", 50)):
                V += (lam * w)[:, None] * (A_ @ V - V)
                V += (mu * w)[:, None] * (A_ @ V - V)
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
        elif op == "fit_multi":
            V = fit_multi(V, F, rows, cols, deg, master, step, eyes)
        elif op == "fit_view":
            V = fit_view(V, F, rows, cols, deg, master, step, eyes)
        elif op == "smooth":
            w = falloff(np.linalg.norm(V - at, axis=1), step["radius"]) * step.get("strength", 0.5)
            for _ in range(step.get("iters", 3)):
                V += w[:, None] * (avg_op(rows, cols, deg) @ V - V)
        else:
            raise ValueError(op)
        np.save(cache_dir / f"{keys[si]}.npy", V)
    # keep the cache to the most recently used meshes (each is ~4 MB)
    files = sorted(cache_dir.glob("*.npy"), key=lambda f: f.stat().st_mtime)
    for f in files[:-800]:
        f.unlink(missing_ok=True)
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
