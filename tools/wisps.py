"""Strand-by-strand tracing of Prince's wisps, pixel by pixel (owner, 2026-11-11:
"since these little wisps are so small, you must go pixel by pixel, and be as
precise as possible so you don't mess up the little guy").

Each strand is traced to sub-pixel precision: at every step along it, the fur
coverage across the strand is fitted with a Gaussian ridge (centre, width,
opacity), the centre is moved onto the fitted centre, and the trace continues
outward to the tip and inward through the fringe to the base, stopping where
the strand can no longer be told apart or reaches the body line. Stored as a
smooth centreline with width and opacity along its length (no pixel masks).

Pixel convention: pixel (col, row) covers [col, col+1) x [row, row+1); a value
a[r, c] is the pixel's centre (c + 0.5, r + 0.5).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import splev, splprep
from scipy.optimize import least_squares

HALF = 4.0            # px: half-length of the cross profile
DS = 0.25             # px: profile sample spacing
STEP = 1.0            # px: spacing of fits along the strand
SIG_MIN, SIG_MAX = 0.35, 3.0
A_MIN = 0.06          # minimum ridge height (coverage) to keep tracing
MAX_SHIFT = 0.9       # px: max sideways jump between neighbouring fits
MAX_EXTEND = 120      # px: max extension at each end
RIDGE_DROP = 0.4      # a hair is a ridge: coverage must drop by >= this x height on BOTH sides
MAX_TURN = 35.0       # deg between successive 1 px steps; sharper = jumped to another hair
# A fitted profile is the true hair blurred by the pixel's own area (variance
# 1/12 px^2) and by bilinear sampling between pixel centres (1/6 px^2). Remove
# that known blur, keeping the hair's total darkness (opacity x width).
BLUR_VAR = 1 / 12 + 1 / 6


def deblur(sig: np.ndarray, amp: np.ndarray):
    s2 = np.maximum(sig ** 2 - BLUR_VAR, SIG_MIN ** 2)
    st = np.sqrt(s2)
    return st, np.clip(amp * sig / st, 0, 1)


def sample(a: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return ndi.map_coordinates(a, [pts[..., 1] - 0.5, pts[..., 0] - 0.5], order=1, mode="constant")


def fit_profile(a: np.ndarray, p: np.ndarray, n: np.ndarray):
    """Fit b + A*exp(-(s-c)^2/(2 sig^2)) across the strand at p along normal n.
    Returns (c, sig, A, b, rms) or None."""
    s = np.arange(-HALF, HALF + 1e-9, DS)
    f = sample(a, p[None, :] + s[:, None] * n[None, :])
    b0 = float(np.percentile(f, 20))
    A0 = float(f.max() - b0)
    if A0 < A_MIN * 0.5:
        return None
    c0 = float(s[np.argmax(f)])
    if abs(c0) > HALF - 1:
        c0 = 0.0

    def res(q):
        c, sig, A, b = q
        return b + A * np.exp(-((s - c) ** 2) / (2 * sig * sig)) - f

    try:
        r = least_squares(res, [c0, 0.9, A0, b0],
                          bounds=([-HALF + 0.5, SIG_MIN, 0.0, -0.05], [HALF - 0.5, SIG_MAX, 1.2, 1.0]))
    except Exception:
        return None
    c, sig, A, b = r.x
    rms = float(np.sqrt(np.mean(r.fun ** 2)))
    # ridge, not a step: lighter on both sides
    d = min(2 * sig + 1.0, HALF - 0.25)
    fc = float(np.interp(c, s, f))
    fl = float(np.interp(c - d, s, f)); fr = float(np.interp(c + d, s, f))
    if max(fl, fr) > fc - RIDGE_DROP * A:
        return None
    return float(c), float(sig), float(A), float(b), rms


def _normal(t: np.ndarray) -> np.ndarray:
    t = t / (np.linalg.norm(t) + 1e-12)
    return np.array([-t[1], t[0]])


def refine(a: np.ndarray, path: np.ndarray, iters: int = 3):
    """Move every point of a rough path onto the fitted ridge centre.
    Returns centres, sigma, amplitude, baseline, ok-mask."""
    pts = resample(path, STEP)
    for _ in range(iters):
        tan = np.gradient(pts, axis=0)
        new, sig, amp, base, ok = [], [], [], [], []
        for p, t in zip(pts, tan):
            n = _normal(t)
            r = fit_profile(a, p, n)
            if r is None or r[2] < A_MIN or abs(r[0]) > 2.0:
                new.append(p); sig.append(np.nan); amp.append(0.0); base.append(np.nan); ok.append(False)
                continue
            c, s_, A, b, _ = r
            new.append(p + c * n); sig.append(s_); amp.append(A); base.append(b); ok.append(True)
        pts = np.array(new)
    return pts, np.array(sig), np.array(amp), np.array(base), np.array(ok)


def extend(a: np.ndarray, pts: np.ndarray, stop_fn=None, from_end: bool = True):
    """Keep tracing past one end of the strand while the ridge is still there."""
    seq = pts if from_end else pts[::-1]
    t = seq[-1] - seq[max(-6, -len(seq))]
    t = t / (np.linalg.norm(t) + 1e-12)
    p = seq[-1].copy()
    out, info = [], []
    for _ in range(int(MAX_EXTEND / STEP)):
        q = p + t * STEP
        if stop_fn is not None and stop_fn(q):
            break
        n = _normal(t)
        r = fit_profile(a, q, n)
        if r is None or r[2] < A_MIN or abs(r[0]) > MAX_SHIFT:
            break
        c, s_, A, b, _ = r
        q2 = q + c * n
        t_new = q2 - p
        t_new = t_new / (np.linalg.norm(t_new) + 1e-12)
        if np.dot(t_new, t) < np.cos(np.radians(25)):
            break
        t = 0.7 * t + 0.3 * t_new
        t /= np.linalg.norm(t)
        out.append(q2); info.append((s_, A, b))
        p = q2
    return np.array(out).reshape(-1, 2), info


def resample(xy: np.ndarray, step: float) -> np.ndarray:
    seg = np.hypot(*np.diff(xy, axis=0).T)
    keep = np.r_[True, seg > 1e-9]
    xy = xy[keep]
    if len(xy) < 2:
        return xy
    arc = np.r_[0, np.cumsum(np.hypot(*np.diff(xy, axis=0).T))]
    t = np.arange(0, arc[-1] + 1e-9, step)
    if t[-1] < arc[-1] - 1e-6:
        t = np.r_[t, arc[-1]]
    return np.c_[np.interp(t, arc, xy[:, 0]), np.interp(t, arc, xy[:, 1])]


def smooth_centreline(pts: np.ndarray, rms: float = 0.12, n_out: int | None = None) -> np.ndarray:
    if len(pts) < 4:
        return pts
    k = 3 if len(pts) > 3 else len(pts) - 1
    tck, u = splprep([pts[:, 0], pts[:, 1]], s=len(pts) * rms ** 2, k=k)
    m = n_out or max(len(pts) * 4, 8)
    x, y = splev(np.linspace(0, 1, m), tck)
    return np.c_[x, y]


def trace(a: np.ndarray, seed: np.ndarray, stop_fn=None):
    """Full trace of one strand from a rough seed path. Returns dict."""
    pts, sig, amp, base, ok = refine(a, seed)
    # longest run of good fits with no sharp turn (a turn = jumped onto another hair)
    good = ok.copy()
    if len(pts) > 2:
        d1 = np.diff(pts, axis=0)
        ang = np.degrees(np.abs(np.arctan2(d1[1:, 0] * d1[:-1, 1] - d1[1:, 1] * d1[:-1, 0],
                                           (d1[1:] * d1[:-1]).sum(1))))
        good[1:-1] &= ang <= MAX_TURN
    runs, cur = [], []
    for i, g in enumerate(good):
        if g:
            cur.append(i)
        elif cur:
            runs.append(cur); cur = []
    if cur:
        runs.append(cur)
    if not runs or max(len(r) for r in runs) < 3:
        return None
    best = max(runs, key=len)
    pts, sig, amp, base = pts[best], sig[best], amp[best], base[best]
    tail, ti = extend(a, pts, stop_fn, True)
    head, hi = extend(a, pts, stop_fn, False)
    allp = np.vstack([head[::-1], pts, tail])
    s_all = np.r_[[i[0] for i in hi][::-1], sig, [i[0] for i in ti]]
    a_all = np.r_[[i[1] for i in hi][::-1], amp, [i[1] for i in ti]]
    b_all = np.r_[[i[2] for i in hi][::-1], base, [i[2] for i in ti]]
    cl = smooth_centreline(allp)
    arc_in = np.r_[0, np.cumsum(np.hypot(*np.diff(allp, axis=0).T))]
    arc_cl = np.r_[0, np.cumsum(np.hypot(*np.diff(cl, axis=0).T))]
    u_in = arc_in / max(arc_in[-1], 1e-9)
    u_cl = arc_cl / max(arc_cl[-1], 1e-9)
    s_all, a_all = deblur(np.asarray(s_all, float), np.asarray(a_all, float))
    width = np.interp(u_cl, u_in, ndi.median_filter(s_all, 3, mode="nearest"))
    opac = np.interp(u_cl, u_in, ndi.median_filter(a_all, 3, mode="nearest"))
    basel = np.interp(u_cl, u_in, b_all)
    return {"centreline": cl, "sigma": width, "opacity": np.clip(opac, 0, 1), "baseline": basel,
            "fit_points": allp, "length": float(arc_cl[-1]),
            "extended_px": [float(len(head) * STEP), float(len(tail) * STEP)]}


def render(shape, strands, pad: float = 4.0, ss: int = 4) -> np.ndarray:
    """Coverage rendered from traced strands (Gaussian cross profile, ss x ss
    sub-samples per pixel), combined as 1 - prod(1 - c_i)."""
    out_inv = np.ones(shape)
    for st in strands:
        cl, sg, op = st["centreline"], st["sigma"], st["opacity"]
        x0 = int(max(0, np.floor(cl[:, 0].min() - pad - 3 * sg.max())))
        x1 = int(min(shape[1], np.ceil(cl[:, 0].max() + pad + 3 * sg.max())))
        y0 = int(max(0, np.floor(cl[:, 1].min() - pad - 3 * sg.max())))
        y1 = int(min(shape[0], np.ceil(cl[:, 1].max() + pad + 3 * sg.max())))
        if x1 <= x0 or y1 <= y0:
            continue
        o = (np.arange(ss) + 0.5) / ss
        gx = (np.arange(x0, x1)[:, None] + o[None, :]).ravel()
        gy = (np.arange(y0, y1)[:, None] + o[None, :]).ravel()
        GX, GY = np.meshgrid(gx, gy)
        P = np.c_[GX.ravel(), GY.ravel()]
        seg_a, seg_b = cl[:-1], cl[1:]
        d = seg_b - seg_a
        L2 = (d ** 2).sum(1) + 1e-12
        best = np.full(len(P), np.inf); bi = np.zeros(len(P), int); bt = np.zeros(len(P))
        for i in range(0, len(seg_a), 64):
            A_, D_, L_ = seg_a[i:i + 64], d[i:i + 64], L2[i:i + 64]
            t = np.clip(((P[:, None, :] - A_[None]) * D_[None]).sum(2) / L_[None], 0, 1)
            q = A_[None] + t[..., None] * D_[None]
            dist = np.hypot(*(P[:, None, :] - q).transpose(2, 0, 1))
            j = dist.argmin(1)
            dm = dist[np.arange(len(P)), j]
            upd = dm < best
            best[upd] = dm[upd]; bi[upd] = i + j[upd]; bt[upd] = t[np.arange(len(P)), j][upd]
        sgp = sg[bi] * (1 - bt) + sg[np.minimum(bi + 1, len(sg) - 1)] * bt
        opp = op[bi] * (1 - bt) + op[np.minimum(bi + 1, len(op) - 1)] * bt
        c = opp * np.exp(-best ** 2 / (2 * sgp ** 2))
        c = c.reshape(len(gy), len(gx))
        c = c.reshape(y1 - y0, ss, x1 - x0, ss).mean(axis=(1, 3))
        out_inv[y0:y1, x0:x1] *= (1 - c)
    return 1 - out_inv


# ---------------------------------------------------------------- seeds ----
_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def skeleton_paths(mask: np.ndarray, min_len: int = 5) -> list[np.ndarray]:
    """Split a skeleton into hair paths: branches between end/junction points,
    joined straight through junctions where two branches continue each other
    (crossing hairs), short spurs dropped. Returns (x, y) pixel-centre paths."""
    from skimage.morphology import skeletonize
    sk = skeletonize(mask)
    pts = set(zip(*np.nonzero(sk)))
    if not pts:
        return []
    deg = {p: sum((p[0] + dy, p[1] + dx) in pts for dy, dx in _NB) for p in pts}
    node = {p for p, d in deg.items() if d != 2}
    branches, seen = [], set()
    for s in node:
        for dy, dx in _NB:
            q = (s[0] + dy, s[1] + dx)
            if q not in pts or (s, q) in seen:
                continue
            path, prev, cur = [s], s, q
            while True:
                path.append(cur)
                seen.add((prev, cur)); seen.add((cur, prev))
                if cur in node:
                    break
                nxt = [(cur[0] + dy2, cur[1] + dx2) for dy2, dx2 in _NB
                       if (cur[0] + dy2, cur[1] + dx2) in pts and (cur[0] + dy2, cur[1] + dx2) != prev]
                nxt = [n for n in nxt if (cur, n) not in seen]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
            branches.append(path)
    if not branches:                       # a closed loop or a single isolated path
        p0 = next(iter(pts)); return [np.array([[p0[1] + 0.5, p0[0] + 0.5]])]
    # join branches through junction clusters when they continue each other
    def end_dir(br, at_start):
        seq = br if at_start else br[::-1]
        k = min(6, len(seq) - 1)
        v = np.array([seq[k][1] - seq[0][1], seq[k][0] - seq[0][0]], float)
        return v / (np.linalg.norm(v) + 1e-9)
    ends = {}
    for i, br in enumerate(branches):
        for at_start in (True, False):
            p = br[0] if at_start else br[-1]
            if deg.get(p, 0) >= 3:
                ends.setdefault(p, []).append((i, at_start))
    # cluster adjacent junction pixels
    jn = list(ends)
    parent = {p: p for p in jn}
    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]; p = parent[p]
        return p
    for p in jn:
        for dy, dx in _NB:
            q = (p[0] + dy, p[1] + dx)
            if q in parent:
                parent[find(p)] = find(q)
    clusters = {}
    for p in jn:
        clusters.setdefault(find(p), []).extend(ends[p])
    link = {}
    for c, inc in clusters.items():
        inc = [e for e in inc if len(branches[e[0]]) >= 3]
        cand = []
        for a_i in range(len(inc)):
            for b_i in range(a_i + 1, len(inc)):
                (i, si), (j, sj) = inc[a_i], inc[b_i]
                if i == j:
                    continue
                d = float(np.dot(end_dir(branches[i], si), end_dir(branches[j], sj)))
                cand.append((d, inc[a_i], inc[b_i]))
        cand.sort()
        used = set()
        for d, e1, e2 in cand:
            if d > -0.8:
                break
            if e1 in used or e2 in used:
                continue
            used |= {e1, e2}; link[e1] = e2; link[e2] = e1
    out, done = [], set()
    for i in range(len(branches)):
        if i in done:
            continue
        # walk to one end of the chain
        cur, cur_start = i, True
        visited = {i}
        while (cur, cur_start) in link:
            j, sj = link[(cur, cur_start)]
            if j in visited:
                break
            visited.add(j); cur, cur_start = j, not sj
        chain, seq = [], []
        cur_end_is_start = cur_start
        while True:
            br = branches[cur]
            done.add(cur)
            piece = br if cur_end_is_start else br[::-1]
            seq.extend(piece if not seq else piece[1:])
            nxt = link.get((cur, not cur_end_is_start))
            if nxt is None or nxt[0] in done:
                break
            cur, cur_end_is_start = nxt[0], nxt[1]
        xy = np.array([[c + 0.5, r + 0.5] for r, c in seq], float)
        if len(xy) >= min_len:
            out.append(xy)
    return out


def straightness(cl: np.ndarray) -> float:
    arc = np.hypot(*np.diff(cl, axis=0).T).sum()
    return float(np.hypot(*(cl[-1] - cl[0])) / max(arc, 1e-9))


# ------------------------------------------------------- classification ----
WHISKER_LEN, WHISKER_STRAIGHT, WHISKER_OPAC = 40.0, 0.95, 0.40
WHISKER_LONG = 60.0    # px: long and straight enough to be a whisker at any opacity
WISP_REACH = 6.0       # px past the fur band's outer edge ("clearly past the fringe")
BLOB_SIGMA, MIN_LEN = 2.0, 6.0
EYE_PAD = 25           # px around each eye box: lashes, reserved for their own step


def classify(t: dict, eye_boxes: dict) -> str:
    med_sig = float(np.median(t["sigma"]))
    med_op = float(np.median(t["opacity"]))
    cl = t["centreline"]
    if med_sig > BLOB_SIGMA or t["length"] < MIN_LEN:
        return "not a hair (blob)"
    if t["length"] >= WHISKER_LEN and t["straight"] >= WHISKER_STRAIGHT and med_op >= WHISKER_OPAC:
        return "whisker (last step)"
    if t["length"] >= WHISKER_LONG and t["straight"] >= WHISKER_STRAIGHT:
        return "whisker (last step)"           # very long and straight: a whisker even if faint
    for (x0, y0, x1, y1) in eye_boxes.values():
        inside = ((cl[:, 0] > x0 - EYE_PAD) & (cl[:, 0] < x1 + EYE_PAD) &
                  (cl[:, 1] > y0 - EYE_PAD) & (cl[:, 1] < y1 + EYE_PAD))
        if inside.mean() > 0.5:
            return "lash (reserved)"
    if t["reach"] < WISP_REACH:
        return "fringe tip"
    return "wisp"


def dedupe(strands: list[dict], tol: float = 1.5, frac: float = 0.7) -> list[dict]:
    from scipy.spatial import cKDTree
    order = sorted(range(len(strands)), key=lambda i: -strands[i]["length"])
    kept = []
    for i in order:
        cl = strands[i]["centreline"]
        dup = False
        for k in kept:
            d = cKDTree(strands[k]["centreline"]).query(cl)[0]
            if (d < tol).mean() >= frac:
                dup = True
                break
        if not dup:
            kept.append(i)
    return [strands[i] for i in sorted(kept)]


def join(t1: dict, t2: dict) -> dict:
    """Join two traces of one hair split by a crossing: t1's far end to t2's
    near end, ordered so the gap is the shortest; centre, width and opacity
    carried across the gap linearly."""
    best = None
    for a_rev in (False, True):
        for b_rev in (False, True):
            A = t1["centreline"][::-1] if a_rev else t1["centreline"]
            B = t2["centreline"][::-1] if b_rev else t2["centreline"]
            g = float(np.hypot(*(A[-1] - B[0])))
            if best is None or g < best[0]:
                best = (g, a_rev, b_rev)
    g, a_rev, b_rev = best
    def o(t, rev):
        f = (lambda v: v[::-1]) if rev else (lambda v: v)
        return f(t["centreline"]), f(t["sigma"]), f(t["opacity"])
    A, sa, oa = o(t1, a_rev); B, sb, ob = o(t2, b_rev)
    n = max(int(g / 0.25), 2)
    gap = np.linspace(A[-1], B[0], n + 2)[1:-1]
    cl = np.vstack([A, gap, B])
    sg = np.r_[sa, np.linspace(sa[-1], sb[0], n + 2)[1:-1], sb]
    op = np.r_[oa, np.linspace(oa[-1], ob[0], n + 2)[1:-1], ob]
    out = dict(t1)
    out.update(centreline=cl, sigma=sg, opacity=op,
               length=float(np.hypot(*np.diff(cl, axis=0).T).sum()), straight=straightness(cl),
               reach=max(t1["reach"], t2["reach"]), joined_gap_px=round(g, 2))
    return out


# ------------------------------------------------------------ whiskers ----
W_HALF = 6.0          # px: wider cross profile for whiskers (room for neighbours)
W_KMAX = 3            # up to 3 ridges side by side
W_MAX_SHIFT = 0.8     # px sideways per step
W_TURN = 12.0         # deg max change of direction per step (whiskers are nearly straight)
W_COAST = 8.0         # px: carry straight on through a crossing for at most this far
W_INERTIA = 0.85      # direction smoothing


def fit_multi(a: np.ndarray, p: np.ndarray, n: np.ndarray, kmax: int = W_KMAX):
    """Fit b + sum_k A_k exp(-(s-c_k)^2/2s_k^2) across the strand with k = 1..kmax
    ridges; return the components of the model with the best BIC."""
    s = np.arange(-W_HALF, W_HALF + 1e-9, DS)
    f = sample(a, p[None, :] + s[:, None] * n[None, :])
    best = None
    for k in range(1, kmax + 1):
        peaks = s[np.argsort(-ndi.maximum_filter1d(f, 5) * (f == ndi.maximum_filter1d(f, 5)))][:k]
        c0 = np.sort(np.r_[peaks, np.linspace(-2, 2, k)][:k])
        q0, lo, hi = [float(np.percentile(f, 10))], [-0.05], [1.0]
        for c in c0:
            q0 += [c, 0.9, max(float(f.max() - q0[0]), 0.05)]
            lo += [-W_HALF + 0.3, SIG_MIN, 0.0]; hi += [W_HALF - 0.3, SIG_MAX, 1.2]

        def model(q):
            out = np.full_like(s, q[0])
            for i in range(k):
                c, sg, A = q[1 + 3 * i: 4 + 3 * i]
                out += A * np.exp(-((s - c) ** 2) / (2 * sg * sg))
            return out
        try:
            r = least_squares(lambda q: model(q) - f, q0, bounds=(lo, hi))
        except Exception:
            continue
        rss = float((r.fun ** 2).sum()) + 1e-9
        bic = len(s) * np.log(rss / len(s)) + (1 + 3 * k) * np.log(len(s))
        comps = [tuple(r.x[1 + 3 * i: 4 + 3 * i]) for i in range(k)]
        if best is None or bic < best[0] - 2.0:
            best = (bic, comps, float(r.x[0]))
    return None if best is None else (best[1], best[2])


def extend_whisker(a: np.ndarray, pts: np.ndarray, stop_fn=None, from_end: bool = True):
    """Extend one end of a whisker: follow the ridge nearest the predicted
    position even with neighbours alongside, and coast straight through
    crossings (at most W_COAST px). Coasted points at the very end are dropped."""
    seq = pts if from_end else pts[::-1]
    t = seq[-1] - seq[max(-10, -len(seq))]
    t = t / (np.linalg.norm(t) + 1e-12)
    p = seq[-1].copy()
    out, info, coast = [], [], 0.0
    for _ in range(int(MAX_EXTEND * 2 / STEP)):
        q = p + t * STEP
        if stop_fn is not None and stop_fn(q):
            break
        n = _normal(t)
        r = fit_multi(a, q, n)
        hit = None
        if r is not None:
            comps, b = r
            cands = [(abs(c), c, sg, A) for c, sg, A in comps if A >= A_MIN and abs(c) <= W_MAX_SHIFT]
            if cands:
                _, c, sg, A = min(cands)
                hit = (c, sg, A, b)
        if hit is None:
            coast += STEP
            if coast > W_COAST:
                break
            out.append(q); info.append((np.nan, np.nan, np.nan, True))
            p = q
            continue
        c, sg, A, b = hit
        q2 = q + c * n
        t_new = (q2 - p) / (np.linalg.norm(q2 - p) + 1e-12)
        if np.dot(t_new, t) < np.cos(np.radians(W_TURN)):
            coast += STEP
            if coast > W_COAST:
                break
            out.append(q); info.append((np.nan, np.nan, np.nan, True))
            p = q
            continue
        coast = 0.0
        t = W_INERTIA * t + (1 - W_INERTIA) * t_new
        t /= np.linalg.norm(t)
        out.append(q2); info.append((sg, A, b, False))
        p = q2
    while info and info[-1][3]:            # drop coasting at the very end
        out.pop(); info.pop()
    return np.array(out).reshape(-1, 2), info


def retrace_whisker(a: np.ndarray, centreline: np.ndarray, stop_fn=None):
    """Re-trace a whisker from its current centreline: refit the middle, then
    extend both ends with extend_whisker. Width/opacity are interpolated across
    coasted stretches. Returns a trace dict (like trace()) plus coasted_px."""
    pts, sig, amp, base, ok = refine(a, centreline[::2] if len(centreline) > 8 else centreline)
    keep = ok if ok.sum() >= 3 else np.ones(len(pts), bool)
    pts = pts[keep]
    sig = np.where(np.isnan(sig[keep]), np.nanmedian(sig), sig[keep])
    amp, base = amp[keep], base[keep]
    tail, ti = extend_whisker(a, pts, stop_fn, True)
    head, hi = extend_whisker(a, pts, stop_fn, False)
    allp = np.vstack([head[::-1], pts, tail])
    def col(info, k):
        return np.array([i[k] for i in info], float)
    s_all = np.r_[col(hi, 0)[::-1], sig, col(ti, 0)]
    a_all = np.r_[col(hi, 1)[::-1], amp, col(ti, 1)]
    coasted = np.r_[col(hi, 3)[::-1].astype(bool) if hi else np.zeros(0, bool), np.zeros(len(pts), bool),
                    col(ti, 3).astype(bool) if ti else np.zeros(0, bool)]
    idx = np.arange(len(s_all))
    good = ~np.isnan(s_all)
    s_all = np.interp(idx, idx[good], s_all[good]); a_all = np.interp(idx, idx[good], a_all[good])
    s_all, a_all = deblur(s_all, a_all)
    cl = smooth_centreline(allp, rms=0.15)
    arc_in = np.r_[0, np.cumsum(np.hypot(*np.diff(allp, axis=0).T))]
    arc_cl = np.r_[0, np.cumsum(np.hypot(*np.diff(cl, axis=0).T))]
    u_in = arc_in / max(arc_in[-1], 1e-9); u_cl = arc_cl / max(arc_cl[-1], 1e-9)
    return {"centreline": cl,
            "sigma": np.interp(u_cl, u_in, ndi.median_filter(s_all, 3, mode="nearest")),
            "opacity": np.clip(np.interp(u_cl, u_in, ndi.median_filter(a_all, 3, mode="nearest")), 0, 1),
            "length": float(arc_cl[-1]), "coasted_px": float(coasted.sum() * STEP),
            "extended_px": [float(len(head) * STEP), float(len(tail) * STEP)]}
