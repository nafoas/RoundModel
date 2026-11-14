"""Whisker step, part 2b: a second, stronger view for the faint face whiskers.

Owner (2026-11-13): "recalibrate the views you're using to try and increase the
contrast ... use a different method of highlighting them ... I don't wanna leave a
single whisker unaccounted for."

What was measured first (on the 9 face whiskers already traced, vs the fur beside
them): colour does not help (whiskers and fur differ only in brightness: R, G, B,
mean all give the same contrast; colour differences give ~0). What helps is
averaging ALONG the line: fur specks are short, whiskers are long.

The line view:
1. A bank of long thin line filters on the photo's grey: second derivative of a
   Gaussian across (sigma 2 px) times a long Gaussian along (sigma 14 px), at 36
   angles. Best scale of 12 tried: median whisker/fur ratio 2.27 (the old 2-px
   detail map: ~1.3), and much smoother along each whisker.
2. Direction: his whiskers sweep across each cheek in one family of directions.
   The expected direction at every point is the smoothed direction of the
   whiskers already traced (and the outside whiskers near their roots); only
   lines within 25 deg of it count, so fur streaks crossing the whiskers are
   ignored. Scores are in units of the fur's spread (robust, on his face fur).
3. The same whole-path search as part 2 (tools/face_whiskers.py) runs in this
   view from: every 5 px down six lines across both cheeks (both ways, joined),
   every 3 px along both cheek outlines, and every whisker root at his cheeks.
4. Acceptance: running (24 px) score >= 4 for >= 40 px, followed down to 3,
   ends at the change point against 2.5 (what a path through plain cheek fur
   scores, median 2.1).
5. Results: pieces that continue an already traced whisker (beyond either end)
   extend it; anything else is a candidate new whisker. Each candidate is also
   tested against identical searches started 8-20 px beside it (it must beat all
   of them), and measured on the photo (width, depth).
6. Candidates are judged one by one at full resolution (VERDICTS below: these
   are judgment calls, marked so, for the owner to overrule). A candidate not in
   the table is listed as "unsure" (owner).
"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.signal import fftconvolve
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_whiskers as fw  # noqa: E402

X0, Y0, X1, Y1 = 110, 480, 1010, 980     # face crop the bank is computed on
NA = 36                                  # filter angles
ACROSS, ALONG = 2.0, 14.0                # px: filter sigma across / along the line
DIR_TOL = np.radians(25.0)               # line must be within this of the whisker direction field
FIELD_SIGMA = 70.0                       # px: smoothing of the direction field
T_L, FAINT_L, H_L, MIN_L = 4.0, 3.0, 2.5, 40
EXT_MIN = 15                             # px: shortest extension piece kept
ATTACH = 6.0                             # px: an extension piece must start this close to the whisker's end
CONTINUE_ANGLE = 30.0                    # deg: and leave within this of the whisker's own direction there
BESIDE = (8.0, 12.0, 16.0, 20.0)         # px: offsets for the side-by-side test
TEST_LEN = 120.0

# Judgment calls on candidates (checked one by one at full resolution on the photo,
# the line view and the stand-out test). Keyed by the candidate's midpoint (px).
# verdict: "whisker" | "not a whisker" | "unsure" (owner decides).
WHISKER, UNCERTAIN = "whisker", "uncertain: owner sorts manually"
VERDICTS = [
    # owner, 2026-11-13: "Those are all whiskers" (L01-L07), then: "L05 does need more
    # scrutiny. But even I can't entirely tell. Put L05 and similar grey areas into
    # their own classification that I'll sort out manually later."
    ((236.0, 767.0), None, WHISKER, "found from the shared root of his right-side fan; beats every search beside it by 1.9"),
    ((245.0, 722.0), None, WHISKER, "faint line on the photo; beats every search beside it by 1.3"),
    ((216.0, 839.0), None, WHISKER, "faint straight line on the photo; beats every search beside it by 2.5"),
    ((193.0, 777.0), "L01", WHISKER, "L01: owner, 2026-11-13"),
    ((338.0, 856.0), "L02", WHISKER, "L02: owner, 2026-11-13"),
    ((299.0, 925.0), "L03", WHISKER, "L03: owner, 2026-11-13"),
    ((817.0, 594.0), "L04", WHISKER, "L04: owner, 2026-11-13"),
    ((931.0, 701.0), "L05", WHISKER, "L05: owner, 2026-11-14 (\"I think they're all whiskers\"; first: "
     "\"even I can't entirely tell\")"),
    ((687.0, 851.0), "L06", WHISKER, "L06: owner, 2026-11-13"),
    ((827.0, 851.0), "L07", WHISKER, "L07: owner, 2026-11-13"),
]
VERDICT_DIST = 18.0


def kernel(th: float) -> np.ndarray:
    h = int(np.ceil(3 * max(ALONG, ACROSS * 3)))
    y, x = np.mgrid[-h:h + 1, -h:h + 1].astype(float)
    u = x * np.cos(th) + y * np.sin(th)
    v = -x * np.sin(th) + y * np.cos(th)
    g = np.exp(-u * u / (2 * ALONG ** 2)) * np.exp(-v * v / (2 * ACROSS ** 2))
    k = g * (v * v / ACROSS ** 4 - 1 / ACROSS ** 2)       # positive for a dark line
    k -= k.mean(); k /= np.abs(k).sum()
    return k


def bank(img: np.ndarray) -> np.ndarray:
    return np.stack([fftconvolve(img, kernel(th), mode="same") for th in np.arange(NA) * np.pi / NA])


def direction_field(lines: list[np.ndarray], shape) -> np.ndarray:
    """expected whisker orientation (mod pi) at every pixel of the crop, from lines (image px)"""
    H, W = shape
    C = np.zeros((H, W)); Sn = np.zeros((H, W))
    for q in lines:
        q = fw.dense(q)
        if len(q) < 3:
            continue
        t = np.gradient(q, axis=0); a = np.arctan2(t[:, 1], t[:, 0])
        for (x, y), aa in zip(q[::3] - [X0, Y0], a[::3]):
            xi, yi = int(x), int(y)
            if 0 <= xi < W and 0 <= yi < H:
                C[yi, xi] += np.cos(2 * aa); Sn[yi, xi] += np.sin(2 * aa)
    C = ndi.gaussian_filter(C, FIELD_SIGMA); Sn = ndi.gaussian_filter(Sn, FIELD_SIGMA)
    return 0.5 * np.arctan2(Sn, C)


def field_lines(face_whiskers: list[dict], F: fw.Face) -> list[np.ndarray]:
    lines = [np.array(w["centreline"]) for w in face_whiskers]
    data = json.loads((fw.ROOT / "data/strands/wisps.json").read_text())
    for t in data["strands"]:       # outside whiskers near their roots anchor the field round his cheeks
        if t["class"].startswith("whisker"):
            cl = np.array(t["centreline"], float)
            seq = cl if abs(F.sdist(cl[0])) < abs(F.sdist(cl[-1])) else cl[::-1]
            lines.append(fw.dense(seq)[:40])
    return lines


class LineView(fw.Face):
    """fw.Face whose line measure is the long-filter bank along the whisker direction field"""

    def __init__(self, lines: list[np.ndarray] | None = None, **kw):
        super().__init__(**kw)
        g = self.grey[Y0:Y1, X0:X1]
        R = bank(g)
        H, W = g.shape
        yy, xx = np.mgrid[0:H, 0:W] + 0.5
        P = np.stack([xx + X0, yy + Y0], -1)
        face = (self.sdist(P) >= 14) & self.valid(P)
        vals = R[:, face]
        s = 1.4826 * np.median(np.abs(vals - np.median(vals)))
        self.Z = np.concatenate([R, R[:1]], 0) / s            # angle axis wraps
        if lines is None:
            lines = field_lines(json.loads((fw.ROOT / "data/strands/face_whiskers.json").read_text())["whiskers"], self)
        self.theta = direction_field(lines, (H, W))
        self.best = R.max(0) / s                              # for the owner's view
        self.best_angle = R.argmax(0) * np.pi / NA

    def contrast(self, P, t):
        ang = np.mod(np.arctan2(t[..., 1], t[..., 0]), np.pi)
        k = ang / (np.pi / NA)
        y = P[..., 1] - Y0 - 0.5; x = P[..., 0] - X0 - 0.5
        v = ndi.map_coordinates(self.Z, [k.ravel(), y.ravel(), x.ravel()], order=1, mode="constant",
                                cval=0.0).reshape(P.shape[:-1])
        th = ndi.map_coordinates(self.theta, [y.ravel(), x.ravel()], order=1, mode="nearest").reshape(P.shape[:-1])
        dd = np.abs(((ang - th + np.pi / 2) % np.pi) - np.pi / 2)
        return np.where(dd <= DIR_TOL, v, np.minimum(v, 0.0))

    def along_view(self):
        """owner's view: best line response along the whisker directions (crop coordinates)"""
        TH = np.arange(NA) * np.pi / NA
        dth = np.abs(((TH[:, None, None] - self.theta[None] + np.pi / 2) % np.pi) - np.pi / 2)
        return np.where(dth <= DIR_TOL, self.Z[:NA], -np.inf).max(0)


