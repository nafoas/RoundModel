"""Depth lines: a rough round shell of Prince, measured against his outline, and lines on it drawn back onto the
photo (3D grounding, step 5). Owner, 2026-11-16: "draw depth lines on him, going back, rooted in 3D space".

1. FIT (prince/shell.py, rule 1: his outline only measures it). A parametric shell (body + head, smoothly joined,
   resting on the surface, his head turned and tipped as measured) is rendered through the anchor camera; its
   parameters are adjusted until its silhouette matches his outline. Not scored: his ears, peets and belly tuft
   (separate parts, shaped later) and anything outside his body outline (whiskers, wisps). His nose must lie on
   the shell's surface at the remembered distance (six inches).
2. LINES: level rings (every 1 cm of height), depth slices going back (every 1 cm from his front), and his
   midline, cut from the shell and drawn through the anchor camera wherever the camera can see them.
3. VIEWS: the same shell from his side and from above, with the camera; what the camera sees (his front)
   drawn solid, what it cannot (his back: ASSUMED round) dashed.

Usage: python tools/depth_lines.py -> data/scene/shell.json, docs/images/space/depth_*.png
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from prince.space import Camera  # noqa: E402
from prince.shell import Shell, trace  # noqa: E402

OUT_IMG = ROOT / "docs/images/space"
FIT_SCALE = 0.15          # fit on a 1/6.7-size picture (each fit pixel ~6.7 photo px)
SOFT_CM = 0.15            # soft silhouette edge width while fitting
NOSE_WEIGHT = 2.0


def load(p):
    return json.loads((ROOT / p).read_text())


def scaled(cam: Camera, s):
    return Camera(R=cam.R, C=cam.C, f=cam.f * s, cx=cam.cx * s, cy=cam.cy * s,
                  width=int(round(cam.width * s)), height=int(round(cam.height * s)))


def masks(cam_small, W, H):
    """What the fit compares against, on the small picture: fraction of each pixel inside his body outline, and
    which pixels count (not his ears, peets or tuft)."""
    from matplotlib.path import Path as MP
    s = cam_small.width / W
    outline = np.array(load("data/strands/body_outline.json")["sampled_curve"])
    k = 4                                                     # 4 x 4 samples per small pixel
    ys, xs = np.mgrid[0:cam_small.height * k, 0:cam_small.width * k] + 0.5
    P = np.c_[xs.ravel() / (k * s), ys.ravel() / (k * s)]
    inside = MP(outline).contains_points(P).reshape(ys.shape)
    frac = inside.reshape(cam_small.height, k, cam_small.width, k).mean((1, 3))
    skip = np.zeros(len(P), bool)
    for f in ("data/strands/parts_ears.json", "data/strands/parts_peets.json"):
        for v in load(f)["parts"].values():
            skip |= MP(np.array(v["exterior"])).contains_points(P)
    skip = skip.reshape(ys.shape).reshape(cam_small.height, k, cam_small.width, k).mean((1, 3)) > 0
    skip = ndi.binary_dilation(skip, iterations=2)            # and a little around them
    return frac, ~skip


def silhouette(shell, cam_small, steps=72):
    ys, xs = np.mgrid[0:cam_small.height, 0:cam_small.width] + 0.5
    d = cam_small.ray(np.c_[xs.ravel(), ys.ravel()])
    hit, best = trace(shell, cam_small.C, d, steps=steps, t0=5.0, t1=45.0)
    # tracing stops at the surface, so a hit reads ~0 there: look 4 mm past it, so a real hit reads as inside
    h = np.isfinite(hit)
    if h.any():
        best[h] = np.minimum(best[h], shell.sdf(cam_small.C + d[h] * (hit[h] + 0.4)[:, None]))
    return (1.0 / (1.0 + np.exp(np.clip(best / SOFT_CM, -50, 50)))).reshape(cam_small.shape if hasattr(cam_small, "shape") else (cam_small.height, cam_small.width))


def fit(cam, lm, facing):
    W, H = cam.width, cam.height
    cs = scaled(cam, FIT_SCALE)
    frac, care = masks(cs, W, H)
    nose = cam.C + 15.24 * cam.ray([lm["nose_y_centre"]["at_px"]])[0]
    base = Shell(head_turn_deg=facing["head"]["turned_deg"], head_tip_deg=facing["head"]["tipped_deg"])
    # a first guess from where his nose is (head centre behind it, body behind and below)
    base = base.with_vector([0.0, nose[2] - 7.5, 7.5, 6.0, 0.0, nose[1] + 2.5, nose[2] - 5.5, 5.5, 4.5, 2.0])
    n_eval = [0]
    # his chin: where the approved head line crosses his midline, at about his nose's distance (+1 cm): his head
    # ends there (data/lines/body_parts_lines.json), so the head shape's lowest point should be near it
    chin = cam.C + cam.ray([lm["chin_midline"]["at_px"]])[0] * 16.24

    def structure(v):
        """How far v breaks the plain structure of a rabbit (no breed, just him): his head above the middle of his
        body and not behind it, a join (not a merge), each shape no more than twice as tall as wide or vice versa."""
        bx, bz, bw, bh, hx, hy, hz, hw, hh, k, by = v
        bad = [max(0.0, by - bh), max(0.0, 0.4 * bh - by), max(0.0, bh - hy + 0.5), abs((hy - hh) - chin[1]) - 1.0 if abs((hy - hh) - chin[1]) > 1.0 else 0.0, max(0.0, bz - hz), max(0.0, k - 3.0), max(0.0, 0.5 - k),
               max(0.0, hh - 2 * hw), max(0.0, hw - 2 * hh), max(0.0, bh - 2 * bw), max(0.0, bw - 2 * bh),
               max(0.0, 1.5 - min(bw, bh, hw, hh))]
        return sum(b * b for b in bad)

    def loss(v):
        n_eval[0] += 1
        sh = base.with_vector(v)
        sil = silhouette(sh, cs)
        e = ((sil - frac) ** 2)[care].mean()
        nz = float(sh.sdf(nose)[0])
        return e + NOSE_WEIGHT * 0.002 * (nz / 0.3) ** 2 + 0.05 * structure(v)
    t0 = time.time()
    starts = []
    for bw, bh, hw, hh, dz in ((7.5, 6.0, 5.5, 4.5, 7.5), (6.5, 5.0, 5.0, 4.0, 6.0), (8.0, 5.5, 6.0, 5.0, 9.0),
                              (7.0, 6.5, 4.5, 4.5, 5.0)):
        starts.append([0.0, nose[2] - dz, bw, bh, 0.0, nose[1] + 2.0, nose[2] - hw, hw, hh, 1.5, 0.8 * bh])
    step = np.array([0.8, 0.8, 0.6, 0.6, 0.8, 0.8, 0.8, 0.6, 0.6, 0.5, 0.6])   # real first steps (zeros don't move)

    def simplex(v0):
        return np.vstack([v0] + [v0 + np.eye(len(v0))[i] * step[i] for i in range(len(v0))])
    results = []
    for v0 in starts:
        v0 = np.array(v0)
        r = minimize(loss, v0, method="Nelder-Mead", options=dict(maxiter=900, xatol=1e-3, fatol=1e-7,
                                                                   initial_simplex=simplex(v0)))
        results.append(r)
    r = min(results, key=lambda rr: rr.fun)
    r = minimize(loss, r.x, method="Nelder-Mead", options=dict(maxiter=900, xatol=1e-4, fatol=1e-8,
                                                                initial_simplex=simplex(r.x) * 1.0 - 0.5 * (simplex(r.x) - r.x)))
    sh = base.with_vector(r.x)
    sil = silhouette(sh, cs) > 0.5
    tgt = frac > 0.5
    iou = float((sil & tgt & care).sum() / max(((sil | tgt) & care).sum(), 1))
    return sh, dict(iou_scored=round(iou, 4), loss=float(r.fun), evaluations=n_eval[0], seconds=round(time.time() - t0, 1),
                    starts_loss=[round(float(rr.fun), 5) for rr in results], structure_penalty=round(float(structure(r.x)), 6),
                    chin_height_cm=round(float(chin[1]), 2), head_lowest_cm=round(float(r.x[5] - r.x[8]), 2),
                    nose_off_surface_cm=round(float(sh.sdf(nose)[0]), 3), fit_scale=FIT_SCALE), (cs, frac, care)


# ---------------------------------------------------------------- the lines and views
REGION_COLOURS = {1: (235, 140, 30), 2: (60, 160, 230), 3: (140, 90, 230), 5: (70, 190, 90), 6: (220, 50, 50),
                  7: (0, 150, 150), 8: (200, 170, 0)}
UNSEEN = (205, 205, 200)


def visible_from(cam, sh, P, tol=0.12):
    """True where a shell point P is the first thing the camera's ray toward it meets (the camera can see it)."""
    d = P - cam.C; dist = np.linalg.norm(d, axis=1); d = d / dist[:, None]
    hit, _ = trace(sh, cam.C, d, steps=200, t0=max(0.5, float(dist.min()) - 40.0), t1=float(dist.max()) + 5.0)
    return np.abs(hit - dist) < tol


