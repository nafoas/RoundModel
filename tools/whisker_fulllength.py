"""Whisker step, part 2c: every face whisker, its whole length.

Owner, 2026-11-13: "a lot of them are missing segments. Try again but be more
rigorous - look up and down from where they are to get the whole outline, and
look for fainter traces. Try other combinations of color and contrast to see if
anything makes the whiskers stand out."

Colour and contrast, measured on every known face whisker (12 traced + L01-L07)
against his face fur, along the whisker directions (AUC: chance 0.5, perfect 1):
- brightness channels (R, G, B, mean, luma, Lab L, min, max): all ~0.988;
- colour channels (Lab a/b, chroma, saturation, B-R, G-B): 0.50-0.70, no use:
  his whiskers and his fur are the same colour;
- the best linear mix of R, G, B (Fisher): 0.981, no better than plain grey;
- gamma / log stretches: no better.
On the FAINTEST quarter of whisker points (the ones that matter here):
- current line view (grey, filter 2 x 14 px): 0.959;
- contrast evened out first (grey minus its 12 px local mean, divided by its
  12 px local spread: his lit and shadowed sides become alike), filter 2 x 24 px:
  0.965;
- the average of the two (the COMBINED view used here): 0.969 (0.991 overall).

Then, in the combined view:
1. The cheek-wide sweep again (fainter traces): pieces beyond a whisker's ends
   extend it; other lines are candidates.
2. Every whisker is followed from both ends, round after round: a whole-path
   search from the end in the whisker's own direction (+-6 deg, smooth arcs,
   <= 0.45 deg/px), paying FOLLOW_COST per px, so it ends where going on no
   longer pays, and it bridges a faint gap when the line shows again after it
   (gaps of plain fur longer than MAX_GAP px are cut). A piece is kept only if
   it beats identical searches started 8-20 px beside it (same length, same
   constraints) by MARGIN, and is on average above the fur.
3. A piece that runs into the end of another whisker (<= JOIN_DIST px, same
   direction) joins the two: one whisker in two pieces was one whisker. A
   face-only whisker that reaches his fur band is linked to the outside whisker
   whose root end is there (same direction).
Candidates are judged one by one at full resolution (FULL_VERDICTS); anything I
can't call goes to "uncertain: owner sorts manually" (owner's class for grey areas).
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
import whisker_lineview as lv  # noqa: E402

LN_SIGMA = 12.0                 # px: local mean/spread for evening out the contrast
ALONG_B = 24.0                  # px: filter length on the evened-out grey
FOLLOW_COST = 2.5               # per px, fur-spread units: above what a SEARCHED path through plain fur scores (~2.1), as the sweep's end level
FOLLOW_LEN, FOLLOW_K0, FOLLOW_KSTEP, FOLLOW_YMAX = 200.0, 0.10, 2, 30.0
MARGIN, MIN_MEAN, MIN_PIECE, MAX_GAP = 0.94, 2.0, 10, 40
# MARGIN calibrated on plain fur: the same test from 75 random cheek starts (>= 12 px from any known
# whisker or candidate, along the whisker directions, 40-120 px) gives margins median -0.63,
# 90th pct 0.50, 95th pct 0.94, max 1.52. So a piece must beat what fur reaches 95% of the time.
FUR_RUN = 1.0                   # running contrast below this = plain fur (for the gap rule)
ROUNDS = 5
JOIN_DIST, JOIN_ANGLE = 5.0, 25.0
LINK_DIST, LINK_ANGLE = 15.0, 35.0

# Owner, 2026-11-14: "I think they're all whiskers. And the ones that connect to another whisker
# are, as far as I know, part of the same whisker ... they are all emanating from his little
# whisker pads ... pointing towards the whisker pads, and they are all straight ... Some of them
# are genuinely faint, and we shouldn't artificially make them more prominent in the photo - but
# we shouldn't forget them either."
OWNER_SAYS = "owner, 2026-11-14: \"I think they're all whiskers\""
FULL_VERDICTS: list = [                 # (midpoint, verdict, reason): candidates found by this pass
    ((311.0, 574.0), lv.WHISKER, "L08: " + OWNER_SAYS),
    ((434.0, 828.0), lv.WHISKER, "L09: " + OWNER_SAYS),
    ((913.0, 726.0), lv.WHISKER, "L10: " + OWNER_SAYS),
    ((906.0, 789.0), lv.WHISKER, "L11: " + OWNER_SAYS),
]
# possible continuations the owner says are part of the same whisker (L12-L19): added whatever the test says
OWNER_CONTINUATIONS = [                  # matched by where the piece is (its midpoint), never by a whisker name
    ((431.0, 673.0), "L12"), ((287.0, 789.0), "L13"), ((303.0, 731.0), "L14"), ((772.0, 712.0), "L15"),
    ((767.0, 768.0), "L16"), ((727.0, 628.0), "L17"), ((717.0, 801.0), "L18"), ((803.0, 702.0), "L19"),
]


def owner_continuation(piece):
    q = fw.dense(piece); m = q[len(q) // 2]
    hit = [lid for (x, y), lid in OWNER_CONTINUATIONS if np.hypot(m[0] - x, m[1] - y) <= lv.VERDICT_DIST]
    return hit[0] if hit else None
STRAIGHT_DEG = 2                         # owner-confirmed joins: the whole whisker as one gentle arc


def bank2(img, across, along):
    out = []
    for th in np.arange(lv.NA) * np.pi / lv.NA:
        h = int(np.ceil(3 * max(along, across * 3)))
        y, x = np.mgrid[-h:h + 1, -h:h + 1].astype(float)
        u = x * np.cos(th) + y * np.sin(th); v = -x * np.sin(th) + y * np.cos(th)
        g = np.exp(-u * u / (2 * along ** 2)) * np.exp(-v * v / (2 * across ** 2))
        k = g * (v * v / across ** 4 - 1 / across ** 2); k -= k.mean(); k /= np.abs(k).sum()
        out.append(fftconvolve(img, k, mode="same"))
    return np.stack(out)


class CombinedView(lv.LineView):
    """average of the line view and the same on contrast-evened grey with a longer filter"""

    def __init__(self, lines=None, **kw):
        super().__init__(lines, **kw)
        g = self.grey[lv.Y0:lv.Y1, lv.X0:lv.X1]
        m = ndi.gaussian_filter(g, LN_SIGMA)
        sd = np.sqrt(ndi.gaussian_filter((g - m) ** 2, LN_SIGMA) + 1e-6)
        R = bank2((g - m) / sd, lv.ACROSS, ALONG_B)
        H, W = g.shape
        yy, xx = np.mgrid[0:H, 0:W] + 0.5
        P = np.stack([xx + lv.X0, yy + lv.Y0], -1)
        face = (self.sdist(P) >= 14) & self.valid(P)
        vals = R[:, face]
        s = 1.4826 * np.median(np.abs(vals - np.median(vals)))
        self.Z = 0.5 * (self.Z + np.concatenate([R, R[:1]], 0) / s)


# ---------------------------------------------------------------- following (parallel)
def _follow(a):
    wid, side, p, th, band_rule = a
    V = lv._L
    path = V.search(np.array(p), th, length=FOLLOW_LEN, k0max=FOLLOW_K0, kstep=FOLLOW_KSTEP,
                    c0=FOLLOW_COST, band_rule=band_rule, ymax=FOLLOW_YMAX)
    q = fw.dense(path)
    if len(q) < 3:
        return wid, side, q, np.zeros(len(q))
    if not band_rule:                    # outline side: stop at the fur band (the outside whisker takes over)
        st = np.flatnonzero(V.sdist(q) < fw.NEAR_OUTLINE)
        if len(st):
            q = q[:max(st[0], 1)]
    _, c = V.line_profile(q) if len(q) >= 3 else (q, np.zeros(len(q)))
    return wid, side, q, np.nan_to_num(c)


def _fixed(a):
    """mean score of the best path of exactly this length from p (no cost per px)"""
    p, th, L, band_rule = a
    V = lv._L
    path = V.search(np.array(p), th, length=L + fw.DX, k0max=FOLLOW_K0, kstep=FOLLOW_KSTEP, c0=-50.0,
                    band_rule=band_rule, ymax=FOLLOW_YMAX)
    q = fw.dense(path)[:int(L)]
    if len(q) < 3:
        return -np.inf, q
    _, c = V.line_profile(q)
    return float(np.mean(np.nan_to_num(c))), q


ON_OTHER = 0.3                  # a beside search lying this much on another known whisker is not "fur beside it"


def beside_margins(F, pool, items, doc=None, ids=None):
    """items: (start, direction, length, band_rule). Returns (margin over the best of the searches
    started 8-20 px beside, own score) per item; all searches identical (fixed length, no cost).
    Beside searches that run along ANOTHER known whisker are left out: whiskers converge toward
    his whisker pads, and the test is against the fur beside it, not against a neighbour."""
    trees = {}
    if doc is not None:
        pts = [(w["id"], fw.dense(np.array(w["centreline"]))) for w in doc["whiskers"]]
        for k in set(ids or []):
            o = [q for i_, q in pts if i_ != k]
            trees[k] = cKDTree(np.vstack(o)) if o else None
    tests, meta = [], []
    for i, (p, th, L, br) in enumerate(items):
        n = np.array([-np.sin(th), np.cos(th)])
        for o in (0.0,) + tuple(s * b for b in lv.BESIDE for s in (-1, 1)):
            pp = np.array(p) + o * n
            if o and (F.sdist(pp) < fw.BAND or not F.valid(pp[None, None])[0, 0]):
                continue
            tests.append((tuple(pp), th, L, br)); meta.append((i, o))
    res = pool.map(_fixed, tests)
    out = []
    for i in range(len(items)):
        tr = trees.get(ids[i]) if ids else None
        own = [v for (j, o), (v, q) in zip(meta, res) if j == i and o == 0]
        oth = [v for (j, o), (v, q) in zip(meta, res) if j == i and o != 0
               and not (tr is not None and len(q) and (tr.query(q)[0] <= 3.0).mean() >= ON_OTHER)]
        # no beside-search left (all on neighbouring whiskers or in the fur band): untestable, None
        out.append(((own[0] - max(oth)) if (own and oth) else (None if own else -np.inf), own[0] if own else -np.inf))
    return out


def on_other(doc, wid, q):
    """fraction of piece q lying within 3 px of a whisker other than wid (a jump onto a neighbour)"""
    o = [fw.dense(np.array(w["centreline"])) for w in doc["whiskers"] if w["id"] != wid]
    if not o or len(q) == 0:
        return 0.0
    return float((cKDTree(np.vstack(o)).query(q)[0] <= 3.0).mean())


def trim_gap(q, c):
    """cut the piece at the first stretch of plain fur longer than MAX_GAP px"""
    wv = fw.windowed(c)
    low = np.where(np.isnan(wv), True, wv < FUR_RUN)
    run = 0
    for i, l in enumerate(low):
        run = run + 1 if l else 0
        if run > MAX_GAP:
            return q[:max(0, i - run + 1)], c[:max(0, i - run + 1)]
    return q, c


def ends(w):
    cl = fw.dense(np.array(w["centreline"]))
    out = {}
    for side, cur in (("nose", cl), ("outline", cl[::-1])):
        d = cur[-1] - cur[-min(11, len(cur))]
        out[side] = (cur[-1], float(np.arctan2(d[1], d[0])))
    return out


def follow_round(F, doc, pool, done):
    jobs = []
    for w in doc["whiskers"]:
        for side, (p, th) in ends(w).items():
            if (w["id"], side) in done:
                continue
            if side == "outline" and F.sdist(p) < fw.NEAR_OUTLINE + 3:
                done.add((w["id"], side)); continue
            jobs.append((w["id"], side, tuple(p), th, side == "nose"))
    res = pool.map(_follow, jobs)
    pieces = []
    for (wid, side, p, th, br), (_, _, q, c) in zip(jobs, res):
        q, c = trim_gap(q[1:], c[1:]) if len(q) > 1 else (q, c)
        if len(q) < MIN_PIECE or np.mean(c) < MIN_MEAN:
            done.add((wid, side)); continue
        pieces.append((wid, side, q, c, p, th, br))
    margins = beside_margins(F, pool, [(p, th, float(len(q)), br) for wid, side, q, c, p, th, br in pieces],
                             doc, [pc[0] for pc in pieces])
    accepted = []
    for (wid, side, q, c, p, th, br), (m, own) in zip(pieces, margins):
        if m is not None and m >= MARGIN:
            accepted.append((wid, side, q, round(float(m), 2)))
        else:
            done.add((wid, side))
    return accepted


MAX_TURN = 3.0                  # deg per px: a whisker never bends this sharply (traced ones: <= 1.7)


def max_turn(cl):
    t = np.gradient(fw.dense(cl), axis=0)
    a = np.unwrap(np.arctan2(t[:, 1], t[:, 0]))
    return float(np.degrees(np.abs(np.diff(a))).max()) if len(a) > 2 else 0.0


def smooth_whole(F, base):
    """one smooth curve through the whole whisker (owner: whiskers are straight): photo fits at
    every px, then a weighted polynomial of degree STRAIGHT_DEG along its main axis"""
    base = fw.dense(base)
    pts, sig, dep, ok = F.refine(base, resample=False)
    w = np.where(ok, np.clip(dep, 0, None), 0.0) + 1e-3
    c0 = pts.mean(0); u, sv, vt = np.linalg.svd(pts - c0, full_matrices=False)
    ax = vt[0]; nx = np.array([-ax[1], ax[0]])
    s_ = (pts - c0) @ ax; t_ = (pts - c0) @ nx
    coef = np.polyfit(s_, t_, STRAIGHT_DEG, w=np.sqrt(w))
    sb = (base - c0) @ ax
    cl = c0 + sb[:, None] * ax + np.polyval(coef, sb)[:, None] * nx
    return cl, sig, dep, ok, float(np.sqrt(np.average((t_ - np.polyval(coef, s_)) ** 2, weights=w)))


def grow(F, w, side, piece, notes=None, owner=None):
    """add a piece at one end and refit the whole line on the photo (as part 2b); refused
    (returns False) if the result would bend sharper than any whisker does. owner: the owner
    says the piece is part of this whisker; it is added, as one smooth curve if needed."""
    cl = np.array(w["centreline"])
    base = np.vstack([cl, piece]) if side == "nose" else np.vstack([piece[::-1], cl])
    new_cl, sig, dep, ok = lv.fit_line(F, base)
    if owner:
        # owner: whiskers are straight. The found piece can wander (into a dark patch of fur);
        # the whole whisker is refitted as ONE gentle arc through the photo fits - at the END of the
        # pass (refit_arcs), after its ends have been followed (refitting first changed its end
        # direction and lost a confirmed stretch).
        w["needs_arc"] = owner
        if max_turn(new_cl) > MAX_TURN:          # keep the joined line sane until the final refit
            new_cl, sig, dep, ok, _ = smooth_whole(F, base)
    if owner:
        w.setdefault("owner_confirmed_stretches", []).append(dict(found_as=owner, at_end=side, px=int(len(piece))))
    elif max_turn(new_cl) > MAX_TURN:
        if notes is not None:
            notes.append(f"{w['id']}: a {len(piece)} px piece at its {side} end was refused (it would bend "
                         f"{max_turn(new_cl):.1f} deg/px)")
        return False
    w["centreline"] = np.round(new_cl, 2).tolist()
    w["sigma"] = np.round(sig, 2).tolist(); w["depth_grey"] = np.round(dep, 1).tolist()
    w.setdefault("full_length_added_px", {}); w["full_length_added_px"][side] = \
        w["full_length_added_px"].get(side, 0) + int(len(piece))
    if side == "outline" and len(w.get("inferred_entry", [])) > 1:
        en = np.array(w["inferred_entry"])
        j = int(np.argmin(np.hypot(*(en - new_cl[0]).T)))
        en = np.vstack([en[:j + 1], new_cl[:1]]) if j > 0 else np.zeros((0, 2))
        w["inferred_entry"] = np.round(en, 2).tolist()
    return True


def try_join(F, doc, wid, side, notes):
    """the grown end now meets the end of another whisker heading the same way: one whisker"""
    W = {w["id"]: w for w in doc["whiskers"]}
    a = W[wid]; ea = ends(a)[side]
    for b in doc["whiskers"]:
        if b["id"] == wid:
            continue
        for bside, (pb, thb) in ends(b).items():
            if np.hypot(*(ea[0] - pb)) > JOIN_DIST:
                continue
            ang = abs((np.degrees(ea[1] - (thb + np.pi)) + 180) % 360 - 180)   # b's end points back at a
            if ang > JOIN_ANGLE:
                continue
            if a.get("continues") and b.get("continues") and a["continues"] != b["continues"]:
                continue                                          # two roots: two whiskers
            bl = np.array(b["centreline"])
            if bside != ("outline" if side == "nose" else "nose"):
                bl = bl[::-1]
            al = np.array(a["centreline"])
            merged = np.vstack([al, bl]) if side == "nose" else np.vstack([bl, al])
            cl, sig, dep, ok = lv.fit_line(F, merged)          # refit across the join
            a["centreline"] = np.round(cl, 2).tolist()
            a["sigma"] = np.round(sig, 2).tolist(); a["depth_grey"] = np.round(dep, 1).tolist()
            if not a.get("continues") and b.get("continues"):
                a["continues"], a["kind"], a["inferred_entry"] = b["continues"], b["kind"], b.get("inferred_entry", [])
            a.setdefault("joined", []).append(b["id"])
            doc["whiskers"].remove(b)
            notes.append(f"{b['id']} was the {bside} part of {wid}: joined into one whisker")
            return True
    return False


def link_outside(F, doc, notes):
    """face-only whiskers reaching his fur band: link to the outside whisker rooted there"""
    data = json.loads((fw.ROOT / "data/strands/wisps.json").read_text())
    used = {w.get("continues") for w in doc["whiskers"] if w.get("continues")}
    for w in doc["whiskers"]:
        if w.get("continues"):
            continue
        p, th = ends(w)["outline"]
        if F.sdist(p) > fw.NEAR_OUTLINE + 12:
            continue
        best = None
        for t in data["strands"]:
            if not t["class"].startswith("whisker") or t["id"] in used:
                continue
            r, thr, dist = fw.root_end(np.array(t["centreline"], float), F)
            d = float(np.hypot(*(r - p)))
            ang = abs((np.degrees(th - (thr + np.pi)) + 180) % 360 - 180)
            if d <= LINK_DIST and ang <= LINK_ANGLE and (best is None or d < best[1]):
                best = (t["id"], d, ang, r)
        if best:
            k, d, ang, r = best
            w["continues"] = k; w["kind"] = "continuation (linked, full length)"; used.add(k)
            w["inferred_entry"] = np.round(fw.dense(np.vstack([r, np.array(w["centreline"])[0]])), 2).tolist()
            notes.append(f"{w['id']}: followed out to his fur band, {d:.0f} px from the root end of {k} "
                         f"(heading {ang:.0f} deg apart): linked as its continuation (owner review)")


PREV = None          # the data saved before this run (stable names)


def add_whisker(F, doc, seg, why, lid):
    """a candidate judged a whisker joins the whiskers (sub-pixel fit, outline -> nose)"""
    cl, sig, dep, ok = lv.fit_line(F, seg)
    if F.sdist(cl[0]) > F.sdist(cl[-1]):
        cl, sig, dep, ok = cl[::-1], sig[::-1], dep[::-1], ok[::-1]
    taken = {w["id"] for w in doc["whiskers"]}
    same = [w["id"] for w in (PREV or {}).get("whiskers", []) if w["id"] not in taken
            and w.get("found_as") == lid] or \
           [w["id"] for w in (PREV or {}).get("whiskers", []) if w["id"] not in taken
            and w["id"].startswith("FW-") and fw.overlap(cl, np.array(w["centreline"]), 4.0) >= 0.5]
    n = max(int(i[3:]) for i in taken | {w["id"] for w in (PREV or {}).get("whiskers", [])} if i.startswith("FW-"))
    doc["whiskers"].append(dict(
        id=same[0] if same else f"FW-{n + 1:02d}", kind="face only (combined view)", found_as=lid, owner_confirmed=True,
        continues=None, judgment=why, median_depth_grey=round(float(np.median(dep[ok])) if ok.any() else float("nan"), 1),
        median_sigma_px=round(float(np.nanmedian(sig[ok])) if ok.any() else float("nan"), 2),
        status="owner-confirmed whisker; faint: rendered at its measured strength, never boosted",
        weight=0, centreline=np.round(cl, 2).tolist(), sigma=np.round(sig, 2).tolist(),
        depth_grey=np.round(dep, 1).tolist(), inferred_entry=[]))


def footprints(doc):
    for w in doc["whiskers"]:
        cl = np.array(w["centreline"]); sg = np.nan_to_num(np.array(w["sigma"], float), nan=1.0)
        lo_ = np.floor(cl.min(0) - 6).astype(int); hi_ = np.ceil(cl.max(0) + 6).astype(int)
        gx, gy = np.meshgrid(np.arange(lo_[0], hi_[0]) + 0.5, np.arange(lo_[1], hi_[1]) + 0.5)
        dd, ii = cKDTree(cl).query(np.c_[gx.ravel(), gy.ravel()])
        w["footprint_px"] = int((dd <= np.maximum(2 * sg[ii], 1.0)).sum())
        w["length_px"] = round(float(np.hypot(*np.diff(cl, axis=0).T).sum()), 1)
        en = np.array(w.get("inferred_entry", [])).reshape(-1, 2)
        w["inferred_entry_px"] = round(float(np.hypot(*np.diff(en, axis=0).T).sum()) if len(en) > 1 else 0.0, 1)
    doc["accounting"]["face_whisker_pixels"] = int(sum(w["footprint_px"] for w in doc["whiskers"]))


def run(F, doc, cache: Path | None = None, procs: int = 4, prev: dict | None = None):
    global PREV
    PREV = prev
    from multiprocessing import Pool
    notes = doc["notes"]
    lv.VIEW = CombinedView
    lines = lv.field_lines(doc["whiskers"], F)
    # 1. the sweep in the combined view (fainter traces)
    if cache and cache.exists():
        found = pickle.loads(cache.read_bytes())
    else:
        with Pool(procs, initializer=lv._init, initargs=(lines,)) as pool:
            found = list(pool.imap(lv._job, lv.starts(F), chunksize=4))
        if cache:
            cache.write_bytes(pickle.dumps(found))
    ext, cands = lv.classify(found, doc["whiskers"])
    listed = [np.array(c["points"]) for c in doc.get("line_view_candidates", [])]
    cands = [c for c in cands if all(fw.overlap(c["seg"], fw.dense(l), 2.5) < 0.5 for l in listed)]
    W = {w["id"]: w for w in doc["whiskers"]}
    sweep_ext, uncertain_ext = {}, []
    done, rounds = set(), []
    with Pool(procs, initializer=lv._init, initargs=(lines,)) as pool:
        # sweep pieces must pass the same side-by-side test as followed pieces
        items = []
        for (k, side), piece in ext.items():
            p, th = ends(W[k])[side]
            items.append((k, side, piece, p, th))
        margins = beside_margins(F, pool, [(p, th, float(len(pc)), sd == "nose") for k, sd, pc, p, th in items],
                                 doc, [k for k, sd, pc, p, th in items])
        for (k, side, piece, p, th), (m, own) in zip(items, margins):
            if owner_continuation(piece):
                lid = owner_continuation(piece)
                grow(F, W[k], side, piece, notes, owner=lid)
                sweep_ext[f"{k}/{side}"] = f"{len(piece)} px ({lid}, owner)"
            elif m is not None and m >= MARGIN and own >= MIN_MEAN and on_other(doc, k, piece) < ON_OTHER \
                    and grow(F, W[k], side, piece, notes):
                sweep_ext[f"{k}/{side}"] = int(len(piece))
            else:
                uncertain_ext.append((k, side, piece, m))
        # 2. follow every whisker from both ends
        for r in range(ROUNDS):
            acc = follow_round(F, doc, pool, done)
            if not acc:
                break
            rounds.append([(wid, side, int(len(q)), m) for wid, side, q, m in acc])
            for wid, side, q, m in acc:
                W = {w["id"]: w for w in doc["whiskers"]}
                if wid not in W:
                    continue
                if on_other(doc, wid, q) >= ON_OTHER:
                    notes.append(f"{wid}: a {len(q)} px piece at its {side} end was refused (it runs along another whisker)")
                    done.add((wid, side)); continue
                if not grow(F, W[wid], side, q, notes):
                    done.add((wid, side)); continue
                if try_join(F, doc, wid, side, notes):
                    done.add((wid, side))
    # owner-joined whiskers: one gentle arc each, now that their ends have been followed
    for w in doc["whiskers"]:
        if w.pop("needs_arc", None):
            cl, sig, dep, ok, rms = smooth_whole(F, np.array(w["centreline"]))
            w["centreline"] = np.round(cl, 2).tolist(); w["sigma"] = np.round(sig, 2).tolist()
            w["depth_grey"] = np.round(dep, 1).tolist(); w["arc_fit_rms_px"] = round(rms, 2)
            notes.append(f"{w['id']}: owner-joined; whole whisker refitted as one arc (degree {STRAIGHT_DEG}); "
                         f"photo fits lie {rms:.1f} px from it (rms)")
    # 3. candidates: side-by-side test and verdicts (default: uncertain, owner sorts)
    if cands:
        lv.standout(F, cands, procs, lines)
    link_outside(F, doc, notes)
    nl = max([int(c["id"][1:]) for c in doc.get("line_view_candidates", [])] + [7])
    for c in sorted(cands, key=lambda c: (c["seg"][:, 0].mean() > 549, c["seg"][:, 1].mean())):
        q = fw.dense(c["seg"]); m = q[len(q) // 2]
        v = [(vv, why) for (x, y), vv, why in FULL_VERDICTS if np.hypot(m[0] - x, m[1] - y) <= lv.VERDICT_DIST]
        verdict, why = v[0] if v else (lv.UNCERTAIN, "not yet judged")
        nl += 1
        if verdict == lv.WHISKER:
            add_whisker(F, doc, q, why, f"L{nl:02d}")
            continue
        pts, sg, dep, ok = F.refine(q)
        doc["line_view_candidates"].append(dict(
            id=f"L{nl:02d}", verdict=verdict, reason=why, margin=round(c.get("margin", float("nan")), 2),
            line_score=round(c.get("line_score", float("nan")), 2),
            sigma_px=round(float(np.nanmedian(sg[ok])) if ok.any() else float("nan"), 2),
            depth_grey=round(float(np.median(dep[ok])) if ok.any() else float("nan"), 1),
            found_by="combined view (part 2c)", points=np.round(q, 1)[::4].tolist()))
    for k, side, piece, m in uncertain_ext:
        nl += 1
        doc["line_view_candidates"].append(dict(
            id=f"L{nl:02d}", verdict=lv.UNCERTAIN, continues=k, at_end=side,
            reason="possible continuation (re-tested below)", margin=None if m is None else round(float(m), 2),
            found_by="combined view (part 2c)", points=np.round(piece, 1)[::4].tolist()))
    # 4. every grey-area candidate re-tested the SAME way as the continuations (from its
    # start, fixed length, beside-searches lying along a known whisker left out): the older
    # test compared lines between two whiskers against those whiskers (owner review, 2026-11-14)
    with Pool(procs, initializer=lv._init, initargs=(lines,)) as pool:
        def recheck(cs):
            items = []
            for c in cs:
                q = fw.dense(np.array(c["points"]))
                d0 = q[min(10, len(q) - 1)] - q[0]
                items.append((tuple(q[0]), float(np.arctan2(d0[1], d0[0])), float(len(q)), True))
            return beside_margins(F, pool, items, doc, ["(none)"] * len(items)) if items else []
        old_ = [c for c in doc.get("line_view_candidates", []) if c["verdict"] != lv.WHISKER]
        for c, (m, own) in zip(old_, recheck(old_)):
            c["margin_before_recheck"] = c.get("margin")
            c["margin"] = None if m is None else round(float(m), 2)
            c["line_score"] = round(float(own), 2)
            test = ("untestable: every search beside it lies on a neighbouring whisker or the fur band"
                    if m is None else f"beats searches beside it by {m:+.2f} (needs {MARGIN})")
            if c.get("continues"):
                c["reason"] = f"possible continuation of {c['continues']} at its {c['at_end']} end; {test}"
            elif c["reason"] == "not yet judged":
                c["reason"] = f"possible whisker on its own; {test}"
    footprints(doc)
    doc["full_length"] = dict(
        about=__doc__.split("\n\n")[0], view="combined: line view + contrast-evened grey (12 px), filter 2 x 24 px",
        sweep_extensions=sweep_ext, follow_rounds=rounds,
        uncertain_continuations={f"{k}/{sd}": int(len(pc)) for k, sd, pc, m in uncertain_ext},
        rules=dict(cost_per_px=FOLLOW_COST, start_bend_deg=6, max_bend_deg_per_px=0.45, margin=MARGIN,
                   min_mean=MIN_MEAN, max_gap_px=MAX_GAP, join_px=JOIN_DIST, link_px=LINK_DIST))
    return doc