# ---------------------------------------------------------------- sweep (parallel)
_L: LineView | None = None


VIEW = None          # view class for the workers (default LineView; part 2c sets its own)


def _init(lines):
    global _L
    _L = (VIEW or LineView)(lines)


def _job(a):
    kind, p, th = a
    if kind == "interior":
        r0 = _L.search(np.array(p), th, length=320, k0max=0.7, kmax=1.0)
        r1 = _L.search(np.array(p), th + np.pi, length=320, k0max=0.7, kmax=1.0)
        q = np.vstack([fw.dense(r1)[::-1], fw.dense(r0)[1:]])
    else:
        q = _L.search(np.array(p), th, length=360, k0max=0.7 if kind == "outline" else 0.5,
                      kmax=1.0 if kind == "outline" else 0.7)
    qd, c = _L.line_profile(q)
    return dict(kind=kind, start=np.array(p, float), q=qd, c=c)


def _job_test(a):
    p, th, L = a
    r0 = _L.search(np.array(p), th, length=L / 2, k0max=0.1, kstep=1, c0=0.0)
    r1 = _L.search(np.array(p), th + np.pi, length=L / 2, k0max=0.1, kstep=1, c0=0.0)
    q = np.vstack([fw.dense(r1)[::-1], fw.dense(r0)[1:]])
    _, c = _L.line_profile(q)
    return float(np.nanmean(np.nan_to_num(c)))