def rings(sh, step=1.0):
    """Lines cut from the shell: level rings (planes y = const), depth slices (z = const, from his front going
    back) and his midline (x = body centre). Each: (kind, value, (N, 3) points)."""
    from skimage.measure import find_contours
    lo, hi = sh.bounds(pad=0.5); g = 0.04
    out = []
    xs = np.arange(lo[0], hi[0], g); zs = np.arange(lo[2], hi[2], g); ys = np.arange(0.0, hi[1], g)
    for y0 in np.arange(step, hi[1], step):
        X, Z = np.meshgrid(xs, zs, indexing="ij")
        v = sh.sdf(np.c_[X.ravel(), np.full(X.size, y0), Z.ravel()]).reshape(X.shape)
        for c in find_contours(v, 0.0):
            out.append(("level", round(float(y0), 2), np.c_[lo[0] + c[:, 0] * g, np.full(len(c), y0), lo[2] + c[:, 1] * g]))
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    front = None
    for z0 in np.arange(hi[2], lo[2], -0.02):                  # his front-most point
        if (sh.sdf(np.c_[X.ravel(), Y.ravel(), np.full(X.size, z0)]) < 0).any():
            front = z0; break
    for k, z0 in enumerate(np.arange(front - step, lo[2], -step)):
        v = sh.sdf(np.c_[X.ravel(), Y.ravel(), np.full(X.size, z0)]).reshape(X.shape)
        for c in find_contours(v, 0.0):
            out.append(("depth", round(float(front - z0), 2), np.c_[lo[0] + c[:, 0] * g, c[:, 1] * g, np.full(len(c), z0)]))
    Y2, Z2 = np.meshgrid(ys, zs, indexing="ij")
    v = sh.sdf(np.c_[np.full(Y2.size, sh.body_x), Y2.ravel(), Z2.ravel()]).reshape(Y2.shape)
    for c in find_contours(v, 0.0):
        out.append(("midline", 0.0, np.c_[np.full(len(c), sh.body_x), c[:, 0] * g, lo[2] + c[:, 1] * g]))
    return out, float(front)


