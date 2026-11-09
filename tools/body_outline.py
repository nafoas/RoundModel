"""Step 3, first part (docs/STRAND_PLAN.md): Prince's body outline.

One gentle, smooth closed curve around his whole silhouette (ears, peets and
tuft included; they're split off in later steps). It runs THROUGH his soft
fuzzy edge (the 50% coverage level of a blurred coverage map), so thin
whiskers and single hairs barely move it, and it's smoothed so it comes out
less jagged than the raw edge. Stored as a sub-pixel periodic spline.

Usage: python tools/body_outline.py   (writes data/strands/body_outline.json)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.interpolate import splev, splprep
from skimage.measure import find_contours

sys.path.insert(0, str(Path(__file__).resolve().parent))
import edge_tiles as et  # noqa: E402

BLUR = 8.0        # px: blur before taking the 50% level, on his furry sides
LEVEL = 0.5       # coverage level the outline runs along
SMOOTH_RMS = 4.0  # px: allowed RMS distance to the 50% level, on his furry sides
# Zones by image row, each with its own fit (blur px, RMS px):
#  - SENSITIVE: the top of his head (both ears, the dip between them, and both
#    eye corners). His identity lives here: fitted as tightly as possible, after
#    removing thin strands (lashes, eyebrow whiskers) so the line follows his
#    head underneath them, not the strands.
#  - PEETS: peets and the tuft between them: faithful.
#  - everything else (his furry sides): gentle.
SENSITIVE_MAX_Y = 520   # above this row: ears + eyes
PEET_MIN_Y = 1100       # (legacy, unused) the peet zone is now defined by the approved peet line
PEET_LINE = "data/lines/peet_line.json"
PEET_RAMP = 10          # px: hand-off half-width across the peet line (gentle above, faithful below)
HANDOFF = 40            # px: smooth hand-off between zones
SENSITIVE_FIT = (2.5, 0.8)
# The body line follows the EDGE OF HIS SOLID BODY, where the intermediate fur
# (fringe) begins: owner, 2026-11-07, "the little intermediate fur gets its own
# colour". Solid body = coverage >= 0.5 with anything narrower than a disk of
# radius SOLID_R removed (fringe spikes and the gaps between them), holes filled.
SOLID_R_SIDES = 9       # px, his furry sides
SOLID_R_PEETS = 5       # px, below the peet line (keeps the peets' corners)
SIDE_RMS = 2.0          # px, spline smoothing on his sides
# Owner-approved top of head (ears, eyes, eye marks, wisp bridge) is LOCKED:
# taken exactly from this file above its lock_row, never recomputed.
APPROVED_TOP = "data/lines/approved_top_of_head.json"
# Pixel-precise top of head (ears, dip, ear bases), owner 2026-11-09; made by
# tools/ear_edges.py. Spliced in after the lock, so it overrides the ear stretch.
PRECISE_TOP = "data/lines/top_of_head_precise.json"
PRECISE_BLEND = 8.0     # px of arc length at each end over which it blends into the outline
PEET_RMS = 1.0
PEET_FIT = (4.0, 1.0)
STRAND_R = 4            # px: strands thinner than ~2*STRAND_R+1 are removed before the sensitive fit
# His black eye marks (hotot "eyeliner") are protected: the outline must contain
# every pixel of them, to sub-pixel precision. Owner: they make him, him.
EYE_BOXES = {"right_eye_image_left": (270, 340, 380, 500), "left_eye_image_right": (670, 330, 790, 490)}
MARK_LUM = 130          # darker than this and connected to the eye's dark core = eye mark
CORE_LUM = 70
UNION_SS = 8            # sub-samples per pixel when merging the marks into the outline
# Owner-guided stretches: the outline is bridged smoothly past things the owner
# has said are not his body. Each bridge joins the outline at both ends with
# matching direction (cubic Hermite), so there is no kink.
OWNER_GUIDED = [
    {"name": "rogue wisp above his right eye (image left)", "x_max": 345, "rows": (368, 401),
     "why": "owner, 2026-11-07: the small bump above his right eye's lashes is a little "
            "rogue piece of wispy fur, not an eyebrow. The wisp goes to the wisp layer."},
]


def coverage(rgb: np.ndarray) -> np.ndarray:
    """0..1: how much of each pixel is Prince, from how far it is from pure
    white relative to the solid fur right next to it."""
    mn = rgb.min(axis=2).astype(float)
    fg = mn < et.WHITE
    body = et.rough_body(fg)
    interior = ndi.binary_erosion(body, et.disk(14))
    fur = None
    for s in (20, 40, 80):
        num = ndi.gaussian_filter(np.where(interior, mn, 0.0), s)
        den = ndi.gaussian_filter(interior.astype(float), s)
        est = np.where(den > 1e-4, num / np.maximum(den, 1e-9), np.nan)
        fur = est if fur is None else np.where(np.isnan(fur), est, fur)
    fur = np.nan_to_num(fur, nan=float(np.median(mn[interior])))
    a = np.clip((255.0 - mn) / np.maximum(255.0 - fur, 25.0), 0, 1)
    a[~fg] = 0
    return a


def level_contour(a: np.ndarray, blur: float) -> np.ndarray:
    """Longest closed contour at LEVEL of the blurred coverage, as (x, y).

    PIXEL CONVENTION (project-wide): pixel (col, row) covers [col, col+1) x
    [row, row+1); its centre is at (col+0.5, row+0.5). find_contours puts pixel
    centres at whole numbers, so +0.5 converts to the project convention."""
    src = ndi.gaussian_filter(a, blur) if blur > 0 else a
    cs = find_contours(src, LEVEL)
    c = max(cs, key=len)
    return np.stack([c[:, 1] + 0.5, c[:, 0] + 0.5], axis=1)


def resample(xy: np.ndarray, step: float = 1.0) -> np.ndarray:
    seg = np.hypot(*np.diff(xy, axis=0).T)
    keep = np.concatenate([[True], seg > 1e-6])
    xy = xy[keep]
    arc = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    t = np.arange(0, arc[-1], step)
    return np.stack([np.interp(t, arc, xy[:, 0]), np.interp(t, arc, xy[:, 1])], axis=1)


def fit_smooth(xy: np.ndarray, w: np.ndarray | None = None):
    pts = resample(xy, 2.0)
    if np.hypot(*(pts[0] - pts[-1])) < 1e-6:
        pts = pts[:-1]
    if w is None:
        w = np.ones(len(pts))
    elif len(w) != len(pts):
        w = np.ones(len(pts))
    tck, _ = splprep([pts[:, 0], pts[:, 1]], w=w, s=len(pts) * SMOOTH_RMS ** 2, per=1)
    return tck, pts


def without_strands(a: np.ndarray) -> np.ndarray:
    """Coverage with thin strands (lashes, whiskers, single hairs) removed. A grey
    opening keeps smooth edges where they are and only drops narrow peaks."""
    return ndi.grey_opening(a, footprint=et.disk(STRAND_R))


def solid_body(a: np.ndarray, r: int) -> np.ndarray:
    """Soft (0..1) field of his solid body: the 50% coverage region with anything
    narrower than a disk of radius r removed. Its 0.5 level is the body's edge."""
    m = ndi.binary_opening(a >= LEVEL, structure=et.disk(r))
    m = ndi.binary_fill_holes(et.largest(m))
    return ndi.gaussian_filter(m.astype(float), 1.0)


