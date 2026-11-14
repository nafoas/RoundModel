"""Every whisker as ONE continuous line, from its root on his whisker pad to its tip.

Owner, 2026-11-14: "whiskers don't just abruptly cut off - that's not how they work ...
it is in our best interest to trace the little guy's whiskers to them [the pads] now, so we
don't go hunting for whisker connections on his little round body in a few steps." And the
rule: whiskers come out of his whisker pads, point toward them, and are straight.

Pieces: outside parts (data/strands/wisps.json), face parts (data/strands/face_whiskers.json).
Each whisker is assembled from an explicit, individually justified decision (WHISKERS below);
the measurements behind each are in its "why".

Pads (working outline; refined in the whisker-pad step): measured from the photo: the upper
lip under each nostril wing, bounded by the nose's lower edge, the philtrum, the mouth corner,
and the line from the nostril wing's outer end to the mouth corner. No free parameters.

Inferred stretches (always labelled):
- "fur band": between an outside part's root end and its face part (G1 Hermite curve);
- "between outside pieces": a whisker invisible against the white background for a stretch;
- "to pad": from the last seen point to the pad: a circular arc that keeps the whisker's own
  end bend as far as possible and bends only as much as needed to reach its pad's outline;
- "hidden under fur": an outside whisker whose face part is buried in the fur (no line seen).
Outer ends: an outside tip; or "out of view" (it reaches his outline with nothing outside: it
follows his round cheek round the side of his head); or "goes under the fur" (stops at full
strength mid-face); or "fades" (thins out like a tip).

Usage: python tools/whisker_chains.py  -> data/strands/whiskers_full.json,
       docs/images/whiskers_full/*.png, docs/WHISKER_MAP.md
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_whiskers as fw  # noqa: E402
import whisker_fulllength as wf  # noqa: E402
import whisker_lineview as lv  # noqa: E402

ROOT = fw.ROOT
OUT_IMG = ROOT / "docs/images/whiskers_full"
MAX_BEND_DEG = 0.25            # deg/px: the sharpest steady bend measured on a seen face whisker (B5-S17: ~0.2)
OWN_K_MAX = 1 / 250.0          # rad/px: a whisker's own end bend is used up to this (radius >= 250 px)
SEEN_LEVEL = 2.5               # running line score along an inferred stretch that counts as "a line is seen"
FADE_RATIO = 0.6               # last 20 px darker than this x its median -> "fades like a tip"

# ---------------------------------------------------------------- the decisions, one per whisker
# outside: outside pieces from the root end outward (each ordered root -> tip); "gap" between two
# means an invisible stretch. face: the face part (None = hidden under fur). shares: the face/outside
# line it shares with another whisker. Every number in "why" was measured (2026-11-14).
WHISKERS = [
    # ---- his left side (image right)
    dict(id="B1-S11", outside=["B1-S11"], face="B1-S11-face",
         why="one arc through the outside and face parts fits to 0.45 px (gap 22 px)"),
    dict(id="B2-S02", outside=["B2-S02"], face="B2-S02-face",
         why="one arc fits to 1.6 px; points at his pad. (FW-13 fits B2-S02 better, 0.7 px, but does not point at a pad)"),
    dict(id="FW-13", outside=["B2-S02"], face="FW-13", shares="B2-S02",
         why="your L05. Starts on B2-S02's outside root stretch (one arc 0.7 px), so it shares that stretch. "
             "FLAG: 2-4x darker than any whisker on his face, runs along the inside edge of his fur band, "
             "and points 158 px off the pad (toward his eye); to reach the pad it must bend more than any whisker"),
    dict(id="B2-S08", outside=["B2-S08"], face="B2-S08-face", why="one arc fits to 0.10 px (gap 8 px)"),
    dict(id="B2-S16", outside=["B2-S16"], face="B2-S16-face", why="one arc fits to 0.32 px (gap 6 px)"),
    dict(id="B2-S20", outside=["B2-S20", "gap", "B2-S29"], face="FW-03",
         why="FW-03 + B2-S20: one arc 0.73 px; B2-S20 + B2-S29 (the 'loose' piece): one arc 0.28 px across a "
             "45 px stretch where the light whisker doesn't show against the white background"),
    dict(id="B2-S12", outside=["B2-S12"], face=None,
         why="no face line on its arc (best: B2-S16-face, 4.9 px off): its face part is under the fur"),
    dict(id="B2-S15", outside=["B2-S15"], face=None,
         why="no face line of its own (B2-S16-face is 12 px off, one arc 2.0 px; B2-S16 owns it at 0.32 px): "
             "its face part is under the fur"),
    dict(id="FW-16", outside=["W-F01"], face="FW-16",
         why="your L10. W-F01 (traced as a fine light hair) fits it: one arc 0.54 px, gap 32 px. (B2-S03, 8 px "
             "beside W-F01, is a separate hair)"),
    dict(id="FW-17", outside=[], face="FW-17",
         why="your L11. Reaches his outline beside B2-S08's root; B2-S08 is not its outside part (one arc "
             "4.3 px; B2-S08's root stretch carries one whisker's darkness, 1.04x): goes round his cheek"),
    dict(id="FW-10", outside=[], face="FW-10", why="your L04 + L17; nothing outside on its line"),
    dict(id="FW-12", outside=[], face="FW-12", why="your L07 + L18; nothing outside on its line"),
    dict(id="FW-11", outside=[], face="FW-11", why="your L06; by his mouth, far from his outline"),
    # ---- his right side (image left)
    dict(id="B4-S02", outside=["B4-S02"], face="B4-S02-face", why="one arc fits to 0.28 px (gap 10 px)"),
    dict(id="B4-S01", outside=["B4-S01"], face="B4-S02-face", shares="B4-S02",
         why="traced as a borderline wisp (34 px, straight). Fits B4-S02-face too (one arc 0.78 px, 2 deg), "
             "and B4-S02-face is the darkest line on that cheek (1.5-2x its neighbours): two whiskers share it"),
    dict(id="B5-S17", outside=["B5-S17"], face="B5-S17-face", why="one arc fits to 0.42 px (gap 8 px)"),
    dict(id="FW-02", outside=["B5-S17"], face="FW-02", shares="B5-S17",
         why="starts exactly on B5-S17's root (one arc 1.2 px); B5-S17's root stretch is 2.8x as dark as the "
             "rest of it (B2-S08 and B1-S11, also rooted at the outline: 1.0x): two whiskers share that stretch"),
    dict(id="B4-S17", outside=["B4-S17"], face="FW-05",
         why="the fan (three whiskers on one root line). FW-05 fits all three (0.37-0.55 px) but carries one "
             "whisker's darkness; B4-S17 fits best (0.37 px, smallest bend)"),
    dict(id="B4-S12", outside=["B4-S12"], face="FW-05", shares="B4-S17", hidden_face=True,
         why="the fan: shares B4-S17's root line outside, so it bends into the cheek the same way; its face "
             "part is under the fur alongside FW-05 (FW-05 carries one whisker's darkness)"),
    dict(id="B4-S15", outside=["B4-S15"], face="FW-05", shares="B4-S17", hidden_face=True,
         why="as B4-S12"),
    dict(id="FW-07", outside=["B4-S13"], face="FW-07",
         why="B4-S13 (traced as a short wisp) fits it almost exactly: one arc 0.09 px (B4-S14: 0.61 px)"),
    dict(id="FW-04", outside=["B4-S06"], face="FW-04",
         why="its tip pokes out of the fringe as B4-S06 (traced as a fringe tip: on its line, 6 deg)"),
    dict(id="FW-01", outside=[], face="FW-01", why="nothing outside on its line"),
    dict(id="FW-06", outside=[], face="FW-06", why="your L01 + L14; nothing outside on its line"),
    dict(id="FW-14", outside=[], face="FW-14", why="your L08; nothing outside on its line"),
    dict(id="FW-08", outside=[], face="FW-08", why="your L02"),
    dict(id="FW-09", outside=[], face="FW-09", why="your L03"),
    dict(id="FW-15", outside=[], face="FW-15", why="your L09"),
]
NOT_PAD = {   # outside whiskers that root elsewhere (their own step)
    "B1-S01": "eyebrow whisker (his left)", "B1-S02": "eyebrow whisker (his left)",
    "B1-S03": "eyebrow whisker (his left)", "B1-S07": "loose piece beside his left eye: nothing lines up with it",
    "B5-S01": "eyebrow whisker (his right)", "B5-S02": "eyebrow whisker (his right)",
    "B5-S06": "eyebrow whisker (his right)", "B5-S08": "eyebrow whisker (his right)",
}


# ---------------------------------------------------------------- geometry helpers
def dense(q):
    return fw.dense(np.asarray(q, float))


def tangent(q, at_end=True, n=10):
    q = dense(q)
    t = (q[-1] - q[-min(n + 1, len(q))]) if at_end else (q[min(n, len(q) - 1)] - q[0])
    return t / (np.linalg.norm(t) + 1e-12)


def own_curvature(q, n=80):
    """signed curvature (rad/px) of the last n px of q (toward its end)"""
    q = dense(q)[-n:]
    if len(q) < 20:
        return 0.0
    t0 = q[10] - q[0]; t1 = q[-1] - q[-11]
    a = np.arctan2(t0[0] * t1[1] - t0[1] * t1[0], t0 @ t1)
    return float(np.clip(a / (len(q) - 10), -OWN_K_MAX, OWN_K_MAX))


def hermite(p0, t0, p1, t1):
    L = float(np.hypot(*(p1 - p0)))
    s = np.linspace(0, 1, max(int(L), 2))[:, None]
    h00 = 2 * s ** 3 - 3 * s ** 2 + 1; h10 = s ** 3 - 2 * s ** 2 + s; h01 = -2 * s ** 3 + 3 * s ** 2; h11 = s ** 3 - s ** 2
    return h00 * p0 + h10 * L * t0 + h01 * p1 + h11 * L * t1


def arc_to(p0, t0, k, L):
    th = np.arctan2(t0[1], t0[0]); p = p0.copy(); out = []
    for _ in range(int(L)):
        th += k; p = p + np.array([np.cos(th), np.sin(th)]); out.append(p.copy())
    return np.array(out)


# ---------------------------------------------------------------- pads, measured from the photo
def measure_pads(F):
    g = F.grey; flat = g * (g.mean() / np.maximum(ndi.gaussian_filter(g, 20), 1))
    x0, y0, x1, y1 = 380, 620, 720, 880
    a = flat[y0:y1, x0:x1]; med = np.median(a)
    dark = a < med - 0.30 * (med - np.percentile(a, 1))
    lab, n = ndi.label(dark); sizes = ndi.sum(dark, lab, range(1, n + 1))
    ys, xs = np.nonzero(lab == int(np.argmax(sizes)) + 1); xs = xs + x0; ys = ys + y0
    rows = {y: (xs[ys == y].min(), xs[ys == y].max()) for y in np.unique(ys)}
    widths = {y: r[1] - r[0] for y, r in rows.items()}
    ph = [y for y in sorted(rows) if widths[y] <= 30 and y > min(rows) + 30]     # philtrum rows
    ph_top, ph_bot = ph[0], [y for y in ph if y < ph[0] + 80][-1]
    ph_x = float(np.median([(rows[y][0] + rows[y][1]) / 2 for y in ph]))
    nose_rows = [y for y in sorted(rows) if y < ph_top]
    mouth_rows = [y for y in sorted(rows) if y > ph_bot]
    yl = min(nose_rows, key=lambda y: rows[y][0]); wing_l = np.array([rows[yl][0], yl], float)
    yr = min(nose_rows, key=lambda y: -rows[y][1]); wing_r = np.array([rows[yr][1], yr], float)
    yml = min(mouth_rows, key=lambda y: rows[y][0]); mouth_l = np.array([rows[yml][0], yml], float)
    ymr = min(mouth_rows, key=lambda y: -rows[y][1]); mouth_r = np.array([rows[ymr][1], ymr], float)
    left = [wing_l] + [np.array([rows[y][0], y], float) for y in nose_rows if y > yl][::4] + \
           [np.array([ph_x - 4, ph_top]), np.array([ph_x - 4, ph_bot]), mouth_l]
    right = [wing_r] + [np.array([rows[y][1], y], float) for y in nose_rows if y > yr][::4] + \
            [np.array([ph_x + 4, ph_top]), np.array([ph_x + 4, ph_bot]), mouth_r]
    return {"image_left": dict(outline=np.array(left), lateral=[wing_l, mouth_l]),
            "image_right": dict(outline=np.array(right), lateral=[wing_r, mouth_r]),
            "landmarks": dict(nostril_wing_left=wing_l, nostril_wing_right=wing_r, philtrum_x=ph_x,
                              philtrum_top=ph_top, philtrum_bottom=ph_bot, mouth_corner_left=mouth_l,
                              mouth_corner_right=mouth_r)}


AT_PAD = 6.0                   # px: a seen end this close to (or inside) its pad has reached it


PAD_TOP_PCT = 10               # the pad reaches up to where 90% of that side's whiskers point


def raise_pads(pads, face_ends):
    """By the owner's rule the pad is where the whiskers point: extend each pad's lateral edge up
    from the nostril wing end to the 10th-percentile height at which that side's whiskers' own
    continuations cross the nostril wing's vertical (never below the wing end)."""
    for side, ends in face_ends.items():
        wing = pads[side]["lateral"][0]
        ys = []
        for p0, t0, k in ends:
            pts = arc_to(p0, t0, k, 600)
            sgn = 1 if side == "image_left" else -1
            if sgn * (p0[0] - wing[0]) >= 0:
                ys.append(p0[1]); continue
            hit = np.flatnonzero(sgn * (pts[:, 0] - wing[0]) >= 0)
            if len(hit):
                ys.append(pts[hit[0], 1])
        top = min(float(np.percentile(ys, PAD_TOP_PCT)), wing[1])
        tp = np.array([wing[0], top])
        pads[side]["lateral"] = [tp] + list(pads[side]["lateral"])
        pads[side]["outline"] = np.vstack([tp, pads[side]["outline"]])
        pads[side]["top_from_whiskers"] = round(top, 1)
    return pads


