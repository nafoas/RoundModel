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

BLUR = 8.0        # px: how much the coverage map is blurred before taking the 50% level
LEVEL = 0.5       # coverage level the outline runs along
SMOOTH_RMS = 4.0  # px: allowed RMS distance between the smooth curve and the 50% level
# Gentle along his furry sides, faithful where his real shape has corners
# (ears, peets, tuft). Those regions get a tighter fit (weight) and less blur.
EAR_MAX_Y = 330        # above this row: ears and the dip between them
PEET_MIN_Y = 1100      # below this row: peets and the tuft between them
FAITHFUL_WEIGHT = 3.0  # how much tighter the fit is in those regions
FAITHFUL_BLUR = 4.0


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


def faithful(xy: np.ndarray) -> np.ndarray:
    return (xy[:, 1] < EAR_MAX_Y) | (xy[:, 1] > PEET_MIN_Y)


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


def blended_contour(a: np.ndarray) -> np.ndarray:
    """50% level of the coverage, blurred BLUR on his sides and FAITHFUL_BLUR at
    the ears/peets (the two blurs are blended smoothly by row)."""
    gentle = ndi.gaussian_filter(a, BLUR)
    sharp = ndi.gaussian_filter(a, FAITHFUL_BLUR)
    rows = np.arange(a.shape[0])[:, None].astype(float)
    t = np.clip(np.maximum((EAR_MAX_Y + 40 - rows) / 40, (rows - (PEET_MIN_Y - 40)) / 40), 0, 1)
    mix = sharp * t + gentle * (1 - t)
    cs = find_contours(mix, LEVEL)
    c = max(cs, key=len)
    return np.stack([c[:, 1], c[:, 0]], axis=1)


def fit_outline(a: np.ndarray):
    """Two closed curves joined: a GENTLE one (blur BLUR, RMS SMOOTH_RMS) used on
    his furry sides, and a FAITHFUL one (blur FAITHFUL_BLUR, RMS 1 px) used at the
    ears, peets and tuft, with a smooth 40 px hand-off between them."""
    global SMOOTH_RMS
    mid_gentle = level_contour(a, BLUR)
    tck_g, _ = fit_smooth(mid_gentle)
    gentle = resample(sample(tck_g, 6000), 1.0)
    rms = SMOOTH_RMS
    SMOOTH_RMS = 1.0
    try:
        tck_f, _ = fit_smooth(level_contour(a, FAITHFUL_BLUR))
    finally:
        SMOOTH_RMS = rms
    tight = resample(sample(tck_f, 6000), 1.0)
    from scipy.spatial import cKDTree
    near = tight[cKDTree(tight).query(gentle)[1]]
    y = gentle[:, 1]
    t = np.clip(np.maximum((EAR_MAX_Y + 40 - y) / 40, (y - (PEET_MIN_Y - 40)) / 40), 0, 1)[:, None]
    joined = t * near + (1 - t) * gentle
    SMOOTH_RMS = 0.5
    try:
        tck, _ = fit_smooth(joined)
    finally:
        SMOOTH_RMS = rms
    mid = np.vstack([mid_gentle])
    return tck, mid


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
        "params": {"blur_px": BLUR, "level": LEVEL, "smooth_rms_px": SMOOTH_RMS,
                   "faithful_regions": f"y < {EAR_MAX_Y} (ears) and y > {PEET_MIN_Y} (peets, tuft)",
                   "faithful_weight": FAITHFUL_WEIGHT, "faithful_blur_px": FAITHFUL_BLUR},
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