def depth_colour(d, dmax):
    t = min(max(d / dmax, 0.0), 1.0)                          # near: warm red; far: cool blue
    return tuple(int(v) for v in np.array([230, 60, 40]) * (1 - t) + np.array([40, 90, 230]) * t)


def region_map():
    import body_parts as bp
    import face_whiskers as fw
    F = fw.Face(); lines = load("data/lines/body_parts_lines.json")
    return bp.regions(F, np.array(lines["head_line"]["sampled_curve"]), np.array(lines["fold_line"]["sampled_curve"]))


def paint(cam, sh, reg, P):
    """Colour for shell points: the approved part the anchor camera sees there, or grey where it can't see."""
    vis = visible_from(cam, sh, P)
    uv = cam.project(P); H, W = reg.shape
    col = np.tile(np.array(UNSEEN, float), (len(P), 1))
    ok = vis & np.isfinite(uv).all(1)
    c = np.clip(uv[ok, 0].astype(int), 0, W - 1); r = np.clip(uv[ok, 1].astype(int), 0, H - 1)
    lab = reg[r, c]
    col[np.flatnonzero(ok)[lab > 0]] = np.array([REGION_COLOURS[int(v)] for v in lab[lab > 0]], float)
    return col, vis


def render(view, sh, cam, reg, scale=2):
    """The shell from another camera: shaded, painted with his parts where the anchor camera saw him."""
    W, H = view.width * scale, view.height * scale
    v2 = Camera(R=view.R, C=view.C, f=view.f * scale, cx=view.cx * scale, cy=view.cy * scale, width=W, height=H)
    ys, xs = np.mgrid[0:H, 0:W] + 0.5
    d = v2.ray(np.c_[xs.ravel(), ys.ravel()])
    hit, _ = trace(sh, v2.C, d, steps=160, t0=1.0, t1=500.0)
    img = np.full((H * W, 3), 250.0)
    h = np.isfinite(hit)
    P = v2.C + d[h] * hit[h][:, None]
    e = 0.02; n = np.stack([sh.sdf(P + [e, 0, 0]) - sh.sdf(P - [e, 0, 0]), sh.sdf(P + [0, e, 0]) - sh.sdf(P - [0, e, 0]),
                            sh.sdf(P + [0, 0, e]) - sh.sdf(P - [0, 0, e])], 1)
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    light = np.array([0.3, 0.8, 0.5]); light /= np.linalg.norm(light)
    shade = 0.55 + 0.45 * np.clip(n @ light, 0, 1)
    col, vis = paint(cam, sh, reg, P)
    hatch = (~vis) & ((((xs.ravel()[h] + ys.ravel()[h]) // (6 * scale)) % 2) == 0)
    col[hatch] = col[hatch] * 0.85
    img[h] = col * shade[:, None]
    return Image.fromarray(img.reshape(H, W, 3).astype(np.uint8)), v2


def draw_lines(im, v2, sh, cam, lines, front, only_visible_from=None, width=2, dmax=6.0, labels=False, font=None):
    d = ImageDraw.Draw(im)
    for kind, val, P in lines:
        if only_visible_from is not None:
            vis = visible_from(only_visible_from, sh, P)
        else:
            vis = visible_from(v2, sh, P)
        q = v2.project(P)
        col = {"level": (0, 150, 150), "midline": (240, 200, 0)}.get(kind) or depth_colour(val, dmax)
        w = width + (1 if kind == "midline" else 0)
        for a, b, va, vb in zip(q[:-1], q[1:], vis[:-1], vis[1:]):
            if va and vb and np.isfinite(a).all() and np.isfinite(b).all() and np.hypot(*(a - b)) < 40 * width:
                d.line([tuple(a), tuple(b)], fill=col, width=w)
        ok = vis & np.isfinite(q).all(1)
        if labels and ok.sum() > 10 and kind != "midline":
            if kind == "level":                                   # at the right end of what is seen
                i = np.flatnonzero(ok)[np.argmax(q[ok, 0])]; xy = (q[i, 0] + 8, q[i, 1] - 14)
                txt = f"{val:g} cm up"
            else:                                                 # at the lowest seen point
                i = np.flatnonzero(ok)[np.argmax(q[ok, 1])]; xy = (q[i, 0] + 6, q[i, 1] - 6)
                txt = f"{val:g} cm back"
            d.text(xy, txt, fill=col, font=font, stroke_width=3, stroke_fill=(255, 255, 255))


def floor_grid(im, v2, sh, step=1.0, reach=(-10, 10, -16, 6)):
    d = ImageDraw.Draw(im)
    x0, x1, z0, z1 = reach
    segs = [np.c_[np.full(200, x), np.zeros(200), np.linspace(z0, z1, 200)] for x in np.arange(x0, x1 + 0.01, step)] + \
           [np.c_[np.linspace(x0, x1, 200), np.zeros(200), np.full(200, z)] for z in np.arange(z0, z1 + 0.01, step)]
    for P in segs:
        dist = np.linalg.norm(P - v2.C, axis=1); dd = (P - v2.C) / dist[:, None]
        hit, _ = trace(sh, v2.C, dd, steps=96, t0=1.0, t1=500.0)
        seen = ~(hit < dist - 0.05)
        q = v2.project(P)
        major = abs(P[0, 0] % 5) < 1e-6 if P[0, 0] == P[-1, 0] else abs(P[0, 2] % 5) < 1e-6
        col = (150, 150, 145) if major else (195, 195, 190)
        for a, b, sa, sb in zip(q[:-1], q[1:], seen[:-1], seen[1:]):
            if sa and sb and np.isfinite(a).all() and np.isfinite(b).all():
                d.line([tuple(a), tuple(b)], fill=col, width=1)


def draw(sh):
    from PIL import ImageFont
    cam = Camera.from_dict(load("data/cameras.json")["anchor_front"])
    photo = Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB"); W, H = photo.size
    lines, front = rings(sh)
    reg = region_map()
    font = ImageFont.load_default(size=26); small = ImageFont.load_default(size=20)
    # 1. on the photo (drawn at 2x, then halved: smooth lines)
    s = 2
    big = photo.resize((W * s, H * s), Image.LANCZOS)
    v2 = Camera(R=cam.R, C=cam.C, f=cam.f * s, cx=cam.cx * s, cy=cam.cy * s, width=W * s, height=H * s)
    floor_grid(big, v2, sh)
    big.paste(photo.resize((W * s, H * s), Image.LANCZOS), (0, 0), mask=photo_mask(W, H, s))
    draw_lines(big, v2, sh, cam, lines, front, width=3, labels=True, font=ImageFont.load_default(size=30))
    im = big.resize((W, H), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 92], fill=(255, 255, 255))
    dr.text((10, 6), "Depth lines on him, from a rough round shell measured against his outline (not the model).", fill=(0, 0, 0), font=small)
    dr.text((10, 32), "Teal: level rings, every 1 cm of height. Red to blue: slices every 1 cm going back from the front of his face.", fill=(60, 60, 60), font=small)
    dr.text((10, 58), "Yellow: his midline. Grey grid: the surface he sits on, 1 cm squares. Lines only where the camera can see.", fill=(60, 60, 60), font=small)
    im.save(OUT_IMG / "depth_lines.png")
    # 2. views of the painted shell with the camera
    tgt = np.array([sh.body_x, 6.0, -5.0])
    views = (("depth_side.png", Camera.orbit(tgt + [0, 0, 6.5], 300, yaw_deg=90, pitch_deg=2, f=9000, width=1150, height=640),
              "From his left side. Painted: what the camera saw. Hatched grey: not seen (his back half is ASSUMED round)."),
             ("depth_top.png", Camera.orbit(tgt + [0, 0, 6.5], 300, yaw_deg=0, pitch_deg=89, f=9000, width=700, height=1120),
              "From above (his face toward the bottom, toward the camera). Hatched grey: not seen, ASSUMED round."),
             ("depth_behind.png", Camera.orbit(tgt, 60, yaw_deg=145, pitch_deg=25, f=1500, width=900, height=700),
              "From behind his left shoulder: the side the photo never saw is hatched grey (ASSUMED round)."))
    for name, view, title in views:
        img, vv = render(view, sh, cam, reg)
        floor_grid(img, vv, sh, reach=(-12, 12, -18, 18))
        draw_lines(img, vv, sh, cam, lines, front, width=2, dmax=14.0)
        d = ImageDraw.Draw(img)
        # the anchor camera, and the floor line
        if np.isfinite(vv.project([cam.C])).all():
            q = vv.project([cam.C])[0]
            d.ellipse([q[0] - 8, q[1] - 8, q[0] + 8, q[1] + 8], fill=(0, 0, 0)); d.text((q[0] + 12, q[1] - 12), "camera", fill=(0, 0, 0), font=small)
            nz = cam.C + cam.ray([load("data/strands/landmarks.json")["landmarks"]["nose_y_centre"]["at_px"]])[0] * 15.24
            d.line([tuple(q), tuple(vv.project([nz])[0])], fill=(90, 90, 90), width=2)
        out = img.resize((view.width, view.height), Image.LANCZOS)
        ImageDraw.Draw(out).text((8, 6), title, fill=(0, 0, 0), font=ImageFont.load_default(size=13))
        out.save(OUT_IMG / name)
    export_for_viewer(sh, cam, reg, lines)
    return lines, front


def export_for_viewer(sh, cam, reg, lines, voxel=0.3):
    """The painted shell as a mesh, and its lines, for the 3D page (tools/room_viewer.py)."""
    from skimage.measure import marching_cubes
    lo, hi = sh.bounds(pad=0.6)
    axes = [np.arange(lo[i], hi[i], voxel) for i in range(3)]
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    v = sh.sdf(np.c_[X.ravel(), Y.ravel(), Z.ravel()]).reshape(X.shape)
    verts, faces, _, _ = marching_cubes(v, 0.0, spacing=(voxel, voxel, voxel))
    verts = verts + lo
    col, vis = paint(cam, sh, reg, verts)
    ln = []
    for kind, val, P in lines:
        P2 = P[::3]
        ln.append(dict(kind=kind, value=val, points=np.round(P2, 2).tolist(),
                       seen=visible_from(cam, sh, P2).astype(int).tolist()))
    (ROOT / "data/scene/shell_view.json").write_text(json.dumps(dict(
        about="The rough shell (data/scene/shell.json) as a mesh painted with his approved parts where the anchor "
              "camera saw him (grey: not seen, ASSUMED round), and its depth lines. For docs/space/room.html.",
        vertices=np.round(verts, 3).tolist(), faces=faces.astype(int).tolist(),
        colours=np.round(col).astype(int).tolist(), seen=vis.astype(int).tolist(), lines=ln)))


def photo_mask(W, H, s):
    """Where he is in the photo (not pure white), so the floor grid shows only around him."""
    a = np.array(Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB")).astype(int)
    m = (a < 250).any(2)
    m = ndi.binary_opening(m, iterations=1)
    return Image.fromarray((m * 255).astype(np.uint8)).resize((W * s, H * s), Image.NEAREST)


def main() -> int:
    if "--draw" in sys.argv and (ROOT / "data/scene/shell.json").exists():
        sh = Shell(**load("data/scene/shell.json")["shell"])
        draw(sh)
        return 0
    cam = Camera.from_dict(load("data/cameras.json")["anchor_front"])
    lm = load("data/strands/landmarks.json")["landmarks"]
    facing = load("data/scene/facing.json")
    sh, q, _ = fit(cam, lm, facing)
    print(json.dumps(asdict(sh), indent=1)); print(q)
    (ROOT / "data/scene").mkdir(exist_ok=True)
    (ROOT / "data/scene/shell.json").write_text(json.dumps(dict(
        about="Rough parametric shell for the depth lines (prince/shell.py). NOT the model. Fitted to his outline "
              "through the anchor camera (the outline only measures it).", shell=asdict(sh), fit=q,
        assumed="front-to-back depth: round (each part as deep as it is wide), until the owner says otherwise "
                "or a side photo shows it"), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