def starts(F: fw.Face):
    jobs = [("interior", (float(x), float(y)), 0.0) for x in fw.INTERIOR_X
            for y in np.arange(fw.INTERIOR_Y[0], fw.INTERIOR_Y[1] + 1, fw.INTERIOR_Y[2])]
    jobs += [("outline", tuple(p), th) for p, th in fw.sweep_starts(F)]
    data = json.loads((fw.ROOT / "data/strands/wisps.json").read_text())
    for t in data["strands"]:
        if t["class"].startswith("whisker"):
            p, th, dist = fw.root_end(np.array(t["centreline"], float), F)
            if dist <= fw.CONT_ROOT_DIST and fw.CONT_Y[0] <= p[1] <= fw.CONT_Y[1]:
                jobs.append(("root:" + t["id"], tuple(p), th))
    return jobs


def segments(r):
    q, c = r["q"], r["c"]
    if len(q) < MIN_L:
        return []
    wv = fw.windowed(c); cc = np.nan_to_num(c); out = []
    faint = fw.chains(wv, FAINT_L)
    for a, b in [ab for ab in fw.chains(wv, T_L) if ab[1] - ab[0] >= MIN_L]:
        fa = [f for f in faint if f[0] <= a and f[1] >= b]
        a2, b2 = fa[0] if fa else (a, b)
        e = a2 + int(np.argmax(np.cumsum(cc[a2:] - H_L)))
        s = e - int(np.argmax(np.cumsum((cc[:e + 1] - H_L)[::-1])))
        if r["kind"].startswith("root:"):
            s = min(s, a2)
        if e - s >= MIN_L:
            out.append((s, e))
    return out