def _nearest_on(poly, p):
    best = None
    for a, b in zip(poly[:-1], poly[1:]):
        ab = b - a; u = np.clip((p - a) @ ab / (ab @ ab), 0, 1); q = a + u * ab
        d_ = float(np.hypot(*(p - q)))
        if best is None or d_ < best:
            best = d_
    return best


OWN_REACH = 600                # px: how far a whisker's own bend is followed looking for its pad


def seg_cross(p, q, a, b):
    """intersection point of segments pq and ab, or None"""
    r, s_ = q - p, b - a
    den = r[0] * s_[1] - r[1] * s_[0]
    if abs(den) < 1e-12:
        return None
    t = ((a - p)[0] * s_[1] - (a - p)[1] * s_[0]) / den
    u = ((a - p)[0] * r[1] - (a - p)[1] * r[0]) / den
    return p + t * r if (0 <= t <= 1 and 0 <= u <= 1) else None


def path_to_pad(p0, t0, k_own, pad):
    """circular arc from p0 (heading t0) to the pad's lateral edge: its own bend if that reaches the
    edge, else the smallest change of bend that does. Returns (points, curvature used, own curvature)."""
    lat = pad["lateral"]
    if MPath(pad["outline"]).contains_point(p0) or _nearest_on(lat, p0) <= AT_PAD:
        return p0[None].copy(), k_own, k_own          # already at its pad: nothing to infer
    # 1. its own bend: where does it cross the pad's lateral edge?
    own = np.vstack([p0, arc_to(p0, t0, k_own, OWN_REACH)])
    for i in range(len(own) - 1):
        for a, b in zip(lat[:-1], lat[1:]):
            q = seg_cross(own[i], own[i + 1], a, b)
            if q is not None:
                return np.vstack([own[1:i + 1], q]), k_own, k_own
    # 2. it doesn't: the smallest change of bend that reaches the edge (targets 1 px apart)
    cands = []
    targets = np.vstack([a + u * (b - a) for a, b in zip(lat[:-1], lat[1:])
                         for u in np.linspace(0, 1, max(int(np.hypot(*(b - a))), 2))])
    for q in targets:
        c = q - p0; dist = float(np.hypot(*c))
        if dist < 2:
            continue
        alpha = np.arctan2(t0[0] * c[1] - t0[1] * c[0], t0 @ c)          # angle from heading to chord
        if abs(alpha) > np.radians(80):
            continue
        k = 2 * np.sin(alpha) / dist                                     # circle through p0 (tangent t0) and q
        L = dist if abs(alpha) < 1e-6 else abs(2 * alpha / k)
        cands.append((abs(k - k_own), k, L, q))
    if not cands:
        return None, None, k_own
    _, k, L, q = min(cands, key=lambda c: c[0])
    pts = arc_to(p0, t0, k, L)
    return np.vstack([pts[:-1], q]) if len(pts) > 1 else q[None], k, k_own


