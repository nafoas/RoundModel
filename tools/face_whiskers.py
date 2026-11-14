"""Whisker step, part 2: the whiskers lying over his face, inside the outline.

Owner rules: whiskers over the face are coloured precisely as whiskers (only the
whisker itself), never removed or painted over, and otherwise weight 0 until they
are added last. His whiskers are light: on his cheeks they show only as faint
lines a few grey levels darker than the white fur around them.

Why a whole-path search: following such a faint line step by step fails (each
whisker bends where it meets his cheek, and fur texture pulls a step-by-step
tracer off it). Instead each whisker's path over the face is found in one go:

1. Detail map D: how much darker each pixel is than the fur around it
   (grey = mean of RGB; D = -(L - gaussian(L, 6)), L = gaussian(grey, 0.7)).
2. Line contrast at a point, across a direction: D on the line minus the mean
   of D 3-4.5 px to either side (a line, not an edge or a blob).
3. Dynamic programming over a lattice aligned with the whisker's entry
   direction: state = sideways offset (0.25 px cells) and slope; per 8 px step
   the slope may change by one notch (whiskers are smooth arcs: <= 0.22 deg/px).
   The path maximises the summed line contrast minus 1 per px (each point
   capped, so a single dark blob cannot pull it); it ends where going on no
   longer pays. The fur band at his outline scores 0 (crossed,
   not followed); once the path is past its entry it may not run within 12 px
   of the outline (otherwise it follows the outline's own dark edge). Eyes
   (+50 px) and the nose/mouth box are off limits (their own later steps).
4. Where the whisker really is: the 24 px running mean of the line contrast
   along the path must be >= T. T = 3.5 sits between plain fur (median 1.2)
   and the faint whisker lines (4-9). The kept face part is the first stretch
   (gaps <= 16 px bridged) of >= 40 px starting within 64 px of the body
   entry, then followed both ways while the running contrast is >= 2.5
   (hysteresis: accepted when clearly real, then followed into its faint parts). Between the outline and that stretch the line is *inferred* (fur band
   too busy to see it), and marked so.
5. Sub-pixel centre, width and depth: a Gaussian dip fitted across the line on
   the photo itself at every 1 px (grey averaged +-4 px along the line).

Two kinds of starts:
  - continuations: every traced whisker whose root end is at his cheek outline;
  - a sweep: a start every 3 px along both cheek outlines, for face whiskers
    whose outside part is hidden or too short to trace;
  - starts across both cheeks (every 5 px down six vertical lines, searching
    both ways), for whiskers whose visible part does not reach his outline
    (owner, 2026-11-13: several had been missed).
Overlapping finds are merged (a continuation wins over a sweep find).

Usage: python tools/face_whiskers.py [--sweep-cache PATH] [--interior-cache PATH] [--line-cache PATH]
Part 2b (the line view, tools/whisker_lineview.py) runs after the first pass.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# ---- parameters (see module doc) ----
DX, DY = 8.0, 0.25          # px per lattice step along; sideways cell
DK = DY / DX                # one slope notch = one cell per step
KMAX = 0.70                 # |slope| relative to the entry direction (35 deg)
K0MAX = 0.50                # starting slope (27 deg): the bend where it meets his cheek
YMAX = 90.0                 # px sideways search room
CAP = 10.0                  # per-point contrast cap
C0 = 1.0                    # cost per px: the path ends where going on no longer pays
LAT = np.array([3.0, 3.75, 4.5])   # shoulder offsets for line contrast
NEAR_OUTLINE = 5.0          # px: fur band at the outline scores 0
BAND = 12.0                 # px: path may not run this close to the outline past its entry
FREE = 32.0                 # px along the path before that rule applies (+1.5x the start's distance outside)
EYE_MARGIN = 50             # px around each eye box
NOSE_BOX = (470, 640, 630, 870)
WINDOW = 24                 # px running mean
T = 3.5                     # running-mean line contrast that counts as a whisker
FAINT_T = 2.5               # a whisker is followed into its fainter parts down to this; fainter lines on their own are only listed
GAP, MIN_LEN, ENTRY = 16, 40, 64
FUR_LEVEL = 1.8             # running line contrast along a searched path through plain fur (forehead, median)
END_H_K = 1.17              # a whisker ends where its contrast falls to about the fur's level:
                            # END_H = END_H_K x the fur's robust speckle around its end
                            # (forehead: speckle 1.88 -> 2.2, just above a searched path's 1.8 in plain fur)
SPECKLE_HALF = 30           # px: box half-size for measuring the fur's speckle
SEARCH_LEN = 360.0
SWEEP_Y = (560.0, 900.0)    # cheek height for sweep starts
SWEEP_STEP = 3.0
SWEEP_K0MAX, SWEEP_KMAX = 0.70, 1.0
INTERIOR_X = (220, 300, 380, 720, 800, 880)   # vertical lines of starts across both cheeks
INTERIOR_Y = (560.0, 900.0, 5.0)
INTERIOR_LEN = 320.0
CONT_ROOT_DIST = 25.0       # px: whisker root end this close to the outline continues onto the face
CONT_Y = (540.0, 940.0)


class Face:
    def __init__(self, photo: np.ndarray | None = None, body: np.ndarray | None = None,
                 boxes: list | None = None):
        if photo is None:
            photo = np.array(Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB"))
        if body is None:
            body = np.array(json.loads((ROOT / "data/strands/body_outline.json").read_text())["sampled_curve"])
        if boxes is None:
            boxes = [(x0 - EYE_MARGIN, y0 - EYE_MARGIN, x1 + EYE_MARGIN, y1 + EYE_MARGIN)
                     for x0, y0, x1, y1 in bo.EYE_BOXES.values()] + [NOSE_BOX]
        self.photo = photo
        self.grey = photo.astype(float).mean(2)
        L = ndi.gaussian_filter(self.grey, 0.7)
        self.D = -(L - ndi.gaussian_filter(L, 6))
        self.body = body
        self.bp = MPath(body)
        seg = np.hypot(*np.diff(body, axis=0).T)
        s = np.r_[0, np.cumsum(seg)]
        u = np.arange(0, s[-1], 0.25)
        self.tb = cKDTree(np.c_[np.interp(u, s, body[:, 0]), np.interp(u, s, body[:, 1])])
        H, W = self.grey.shape
        ys, xs = np.mgrid[0:H * 2, 0:W * 2]
        P = np.c_[(xs.ravel() + 0.5) / 2, (ys.ravel() + 0.5) / 2]
        d = self.tb.query(P)[0]
        ins = self.bp.contains_points(P)
        self.sd = np.where(ins, d, -d).reshape(H * 2, W * 2).astype(np.float32)   # signed distance, + inside
        self.boxes = boxes

    # ---- maps ----
    def sdist(self, P):
        P = np.asarray(P, float)
        ix = np.clip((P[..., 0] * 2).astype(int), 0, self.sd.shape[1] - 1)
        iy = np.clip((P[..., 1] * 2).astype(int), 0, self.sd.shape[0] - 1)
        return self.sd[iy, ix]

    def neutral(self, P):
        return self.sdist(P) < NEAR_OUTLINE

    def valid(self, P):
        f = P.reshape(-1, 2)
        ok = (f[:, 0] > 1) & (f[:, 0] < self.grey.shape[1] - 2) & (f[:, 1] > 1) & (f[:, 1] < self.grey.shape[0] - 2)
        for x0, y0, x1, y1 in self.boxes:
            ok &= ~((f[:, 0] >= x0) & (f[:, 0] <= x1) & (f[:, 1] >= y0) & (f[:, 1] <= y1))
        return ok.reshape(P.shape[:-1])

    def contrast(self, P, t):
        n = np.stack([-t[..., 1], t[..., 0]], -1)
        pts = [P] + [P + s * l * n for l in LAT for s in (-1, 1)]
        v = [ndi.map_coordinates(self.D, [q[..., 1].ravel() - 0.5, q[..., 0].ravel() - 0.5], order=1,
                                 mode="nearest").reshape(P.shape[:-1]) for q in pts]
        return v[0] - np.mean(v[1:], 0)

    # ---- whole-path search ----
    def search(self, start, th0, length=SEARCH_LEN, k0max=K0MAX, kmax=KMAX, kstep=1, c0=C0, band_rule=True,
               ymax=YMAX):
        start = np.asarray(start, float)
        free = FREE + 1.5 * max(0.0, -float(self.sdist(start)))
        t0 = np.array([np.cos(th0), np.sin(th0)]); n0 = np.array([-t0[1], t0[0]])
        ny = int(round(ymax / DY)); Y = np.arange(-ny, ny + 1) * DY
        nk = int(round(kmax / DK)); K = np.arange(-nk, nk + 1)
        V = np.full((len(Y), len(K)), -np.inf); V[ny, np.abs(K * DK) <= k0max] = 0.0
        hist, backs = [V], []
        sub = np.arange(0.5, DX, 1.0)
        tt = t0 + (K * DK)[:, None] * n0; tt /= np.linalg.norm(tt, axis=1, keepdims=True)
        idx = np.arange(len(K))
        for j in range(int(length / DX)):
            x = j * DX
            Ys = Y[:, None, None] + (K * DK)[None, :, None] * sub[None, None, :]
            P = start + (x + sub)[None, None, :, None] * t0 + Ys[..., None] * n0
            c = self.contrast(P, np.broadcast_to(tt[None, :, None, :], P.shape))
            c = np.minimum(c, CAP)
            c = np.where(self.neutral(P), 0.0, c)
            c = np.where(self.valid(P), c, -1e3)
            if band_rule and x >= free:
                c = np.where(self.sdist(P) < BAND, -1e3, c)
            seg = c.mean(-1) - c0
            best = np.full_like(V, -np.inf); prev = np.zeros(V.shape, np.int16)
            for d in range(-kstep, kstep + 1):
                src = idx + d; okk = (src >= 0) & (src < len(K))
                Vs = np.full_like(V, -np.inf); Vs[:, okk] = V[:, src[okk]]
                m = Vs > best
                best = np.where(m, Vs, best)
                prev = np.where(m, np.broadcast_to(np.where(okk, src, 0), V.shape), prev)
            cand = best + seg
            newV = np.full_like(V, -np.inf); newP = np.zeros(V.shape, np.int16)
            for ik, k in enumerate(K):
                if k >= 0:
                    newV[k:, ik] = cand[:len(Y) - k, ik]; newP[k:, ik] = prev[:len(Y) - k, ik]
                else:
                    newV[:k, ik] = cand[-k:, ik]; newP[:k, ik] = prev[-k:, ik]
            backs.append(newP); V = newV; hist.append(V)
        # best end over every length (the cut then decides where the whisker is really seen)
        j = int(np.argmax([h.max() for h in hist]))
        iy, ik = np.unravel_index(np.argmax(hist[j]), hist[j].shape)
        cells = [iy]
        for jj in range(j - 1, -1, -1):
            iy_s = iy - K[ik]; ik = backs[jj][iy, ik]; iy = iy_s; cells.append(iy)
        cells = cells[::-1]
        x = np.arange(len(cells)) * DX
        return start + x[:, None] * t0 + Y[cells][:, None] * n0

    # ---- along-path measures ----
    def line_profile(self, path):
        q = dense(path)
        if len(q) < 3:                      # no path worth the name: nothing to measure
            return q, np.full(len(q), np.nan)
        t = np.gradient(q, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
        c = self.contrast(q, t)
        return q, np.where(self.neutral(q), np.nan, c)

    def cut(self, q, wv, entry_rule=True):
        """Hysteresis: a stretch counts as a whisker if its running contrast is >= T
        for >= MIN_LEN px (gaps <= GAP bridged) starting within ENTRY px of the body
        entry; it is then extended both ways while the running contrast stays
        >= FAINT_T (same gap rule), so a line accepted as clearly real is followed
        into its fainter parts (toward the fur band, and where it fades)."""
        ins = np.flatnonzero(self.sdist(q) >= 0)
        if len(ins) == 0:
            return None
        ie = int(ins[0])
        strong = None
        if entry_rule:
            for a, b in chains(wv):
                if b - a >= MIN_LEN and a - ie <= ENTRY:
                    strong = (a, b); break
                if a - ie > ENTRY:
                    break
        else:                                   # found inside his face: its longest strong stretch
            cs = [ab for ab in chains(wv) if ab[1] - ab[0] >= MIN_LEN]
            strong = max(cs, key=lambda ab: ab[1] - ab[0]) if cs else None
        if strong is None:
            return None
        for a, b in chains(wv, FAINT_T):
            if a <= strong[0] and b >= strong[1]:
                return ie, int(max(a, ie)), int(b)
        return ie, int(strong[0]), int(strong[1])

    def refine(self, q, along=4.0, half=4.5, resample=True):
        """sub-pixel centre / width (sigma) / depth (grey levels darker than the fur beside it)"""
        q = dense(q) if resample else np.asarray(q, float)
        t = np.gradient(q, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
        n = np.c_[-t[:, 1], t[:, 0]]
        s = np.arange(-half, half + 1e-9, 0.25); u = np.arange(-along, along + 1e-9, 1.0)
        pts, sig, dep, ok = [], [], [], []
        for p, tt, nn in zip(q, t, n):
            Pp = p[None, None, :] + s[:, None, None] * nn + u[None, :, None] * tt
            f = ndi.map_coordinates(self.grey, [Pp[..., 1].ravel() - 0.5, Pp[..., 0].ravel() - 0.5], order=1,
                                    mode="nearest").reshape(len(s), len(u)).mean(1)
            b0 = float(np.percentile(f, 80)); A0 = max(b0 - f.min(), 0.5)

            def res(z):
                c, sg, A, b, m = z
                return b + m * s - A * np.exp(-(s - c) ** 2 / (2 * sg * sg)) - f
            try:
                r = least_squares(res, [0.0, 0.9, A0, b0, 0.0], bounds=([-1.5, 0.35, 0, 0, -20], [1.5, 2.5, 80, 255, 20]))
                c, sg, A, b, m = r.x
                good = A >= 2.0
            except Exception:
                c, sg, A, good = 0.0, np.nan, 0.0, False
            pts.append(p + c * nn if good else p); sig.append(sg); dep.append(A); ok.append(good)
        return np.array(pts), np.array(sig), np.array(dep), np.array(ok)

    def finish(self, q, a, b, both_ends=False):
        """Final whisker line from the searched path q, kept stretch [a, b].
        Far end: change point of the per-point line contrast along the whole
        searched path: the index where the running sum of (contrast - h) peaks,
        h = END_H_K x the robust speckle of the fur around the stretch's far end
        (just above what a searched path through that fur scores). So a whisker
        ends where it can no longer be told from the fur around it, not where it
        gets fainter than its own typical strength (that cut fading whiskers
        short; owner, 2026-11-13).
        Then per-point sub-pixel fits, and through them a least-squares cubic
        spline (knots every 32 px: whiskers are smooth arcs and do not wiggle at
        that scale), each fit weighted by how deep its dip is."""
        _, c = self.line_profile(q)
        cc = np.nan_to_num(c)
        mu = float(np.median(cc[a:b + 1]))
        h = END_H_K * self.speckle(q[b])
        end = a + int(np.argmax(np.cumsum(cc[a:] - h)))
        if both_ends:                       # the near end the same way (lines found inside his face)
            h0 = END_H_K * self.speckle(q[a])
            a = end - int(np.argmax(np.cumsum((cc[:end + 1] - h0)[::-1])))
        base = np.asarray(q[a:end + 1], float)
        pts, sig, dep, ok = self.refine(base, resample=False)
        line = smooth_line(base, pts, np.where(ok, np.clip(dep, 0, None), 0.0))
        return dict(centreline=line, sigma=sig, depth=dep, fit_ok=ok, end_index=end,
                    median_contrast=mu, end_level=h, median_depth=float(np.median(dep[ok])) if ok.any() else float("nan"))

    def speckle(self, p):
        """robust spread (1.4826 x MAD) of the detail map D in a box around p"""
        x, y = int(round(p[0])), int(round(p[1]))
        y0, x0 = max(0, y - SPECKLE_HALF), max(0, x - SPECKLE_HALF)
        a = self.D[y0:y + SPECKLE_HALF + 1, x0:x + SPECKLE_HALF + 1]
        gy, gx = np.mgrid[y0:y0 + a.shape[0], x0:x0 + a.shape[1]] + 0.5
        P = np.stack([gx, gy], -1)
        m = (self.sdist(P) >= BAND) & self.valid(P)          # his face fur only: not the fur band, eyes, nose
        a = a[m] if m.sum() >= 200 else a.ravel()
        return float(1.4826 * np.median(np.abs(a - np.median(a))))

    def find(self, start, th, **kw):
        path = self.search(start, th, **kw)
        q, c = self.line_profile(path)
        wv = windowed(c)
        return dict(start=np.asarray(start, float), th=float(th), q=q, wv=wv, cut=self.cut(q, wv))


def dense(path, step=1.0):
    path = np.asarray(path, float).reshape(-1, 2)
    if len(path) < 2:
        return path.copy()
    seg = np.hypot(*np.diff(path, axis=0).T); s = np.r_[0, np.cumsum(seg)]
    u = np.arange(0, s[-1] + 1e-9, step)
    return np.c_[np.interp(u, s, path[:, 0]), np.interp(u, s, path[:, 1])]


KNOT = 32.0


def smooth_line(base, pts, w):
    """least-squares cubic spline through pts (x and y against arc length of base)"""
    from scipy.interpolate import make_lsq_spline
    sb = np.r_[0, np.cumsum(np.hypot(*np.diff(base, axis=0).T))]
    L = sb[-1]
    nint = max(1, int(round(L / KNOT)))
    inner = np.linspace(0, L, nint + 1)[1:-1]
    tk = np.r_[[0.0] * 4, inner, [L] * 4]
    w = np.asarray(w, float) + 1e-3
    try:
        sx = make_lsq_spline(sb, pts[:, 0], tk, k=3, w=w)
        sy = make_lsq_spline(sb, pts[:, 1], tk, k=3, w=w)
    except Exception:
        return pts
    return np.c_[sx(sb), sy(sb)]


def windowed(c, w=WINDOW):
    out = np.full(len(c), np.nan)
    for i in range(len(c)):
        a = c[max(0, i - w // 2):i + w // 2 + 1]; a = a[~np.isnan(a)]
        if len(a) >= w // 2:
            out[i] = a.mean()
    return out


def chains(wv, thr=T, gap=GAP):
    good = np.flatnonzero(np.where(np.isnan(wv), False, wv >= thr))
    out = []
    if len(good) == 0:
        return out
    a = b = good[0]
    for i in good[1:]:
        if i - b > gap:
            out.append((a, b)); a = i
        b = i
    out.append((a, b))
    return out


def overlap(a, b, tol=2.0):
    a, b = dense(a), dense(b)
    if len(a) > len(b):
        a, b = b, a
    return float((cKDTree(b).query(a)[0] <= tol).mean())


# ---------------------------------------------------------------- the run
_F: Face | None = None


def _init():
    global _F
    _F = Face()


def _job(arg):
    start, th, k0, km = arg
    return _F.find(np.asarray(start), th, k0max=k0, kmax=km)


def root_end(cl: np.ndarray, F: Face):
    """(root point, inward direction angle): the end nearer his outline, direction over its last 6 px"""
    a, b = abs(float(F.sdist(cl[0]))), abs(float(F.sdist(cl[-1])))
    seq = cl[::-1] if a < b else cl
    s = np.r_[0, np.cumsum(np.hypot(*np.diff(seq, axis=0).T))]
    j = int(np.searchsorted(s, s[-1] - 6.0))
    d = seq[-1] - seq[j]
    return seq[-1], float(np.arctan2(d[1], d[0])), min(a, b)


def sweep_starts(F: Face):
    seg = np.hypot(*np.diff(F.body, axis=0).T); s = np.r_[0, np.cumsum(seg)]
    u = np.arange(0, s[-1], SWEEP_STEP)
    ob = np.c_[np.interp(u, s, F.body[:, 0]), np.interp(u, s, F.body[:, 1])]
    mid = 0.5 * (F.body[:, 0].min() + F.body[:, 0].max())
    return [(p, 0.0 if p[0] < mid else np.pi) for p in ob if SWEEP_Y[0] <= p[1] <= SWEEP_Y[1]]


def interior_starts():
    """starts across both cheeks (every 5 px down vertical lines), searching both
    ways: whiskers whose visible part does not reach his outline"""
    return [((float(x), float(y)), th) for x in INTERIOR_X
            for y in np.arange(INTERIOR_Y[0], INTERIOR_Y[1] + 1, INTERIOR_Y[2]) for th in (0.0, np.pi)]


def _job_interior(arg):
    (x, y), th = arg
    return _F.find(np.array([x, y]), th, length=INTERIOR_LEN, k0max=SWEEP_K0MAX, kmax=SWEEP_KMAX)


def run(sweep_cache: Path | None = None, procs: int = 4, interior_cache: Path | None = None):
    from multiprocessing import Pool
    F = Face()
    data = json.loads((ROOT / "data/strands/wisps.json").read_text())
    whiskers = [t for t in data["strands"] if t["class"].startswith("whisker")]
    conts = []
    for t in whiskers:
        p, th, dist = root_end(np.array(t["centreline"], float), F)
        if dist <= CONT_ROOT_DIST and CONT_Y[0] <= p[1] <= CONT_Y[1]:
            conts.append((t["id"], p, th))
    starts = sweep_starts(F)
    if sweep_cache and sweep_cache.exists():
        found = pickle.loads(sweep_cache.read_bytes())
        for r in found:          # the searched paths are cached; the cut rule is re-applied
            r["cut"] = F.cut(r["q"], r["wv"])
    else:
        jobs = [(p, th, K0MAX, KMAX) for _, p, th in conts] + [(p, th, SWEEP_K0MAX, SWEEP_KMAX) for p, th in starts]
        with Pool(procs, initializer=_init) as pool:
            found = list(pool.imap(_job, jobs, chunksize=2))
        if sweep_cache:
            sweep_cache.write_bytes(pickle.dumps(found))
    if interior_cache and interior_cache.exists():
        inner = pickle.loads(interior_cache.read_bytes())
        for r in inner:
            r["cut"] = F.cut(r["q"], r["wv"])
    else:
        with Pool(procs, initializer=_init) as pool:
            inner = list(pool.imap(_job_interior, interior_starts(), chunksize=4))
        if interior_cache:
            interior_cache.write_bytes(pickle.dumps(inner))
    joined = []
    for r0, r1 in zip(inner[0::2], inner[1::2]):   # same start, searched both ways: one path through it
        q = np.vstack([r1["q"][::-1], r0["q"][1:]]) if len(r1["q"]) and len(r0["q"]) else (r0["q"] if len(r0["q"]) else r1["q"])
        if len(q) < 3:
            continue
        qd, c = F.line_profile(q)
        wv = windowed(c)
        joined.append(dict(start=r0["start"], th=r0["th"], q=qd, wv=wv, cut=F.cut(qd, wv, entry_rule=False),
                           inside=True))
    cont_found = dict(zip([c[0] for c in conts], found[:len(conts)]))
    sweep_found = found[len(conts):] + joined
    return F, conts, cont_found, sweep_found


LINK_DIST, LINK_ANGLE = 12.0, 35.0   # a face-only line starting this close to a whisker's root end, same way


def select(F: Face, cont_found: dict, sweep_found: list, conts: list | None = None):
    """continuations first (a face line belongs to the outside whisker that runs into it);
    two continuations on one face line: the stronger keeps it, the other is noted"""
    lines, notes = [], []
    for k, r in cont_found.items():
        if r["cut"] is None:
            notes.append(f"{k}: no sustained line on the face (running contrast never >= {T} for "
                         f"{MIN_LEN} px within {ENTRY} px of where it enters) - face part not visible")
            continue
        ie, a, b = r["cut"]
        lines.append(dict(kind="continuation", of=k, r=r, seg=r["q"][a:b + 1],
                          score=float(np.nanmean(r["wv"][a:b + 1])) * (b - a + 1)))
    lines.sort(key=lambda x: -x["score"])
    kept = []
    for x in lines:
        clash = [y for y in kept if overlap(x["seg"], y["seg"]) >= 0.5]
        if clash:
            notes.append(f"{x['of']}: its face path runs onto the same face line as {clash[0]['of']} "
                         f"(stronger match); left to {clash[0]['of']}")
            continue
        kept.append(x)
    sw = []
    for r in sweep_found:
        if r["cut"] is None:
            continue
        ie, a, b = r["cut"]
        sw.append(dict(kind="face only", of=None, r=r, seg=r["q"][a:b + 1],
                       score=float(np.nanmean(r["wv"][a:b + 1])) * (b - a + 1)))
    sw.sort(key=lambda x: -x["score"])
    n_cont = len(kept)
    for x in sw:
        if all(overlap(x["seg"], y["seg"]) < 0.5 for y in kept):
            kept.append(x)
    # the same line found more than once: keep the find that covers the most of it
    # (finished length), so a better-scoring but shorter find never shortens a whisker
    for i in range(n_cont, len(kept)):
        x = kept[i]
        alts = [y for y in sw if overlap(y["seg"], x["seg"]) >= 0.5]
        def flen(y):
            ie_, a_, b_ = y["r"]["cut"]
            cl_ = F.finish(y["r"]["q"], a_, b_, both_ends=bool(y["r"].get("inside")))["centreline"]
            return float(np.hypot(*np.diff(cl_, axis=0).T).sum()) if len(cl_) > 1 else 0.0
        kept[i] = max(alts, key=flen)
    # a face-only line reached by a search that starts at the root end of a whisker with
    # no face part yet, heading the same way, is that whisker's continuation (its own
    # search went off it). The search may be a weaker find of the same line.
    have = {y["of"] for y in kept if y["of"]}
    outline_finds = [y for y in sw if not y["r"].get("inside")]
    for x in kept:
        if x["kind"] != "face only" or not conts:
            continue
        best = None
        for y in [x] + [y for y in outline_finds if y is not x and overlap(y["seg"], x["seg"]) >= 0.5]:
            if y["r"].get("inside"):
                continue
            q = y["r"]["q"]; d0 = q[min(10, len(q) - 1)] - q[0]; a0 = np.arctan2(d0[1], d0[0])
            for k, p, th in conts:
                if k in have:
                    continue
                dist = float(np.hypot(*(y["r"]["start"] - p)))
                ang = abs((np.degrees(a0 - th) + 180) % 360 - 180)
                if dist <= LINK_DIST and ang <= LINK_ANGLE and (best is None or dist < best[1]):
                    best = (k, dist, ang, y)
        if best:
            k, dist, ang, y = best
            x["kind"] = "continuation (linked)"; x["of"] = k; have.add(k)
            x["root"] = next(p for kk, p, _ in conts if kk == k)
            # the inferred link: the root-end search from its start to where it meets the line
            yq = y["r"]["q"]; dd = cKDTree(dense(x["seg"])).query(yq)[0]
            meet = int(np.flatnonzero(dd <= 2.0)[0]) if (dd <= 2.0).any() else len(yq) - 1
            x["link_path"] = yq[:meet + 1]
            notes[:] = [n for n in notes if not n.startswith(f"{k}:")]
            notes.append(f"{k}: its own search went off its line; a sweep start {dist:.0f} px from its root end "
                         f"(heading {ang:.0f} deg from its direction) found the face line it runs into - linked "
                         f"as its continuation (owner review)")
    # fainter lines (running contrast >= FAINT_T) not already kept: listed for the owner only
    faint = []
    for r in list(cont_found.values()) + sweep_found:
        for a, b in chains(r["wv"], FAINT_T):
            if b - a < MIN_LEN:
                continue
            seg = r["q"][a:b + 1]
            if all(overlap(seg, y["seg"]) < 0.5 for y in kept) and all(overlap(seg, f) < 0.5 for f in faint):
                faint.append(seg)
    return kept, notes, faint


def save(F: Face, kept: list, notes: list, faint: list):
    # stable names: a face-only line keeps the name it had in the saved data (same line)
    prev = []
    path_ = ROOT / "data/strands/face_whiskers.json"
    if path_.exists():
        prev = [(w_["id"], np.array(w_["centreline"])) for w_ in json.loads(path_.read_text())["whiskers"]
                if w_["kind"] == "face only"]
    used = {i for i, _ in prev}
    n_face_only = max([int(i[3:]) for i in used] or [0])
    out = []
    for x in sorted(kept, key=lambda x: (not x["kind"].startswith("continuation"), x["of"] or "", x["seg"][0][1])):
        r = x["r"]; ie, a, b = r["cut"]
        fin = F.finish(r["q"], a, b, both_ends=bool(r.get("inside")))
        if x["kind"].startswith("continuation"):
            fid = f"{x['of']}-face"
        else:
            same = [i for i, cl0 in prev if overlap(x["seg"], cl0) >= 0.5]
            if same:
                fid = same[0]
            else:
                n_face_only += 1; fid = f"FW-{n_face_only:02d}"
        entry = r["q"][:a + 1]
        if "root" in x:      # linked: the inferred link starts at the whisker's own root end
            entry = np.vstack([x["root"], x.get("link_path", entry)])
        elif abs(float(F.sdist(r["start"]))) > NEAR_OUTLINE + 3:
            entry = np.zeros((0, 2))   # started inside his face: no link through the fur band to infer
        entry = dense(entry) if len(entry) > 1 else np.zeros((0, 2))
        cl = fin["centreline"]
        if F.sdist(cl[0]) > F.sdist(cl[-1]):
            # every face whisker runs from his outline side toward his nose
            cl = cl[::-1]
            fin = dict(fin, centreline=cl, sigma=fin["sigma"][::-1], depth=fin["depth"][::-1], fit_ok=fin["fit_ok"][::-1])
        # footprint: pixels whose centre lies within 2 sigma (>= 1 px) of the line
        sg = np.nan_to_num(fin["sigma"], nan=1.0)
        lo_ = np.floor(cl.min(0) - 6).astype(int); hi_ = np.ceil(cl.max(0) + 6).astype(int)
        gx, gy = np.meshgrid(np.arange(lo_[0], hi_[0]) + 0.5, np.arange(lo_[1], hi_[1]) + 0.5)
        dd, ii = cKDTree(cl).query(np.c_[gx.ravel(), gy.ravel()])
        foot = int((dd <= np.maximum(2 * sg[ii], 1.0)).sum())
        out.append(dict(
            id=fid, kind=x["kind"], continues=x["of"],
            length_px=round(float(np.hypot(*np.diff(cl, axis=0).T).sum()), 1),
            inferred_entry_px=round(float(np.hypot(*np.diff(entry, axis=0).T).sum()) if len(entry) > 1 else 0.0, 1),
            median_line_contrast=round(fin["median_contrast"], 2),
            median_depth_grey=round(fin["median_depth"], 1),
            median_sigma_px=round(float(np.nanmedian(fin["sigma"][fin["fit_ok"]])), 2),
            footprint_px=foot,
            status="first pass, self-checked at full resolution; owner review pending",
            weight=0,
            centreline=np.round(cl, 2).tolist(),
            sigma=np.round(fin["sigma"], 2).tolist(),
            depth_grey=np.round(fin["depth"], 1).tolist(),
            inferred_entry=np.round(entry, 2).tolist(),
        ))
    doc = dict(
        about=("Whiskers lying over his face, inside the outline (tools/face_whiskers.py). "
               "Coloured precisely as whiskers and otherwise ignored (weight 0) until they are added last. "
               "centreline: sub-pixel, 1 px spacing (pixel (c,r) covers [c,c+1)x[r,r+1)); "
               "sigma: Gaussian half-width across (px, as seen in the photo); depth_grey: how many grey levels "
               "darker than the fur beside it the line is (his whiskers are light: on white fur they show "
               "only faintly). inferred_entry: from the outside whisker's root end to where the line can be "
               "seen on the face (through the busy fur band) - inferred, owner review."),
        photo="data/photos/anchor_front.webp",
        rules=dict(line_contrast_T=T, window_px=WINDOW, min_len_px=MIN_LEN, entry_px=ENTRY, gap_px=GAP,
                   slope_change_per_px_deg=round(float(np.degrees(np.arctan(DK / DX))), 3),
                   start_bend_deg=round(float(np.degrees(np.arctan(K0MAX))), 1),
                   keep_off_outline_px=BAND, eye_margin_px=EYE_MARGIN, nose_mouth_box=list(NOSE_BOX)),
        whiskers=out, notes=notes,
        accounting=dict(face_whisker_pixels=int(sum(o["footprint_px"] for o in out)),
                        note=("inside the outline every pixel is already classified (head / undercarriage / "
                              "parts); these pixels are additionally marked WHISKER (weight 0) on top")),
        faint_candidates_not_classified=[dict(id=f"C{i + 1:02d}", points=np.round(f, 1)[::4].tolist())
                                         for i, f in enumerate(sorted(faint, key=lambda f: (f[:, 0].mean() > 549, f[:, 1].mean())))],
    )
    (ROOT / "data/strands/face_whiskers.json").write_text(json.dumps(doc, indent=1))
    return doc


def sheets(doc=None):
    """Review pictures (docs/images/face_whiskers_*.png). Photo shown in grey with its
    large-scale shading taken out and contrast stretched over his fur, so the faint
    lines can be seen; guides 3 px either
    side of each traced line (the line itself is left uncovered); dashed = inferred."""
    from PIL import ImageDraw
    F = Face()
    if doc is None:
        doc = json.loads((ROOT / "data/strands/face_whiskers.json").read_text())
    grey = F.grey

    def panel(box, sc, items, faint=(), label="", lvc=()):
        x0, y0, x1, y1 = box
        # display only: the photo's grey with its large-scale shading taken out (local
        # contrast), so faint lines show the same on lit and shadowed fur
        a = (grey - ndi.gaussian_filter(grey, 12))[y0:y1, x0:x1]
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        ins = F.sdist(np.stack([gx, gy], -1)) > 3
        lo, hi = np.percentile(a[ins], [1, 99]) if ins.any() else (a.min(), a.max())
        a = np.clip((a - lo) / max(hi - lo, 1e-6) * 235 + 10, 0, 255).astype(np.uint8)
        im = Image.fromarray(a).resize(((x1 - x0) * sc, (y1 - y0) * sc), Image.LANCZOS).convert("RGB")
        top = im.copy(); dr = ImageDraw.Draw(im)
        P = lambda z: ((z[0] - x0) * sc, (z[1] - y0) * sc)

        def guides(q, col, dash=False):
            if len(q) < 2:
                return
            t = np.gradient(q, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
            n = np.c_[-t[:, 1], t[:, 0]]
            for sg in (-1, 1):
                g = q + sg * 3.0 * n
                if dash:
                    for i in range(0, len(g) - 1, 4):
                        dr.line([P(g[i]), P(g[min(i + 2, len(g) - 1)])], fill=col, width=1)
                else:
                    dr.line([P(z) for z in g], fill=col, width=1)
        for fc in faint:
            f = dense(np.array(fc["points"]))
            for i in range(0, len(f) - 1, 6):
                dr.line([P(f[i]), P(f[min(i + 2, len(f) - 1)])], fill=(80, 160, 255), width=1)
            m = f[len(f) // 2]
            if box[0] <= m[0] < box[2] and box[1] <= m[1] < box[3]:
                dr.text(P(m + np.array([2, 3])), fc["id"], fill=(80, 160, 255))
        for lc_ in lvc:
            f = dense(np.array(lc_["points"]))
            col = (0, 200, 255) if lc_["verdict"] != "whisker" else (255, 140, 0)
            for i in range(0, len(f) - 1, 5):
                dr.line([P(f[i]), P(f[min(i + 3, len(f) - 1)])], fill=col, width=3)
            m = f[len(f) // 2]
            if box[0] <= m[0] < box[2] and box[1] <= m[1] < box[3]:
                dr.text(P(m + np.array([3, 4])), lc_["id"], fill=col)
        for w_ in items:
            guides(dense(np.array(w_["inferred_entry"])) if len(w_["inferred_entry"]) > 1 else np.zeros((0, 2)),
                   (255, 190, 0), dash=True)
            cl = np.array(w_["centreline"]); guides(cl, (255, 0, 150))
            m = cl[len(cl) // 2]
            dr.text(P(m + np.array([0, -9])), w_["id"], fill=(0, 230, 0))
        dr.text((6, 6), label, fill=(0, 230, 0))
        out = Image.new("RGB", (im.width, im.height * 2 + 6), (30, 30, 30))
        out.paste(top, (0, 0)); out.paste(im, (0, im.height + 6))
        return out
    W = doc["whiskers"]
    imgs = []
    for side, box in (("image_left", (130, 560, 470, 900)), ("image_right", (630, 620, 990, 900))):
        items = [w_ for w_ in W if box[0] <= np.array(w_["centreline"])[:, 0].mean() <= box[2]]
        fa = [f for f in doc["faint_candidates_not_classified"] if box[0] <= np.array(f["points"])[:, 0].mean() <= box[2]]
        lvc = [c for c in doc.get("line_view_candidates", []) if box[0] <= np.array(c["points"])[:, 0].mean() <= box[2]]
        im = panel(box, 3, items, fa, f"face whiskers, {side.replace('_', ' ')} cheek: photo, local contrast (top); "
                                     f"magenta = whisker (guides 3 px each side), dashed yellow = inferred, dotted blue = faint, "
                                     f"bold cyan L = uncertain: owner sorts manually", lvc)
        im.save(ROOT / f"docs/images/face_whiskers_{side}.png"); imgs.append(im)
    # the line view itself (owner's request: a different way of highlighting them)
    import whisker_lineview as lv
    LV = lv.LineView(lv.field_lines(W, F))
    A = LV.along_view()
    for side, box in (("image_left", (130, 560, 470, 960)), ("image_right", (630, 560, 1000, 920))):
        x0, y0, x1, y1 = box; sc = 2
        a = A[y0 - lv.Y0:y1 - lv.Y0, x0 - lv.X0:x1 - lv.X0]
        g = np.clip(255 - np.clip(a, 0, 8) / 8 * 255, 0, 255).astype(np.uint8)
        im = Image.fromarray(g).resize(((x1 - x0) * sc, (y1 - y0) * sc), Image.LANCZOS).convert("RGB")
        top = im.copy(); dr = ImageDraw.Draw(im)
        P = lambda z: ((z[0] - x0) * sc, (z[1] - y0) * sc)
        for w_ in W:
            cl = np.array(w_["centreline"]); t = np.gradient(cl, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
            n = np.c_[-t[:, 1], t[:, 0]]
            if not (box[0] <= cl[:, 0].mean() <= box[2]):
                continue
            for sg in (-1, 1):
                dr.line([P(z) for z in cl + sg * 4 * n], fill=(255, 0, 150), width=1)
            dr.text(P(cl[0] + np.array([0, -12])), w_["id"], fill=(0, 170, 0))
        for c in doc.get("line_view_candidates", []):
            f = dense(np.array(c["points"]))
            if not (box[0] <= f[:, 0].mean() <= box[2]):
                continue
            col = (0, 200, 255) if c["verdict"] != "whisker" else (255, 140, 0)
            for i in range(0, len(f) - 1, 5):
                dr.line([P(f[i]), P(f[min(i + 3, len(f) - 1)])], fill=col, width=3)
            dr.text(P(f[len(f) // 2] + np.array([4, 4])), c["id"], fill=col)
        dr.text((6, 6), "line view: long thin line filters along the whisker directions (darker = more line-like); "
                        "magenta = whisker, bold cyan L = uncertain: owner sorts manually", fill=(0, 170, 0))
        out = Image.new("RGB", (im.width, im.height * 2 + 6), (30, 30, 30)); out.paste(top, (0, 0)); out.paste(im, (0, im.height + 6))
        out.save(ROOT / f"docs/images/face_whiskers_lineview_{side}.png")
    for w_ in W:
        cl = np.array(w_["centreline"]); en = np.array(w_["inferred_entry"]).reshape(-1, 2)
        allp = np.vstack([en, cl]) if len(en) else cl
        x0, y0 = np.floor(allp.min(0) - 12).astype(int); x1, y1 = np.ceil(allp.max(0) + 12).astype(int)
        sc = max(3, min(7, int(900 / (x1 - x0))))
        panel((x0, y0, x1, y1), sc, [w_], (), f"{w_['id']} at x{sc}").save(ROOT / f"docs/images/face_whisker_{w_['id']}.png")
    return imgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep-cache", type=Path, default=None)
    ap.add_argument("--interior-cache", type=Path, default=None)
    ap.add_argument("--line-cache", type=Path, default=None)
    ap.add_argument("--full-cache", type=Path, default=None)
    ap.add_argument("--sheets-only", action="store_true")
    args = ap.parse_args()
    if args.sheets_only:
        sheets(); return 0
    F, conts, cont_found, sweep_found = run(args.sweep_cache, interior_cache=args.interior_cache)
    kept, notes, faint = select(F, cont_found, sweep_found, conts)
    doc = save(F, kept, notes, faint)
    # part 2b: the line view (tools/whisker_lineview.py): extends whiskers, finds missed ones
    import whisker_lineview as lv
    ext, cands, _ = lv.run(F, doc, args.line_cache)
    doc = lv.apply(F, doc, ext, cands)
    # part 2c: whole length in the combined view (tools/whisker_fulllength.py)
    import whisker_fulllength as wf
    doc = wf.run(F, doc, args.full_cache)
    (ROOT / "data/strands/face_whiskers.json").write_text(json.dumps(doc, indent=1))
    for k_, n_ in doc["full_length"]["sweep_extensions"].items():
        print(f"combined view sweep: {k_} +{n_} px")
    for i_, rr in enumerate(doc["full_length"]["follow_rounds"]):
        print(f"follow round {i_ + 1}: " + ", ".join(f"{a}/{b} +{n} px (margin {m:+.1f})" for a, b, n, m in rr))
    for k_, n_ in doc["line_view"]["extensions"].items():
        print(f"line view: {k_} extended by {n_} px")
    for c in doc["line_view_candidates"]:
        print(f"line view candidate {c['id']} ({c['verdict']}): margin {c['margin']:+.2f}  {c['reason']}")
    for w_ in doc["whiskers"]:
        print(f"{w_['id']:12s} {w_['kind']:22s} face {w_['length_px']:6.1f} px  inferred entry {w_['inferred_entry_px']:5.1f} px  "
              f"contrast {w_['median_line_contrast']:4.1f}  depth {w_['median_depth_grey']:4.1f} grey  sigma {w_['median_sigma_px']:.2f}")
    for n in notes:
        print("note:", n)
    print("faint candidates (not classified):", len(faint))
    sheets(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