def classify(found: list[dict], whiskers: list[dict]):
    traced = {w["id"]: fw.dense(np.array(w["centreline"])) for w in whiskers}
    trees = {k: cKDTree(v) for k, v in traced.items()}
    ext, new = {}, []
    for r in found:
        for s, e in segments(r):
            seg = r["q"][s:e + 1]
            hit = None
            for k, t in trees.items():
                dd = t.query(seg)[0]
                if (dd <= 2.5).mean() >= 0.3 or (dd <= 2.5).sum() >= 40:
                    hit = (k, dd); break
            if not hit:
                new.append(dict(seg=seg, kind=r["kind"], start=r["start"],
                                score=float(np.mean(np.nan_to_num(r["c"][s:e + 1])))))
                continue
            k, dd = hit
            idx = np.flatnonzero(dd > 2.5)
            if len(idx) == 0:
                continue
            tr = traced[k]
            for rr in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1):
                if len(rr) < EXT_MIN:
                    continue
                piece = seg[rr[0]:rr[-1] + 1]
                d_nose = min(np.hypot(*(piece[0] - tr[-1])), np.hypot(*(piece[-1] - tr[-1])))
                d_out = min(np.hypot(*(piece[0] - tr[0])), np.hypot(*(piece[-1] - tr[0])))
                if min(d_nose, d_out) > ATTACH:
                    continue
                side = "nose" if d_nose < d_out else "outline"
                end = tr[-1] if side == "nose" else tr[0]
                if np.hypot(*(piece[0] - end)) > np.hypot(*(piece[-1] - end)):
                    piece = piece[::-1]                  # every piece runs away from the whisker
                # it must CONTINUE the whisker: leave in the whisker's own direction at that end
                # (a piece that branches off near an end and runs back along it is another line)
                cur = tr if side == "nose" else tr[::-1]
                t_w = cur[-1] - cur[-min(11, len(cur))]
                t_p = piece[min(10, len(piece) - 1)] - piece[0]
                cosang = float(t_w @ t_p) / (np.linalg.norm(t_w) * np.linalg.norm(t_p) + 1e-9)
                if cosang < np.cos(np.radians(CONTINUE_ANGLE)):
                    continue
                if (k, side) not in ext or len(piece) > len(ext[(k, side)]):
                    ext[(k, side)] = piece
    # new lines: one per line (longest find), and not a line already traced or extended
    allk = [np.vstack([traced[k]] + [p for (kk, _), p in ext.items() if kk == k]) for k in traced]
    new.sort(key=lambda c: -len(c["seg"]))
    kept = []
    for c in new:
        if any(fw.overlap(c["seg"], a, 2.5) >= 0.5 for a in allk):
            continue
        if all(fw.overlap(c["seg"], k_["seg"], 2.5) < 0.4 for k_ in kept):
            kept.append(c)
    return ext, kept


