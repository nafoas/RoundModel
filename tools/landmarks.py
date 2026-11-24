"""Named landmarks on the anchor photo, each tied to one of his parts (3D grounding, step 2).

Owner, 2026-11-16: anchor his model in a real 3D space so every shape can be traced back and nothing of
him is misread between shots. Landmarks are the fixed points of him that are unmistakable from almost any
angle; in a new photo they are found first, and its camera is solved from them.

Each landmark: a name by HIS side (his left = the picture's right = the room's +X), the part it belongs to,
its picture position (sub-pixel where measured that finely), how it was found, how sure (px), its mirror
partner, and its kind:
- "surface point": a fixed point of him (an eye's centre, a nostril wing, an ear-base end);
- "view-dependent": a point that slides over him as the camera moves (the topmost point of an ear, the
  catchlight on an eye, where a line crosses his outline). Useful here, never matched as a fixed point.

Usage: python tools/landmarks.py -> data/strands/landmarks.json, docs/images/space/landmarks*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
OUT_IMG = ROOT / "docs/images/space"
# His eyes on the anchor photo: where his black marking touches his eye (the top) and where a soft fringe of lashes and
# fur lies along it, the photo shows no boundary, so these are OWNER-GUIDED (2026-11-24, CLAUDE.md precision
# protocol): the top sits halfway between the plain oval's top and the dark edge of his marking ("It is between
# B and C"); on his left eye the edge points along his fringe (down the picture-left side from the top, before the
# measured edge first steps inward) are left out ("a little strip of fur that accidentally got captured").
EYE_OWNER = {"eye_his_right": dict(top=0.5), "eye_his_left": dict(top=0.5, fringe=True)}
EYE_BOXES = {"eye_his_right": (260, 330, 400, 530), "eye_his_left": (660, 320, 800, 520)}   # picture left / right
N_DIRS = 180


def load(p):
    return json.loads((ROOT / p).read_text())


# ---------------------------------------------------------------- eyes
def conic_to_ellipse(coef, mx, my):
    """Conic A x^2 + B xy + C y^2 + D x + E y + F = 0 (in coordinates shifted by mx, my) -> centre, semi-axes (a >= b),
    long axis angle (deg)."""
    A, B, Cc, Dd, E, Fc = coef
    den = B * B - 4 * A * Cc
    x0 = (2 * Cc * Dd - B * E) / den; y0 = (2 * A * E - B * Dd) / den
    num = 2 * (A * E * E + Cc * Dd * Dd - B * Dd * E + den * Fc)
    r = np.sqrt((A - Cc) ** 2 + B * B)
    ax1 = -np.sqrt(num * (A + Cc + r)) / den; ax2 = -np.sqrt(num * (A + Cc - r)) / den
    th = 0.5 * np.arctan2(-B, Cc - A)
    a, b = (ax1, ax2) if ax1 >= ax2 else (ax2, ax1)
    if ax1 < ax2:
        th += np.pi / 2
    return np.array([x0 + mx, y0 + my]), float(a), float(b), float(np.degrees(th) % 180)


def fit_ellipse_through(P, T):
    """The direct least-squares ellipse fit (Fitzgibbon et al. 1999) with one exact condition: the ellipse passes
    through the point T. (Used for his eye: through the point where his eye meets his lash line, 2026-11-19.)"""
    from scipy.linalg import eig, null_space
    mx, my = P[:, 0].mean(), P[:, 1].mean()
    row = lambda x, y: np.c_[x * x, x * y, y * y, x, y, np.ones_like(x)]
    D = row(P[:, 0] - mx, P[:, 1] - my)
    N = null_space(row(np.array([T[0] - mx]), np.array([T[1] - my])))          # conics through T
    C = np.zeros((6, 6)); C[0, 2] = C[2, 0] = 2; C[1, 1] = -1                  # 4AC - B^2: ellipse when > 0
    w, V = eig(N.T @ (D.T @ D) @ N, N.T @ C @ N)
    best = None
    for lam, y in zip(np.real(w), np.real(V.T)):
        a = N @ y
        if np.isfinite(lam) and lam > 0 and 4 * a[0] * a[2] - a[1] ** 2 > 0 and (best is None or lam < best[0]):
            best = (lam, a)
    return conic_to_ellipse(best[1], mx, my)


def fit_ellipse(P):
    """Direct least-squares ellipse fit (Fitzgibbon et al. 1999). Returns centre, semi-axes (a >= b),
    angle of the long axis (deg, picture coords: x right, y down), and the conic."""
    x, y = P[:, 0] - P[:, 0].mean(), P[:, 1] - P[:, 1].mean()
    D = np.c_[x * x, x * y, y * y, x, y, np.ones_like(x)]
    S = D.T @ D
    C = np.zeros((6, 6)); C[0, 2] = C[2, 0] = 2; C[1, 1] = -1
    S1, S2, S3 = S[:3, :3], S[:3, 3:], S[3:, 3:]
    T = -np.linalg.solve(S3, S2.T)
    M = S1 + S2 @ T
    M = np.array([M[2] / 2, -M[1], M[0] / 2])
    w, v = np.linalg.eig(M)
    v = np.real(v); cond = 4 * v[0] * v[2] - v[1] ** 2
    a1 = v[:, np.argmax(cond > 0)]
    A, B, Cc, Dd, E, Fc = np.r_[a1, T @ a1]
    den = B * B - 4 * A * Cc
    x0 = (2 * Cc * Dd - B * E) / den; y0 = (2 * A * E - B * Dd) / den
    num = 2 * (A * E * E + Cc * Dd * Dd - B * Dd * E + den * Fc)
    r = np.sqrt((A - Cc) ** 2 + B * B)
    ax1 = -np.sqrt(num * (A + Cc + r)) / den; ax2 = -np.sqrt(num * (A + Cc - r)) / den
    th = 0.5 * np.arctan2(-B, Cc - A)
    a, b = (ax1, ax2) if ax1 >= ax2 else (ax2, ax1)
    if ax1 < ax2:
        th += np.pi / 2
    c = np.array([x0 + P[:, 0].mean(), y0 + P[:, 1].mean()])
    return c, float(a), float(b), float(np.degrees(th) % 180)


def ellipse_dist(P, c, a, b, ang):
    t = np.radians(ang); R = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]])
    q = (P - c) @ R.T
    s = np.sqrt((q[:, 0] / a) ** 2 + (q[:, 1] / b) ** 2)
    return (s - 1) * np.sqrt(a * b)                     # approx. distance, + outside


def measure_eye(lum, box, owner=None):
    """His eye: a smooth, glossy oval (an eye has no corners or bends; owner, 2026-11-19/24). Its edge is measured
    along N_DIRS directions from its middle (where the brightness crosses halfway between eyeball and fur, to a
    fraction of a pixel); directions that run into lashes, his black marking or fur over the eye are dropped by a
    robust oval fit. `owner` (EYE_OWNER, anchor only): owner-guided top and fringe, see above.
    """
    x0, y0, x1, y1 = box
    L = ndi.gaussian_filter(lum[y0:y1, x0:x1], 0.8)
    dark = L < 70
    core = ndi.binary_opening(dark, structure=np.ones((7, 7), bool))         # lashes are thinner than 7 px
    lab, n = ndi.label(core); k = int(np.argmax(ndi.sum(core, lab, range(1, n + 1)))) + 1
    ball = ndi.binary_fill_holes(lab == k)
    cy, cx = np.argwhere(ball).mean(0) + 0.5
    eye_lum = float(np.median(L[ball & dark]))
    ring = ndi.binary_dilation(ball, iterations=12) & ~ndi.binary_dilation(ball, iterations=5) & ~dark
    fur_lum = float(np.median(L[ring])); level = (eye_lum + fur_lum) / 2
    pts, used = [], []
    r = np.arange(0, 70, 0.25)
    for ang in np.linspace(0, 2 * np.pi, N_DIRS, endpoint=False):
        xs = cx + r * np.cos(ang) - 0.5; ys = cy + r * np.sin(ang) - 0.5
        v = ndi.map_coordinates(L, [ys, xs], order=1, mode="nearest")
        above = np.flatnonzero((v[1:] >= level) & (v[:-1] < level) & (r[1:] > 4))
        if not len(above):
            continue
        i = above[0]; t = (level - v[i]) / (v[i + 1] - v[i])
        rr = r[i] + t * (r[i + 1] - r[i])
        pts.append([x0 + cx + rr * np.cos(ang), y0 + cy + rr * np.sin(ang)]); used.append(np.degrees(ang))
    P = np.array(pts); keep = np.ones(len(P), bool)
    def robust(Q, through=None):
        fit = (lambda R: fit_ellipse_through(R, through)) if through is not None else fit_ellipse
        k = np.ones(len(Q), bool)
        for _ in range(6):
            c_, a_, b_, t_ = fit(Q[k]); d_ = ellipse_dist(Q, c_, a_, b_, t_)
            mad = 1.4826 * np.median(np.abs(d_[k] - np.median(d_[k])))
            k = np.abs(d_) <= max(2.5 * mad, 0.75)
        return fit(Q[k]), k
    (c, a, b, th), keep = robust(P)
    use = np.ones(len(P), bool); top = top_point = None
    if owner:
        top = lash_line_point(L, level, ball, x0, y0)
        if owner.get("fringe") and top is not None:
            # down the picture-left side from his eye's top: the points before the measured edge first steps inward
            # (its distance from the smooth oval drops by more than 1 px from one point to the next) lie on the fringe
            d0 = ellipse_dist(P, c, a, b, th)
            ang = np.degrees(np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0]))
            down = np.mod(np.degrees(np.arctan2(top[1] - c[1], top[0] - c[0])) - ang, 360)
            side = np.flatnonzero((down < 180) & (np.abs(d0) < 5)); side = side[np.argsort(down[side])]
            for i in range(1, len(side)):
                if d0[side[i - 1]] - d0[side[i]] > 1.0:
                    use[side[:i]] = False
                    break
            (c, a, b, th), _ = robust(P[use])
        if top is not None:
            t = np.linspace(0, 2 * np.pi, 800); tr = np.radians(th)
            ov = c + np.c_[a * np.cos(t) * np.cos(tr) - b * np.sin(t) * np.sin(tr), a * np.cos(t) * np.sin(tr) + b * np.sin(t) * np.cos(tr)]
            u = (top - c) / np.linalg.norm(top - c)
            plain_top = ov[np.argmax(ov @ u)]
            top_point = plain_top + owner.get("top", 0.0) * (top - plain_top)
            (c, a, b, th), k2 = robust(P[use], top_point)
            keep = np.zeros(len(P), bool); keep[np.flatnonzero(use)[k2]] = True
    d = ellipse_dist(P, c, a, b, th)
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False); tr = np.radians(th)
    outline = c + np.c_[a * np.cos(t) * np.cos(tr) - b * np.sin(t) * np.sin(tr), a * np.cos(t) * np.sin(tr) + b * np.sin(t) * np.cos(tr)]
    # catchlight: the bright spot inside the eye (brightness-weighted centre of its brightest pixels)
    t = np.radians(th); Rm = np.array([[np.cos(t), np.sin(t)], [-np.sin(t), np.cos(t)]])
    H, W = L.shape; gy, gx = np.mgrid[0:H, 0:W] + 0.5
    q = (np.c_[gx.ravel() + x0, gy.ravel() + y0] - c) @ Rm.T
    inside = (((q[:, 0] / a) ** 2 + (q[:, 1] / b) ** 2) < 0.8).reshape(H, W)
    raw = lum[y0:y1, x0:x1]
    hi = inside & (raw >= np.percentile(raw[inside], 99.5))
    lab2, n2 = ndi.label(hi); k2 = int(np.argmax(ndi.sum(raw * hi, lab2, range(1, n2 + 1)))) + 1
    spot = lab2 == k2; w = raw[spot] - level
    sy, sx = np.argwhere(spot).T
    catch = np.array([x0 + 0.5 + (sx * w).sum() / w.sum(), y0 + 0.5 + (sy * w).sum() / w.sum()])
    return dict(centre=c, outline=outline, semi_axes=(a, b), angle_deg=th, aspect=b / a, edge_points=P, kept=keep,
                left_out_as_fringe=~use, marking_edge=top, top_point=top_point, owner=owner,
                rms_px=float(np.sqrt(np.mean(d[keep] ** 2))), kept_fraction=float(keep.mean()),
                dropped_directions_deg=np.round(np.array(used)[~keep], 0).tolist(),
                eye_lum=eye_lum, fur_lum=fur_lum, catchlight=catch)


def lash_line_point(L, level, ball, x0, y0):
    """Where his eye meets his upper lash clump: the dark region around the eyeball (darker than `level`) is split
    where it narrows (watershed on each pixel's distance from its edge); the eye is the thickest part; the clump is
    the part above it. Returns the middle of the line between them (picture px), or None when no clump sits on
    the eye. (2026-11-19: the dark region also holds his black eye ring and lashes, so it is used only to find
    this one point; owner: "they go around his little eye ring too".)"""
    from skimage import measure as skm, morphology, segmentation
    dark = ndi.binary_fill_holes(L < level)
    lab, _ = ndi.label(dark)
    comp = lab == np.bincount(lab[ball]).argmax()
    dist = ndi.distance_transform_edt(comp)
    ws = segmentation.watershed(-dist, skm.label(morphology.h_maxima(dist, 2) & comp), mask=comp)
    eye = ws == ws[np.unravel_index(np.argmax(dist), dist.shape)]
    ey = np.nonzero(eye)[0].mean()
    best = None
    for other in set(np.unique(ws[comp])) - {0, int(ws[np.unravel_index(np.argmax(dist), dist.shape)])}:
        part = ws == other
        touch = eye & ndi.binary_dilation(part)
        if touch.sum() and np.nonzero(part)[0].mean() < ey and (best is None or touch.sum() > best[0]):
            ys, xs = np.nonzero(touch)
            best = (int(touch.sum()), np.array([x0 + xs.mean() + 0.5, y0 + ys.mean() + 0.5]))
    return None if best is None else best[1]


# ---------------------------------------------------------------- the rest of him
def lowest_point(poly, tol=4.0):
    """The lowest point of a part (largest y); if its bottom is flat, the middle of the flat stretch."""
    y = poly[:, 1].max(); flat = poly[poly[:, 1] >= y - tol]
    return np.array([float(np.median(flat[:, 0])), float(y)])


def at_x(curve, x):
    o = curve[np.argsort(curve[:, 0])]
    return np.array([float(x), float(np.interp(x, o[:, 0], o[:, 1]))])


def top_outline_at(outline, x):
    """His outline's topmost crossing at picture x (the top of his head there)."""
    seg = np.c_[outline[:-1], outline[1:]]
    ys = []
    for x_a, y_a, x_b, y_b in seg:
        if (x_a - x) * (x_b - x) <= 0 and x_a != x_b:
            ys.append(y_a + (x - x_a) / (x_b - x_a) * (y_b - y_a))
    return np.array([float(x), float(min(ys))])


def peet_specks(lum, poly, min_contrast=25.0):
    """Small dark marks on a peet (fixed marks of him): local dark spots well below the fur around them."""
    from matplotlib.path import Path as MP
    H, W = lum.shape
    x0, y0 = np.floor(poly.min(0)).astype(int); x1, y1 = np.ceil(poly.max(0)).astype(int)
    sub = ndi.gaussian_filter(lum[y0:y1, x0:x1], 1.2)
    bg = ndi.median_filter(sub, size=21)
    gy, gx = np.mgrid[y0:y1, x0:x1] + 0.5
    inside = MP(poly).contains_points(np.c_[gx.ravel(), gy.ravel()]).reshape(sub.shape)
    inside = ndi.binary_erosion(inside, iterations=12)      # not the darker fur along the peet's own edge
    c = (bg - sub) * inside
    lab, n = ndi.label(c > min_contrast)
    out = []
    for i in range(1, n + 1):
        m = lab == i; w = c[m]; yy, xx = np.argwhere(m).T
        out.append(dict(at=[x0 + 0.5 + float((xx * w).sum() / w.sum()), y0 + 0.5 + float((yy * w).sum() / w.sum())],
                        contrast=round(float(w.max()), 1), px=int(m.sum())))
    return sorted(out, key=lambda s: -s["contrast"])


def main() -> int:
    photo = np.array(Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB"))
    lum = photo.astype(float).mean(2)
    outline = np.array(load("data/strands/body_outline.json")["sampled_curve"])
    ears = load("data/strands/parts_ears.json")["parts"]
    peets = load("data/strands/parts_peets.json")["parts"]
    bases = load("data/strands/ear_bases.json")
    lines = load("data/lines/body_parts_lines.json")
    face = load("data/strands/whiskers_full.json")
    fl = face["landmarks"]; corners = face["pads"]["corners"]
    head, fold = np.array(lines["head_line"]["sampled_curve"]), np.array(lines["fold_line"]["sampled_curve"])
    axis_x = lines["head_line"]["axis_x"]

    LM = {}

    def add(name, part, at, how, sure_px, kind="surface point", mirror=None, **extra):
        LM[name] = dict(part=part, at_px=np.round(np.asarray(at, float), 2).tolist(), how=how, sure_px=sure_px,
                        kind=kind, mirror_of=mirror, **extra)

    eyes = {}
    for name, box in EYE_BOXES.items():
        e = eyes[name] = measure_eye(lum, box, EYE_OWNER.get(name))
        mirror = "eye_his_left" if name == "eye_his_right" else "eye_his_right"
        add(name, "head", e["centre"],
            f"middle of his eye (outline_px): a smooth oval fitted to the eye's own edge (measured in {N_DIRS} "
            f"directions to a fraction of a pixel; {int(e['kept'].sum())}/{len(e['kept'])} kept: the rest ran into "
            f"lashes, his black marking or fur over the eye; fit rms {e['rms_px']:.2f} px). OWNER-GUIDED top "
            f"(2026-11-24: 'between B and C', docs/images/space/eye_top_choices.png): halfway between the plain "
            f"oval's top and the dark edge of his marking"
            f"{'; the soft fringe along its picture-left side left out (' + str(int(e['left_out_as_fringe'].sum())) + ' points: a strip of fur, owner)' if e['left_out_as_fringe'].any() else ''}", 2.0, mirror=mirror,
            oval=dict(semi_axes_px=np.round(e["semi_axes"], 2).tolist(), long_axis_angle_deg=round(e["angle_deg"], 1),
                      short_over_long=round(e["aspect"], 3),
                      note=("the oval fitted to his eye (before its top is narrowed): short/long is a clue to how far "
                            "the eye faces away from the camera")),
            outline_px=np.round(e["outline"][::2], 2).tolist())
        add(name + "_catchlight", "head", e["catchlight"],
            "brightness-weighted centre of the brightest spot inside the eye (the light's reflection)", 0.5,
            kind="view-dependent", mirror=mirror + "_catchlight")
    add("nostril_wing_his_right", "head", fl["nostril_wing_left"], "outer end of the nose's dark shape "
        "(tools/whisker_chains.py measure_pads), whole pixels; the shape fades out gradually there", 3.0,
        mirror="nostril_wing_his_left")
    add("nostril_wing_his_left", "head", fl["nostril_wing_right"], "as nostril_wing_his_right", 3.0,
        mirror="nostril_wing_his_right")
    add("nose_y_centre", "head", [fl["philtrum_x"], fl["philtrum_top"]],
        "where the two sides of his nose meet and the philtrum starts (the middle of the Y)", 1.5)
    add("philtrum_bottom", "head", [fl["philtrum_x"], fl["philtrum_bottom"]],
        "bottom of the philtrum, where his mouth splits", 1.5)
    add("mouth_corner_his_right", "head", fl["mouth_corner_left"], "outer end of the mouth's dark line, whole px",
        1.5, mirror="mouth_corner_his_left")
    add("mouth_corner_his_left", "head", fl["mouth_corner_right"], "as mouth_corner_his_right", 1.5,
        mirror="mouth_corner_his_right")
    add("lip_corner_his_right", "head", corners["image_left"]["lip_corner"],
        "corner of the approved whisker-pad outline at his lip line", 2.0, mirror="lip_corner_his_left")
    add("lip_corner_his_left", "head", corners["image_right"]["lip_corner"], "as lip_corner_his_right", 2.0,
        mirror="lip_corner_his_right")
    add("chin_midline", "head", at_x(head, axis_x),
        "the approved head line where it crosses his midline (under his mouth)", 1.0,
        note="owner-guided line (data/lines/body_parts_lines.json)")
    # ears (picture left = his right)
    for side, key, base_key in (("his_right", "ear_image_left", "ear_image_left_base"),
                                ("his_left", "ear_image_right", "ear_image_right_base")):
        other = "his_left" if side == "his_right" else "his_right"
        poly = np.array(ears[key]["exterior"]); b = np.array(bases[base_key])
        inner, outer = (b[0], b[-1]) if abs(b[0, 0] - axis_x) < abs(b[-1, 0] - axis_x) else (b[-1], b[0])
        add(f"ear_tip_{side}", f"ear ({side.replace('_', ' ')})", poly[np.argmin(poly[:, 1])],
            "topmost point of the approved ear outline", 1.0, kind="view-dependent", mirror=f"ear_tip_{other}")
        add(f"ear_base_inner_{side}", f"ear ({side.replace('_', ' ')})", inner,
            "inner end of the approved ear base (a notch in his outline)", 1.0, mirror=f"ear_base_inner_{other}")
        add(f"ear_base_outer_{side}", f"ear ({side.replace('_', ' ')})", outer,
            "outer end of the approved ear base (a notch in his outline)", 1.0, mirror=f"ear_base_outer_{other}")
    crown_x = (LM["ear_base_inner_his_right"]["at_px"][0] + LM["ear_base_inner_his_left"]["at_px"][0]) / 2
    add("crown_front", "top of his head (the strip joining his ears)", top_outline_at(outline, crown_x),
        "his outline at the middle of the strip joining his ears", 1.0, kind="view-dependent",
        note=("owner: the strip is the top of his head seen from above; here his head's top starts going back, "
              "so this point is where the camera's line of sight grazes it"))
    # body
    add("fold_midline", "intermediate bnuy / undercarriage", at_x(fold, axis_x),
        "the approved lower fold where it crosses his midline", 2.0)
    for side, key in (("his_right", "cream_peet_image_left"), ("his_left", "gray_peet_image_right")):
        other = "his_left" if side == "his_right" else "his_right"
        poly = np.array(peets[key]["exterior"])
        add(f"peet_bottom_{side}", f"peet ({side.replace('_', ' ')})", lowest_point(poly),
            "lowest point of the approved peet outline (where it meets the floor)", 1.0,
            kind="view-dependent", mirror=f"peet_bottom_{other}",
            note="used to put the floor under him; a rounded peet touches the floor near here")
        sp = peet_specks(lum, poly)
        for i, s in enumerate(sp[:3]):
            add(f"peet_mark_{side}_{i + 1}", f"peet ({side.replace('_', ' ')})", s["at"],
                f"small dark mark on the peet (contrast {s['contrast']} grey levels, {s['px']} px)", 1.5,
                note="a mark on his fur, so a fixed point of him if it shows in another photo")
    tuft = np.array(peets["underfluff_tuft"]["exterior"])
    add("belly_front", "belly (the underfluff tuft)", tuft.mean(0),
        "middle of the underfluff tuft", 5.0, kind="view-dependent",
        note="owner: the tuft is his belly seen from below; it carries on back underneath him")
    pr, pl = np.array(LM["peet_bottom_his_right"]["at_px"]), np.array(LM["peet_bottom_his_left"]["at_px"])
    add("floor_contact_midpoint", "floor", (pr + pl) / 2,
        "midpoint of his two peets' lowest points: the room's origin is on the floor under here", 1.0,
        kind="view-dependent")

    pairs = sorted({tuple(sorted((k, v["mirror_of"]))) for k, v in LM.items() if v["mirror_of"]})
    doc = dict(about=__doc__.split("\n\n")[0], photo="data/photos/anchor_front.webp",
               coords="picture px, x right, y down; pixel (c, r) covers [c, c+1) x [r, r+1)",
               sides="named by HIS side: his left = the picture's right = the room's +X",
               status="first pass, owner review pending", landmarks=LM, mirror_pairs=[list(p) for p in pairs],
               eye_fit={k: dict(rms_px=round(e["rms_px"], 3), kept_fraction=round(e["kept_fraction"], 3),
                                dropped_directions_deg=e["dropped_directions_deg"],
                                eyeball_lum=round(e["eye_lum"], 1), fur_lum=round(e["fur_lum"], 1))
                        for k, e in eyes.items()})
    (ROOT / "data/strands/landmarks.json").write_text(json.dumps(doc, indent=1))
    sheets(photo, LM, eyes)
    for k, v in LM.items():
        print(f"{k:32s} {v['part']:45s} {v['at_px']}  ±{v['sure_px']}  {v['kind']}")
    print({k: (round(e['rms_px'], 2), round(e['kept_fraction'], 2), round(e['aspect'], 3)) for k, e in eyes.items()})
    return 0


def sheets(photo, LM, eyes):
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    sc = 2
    im = Image.fromarray(photo).resize((photo.shape[1] * sc, photo.shape[0] * sc), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for k, v in LM.items():
        x, y = (np.array(v["at_px"]) * sc)
        col = (220, 0, 120) if v["kind"] == "surface point" else (0, 120, 220)
        d.line([(x - 9, y), (x + 9, y)], fill=col, width=2); d.line([(x, y - 9), (x, y + 9)], fill=col, width=2)
        d.text((x + 8, y + 4), k, fill=col)
    for e in eyes.values():
        d.line([tuple(p * sc) for p in np.vstack([e["outline"], e["outline"][:1]])], fill=(255, 200, 0), width=1)
    d.text((10, 10), "Landmarks (first pass). Magenta = fixed points of him; blue = view-dependent points. "
                     "Names are by HIS side (his left = picture right). Yellow = his eyes' outlines.", fill=(0, 0, 0))
    im.save(OUT_IMG / "landmarks.png")
    # eyes at 6x: photo, and photo with the measured edge points (kept green, dropped red) and the oval
    rows = []
    for name, box in EYE_BOXES.items():
        e = eyes[name]; x0, y0, x1, y1 = box; s = 6
        crop = Image.fromarray(photo[y0:y1, x0:x1]).resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
        mk = crop.copy(); dr = ImageDraw.Draw(mk)
        c = e["centre"]
        dr.line([((p[0] - x0) * s, (p[1] - y0) * s) for p in np.vstack([e["outline"], e["outline"][:1]])],
                fill=(0, 230, 110), width=3)
        for p, k in zip(e["edge_points"], e["kept"]):
            X, Y = (p[0] - x0) * s, (p[1] - y0) * s
            dr.ellipse([X - 3, Y - 3, X + 3, Y + 3], fill=(0, 200, 0) if k else (255, 0, 0))
        marks = ((c, (220, 0, 120)), (e["catchlight"], (0, 120, 220))) + (((e["top_point"], (255, 0, 0)),) if e["top_point"] is not None else ())
        for p, col in marks:
            X, Y = (p[0] - x0) * s, (p[1] - y0) * s
            dr.line([(X - 12, Y), (X + 12, Y)], fill=col, width=2); dr.line([(X, Y - 12), (X, Y + 12)], fill=col, width=2)
        row = Image.new("RGB", (crop.width * 2 + 8, crop.height), (30, 30, 30)); row.paste(crop, (0, 0)); row.paste(mk, (crop.width + 8, 0))
        rows.append(row)
    o = Image.new("RGB", (rows[0].width, sum(r.height for r in rows) + 8), (30, 30, 30)); y = 0
    for r in rows:
        o.paste(r, (0, y)); y += r.height + 8
    o.save(OUT_IMG / "landmarks_eyes.png")


if __name__ == "__main__":
    raise SystemExit(main())