def _curve(src: np.ndarray, blur: float, rms: float) -> np.ndarray:
    global SMOOTH_RMS
    keep = SMOOTH_RMS
    SMOOTH_RMS = rms
    try:
        tck, _ = fit_smooth(level_contour(src, blur))
    finally:
        SMOOTH_RMS = keep
    return resample(sample(tck, 8000), 1.0)


def peet_weight(xy: np.ndarray) -> np.ndarray:
    """0..1: how much a point belongs to the peets/underfluff zone, i.e. lies
    below the owner-approved peet line (notch to notch; beyond the notches the
    line is extended flat at the notch height). Smooth over +-PEET_RAMP px."""
    line = np.array(json.loads(Path(PEET_LINE).read_text())["sampled_curve"])
    line = line[np.argsort(line[:, 0])]
    ly = np.interp(xy[:, 0], line[:, 0], line[:, 1])   # np.interp clamps beyond the ends
    return np.clip((xy[:, 1] - ly + PEET_RAMP) / (2 * PEET_RAMP), 0, 1)


def fit_outline(a: np.ndarray):
    """Three closed curves joined by image row: SENSITIVE (top of head: ears and
    eyes, strands removed, tightest fit), PEET (faithful), and GENTLE (his furry
    sides), with smooth HANDOFF-px transitions."""
    global SMOOTH_RMS
    from scipy.spatial import cKDTree
    mid_gentle = level_contour(a, BLUR)
    gentle = _curve(solid_body(a, SOLID_R_SIDES), 0, SIDE_RMS)
    sens = _curve(without_strands(a), *SENSITIVE_FIT)
    peet = _curve(solid_body(a, SOLID_R_PEETS), 0, PEET_RMS)
    near_s = sens[cKDTree(sens).query(gentle)[1]]
    near_p = peet[cKDTree(peet).query(gentle)[1]]
    y = gentle[:, 1]
    ts = np.clip((SENSITIVE_MAX_Y + HANDOFF - y) / HANDOFF, 0, 1)[:, None]
    tp = peet_weight(gentle)[:, None]
    joined = ts * near_s + tp * near_p + (1 - ts - tp) * gentle
    keep = SMOOTH_RMS
    SMOOTH_RMS = 0.2
    try:
        tck, _ = fit_smooth(joined)
    finally:
        SMOOTH_RMS = keep
    return tck, mid_gentle


