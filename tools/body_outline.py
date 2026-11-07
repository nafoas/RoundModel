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
PEET_MIN_Y = 1100       # below this row: peets + tuft
HANDOFF = 40            # px: smooth hand-off between zones
SENSITIVE_FIT = (2.5, 0.8)
PEET_FIT = (4.0, 1.0)
STRAND_R = 4            # px: strands thinner than ~2*STRAND_R+1 are removed before the sensitive fit


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
    """Longest closed contour at LEVEL of the blurred coverage, as (x, y)."""
    src = ndi.gaussian_filter(a, blur) if blur > 0 else a
    cs = find_contours(src, LEVEL)
    c = max(cs, key=len)
    return np.stack([c[:, 1], c[:, 0]], axis=1)


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


def _curve(src: np.ndarray, blur: float, rms: float) -> np.ndarray:
    global SMOOTH_RMS
    keep = SMOOTH_RMS
    SMOOTH_RMS = rms
    try:
        tck, _ = fit_smooth(level_contour(src, blur))
    finally:
        SMOOTH_RMS = keep
    return resample(sample(tck, 8000), 1.0)


def fit_outline(a: np.ndarray):
    """Three closed curves joined by image row: SENSITIVE (top of head: ears and
    eyes, strands removed, tightest fit), PEET (faithful), and GENTLE (his furry
    sides), with smooth HANDOFF-px transitions."""
    global SMOOTH_RMS
    from scipy.spatial import cKDTree
    mid_gentle = level_contour(a, BLUR)
    gentle = _curve(a, BLUR, SMOOTH_RMS)
    sens = _curve(without_strands(a), *SENSITIVE_FIT)
    peet = _curve(a, *PEET_FIT)
    near_s = sens[cKDTree(sens).query(gentle)[1]]
    near_p = peet[cKDTree(peet).query(gentle)[1]]
    y = gentle[:, 1]
    ts = np.clip((SENSITIVE_MAX_Y + HANDOFF - y) / HANDOFF, 0, 1)[:, None]
    tp = np.clip((y - (PEET_MIN_Y - HANDOFF)) / HANDOFF, 0, 1)[:, None]
    joined = ts * near_s + tp * near_p + (1 - ts - tp) * gentle
    keep = SMOOTH_RMS
    SMOOTH_RMS = 0.2
    try:
        tck, _ = fit_smooth(joined)
    finally:
        SMOOTH_RMS = keep
    return tck, mid_gentle


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
        "params": {"gentle_fit_blur_rms_px": [BLUR, SMOOTH_RMS], "level": LEVEL,
                   "sensitive_zone": f"y < {SENSITIVE_MAX_Y} (ears, eyes), strands removed (r={STRAND_R})",
                   "sensitive_fit_blur_rms_px": list(SENSITIVE_FIT),
                   "peet_zone": f"y > {PEET_MIN_Y}", "peet_fit_blur_rms_px": list(PEET_FIT),
                   "handoff_px": HANDOFF},
        "spline": {"t": tck[0].tolist(), "cx": tck[1][0].tolist(), "cy": tck[1][1].tolist(), "k": tck[2]},
        "fit_to_50pct_level_px": {"mean": round(float(dist.mean()), 2), "max": round(float(dist.max()), 2)},
        "tiles_where_not_smoother_than_raw": worse,
        "sampled_curve": [[round(float(x), 2), round(float(y), 2)] for x, y in curve[::4]],
    }
    Path("data/strands/body_outline.json").write_text(json.dumps(out, indent=1))
    print(f"curve length {len(curve)} px; fit to 50% level: mean {dist.mean():.2f}, max {dist.max():.2f} px")
    print(f"total turning: raw edge {turning(raw).sum():.0f} rad, smooth outline {turning(curve).sum():.0f} rad")
    print(f"tiles where the outline is NOT smoother than the raw edge: {worse or 'none'}")
    return 0 if not worse else 1


if __name__ == "__main__":
    sys.exit(main())