# ---------------------------------------------------------------- assembly
def load_pieces(F):
    o = json.loads((ROOT / "data/strands/wisps.json").read_text())
    d = json.loads((ROOT / "data/strands/face_whiskers.json").read_text())
    outs = {}
    for t in o["strands"]:
        sc = np.array(t["centreline"], float)
        outs[t["id"]] = dict(cls=t["class"], line=dense(sc if abs(F.sdist(sc[0])) < abs(F.sdist(sc[-1])) else sc[::-1]))
    face = {w["id"]: dict(line=dense(np.array(w["centreline"])), w=w) for w in d["whiskers"]}   # outline -> nose
    return outs, face, d


def build(F, V=None):
    outs, face, d = load_pieces(F)
    pads = measure_pads(F)
    mid = pads["landmarks"]["philtrum_x"]
    ends = {"image_left": [], "image_right": []}
    for spec in WHISKERS:
        if spec["face"]:
            fp = face[spec["face"]]["line"]
            ends["image_left" if fp[:, 0].mean() < mid else "image_right"].append((fp[-1], tangent(fp, True), own_curvature(fp)))
    pads = raise_pads(pads, ends)
    result, used_face = [], set()
    for spec in WHISKERS:
        segs = []          # (points ordered root(pad) -> tip, label)
        # outside pieces, root -> tip, with invisible stretches between them
        out_lines = []
        for item in spec["outside"]:
            if item == "gap":
                out_lines.append("gap")
            else:
                out_lines.append(outs[item]["line"])
        fpart = face[spec["face"]]["line"] if spec["face"] else None
        side = "image_left" if ((fpart if fpart is not None else out_lines[0])[:, 0].mean() < mid) else "image_right"
        if spec["face"]:
            used_face.add(spec["face"])
        # face part (outline -> nose): hidden for the fan's other whiskers
        if fpart is not None:
            nose_end, t_in = fpart[-1], tangent(fpart, True)
            k_own = own_curvature(fpart)
        else:
            o0 = out_lines[0]                                   # root -> tip
            nose_end, t_in = o0[0], -tangent(o0, False)
            k_own = -own_curvature(o0[::-1])                   # bend continued inward
        to_pad, k_used, _ = path_to_pad(nose_end, t_in, k_own, pads[side])
        if to_pad is None:
            raise RuntimeError(f"{spec['id']}: no gentle path to its pad")
        label_in = "hidden under fur, to pad" if fpart is None else "to pad"
        segs.append((to_pad[::-1], label_in))
        if fpart is not None:
            segs.append((fpart[::-1], "face (seen)" if not spec.get("hidden_face") else "face (hidden under fur, along shared line)"))
        # fur band bridge from face start to the first outside piece
        first = next((x for x in out_lines if not isinstance(x, str)), None)
        if fpart is not None and first is not None:
            br = hermite(fpart[0], -tangent(fpart, False), first[0], tangent(first, False))
            segs.append((br, "fur band"))
        prev = None
        for i, x in enumerate(out_lines):
            if isinstance(x, str):
                continue
            if prev is not None and isinstance(out_lines[i - 1], str):
                segs.append((hermite(prev[-1], tangent(prev, True), x[0], tangent(x, False)), "between outside pieces"))
            segs.append((x, "outside (seen)" + (" - shared stretch" if spec.get("shares") and i == 0 else "")))
            prev = x
        # outer end
        if out_lines:
            outer = "outside tip"
        else:
            sd = float(F.sdist(fpart[0]))
            if sd <= 25:
                outer = "out of view: reaches his outline with nothing outside, so it goes round his cheek"
            else:
                dep = np.array(face[spec["face"]]["w"]["depth_grey"], float)
                ratio = np.nanmedian(dep[:20]) / max(np.nanmedian(dep), 1e-6)
                outer = (f"fades like a tip, {sd:.0f} px inside his outline (last 20 px at {ratio:.1f}x its usual darkness)"
                         if ratio < FADE_RATIO else
                         f"goes under the fur {sd:.0f} px inside his outline (stops at {ratio:.1f}x its usual darkness, "
                         f"not tapering); where its line meets his outline nothing comes out")
        line = np.vstack([s for s, _ in segs]); labels = np.concatenate([[lab] * len(s) for s, lab in segs])
        doubt = None
        change = abs(np.degrees(k_used - k_own))
        if len(to_pad) > 30 and (abs(np.degrees(k_used)) > MAX_BEND_DEG or (fpart is not None and change > MAX_BEND_DEG)):
            doubt = (f"to reach the pad outline it must bend {np.degrees(k_used):+.2f} deg/px against its own "
                     f"{np.degrees(k_own):+.2f} (whiskers on his face bend at most {MAX_BEND_DEG}); it points "
                     f"{'above' if nose_end[1] < pads[side]['lateral'][0][1] else 'away from'} its pad: its root may be "
                     f"higher (up the side of his nose), or it is not a pad whisker")
        rec = dict(id=spec["id"], side=side, why=spec["why"], shares=spec.get("shares"), outer_end=outer, doubt=doubt,
                   pieces=[lab for _, lab in segs],
                   to_pad=dict(px=int(len(to_pad)), bend_deg_per_px=round(float(np.degrees(k_used)), 3),
                               own_bend_deg_per_px=round(float(np.degrees(k_own)), 3),
                               extra_bend_deg_per_px=round(float(np.degrees(k_used - k_own)), 3),
                               root=np.round(to_pad[-1], 1).tolist()),
                   centreline=np.round(line, 2).tolist(), labels=labels.tolist())
        if V is not None:   # is a line seen along the inferred stretches? (combined view, running score)
            for key, lab in (("to_pad", label_in), ("fur_band", "fur band")):
                m = labels == lab
                if m.sum() >= 12:
                    q = line[m]; _, c = V.line_profile(q)
                    wv = fw.windowed(np.nan_to_num(c))
                    rec.setdefault("seen_along_inferred", {})[key] = round(float(np.mean(np.nan_to_num(wv) >= SEEN_LEVEL)), 2)
        result.append(rec)
    missing = sorted(set(face) - used_face)
    return result, pads, missing, outs