def eye_mark_fields(rgb: np.ndarray, a: np.ndarray) -> dict:
    """For each eye box: a 0..1 field of the black eye mark (its soft edge kept)."""
    lum = rgb.mean(axis=2).astype(float)
    out = {}
    for name, (x0, y0, x1, y1) in EYE_BOXES.items():
        L = lum[y0:y1, x0:x1]
        dark = L < MARK_LUM
        lab, n = ndi.label(dark, structure=np.ones((3, 3), int))
        core_ids = set(np.unique(lab[(L < CORE_LUM) & dark])) - {0}
        mark = np.isin(lab, list(core_ids))
        near = ndi.binary_dilation(mark, iterations=2)          # include the mark's anti-aliased edge
        out[name] = ((x0, y0, x1, y1), a[y0:y1, x0:x1] * near, mark)
    return out


def merge_marks(curve: np.ndarray, fields: dict) -> np.ndarray:
    """Union the outline with each eye mark on an UNION_SS-times finer grid and
    splice the union's boundary back into the outline inside that eye box."""
    from matplotlib.path import Path as MPath
    from scipy.spatial import cKDTree
    for (x0, y0, x1, y1), field, _ in fields.values():
        ss = UNION_SS
        xs = x0 + (np.arange((x1 - x0) * ss) + 0.5) / ss
        ys = y0 + (np.arange((y1 - y0) * ss) + 0.5) / ss
        X, Y = np.meshgrid(xs, ys)
        inside = MPath(curve).contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(X.shape)
        # mark field sampled on the fine grid (bilinear), its 50% level is the mark's edge
        fine = ndi.map_coordinates(field, [(Y - y0 - 0.5).ravel(), (X - x0 - 0.5).ravel()],
                                   order=1, mode="nearest").reshape(X.shape)
        mk = ndi.binary_dilation(fine >= LEVEL, structure=et.disk(ss // 2))   # +0.5 px safety margin
        union = np.maximum(inside.astype(float), mk.astype(float))
        union = ndi.gaussian_filter(union, ss * 0.35)           # remove 1/8-px stair steps only
        union[[0, -1], :] = inside[[0, -1], :]                  # box border: keep the outline as it was
        union[:, [0, -1]] = inside[:, [0, -1]]
        cs = find_contours(union, 0.5)
        if not cs:
            continue
        c = max(cs, key=len)
        seg = np.stack([x0 + (c[:, 1] + 0.5) / ss, y0 + (c[:, 0] + 0.5) / ss], axis=1)
        tree = cKDTree(curve)
        i0, i1 = tree.query(seg[0])[1], tree.query(seg[-1])[1]
        n = len(curve)
        fwd = (i1 - i0) % n
        mid_f = curve[(i0 + fwd // 2) % n]
        in_box = (x0 <= mid_f[0] < x1) and (y0 <= mid_f[1] < y1)
        if in_box:      # replace i0 -> i1 going forward
            keep = curve[[(i1 + k) % n for k in range(n - fwd)]]
            curve = np.vstack([seg, keep[1:]]) if np.allclose(seg[-1], keep[0], atol=2) else np.vstack([seg, keep])
        else:           # replace i1 -> i0 going forward; reverse seg to keep orientation
            back = (i0 - i1) % n
            keep = curve[[(i0 + k) % n for k in range(n - back)]]
            curve = np.vstack([seg[::-1], keep])
    return resample(curve, 0.5)


def bridge(curve: np.ndarray, x_max: float, rows: tuple[int, int]) -> np.ndarray:
    """Replace the stretch of outline with x < x_max between the two rows by a
    cubic Hermite curve that matches position and direction at both ends."""
    y0, y1 = rows
    n = len(curve)
    side = curve[:, 0] < x_max
    i0 = int(np.argmin(np.where(side, np.abs(curve[:, 1] - y0), np.inf)))
    i1 = int(np.argmin(np.where(side, np.abs(curve[:, 1] - y1), np.inf)))
    fwd = (i1 - i0) % n
    if fwd > n // 2:                     # make i0 -> i1 the short way round
        i0, i1 = i1, i0
        fwd = (i1 - i0) % n
    p0, p1 = curve[i0], curve[i1]
    k = 8   # directions measured only from the outline OUTSIDE the bridged stretch
    t0 = curve[i0] - curve[(i0 - k) % n]
    t1 = curve[(i1 + k) % n] - curve[i1]
    chord = np.hypot(*(p1 - p0))
    t0 = t0 / np.hypot(*t0) * chord
    t1 = t1 / np.hypot(*t1) * chord
    t = np.linspace(0, 1, max(fwd, 8))[:, None]
    h00, h10, h01, h11 = 2*t**3 - 3*t**2 + 1, t**3 - 2*t**2 + t, -2*t**3 + 3*t**2, t**3 - t**2
    seg = h00 * p0 + h10 * t0 + h01 * p1 + h11 * t1
    rest = curve[[(i1 + j) % n for j in range(1, n - fwd)]]
    return np.vstack([seg, rest])


def _canon(c: np.ndarray) -> np.ndarray:
    """Same orientation for every closed curve (positive signed area in image
    coordinates), rolled to start at its lowest point (max y)."""
    x, y = c[:, 0], c[:, 1]
    if 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) < 0:
        c = c[::-1]
    return np.roll(c, -int(np.argmax(c[:, 1])), axis=0)


def lock_top(curve: np.ndarray, path: str = APPROVED_TOP) -> np.ndarray:
    """Replace everything above lock_row with the approved curve, and hand off
    smoothly over hand_off_px below it (the two curves must already be close
    there; the hand-off moves each new point toward the nearest approved point)."""
    from scipy.spatial import cKDTree
    d = json.loads(Path(path).read_text())
    lock, hand = d["lock_row"], d["hand_off_px"]
    app = _canon(np.array(d["closed_curve"], float))
    new = _canon(curve)
    a_top = np.where(app[:, 1] < lock)[0]
    n_top = np.where(new[:, 1] < lock)[0]
    if not (np.all(np.diff(a_top) == 1) and np.all(np.diff(n_top) == 1)):
        raise RuntimeError("top-of-head region is not one contiguous stretch")
    joined = np.vstack([new[:n_top[0]], app[a_top], new[n_top[-1] + 1:]])
    band = (joined[:, 1] >= lock) & (joined[:, 1] < lock + hand)
    near = app[cKDTree(app).query(joined[band])[1]]
    w = ((lock + hand - joined[band, 1]) / hand)[:, None]
    gap = np.hypot(*(near - joined[band]).T).max() if band.any() else 0.0
    if gap > 8.0:   # a few px eased over the hand-off is gentle; the eye bug was 14 px
        raise RuntimeError(f"hand-off curves are {gap:.1f} px apart; too far to blend safely")
    joined[band] = w * near + (1 - w) * joined[band]
    return resample(np.vstack([joined, joined[:1]]), 0.5)[:-1]


def splice_precise(curve: np.ndarray, path: str = PRECISE_TOP) -> np.ndarray:
    """Replace the outline over the top of his head with the precise stretch,
    blending the first/last PRECISE_BLEND px into the outline."""
    from scipy.spatial import cKDTree
    st = np.array(json.loads(Path(path).read_text())["curve"], float)
    c = _canon(curve)
    t = cKDTree(c)
    i, j = t.query(st[0])[1], t.query(st[-1])[1]
    n = len(c)
    fwd = [(i + k) % n for k in range((j - i) % n + 1)]
    bwd = [(i - k) % n for k in range((i - j) % n + 1)]
    over = fwd if c[fwd, 1].mean() < c[bwd, 1].mean() else bwd
    if over is bwd:
        st = st[::-1]; i, j = j, i
        over = [(i + k) % n for k in range((j - i) % n + 1)]
    st = st.copy()
    arc = np.r_[0, np.cumsum(np.hypot(*np.diff(st, axis=0).T))]
    for end_idx, dist in ((i, arc), (j, arc[-1] - arc)):
        w = np.clip(dist / PRECISE_BLEND, 0, 1)[:, None]
        anchor = c[end_idx]
        near = w < 1
        st[near[:, 0]] = (w * st + (1 - w) * anchor)[near[:, 0]]
    keep = [k for k in range(n) if k not in set(over)]
    start = (j + 1) % n
    rest = c[[(start + k) % n for k in range(len(keep))]]
    joined = np.vstack([st, rest])
    return resample(np.vstack([joined, joined[:1]]), 0.5)[:-1]


def mark_check(curve: np.ndarray, fields: dict) -> dict:
    """Sub-pixel check: how much of each eye-mark pixel lies outside the outline."""
    from matplotlib.path import Path as MPath
    path = MPath(curve)
    res = {}
    for name, ((x0, y0, x1, y1), field, mark) in fields.items():
        ss = 8
        xs = x0 + (np.arange((x1 - x0) * ss) + 0.5) / ss
        ys = y0 + (np.arange((y1 - y0) * ss) + 0.5) / ss
        X, Y = np.meshgrid(xs, ys)
        f = path.contains_points(np.c_[X.ravel(), Y.ravel()]).reshape(y1 - y0, ss, x1 - x0, ss).mean(axis=(1, 3))
        res[name] = {"mark_pixels": int(mark.sum()),
                     "mark_pixels_not_fully_inside": int((mark & (f < 1)).sum()),
                     "mark_area_outside_px": round(float(((1 - f) * mark).sum()), 3)}
    return res


def sample(tck, n: int) -> np.ndarray:
    x, y = splev(np.linspace(0, 1, n, endpoint=False), tck)
    return np.stack([x, y], axis=1)


def turning(xy: np.ndarray) -> np.ndarray:
    """Absolute turning angle at each point of a closed polyline (radians)."""
    d = np.diff(np.vstack([xy, xy[:1]]), axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    t = np.diff(np.concatenate([ang, ang[:1]]))
    return np.abs((t + np.pi) % (2 * np.pi) - np.pi)


def roughness_in_box(xy: np.ndarray, box) -> float:
    x0, y0, x1, y1 = box
    m = (xy[:, 0] >= x0) & (xy[:, 0] < x1) & (xy[:, 1] >= y0) & (xy[:, 1] < y1)
    if m.sum() < 3:
        return 0.0
    return float(turning(xy)[m].sum())


def main() -> int:
    rgb = np.asarray(Image.open("data/photos/anchor_front.webp").convert("RGB"))
    a = coverage(rgb)
    raw = resample(level_contour(a, 0.0), 1.0)          # unblurred 50% edge: "the raw edge"
    tck, mid = fit_outline(a)
    curve = resample(sample(tck, 6000), 1.0)
    fields = eye_mark_fields(rgb, a)
    curve = merge_marks(curve, fields)
    for g in OWNER_GUIDED:
        curve = resample(bridge(curve, g["x_max"], g["rows"]), 0.5)
    curve = resample(np.vstack([curve, curve[:1]]), 0.5)[:-1]   # even spacing all the way round the loop
    if Path(APPROVED_TOP).exists():
        curve = lock_top(curve)
    if Path(PRECISE_TOP).exists():
        curve = splice_precise(curve)
    marks = mark_check(curve, fields)
    # distance from the smooth curve to the 50% level it was fitted to
    from scipy.spatial import cKDTree
    dist = cKDTree(curve).query(resample(mid, 1.0))[0]
    ledger = json.loads(Path("data/strands/ledger.json").read_text())
    worse = []
    for t in ledger["tiles"]:
        box = (t["x0"], t["y0"], t["x1"], t["y1"])
        r_raw, r_new = roughness_in_box(raw, box), roughness_in_box(curve, box)
        if r_new > 0 and r_new >= r_raw:
            worse.append(t["id"])
    out = {
        "about": "Prince's body outline (step 3, part 1). Closed periodic cubic "
                 "spline in photo pixels (x right, y down). Runs through his soft "
                 "edge at 50% coverage of a blurred coverage map; ears, peets and "
                 "tuft are still included and get split off in later steps.",
        "photo": "data/photos/anchor_front.webp",
        "status": "first pass, not yet verified",
        "params": {"sides": f"edge of solid body (opening r={SOLID_R_SIDES}), RMS {SIDE_RMS} px",
                   "peets": f"edge of solid body (opening r={SOLID_R_PEETS}), RMS {PEET_RMS} px", "level": LEVEL,
                   "sensitive_zone": f"y < {SENSITIVE_MAX_Y} (ears, eyes), strands removed (r={STRAND_R})",
                   "sensitive_fit_blur_rms_px": list(SENSITIVE_FIT),
                   "peet_zone": f"below the approved peet line ({PEET_LINE}), ramp +-{PEET_RAMP} px",
                   "peet_fit_blur_rms_px": list(PEET_FIT),
                   "handoff_px": HANDOFF},
        "spline": {"t": tck[0].tolist(), "cx": tck[1][0].tolist(), "cy": tck[1][1].tolist(), "k": tck[2]},
        "fit_to_50pct_level_px": {"mean": round(float(dist.mean()), 2), "max": round(float(dist.max()), 2)},
        "tiles_where_not_smoother_than_raw": worse,
        "eye_marks_check": marks,
        "owner_guided": OWNER_GUIDED,
        "locked": f"rows above the approved top of head ({APPROVED_TOP}); ears/dip/ear bases from {PRECISE_TOP}",
        "sampled_curve": [[round(float(x), 3), round(float(y), 3)] for x, y in curve],
    }
    Path("data/strands/body_outline.json").write_text(json.dumps(out, indent=1))
    print(f"curve points {len(curve)}; fit to 50% level: mean {dist.mean():.2f}, max {dist.max():.2f} px")
    print(f"total turning: raw edge {turning(raw).sum():.0f} rad, smooth outline {turning(curve).sum():.0f} rad")
    print(f"tiles where the outline is NOT smoother than the raw edge: {worse or 'none'}")
    print(f"eye marks check: {marks}")
    return 0 if not worse else 1


if __name__ == "__main__":
    sys.exit(main())