def standout(F: fw.Face, cands: list[dict], procs: int, lines):
    """margin of each candidate over identical searches started beside it (starts in the fur band skipped)"""
    from multiprocessing import Pool
    jobs, meta = [], []
    for i, c in enumerate(cands):
        q = fw.dense(c["seg"]); m = q[len(q) // 2]
        t = q[min(len(q) - 1, len(q) // 2 + 10)] - q[max(0, len(q) // 2 - 10)]; t /= np.linalg.norm(t)
        n = np.array([-t[1], t[0]]); L = float(min(len(q), TEST_LEN))
        for o in (0.0,) + tuple(s * b for b in BESIDE for s in (-1, 1)):
            p = m + o * n
            if o and (F.sdist(p) < fw.BAND or not F.valid(p[None, None])[0, 0]):
                continue
            jobs.append((tuple(p), float(np.arctan2(t[1], t[0])), L)); meta.append((i, o))
    from multiprocessing import Pool
    with Pool(procs, initializer=_init, initargs=(lines,)) as pool:
        res = list(pool.imap(_job_test, jobs, chunksize=3))
    for i, c in enumerate(cands):
        own = [r for (j, o), r in zip(meta, res) if j == i and o == 0]
        oth = [r for (j, o), r in zip(meta, res) if j == i and o != 0]
        c["line_score"] = own[0]
        c["beside_max"] = max(oth) if oth else float("nan")
        c["margin"] = own[0] - max(oth) if oth else float("nan")


def verdict(c):
    q = fw.dense(c["seg"]); m = q[len(q) // 2]
    best = None
    for (x, y), lid, v, why in VERDICTS:
        d = float(np.hypot(m[0] - x, m[1] - y))
        if d <= VERDICT_DIST and (best is None or d < best[0]):
            best = (d, lid, v, why)
    if best:
        c["lid"] = best[1]
        return best[2], best[3]
    c["lid"] = None
    return UNCERTAIN, "not yet judged"


def run(F: fw.Face, doc: dict, cache: Path | None = None, procs: int = 4):
    from multiprocessing import Pool
    lines = field_lines(doc["whiskers"], F)
    if cache and cache.exists():
        found = pickle.loads(cache.read_bytes())
    else:
        with Pool(procs, initializer=_init, initargs=(lines,)) as pool:
            found = list(pool.imap(_job, starts(F), chunksize=4))
        if cache:
            cache.write_bytes(pickle.dumps(found))
    ext, cands = classify(found, doc["whiskers"])
    standout(F, cands, procs, lines)
    G = F
    for c in cands:
        pts, sg, dep, ok = G.refine(fw.dense(c["seg"]))
        c["sigma"] = float(np.nanmedian(sg[ok])) if ok.any() else float("nan")
        c["depth"] = float(np.median(dep[ok])) if ok.any() else float("nan")
        c["verdict"], c["reason"] = verdict(c)
    return ext, cands, lines


def fit_line(F: fw.Face, base: np.ndarray):
    """sub-pixel line through base (photo fits + spline), as in part 2"""
    base = fw.dense(base)
    pts, sig, dep, ok = F.refine(base, resample=False)
    cl = fw.smooth_line(base, pts, np.where(ok, np.clip(dep, 0, None), 0.0))
    return cl, sig, dep, ok


def apply(F: fw.Face, doc: dict, ext: dict, cands: list[dict], prev_doc: dict | None = None):
    """extend whiskers, add accepted new whiskers, list the rest; updates doc in place"""
    W = {w["id"]: w for w in doc["whiskers"]}
    for (k, side), piece in ext.items():
        w = W[k]; cl = np.array(w["centreline"])
        base = np.vstack([cl, piece]) if side == "nose" else np.vstack([piece[::-1], cl])
        new_cl, sig, dep, ok = fit_line(F, base)
        w.setdefault("line_view_extension_px", {})[side] = int(len(piece))
        w["centreline"] = np.round(new_cl, 2).tolist()
        w["sigma"] = np.round(sig, 2).tolist(); w["depth_grey"] = np.round(dep, 1).tolist()
        if side == "outline" and len(w["inferred_entry"]) > 1:
            en = np.array(w["inferred_entry"])
            j = int(np.argmin(np.hypot(*(en - new_cl[0]).T)))
            en = np.vstack([en[:j + 1], new_cl[:1]]) if j > 0 else np.zeros((0, 2))
            w["inferred_entry"] = np.round(en, 2).tolist()
            w["inferred_entry_px"] = round(float(np.hypot(*np.diff(en, axis=0).T).sum()) if len(en) > 1 else 0.0, 1)
    # new whiskers (judged "whisker"): stable names from the saved data where the same line was there before
    prev = [(w_["id"], np.array(w_["centreline"])) for w_ in (prev_doc or {}).get("whiskers", [])
            if w_["id"].startswith("FW-")]
    taken = {w["id"] for w in doc["whiskers"]}
    n = max([int(i[3:]) for i in taken | {i for i, _ in prev} if i.startswith("FW-")] or [0])
    listed = []
    for c in sorted(cands, key=lambda c: (c["seg"][:, 0].mean() > 549, c["seg"][:, 1].mean())):
        c["id"] = None
        if c["verdict"] != WHISKER:
            listed.append(c); continue
        cl, sig, dep, ok = fit_line(F, c["seg"])
        if F.sdist(cl[0]) > F.sdist(cl[-1]):
            cl, sig, dep, ok = cl[::-1], sig[::-1], dep[::-1], ok[::-1]
        same = [i for i, p in prev if i not in taken and fw.overlap(cl, p) >= 0.5]
        if same:
            fid = same[0]
        else:
            n += 1; fid = f"FW-{n:02d}"
        taken.add(fid); c["id"] = fid
        doc["whiskers"].append(dict(
            id=fid, kind="face only (line view)", found_as=c["lid"],
            owner_confirmed=bool(c["lid"]),
            continues=c["kind"][5:] if c["kind"].startswith("root:") else None,
            length_px=round(float(np.hypot(*np.diff(cl, axis=0).T).sum()), 1), inferred_entry_px=0.0,
            median_line_contrast=round(c["score"], 2),
            median_depth_grey=round(float(np.median(dep[ok])) if ok.any() else float("nan"), 1),
            median_sigma_px=round(float(np.nanmedian(sig[ok])) if ok.any() else float("nan"), 2),
            line_view_margin=round(c["margin"], 2), judgment=c["reason"],
            status="judgment call (line view), checked at full resolution; owner review pending",
            weight=0, centreline=np.round(cl, 2).tolist(), sigma=np.round(sig, 2).tolist(),
            depth_grey=np.round(dep, 1).tolist(), inferred_entry=[]))
        if c["kind"].startswith("root:"):
            doc["notes"].append(f"{fid}: found by a search from the root end of {c['kind'][5:]} (his right-side "
                                f"fan shares one root, so it may be any of B4-S12/S15/S17): owner review")
    nl = max([int(c["lid"][1:]) for c in cands if c.get("lid")] or [0])
    for c in listed:
        if not c.get("lid"):
            nl += 1; c["lid"] = f"L{nl:02d}"
    doc["line_view_candidates"] = [dict(
        id=c["lid"], verdict=c["verdict"], reason=c["reason"], margin=round(c["margin"], 2),
        line_score=round(c["line_score"], 2), sigma_px=round(c["sigma"], 2), depth_grey=round(c["depth"], 1),
        points=np.round(fw.dense(c["seg"]), 1)[::4].tolist()) for c in listed]
    doc["line_view"] = dict(
        about=__doc__.split("\n\n")[0],
        filters=dict(angles=NA, across_sigma_px=ACROSS, along_sigma_px=ALONG, direction_tolerance_deg=25,
                     field_sigma_px=FIELD_SIGMA),
        acceptance=dict(accept=T_L, follow=FAINT_L, end_level=H_L, min_len_px=MIN_L, units="fur spread"),
        extensions={f"{k}/{s}": int(len(p)) for (k, s), p in ext.items()},
    )
    # footprints and accounting
    for w in doc["whiskers"]:
        cl = np.array(w["centreline"]); sg = np.nan_to_num(np.array(w["sigma"], float), nan=1.0)
        lo_ = np.floor(cl.min(0) - 6).astype(int); hi_ = np.ceil(cl.max(0) + 6).astype(int)
        gx, gy = np.meshgrid(np.arange(lo_[0], hi_[0]) + 0.5, np.arange(lo_[1], hi_[1]) + 0.5)
        dd, ii = cKDTree(cl).query(np.c_[gx.ravel(), gy.ravel()])
        w["footprint_px"] = int((dd <= np.maximum(2 * sg[ii], 1.0)).sum())
        w["length_px"] = round(float(np.hypot(*np.diff(cl, axis=0).T).sum()), 1)
    doc["accounting"]["face_whisker_pixels"] = int(sum(w["footprint_px"] for w in doc["whiskers"]))
    return doc
