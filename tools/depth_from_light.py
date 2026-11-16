"""His face's depth, read from the light on his fur (owner, 2026-11-16: "look at the shading ... the albedo ...
his little eyes ... narrow down where the light must be coming from"; then: go ahead and read his depth from it).

He is white all over, so how bright his fur is says which way it faces the room's one soft light.
1. CALIBRATE on his outline: there his surface is edge-on to the camera and faces straight out, so its direction
   is known exactly. Brightness just inside the outline (red channel: the navy blanket under him tints mostly
   blue) against the direction it faces gives the light: brightness = ambient + strength * cos(angle to light).
2. READ his depth over his visible fur: the surface (a depth along every pixel's ray) whose facing directions
   make the brightness the photo shows, held by: his nose at six inches, his surface edge-on along his outline,
   and smoothness. Left out of the brightness: his eyes, eye marks, mouth lines, his pink nose, his ears, peets
   and belly tuft (separate parts), and the fuzzy fringe. His eye directions are NOT used: they are the check.
This is a MEASUREMENT of his visible surface (like the masks), not the model (rule 1).

Usage: python tools/depth_from_light.py -> data/scene/depth_from_light.json, docs/images/space/light_depth*.png
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from scipy.optimize import least_squares
from scipy.sparse import lil_matrix

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from prince.space import Camera  # noqa: E402
from prince.shell import Shell, trace  # noqa: E402

OUT_IMG = ROOT / "docs/images/space"
SCALE = 1 / 8             # solve on a 1/8-size grid (each cell 8 x 8 photo pixels, ~1 mm on him)
SHADE_SD = 8.0            # grey levels
NORMAL_W = 8.0            # how strongly neighbouring spots must face alike (scale-free smoothness)
EDGE_W = 4.0
PRIOR_SD_CM = 5.0         # a very loose pull toward the earlier shell, only to stop run-aways
NOSE_CM = 15.24
TOWARD_CAMERA = 0.0       # the light's front/back part: owner: "a very shallow angle" (overhead / to his right),
                          # and his face's middle is about as bright as his edges' average -> ~0 (tried +-10)


def load(p):
    return json.loads((ROOT / p).read_text())


def fur_masks(rgb, lm):
    from matplotlib.path import Path as MP
    H, W = rgb.shape[:2]; L = rgb.mean(2)
    outline = np.array(load("data/strands/body_outline.json")["sampled_curve"])
    yy, xx = np.mgrid[0:H, 0:W] + 0.5; P = np.c_[xx.ravel(), yy.ravel()]
    ins = MP(outline).contains_points(P).reshape(H, W)
    skip = np.zeros(H * W, bool)
    for f in ("data/strands/parts_ears.json", "data/strands/parts_peets.json"):
        for v in load(f)["parts"].values():
            skip |= MP(np.array(v["exterior"])).contains_points(P)
    skip = skip.reshape(H, W)
    # his pink nose: only around his nose (warm-lit fur elsewhere is also redder than blue)
    x0 = lm["nostril_wing_his_right"]["at_px"][0] - 25; x1 = lm["nostril_wing_his_left"]["at_px"][0] + 25
    y0 = min(lm["nostril_wing_his_right"]["at_px"][1], lm["nostril_wing_his_left"]["at_px"][1]) - 40
    y1 = lm["philtrum_bottom"]["at_px"][1] + 15
    box = np.zeros((H, W), bool); box[int(y0):int(y1), int(x0):int(x1)] = True
    feature = ndi.binary_dilation((L < 70) | (L < ndi.gaussian_filter(L, 15) - 40) | (((rgb[..., 0] - rgb[..., 2]) > 15) & box),
                                  iterations=5)
    return outline, ins, skip, feature


def calibrate(rgb, outline, ins, skip, feature):
    """The light from his outline: brightness (red) 15-30 px inside it vs the direction it faces."""
    from matplotlib.path import Path as MP
    H, W = ins.shape
    seg = np.hypot(*np.diff(outline, axis=0).T); s = np.r_[0, np.cumsum(seg)]; u = np.arange(0, s[-1], 3.0)
    O = np.c_[np.interp(u, s, outline[:, 0]), np.interp(u, s, outline[:, 1])]
    O = np.c_[ndi.gaussian_filter1d(O[:, 0], 8, mode="wrap"), ndi.gaussian_filter1d(O[:, 1], 8, mode="wrap")]
    t = np.gradient(O, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True); n = np.c_[t[:, 1], -t[:, 0]]
    if MP(outline).contains_points(O - n * 20).mean() < 0.5:
        n = -n
    ang, red = [], []
    for p, nn in zip(O, n):
        q = np.clip((p[None] - nn[None] * np.arange(15, 31, 1.0)[:, None]).astype(int), 0, [W - 1, H - 1])
        ok = ~skip[q[:, 1], q[:, 0]] & ~feature[q[:, 1], q[:, 0]]
        if ok.sum() >= 8:
            ang.append(np.arctan2(-nn[1], nn[0])); red.append(np.median(rgb[q[ok, 1], q[ok, 0], 0]))
    a = np.array(ang); red = np.array(red)
    A = np.c_[np.ones(len(a)), np.cos(a), np.sin(a)]; c, *_ = np.linalg.lstsq(A, red, rcond=None)
    r2 = 1 - ((red - A @ c) ** 2).sum() / ((red - red.mean()) ** 2).sum()
    # brightness = a0 + gx * (facing picture-right) + gy * (facing up)
    return dict(ambient=float(c[0]), toward_picture_right=float(c[1]), toward_up=float(c[2]),
                from_deg_in_picture=float(np.degrees(np.arctan2(c[2], c[1])) % 360), explains=float(r2),
                strength=float(np.hypot(c[1], c[2])), edge_points=int(len(a)))


def solve(cam, rgb, lm, sh, cal, ins, skip, feature, toward_camera=TOWARD_CAMERA):
    H, W = ins.shape
    cs = Camera(R=cam.R, C=cam.C, f=cam.f * SCALE, cx=cam.cx * SCALE, cy=cam.cy * SCALE,
                width=int(W * SCALE), height=int(H * SCALE))
    h, w = cs.height, cs.width
    k = int(round(1 / SCALE))
    inside = ins[:h * k, :w * k].reshape(h, k, w, k).mean((1, 3)) > 0.95
    fur = (ins & ~skip & ~feature & (ndi.distance_transform_edt(ins) > 18)).astype(float)
    red = ndi.gaussian_filter(rgb[..., 0] * fur, 4) / np.maximum(ndi.gaussian_filter(fur, 4), 1e-6)
    use = (fur[:h * k, :w * k].reshape(h, k, w, k).mean((1, 3)) > 0.8) & inside
    I = red[(np.arange(h) * k + k // 2)[:, None], (np.arange(w) * k + k // 2)[None, :]]
    ys, xs = np.mgrid[0:h, 0:w] + 0.5
    rays = cs.ray(np.c_[xs.ravel(), ys.ravel()]).reshape(h, w, 3)
    rays_cam = rays @ cam.R.T                                     # camera frame: x right, y down, z forward
    idx = -np.ones((h, w), int); cells = np.argwhere(inside); idx[cells[:, 0], cells[:, 1]] = np.arange(len(cells))
    N = len(cells)
    # start: the shell's depth along each ray (a convex start), misses filled from neighbours
    hit, _ = trace(sh, cs.C, rays[inside], steps=200, t0=5.0, t1=45.0)
    d0 = hit.copy()
    if (~np.isfinite(d0)).any():
        good = np.isfinite(d0); from scipy.spatial import cKDTree
        tr = cKDTree(cells[good]); _, j = tr.query(cells[~good]); d0[~good] = d0[good][j] + 0.5
    # neighbours (inside only); edge cells: inside with an outside neighbour
    def nb(di, dj):
        r = cells[:, 0] + di; c = cells[:, 1] + dj
        ok = (r >= 0) & (r < h) & (c >= 0) & (c < w)
        out = -np.ones(N, int); out[ok] = idx[r[ok], c[ok]]; return out
    R_, L_, D_, U_ = nb(0, 1), nb(0, -1), nb(1, 0), nb(-1, 0)
    edge = (R_ < 0) | (L_ < 0) | (D_ < 0) | (U_ < 0)
    full = ~edge
    rc = rays_cam[cells[:, 0], cells[:, 1]]
    nose_px = np.array(lm["nose_y_centre"]["at_px"]) * SCALE
    nose_i = idx[int(nose_px[1]), int(nose_px[0])]
    shade_i = np.flatnonzero(use[cells[:, 0], cells[:, 1]])
    gx, gy, a0 = cal["toward_picture_right"], cal["toward_up"], cal["ambient"]

    def normals(d):
        P = rc * d[:, None]                                       # camera frame points
        def pick(a, b):                                           # central difference, one-sided at the edge
            pa = np.where((a >= 0)[:, None], P[np.maximum(a, 0)], P); pb = np.where((b >= 0)[:, None], P[np.maximum(b, 0)], P)
            return pa - pb
        tu = pick(R_, L_); tv = pick(D_, U_)
        n = np.cross(tu, tv); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        n *= np.where((n * rc).sum(1) > 0, -1.0, 1.0)[:, None]   # facing the camera
        return n

    pairs = np.r_[np.c_[np.arange(N), R_][R_ >= 0], np.c_[np.arange(N), D_][D_ >= 0]]

    def residuals(d):
        n = normals(d)
        pred = a0 + gx * n[:, 0] + gy * (-n[:, 1]) + toward_camera * (-n[:, 2])
        r_sh = (I[cells[shade_i, 0], cells[shade_i, 1]] - pred[shade_i]) / SHADE_SD
        r_sm = NORMAL_W * (n[pairs[:, 0]] - n[pairs[:, 1]]).ravel()
        r_ed = EDGE_W * (n[edge] * rc[edge]).sum(1)              # edge-on: facing at right angles to the ray
        return np.r_[r_sh, r_sm, r_ed, (d - d0) / PRIOR_SD_CM, (d[nose_i] - NOSE_CM) / 0.05]
    # which unknowns each residual depends on (a spot's facing uses its four neighbours)
    neigh = np.c_[np.arange(N), R_, L_, D_, U_]
    rows = len(shade_i) + 3 * len(pairs) + edge.sum() + N + 1
    S = lil_matrix((rows, N), dtype=int); r = 0
    for i in shade_i:
        S[r, neigh[i][neigh[i] >= 0]] = 1; r += 1
    for a, b in pairs:
        cols = np.unique(np.r_[neigh[a], neigh[b]]); cols = cols[cols >= 0]
        for _ in range(3):
            S[r, cols] = 1; r += 1
    for i in np.flatnonzero(edge):
        S[r, neigh[i][neigh[i] >= 0]] = 1; r += 1
    for i in range(N):
        S[r, i] = 1; r += 1
    S[r, nose_i] = 1
    t0 = time.time()
    res = least_squares(residuals, d0.copy(), jac_sparsity=S, method="trf", x_scale="jac", max_nfev=60, verbose=0)
    d = res.x; n = normals(d)
    pred = a0 + gx * n[:, 0] + gy * (-n[:, 1]) + toward_camera * (-n[:, 2])
    obs = I[cells[shade_i, 0], cells[shade_i, 1]]
    r2 = 1 - ((obs - pred[shade_i]) ** 2).sum() / ((obs - obs.mean()) ** 2).sum()
    depth = np.full((h, w), np.nan); depth[cells[:, 0], cells[:, 1]] = d
    P = np.full((h, w, 3), np.nan); P[cells[:, 0], cells[:, 1]] = cam.C + rays[inside] * d[:, None]
    return dict(depth=depth, points=P, cam_small=cs, toward_camera=float(toward_camera), shading_r2=float(r2),
                seconds=round(time.time() - t0, 1), evaluations=int(res.nfev), cells=N)


def features(out, lm):
    """cm behind the front of his nose, for each named feature."""
    P = out["points"]; cs = out["cam_small"]
    def at(k):
        p = np.array(lm[k]["at_px"]) * SCALE; i, j = int(p[1]), int(p[0])
        win = P[max(i - 1, 0):i + 2, max(j - 1, 0):j + 2].reshape(-1, 3); win = win[np.isfinite(win).all(1)]
        return win.mean(0) if len(win) else None
    nose = at("nose_y_centre"); res = {}
    for k in ("nostril_wing_his_right", "nostril_wing_his_left", "mouth_corner_his_right", "mouth_corner_his_left",
              "lip_corner_his_right", "lip_corner_his_left", "chin_midline", "fold_midline", "eye_his_right",
              "eye_his_left", "crown_front"):
        p = at(k)
        res[k] = None if p is None else round(float(nose[2] - p[2]), 2)
    return res


def eye_check(out, lm, cam):
    """HELD OUT: which way his fur around each eye faces, vs how far each eye faces away (its oval)."""
    P = out["points"]; res = {}
    for k in ("eye_his_right", "eye_his_left"):
        p = np.array(lm[k]["at_px"]) * SCALE; i, j = int(p[1]), int(p[0]); r = 4
        win = P[i - r:i + r + 1, j - r:j + r + 1].reshape(-1, 3); win = win[np.isfinite(win).all(1)]
        if len(win) < 10:
            res[k] = None; continue
        c = win.mean(0); _, _, vt = np.linalg.svd(win - c); n = vt[2]
        ray = (c - cam.C) / np.linalg.norm(c - cam.C)
        if n @ ray > 0:
            n = -n
        res[k] = dict(fur_faces_deg=round(float(np.degrees(np.arccos(np.clip(-n @ ray, -1, 1)))), 1),
                      eye_oval_deg=round(float(np.degrees(np.arccos(lm[k]["oval"]["short_over_long"]))), 1))
    return res


def pictures(rgb, out, lm, cam):
    H, W = rgb.shape[:2]; depth = out["depth"]; P = out["points"]
    nose = np.array(lm["nose_y_centre"]["at_px"]) * SCALE
    z_nose = P[int(nose[1]), int(nose[0]), 2]
    back = z_nose - P[..., 2]                                     # cm behind the front of his nose
    big = ndi.zoom(np.nan_to_num(back, nan=-1.0), 1 / SCALE, order=1)[:H, :W]
    valid = ndi.zoom(np.isfinite(back).astype(float), 1 / SCALE, order=0)[:H, :W] > 0.5
    from skimage.measure import find_contours
    im = Image.fromarray(rgb.astype(np.uint8)).resize((W * 2, H * 2), Image.LANCZOS); d = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=30)
    levels = np.arange(0.5, 8.01, 0.5)
    for lv in levels:
        t = min(lv / 6.0, 1.0); col = tuple(int(v) for v in np.array([230, 60, 40]) * (1 - t) + np.array([40, 90, 230]) * t)
        for c in find_contours(np.where(valid, big, np.nan), lv):
            pts = [(x * 2, y * 2) for y, x in c]
            if len(pts) > 10:
                d.line(pts, fill=col, width=3 if lv % 1 == 0 else 1)
                if lv % 1 == 0:
                    lo = max(pts, key=lambda q: q[1]); d.text((lo[0] + 6, lo[1] - 16), f"{lv:g} cm", fill=col, font=font,
                                                               stroke_width=3, stroke_fill=(255, 255, 255))
    im = im.resize((W, H), Image.LANCZOS); dr = ImageDraw.Draw(im)
    dr.rectangle([0, 0, W, 64], fill=(255, 255, 255))
    small = ImageFont.load_default(size=20)
    dr.text((10, 6), "Depth read from the light on his fur: lines every 0.5 cm behind the front of his nose (bold: whole cm).",
            fill=(0, 0, 0), font=small)
    dr.text((10, 34), "Red = near his nose, blue = further back. A measurement of his visible surface, not the model.",
            fill=(60, 60, 60), font=small)
    im.save(OUT_IMG / "light_depth.png")
    # his profile (down his midline) and a cross-section at eye level and at mouth level, seen as numbers in a chart
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    j_mid = int(np.array(lm["nose_y_centre"]["at_px"])[0] * SCALE)
    prof = P[:, j_mid]; okp = np.isfinite(prof).all(1)
    fig, ax = plt.subplots(1, 2, figsize=(11, 5.2), dpi=110)
    ax[0].plot(z_nose - prof[okp, 2], prof[okp, 1], color="#c0392b", lw=2)
    ax[0].set_xlabel("cm behind the front of his nose"); ax[0].set_ylabel("cm above the surface he sits on")
    ax[0].set_title("His profile down his midline (seen from his left; his face to the left)", fontsize=10)
    ax[0].set_aspect("equal"); ax[0].grid(alpha=0.3)
    for k, mk in (("eye_his_right", "o"), ("mouth_corner_his_right", "s")):
        i = int(np.array(lm[k]["at_px"])[1] * SCALE); row = P[i]; okr = np.isfinite(row).all(1)
        ax[1].plot(row[okr, 0], z_nose - row[okr, 2], lw=2, label={"eye_his_right": "across at eye level",
                                                                   "mouth_corner_his_right": "across at mouth level"}[k])
    ax[1].invert_yaxis(); ax[1].set_xlabel("cm, his right (-) to his left (+)"); ax[1].set_ylabel("cm behind his nose")
    ax[1].set_title("Across his face (seen from above; his nose toward the top)", fontsize=10)
    ax[1].set_aspect("equal"); ax[1].grid(alpha=0.3); ax[1].legend(fontsize=9)
    plt.tight_layout(); plt.savefig(OUT_IMG / "light_depth_profile.png"); plt.close(fig)


def main() -> int:
    cam = Camera.from_dict(load("data/cameras.json")["anchor_front"])
    lm = load("data/strands/landmarks.json")["landmarks"]
    rgb = np.array(Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB")).astype(float)
    outline, ins, skip, feature = fur_masks(rgb, lm)
    cal = calibrate(rgb, outline, ins, skip, feature)
    print("light from his outline:", {k: round(v, 3) if isinstance(v, float) else v for k, v in cal.items()})
    sh = Shell(**load("data/scene/shell.json")["shell"])
    sens = {}
    for tc in (-10.0, 10.0):                                     # how much the answer depends on the light's front/back part
        o2 = solve(cam, rgb, lm, sh, cal, ins, skip, feature, toward_camera=tc)
        sens[f"light front/back part {tc:+g}"] = features(o2, lm)
    out = solve(cam, rgb, lm, sh, cal, ins, skip, feature)
    feats = features(out, lm); eyes = eye_check(out, lm, cam)
    print("sensitivity:", json.dumps(sens))
    print("depth solved:", {k: v for k, v in out.items() if k in ("toward_camera", "shading_r2", "seconds", "evaluations", "cells")})
    print("cm behind the front of his nose:", json.dumps(feats, indent=1)); print("eyes (held out):", eyes)
    pictures(rgb, out, lm, cam)
    (ROOT / "data/scene/depth_from_light.json").write_text(json.dumps(dict(
        about=__doc__.split("\n\n")[0], light=cal, light_toward_camera=out["toward_camera"],
        shading_explained=round(out["shading_r2"], 3), cm_behind_nose=feats, eyes_held_out=eyes, sensitivity=sens,
        grid_scale=SCALE, depth_cm_along_rays=np.round(np.nan_to_num(out["depth"], nan=-1), 3).tolist()), indent=0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