def sheets(F, recs, pads, V):
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    g = F.grey; flat = g * (g.mean() / np.maximum(ndi.gaussian_filter(g, 20), 1))
    chroma = F.photo.astype(float) - F.photo.astype(float).mean(2, keepdims=True)
    A = np.full(g.shape, -np.inf); A[lv.Y0:lv.Y1, lv.X0:lv.X1] = V.along_view()
    lview = np.clip(255 - np.clip(A, 0, 8) / 8 * 255, 0, 255).astype(np.uint8)
    COL = {"outside (seen)": (0, 170, 0), "face (seen)": (255, 0, 150)}

    def draw(box, sc, focus, title):
        x0, y0, x1, y1 = box
        a = flat[y0:y1, x0:x1]; l, h = np.percentile(a, [1, 99])
        ph = np.clip(np.clip((a - l) / (h - l) * 255, 0, 255)[..., None] + chroma[y0:y1, x0:x1], 0, 255).astype(np.uint8)
        panels = []
        for src in (ph, lview[y0:y1, x0:x1]):
            im = Image.fromarray(src).convert("RGB").resize(((x1 - x0) * sc, (y1 - y0) * sc), Image.LANCZOS)
            top = im.copy(); dr = ImageDraw.Draw(im)
            P = lambda z: ((z[0] - x0) * sc, (z[1] - y0) * sc)
            for sd in ("image_left", "image_right"):
                dr.line([P(z) for z in np.vstack([pads[sd]["outline"], pads[sd]["outline"][:1]])], fill=(0, 190, 255), width=2)
            for r in recs:
                if r["id"] in focus:
                    continue
                q = np.array(r["centreline"]); dr.line([P(z) for z in q[::3]], fill=(150, 150, 150), width=1)
            for r in recs:
                if r["id"] not in focus:
                    continue
                q = np.array(r["centreline"]); lab = np.array(r["labels"])
                t = np.gradient(q, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
                n = np.c_[-t[:, 1], t[:, 0]]
                for sg in (-1, 1):
                    gl = q + sg * 4 * n
                    for i in range(0, len(gl) - 1):
                        seen = lab[i].startswith(("outside", "face (seen)"))
                        if not seen and (i // 3) % 2:
                            continue
                        col = COL.get(lab[i].split(" - ")[0], (255, 140, 0))
                        dr.line([P(gl[i]), P(gl[i + 1])], fill=col, width=2 if len(focus) == 1 else 1)
                i = len(q) // 2
                dr.text(P(q[i] + 9 * n[i]), r["id"], fill=(0, 0, 0))
            o = Image.new("RGB", (im.width, im.height * 2 + 4), (30, 30, 30)); o.paste(top, (0, 0)); o.paste(im, (0, im.height + 4))
            panels.append(o)
        out = Image.new("RGB", (panels[0].width * 2 + 6, panels[0].height + 26), (255, 255, 255))
        out.paste(panels[0], (0, 26)); out.paste(panels[1], (panels[0].width + 6, 26))
        ImageDraw.Draw(out).text((6, 6), title, fill=(0, 0, 0))
        return out
    key = ("solid = seen in the photo (green outside, magenta on his face); dashed orange = inferred; "
           "cyan = working pad outline; grey = his other whiskers. Left: photo (brightness stretched, true colour). "
           "Right: line view. Top: unmarked.")
    for r in recs:
        q = np.array(r["centreline"])
        x0, y0 = np.floor(q.min(0) - 25).astype(int); x1, y1 = np.ceil(q.max(0) + 25).astype(int)
        H_, W_ = F.grey.shape
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W_), min(y1, H_)      # the whole whisker, always
        sc = int(np.clip(700 // max(x1 - x0, 1), 1, 4))
        draw((x0, y0, x1, y1), sc, {r["id"]}, f"{r['id']}: {key}").save(OUT_IMG / f"{r['id']}.png")
    pages = []
    for side, box in (("image_left", (60, 540, 560, 1060)), ("image_right", (530, 540, 1098, 1060))):
        ids = {r["id"] for r in recs if r["side"] == side}
        im = draw(box, 2, ids, f"all whiskers, {side.replace('_', ' ')} side: {key}"); im.save(OUT_IMG / f"all_{side}.png")
        pages.append(im)
    for r in recs:
        pages.append(Image.open(OUT_IMG / f"{r['id']}.png").convert("RGB"))
    pages[0].save(OUT_IMG / "whiskers_full.pdf", save_all=True, append_images=pages[1:], resolution=110)


def write_map(recs, pads, missing, outs):
    L = ["# Prince's whiskers, pad to tip", "",
         "Every whisker on his face as one continuous line from its root on his whisker pad to its tip",
         "(`tools/whisker_chains.py`, data `data/strands/whiskers_full.json`, pictures",
         "`docs/images/whiskers_full/`). Owner, 2026-11-14: whiskers don't just cut off; trace them to",
         "the pads now. Each decision below was made individually from measurements (one arc through",
         "both pieces: how close it fits; darkness; direction). Inferred stretches are labelled.", "",
         "Working pad outline (refined in the whisker-pad step): the upper lip under each nostril wing,",
         f"measured from the photo: nostril wings end at {pads['landmarks']['nostril_wing_left'].round(0).tolist()} and "
         f"{pads['landmarks']['nostril_wing_right'].round(0).tolist()}, philtrum at x {pads['landmarks']['philtrum_x']:.0f}, "
         f"mouth corners {pads['landmarks']['mouth_corner_left'].round(0).tolist()} and "
         f"{pads['landmarks']['mouth_corner_right'].round(0).tolist()}; raised up the side of his nose to where 90% of",
         f"that side's whiskers point (your rule: they point to the pads): y {pads['image_left']['top_from_whiskers']:.0f} "
         f"(image left) and {pads['image_right']['top_from_whiskers']:.0f} (image right).", ""]
    for side, name in (("image_right", "His left side (image right)"), ("image_left", "His right side (image left)")):
        L += [f"## {name}", "", "| whisker | made of | why | to its pad | outer end |", "|---|---|---|---|---|"]
        for r in recs:
            if r["side"] != side:
                continue
            parts = []
            for p in r["pieces"]:
                if not parts or parts[-1] != p:
                    parts.append(p)
            tp = r["to_pad"]
            seen = r.get("seen_along_inferred", {}).get("to_pad")
            extra = f"; bends {tp['extra_bend_deg_per_px']:+.2f} deg/px more than its own end" if abs(tp["extra_bend_deg_per_px"]) > 0.02 else ""
            if r.get("doubt"):
                extra += f"; **DOUBT: {r['doubt']}**"
            L.append(f"| {r['id']} | {' + '.join(parts)} | {r['why']} | {tp['px'] if tp['px'] > 1 else 0} px inferred"
                     f"{f', a line seen along {seen:.0%} of it' if seen is not None else ''}{extra} | {r['outer_end']} |")
        L.append("")
    L += ["## Outside whiskers that root elsewhere", ""]
    for k, v in NOT_PAD.items():
        L.append(f"- {k}: {v} (for the eye/brow step)")
    if missing:
        L += ["", "## Face whiskers not assigned (should be none)", "", ", ".join(missing)]
    (ROOT / "docs/WHISKER_MAP.md").write_text("\n".join(L) + "\n")


def main() -> int:
    F = fw.Face()
    d = json.loads((ROOT / "data/strands/face_whiskers.json").read_text())
    V = wf.CombinedView(lv.field_lines(d["whiskers"], F))
    recs, pads, missing, outs = build(F, V)
    if missing:
        print("face whiskers not assigned:", missing)
    doc = dict(about=__doc__.split("\n\n")[0] + " " + __doc__.split("\n\n")[1],
               pads={k: dict(outline=np.round(v["outline"], 1).tolist(), top_from_whiskers=v["top_from_whiskers"])
                     for k, v in pads.items() if k != "landmarks"},
               landmarks={k: (np.round(v, 1).tolist() if isinstance(v, np.ndarray) else v) for k, v in pads["landmarks"].items()},
               whiskers=recs, not_pad_whiskers=NOT_PAD,
               reclassified_outside_pieces={"B4-S01": "wisp -> outside part of whisker B4-S01 (shares B4-S02's face line)",
                                            "B4-S13": "wisp -> outside part of FW-07", "B4-S06": "fringe tip -> tip of FW-04",
                                            "W-F01": "fine hair -> outside part of FW-16",
                                            "B2-S29": "loose whisker section -> outer part of B2-S20"},
               status="first pass, self-checked; owner review pending")
    (ROOT / "data/strands/whiskers_full.json").write_text(json.dumps(doc, indent=1, default=lambda x: x.item()))
    write_map(recs, pads, missing, outs)
    sheets(F, recs, pads, V)
    for r in recs:
        tp = r["to_pad"]
        print(f"{r['id']:7s} {r['side'][6:]:5s} to pad {tp['px']:3d} px (own bend {tp['own_bend_deg_per_px']:+.2f}, "
              f"used {tp['bend_deg_per_px']:+.2f} deg/px) seen {r.get('seen_along_inferred', {})}  outer: {r['outer_end'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
