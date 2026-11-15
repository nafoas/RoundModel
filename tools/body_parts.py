"""Head / Intermediate Bnuy / Undercarriage: the three body parts (owner, 2026-11-15).

Owner: "Rather than doing Head and then Undercarriage, can we do it in threes? We do Head, then
Intermediate Bnuy, then Undercarriage. I agree with your boundary for the undercarriage, but I also
think we should have an intermediate one. See that dark line under his mouth that goes up through his
cheeks diagonally to his edge? That seems like where his head ends - he doesn't have a visible neck
but that crease is the closest thing."

Two lines across his body (judgment lines, METHOD §4: shown as a drawn guess for the owner):
1. HEAD LINE (head ends): under his whole mouth (owner, 2026-11-15: not along the lip, which split it
   into two zones): one gentle line from just under one mouth corner to the other, so his nose, the
   cheeks under it, his pads and both lips are all in the head; then on each side the crease rising
   diagonally through his cheek from the mouth corner. The crease is found in a view that shows only creases slanting up and outward
   (oriented line filters, 8 px across x 30 px along, 0..70 deg on that side), followed from the mouth
   corner outward (dynamic programming: rises up to 53 deg, never drops more than 1 px per 3 px).
   SEEN: from the lowest point near the corner up to the highest point the crease reaches while it is
   clearly there (strength >= 1.5). Beyond that it fades; it is carried on in the direction of its seen
   diagonal (straight) to his outline: INFERRED.
2. FOLD (intermediate / undercarriage): the soft fold under his chin, the valley of the shading at bulge
   scale (8-60 px), followed across his body (dynamic programming, smooth), each end carried on to his
   outline in its own direction. Owner agreed with this one (2026-11-15).
Both smoothed to sub-pixel splines (head line 1 px rms, fold 2 px rms; gentle edges).
Parts: HEAD above the head line; INTERMEDIATE BNUY between the lines; UNDERCARRIAGE from the fold down
to the approved peet line (data/lines/peet_line.json); below that: peets and underfluff (their own parts).

Usage: python tools/body_parts.py -> data/strands/body_parts.json, docs/images/body_parts/*.png
"""
from __future__ import annotations

import json
from functools import lru_cache
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.interpolate import splev, splprep
from scipy.signal import fftconvolve
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_whiskers as fw  # noqa: E402
import whisker_chains as wc  # noqa: E402

ROOT = fw.ROOT
OUT = ROOT / "docs/images/body_parts"
CREASE_ACROSS, CREASE_ALONG = 8.0, 30.0
CREASE_SEEN = 1.5
FOLD_BAND = (880.0, 1120.0)
HEAD_RMS, FOLD_RMS = 1.0, 2.0
COLOURS = {1: (255, 170, 60), 2: (90, 200, 255), 3: (170, 110, 255), 4: (120, 120, 120), 5: (120, 220, 120)}
NAMES = {1: "head", 2: "intermediate bnuy", 3: "undercarriage", 4: "peets & underfluff", 5: "ears"}
# approved parts win outright over the new regions (lesson 25): file -> region they must carry
APPROVED_PARTS = {"data/strands/parts_peets.json": 4, "data/strands/parts_ears.json": 5}


@lru_cache(maxsize=2)
def approved_masks(H, W):
    """{(file, part): mask} for every approved part polygon, pixel (c, r) tested at its centre."""
    from matplotlib.path import Path as MP
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    P = np.c_[xx.ravel(), yy.ravel()]; out = {}
    for f in APPROVED_PARTS:
        for k, v in json.loads((ROOT / f).read_text())["parts"].items():
            out[(f, k)] = MP(np.array(v["exterior"])).contains_points(P).reshape(H, W)
    return out


def kern(th, sa, sl):
    h = int(3 * max(sa * 3, sl)); y, x = np.mgrid[-h:h + 1, -h:h + 1].astype(float)
    u = x * np.cos(th) + y * np.sin(th); v = -x * np.sin(th) + y * np.cos(th)
    k = np.exp(-u * u / (2 * sl * sl)) * np.exp(-v * v / (2 * sa * sa)) * (v * v / sa ** 4 - 1 / sa ** 2)
    k -= k.mean(); return k / np.abs(k).sum()


def smooth(P, rms):
    P = P[np.r_[True, np.hypot(*np.diff(P, axis=0).T) > 0.3]]
    tck, _ = splprep([P[:, 0], P[:, 1]], s=len(P) * rms ** 2)
    x, y = splev(np.linspace(0, 1, max(len(P) * 2, 50)), tck)
    return np.c_[x, y]


def to_outline(F, p0, t, max_len=500):
    for i in range(1, max_len):
        if F.sdist(p0 + i * t) <= 0:
            return np.array([p0 + k * t for k in range(1, i + 1)])
    return np.zeros((0, 2))


def dp_path(cost, Y, steps, start_index=None, step_cost=0.15):
    V = cost[0].copy() if start_index is None else np.full(len(Y), np.inf)
    if start_index is not None:
        V[start_index] = 0
    back = []
    for i in range(1, len(cost)):
        Vn = np.full(len(Y), np.inf); Bn = np.zeros(len(Y), int)
        for d in steps:
            src = np.arange(len(Y)) - d; ok = (src >= 0) & (src < len(Y))
            c = np.full(len(Y), np.inf); c[ok] = V[src[ok]] + step_cost * abs(d)
            m = c < Vn; Vn[m] = c[m]; Bn[m] = src[m]
        V = Vn + cost[i]; back.append(Bn)
    j = int(np.argmin(V)); path = [j]
    for Bn in back[::-1]:
        path.append(Bn[path[-1]])
    return path[::-1]


def head_line(F, pads):
    g = F.grey
    R = {d: fftconvolve(g, kern(np.radians(d), CREASE_ACROSS, CREASE_ALONG), mode="same") for d in range(-70, 71, 10)}
    crease = {"image_left": np.max([R[d] for d in range(0, 71, 10)], 0),
              "image_right": np.max([R[d] for d in range(-70, 1, 10)], 0)}
    info = pads["pad_info"]; out = {}
    for side, d in (("image_left", -1), ("image_right", 1)):
        c0 = np.array(info[side]["lip_corner"]); img = -crease[side]
        xs = np.arange(c0[0], (80 if d < 0 else F.grey.shape[1] - 80), 3.0 * d); Y = np.arange(600, 940, 1.0)
        cost = np.array([ndi.map_coordinates(img, [Y - 0.5, np.full(len(Y), x - 0.5)], order=1) for x in xs])
        sd = np.array([F.sdist(np.c_[np.full(len(Y), x), Y]) for x in xs])
        cost = cost / np.abs(cost[sd >= -2]).std(); cost[sd < -2] = 1e3
        path = dp_path(cost, Y, range(-4, 2), start_index=int(np.argmin(np.abs(Y - c0[1]))))
        ln = np.c_[xs, Y[path]]
        v = ndi.gaussian_filter1d(np.array([crease[side][int(p[1]), int(p[0])] for p in ln]), 2)
        strong = np.flatnonzero(v >= CREASE_SEEN); run_end = strong[0]
        for i in strong[1:]:
            if i - run_end > 4:
                break
            run_end = i
        i_top = int(np.argmin(ln[:run_end + 1, 1])); i_start = int(np.argmax(ln[:i_top + 1, 1]))
        seen = ln[i_start:i_top + 1]; diag = seen
        u, s_, vt = np.linalg.svd(diag - diag.mean(0)); t = vt[0]
        if t @ (diag[-1] - diag[0]) < 0:
            t = -t
        out[side] = dict(seen=seen, inferred=to_outline(F, seen[-1], t),
                         rise_deg=float(np.degrees(np.arctan2(-t[1], abs(t[0])))))
    # under his mouth (owner, 2026-11-15: "move the center ... down a little bit ... make sure his little nose,
    # under-nose cheeks, and little pads above his mouth are all in one area"): one gentle line from just under
    # each mouth corner (where the dark band under the corner fades halfway back to his fur) to the other, so the
    # whole mouth, both lips, the nose and the pads are in the head; no bump up in the middle.
    bulge = ndi.gaussian_filter(g, 8) - ndi.gaussian_filter(g, 60)

    def band_end(x, y0):
        ys = np.arange(y0 - 15, y0 + 90, 1.0)
        v = ndi.map_coordinates(bulge, [ys - 0.5, np.full(len(ys), x - 0.5)], order=1)
        i = int(np.argmin(v)); return ys[i + int(np.argmax(v[i:] > v[i] / 2))]
    cl = np.array(info["image_left"]["lip_corner"]); cr = np.array(info["image_right"]["lip_corner"])
    A = np.array([cl[0], band_end(cl[0], cl[1])]); B = np.array([cr[0], band_end(cr[0], cr[1])])
    xs = np.arange(A[0], B[0] + 0.5, 1.0)
    under = np.c_[xs, A[1] + (xs - A[0]) / (B[0] - A[0]) * (B[1] - A[1])]
    L, Rr = out["image_left"], out["image_right"]
    # owner, 2026-11-15: the image-right side went up "just a tiny, tiny, tiny bit too high ... ideally, mirror
    # the line on the left on the right": the image-right cheek line is the image-left one mirrored (left-right).
    # His face is tipped a few degrees in this photo (image-right nostril wing 16 px and lip corner 22 px higher),
    # so B starts higher than A; that difference is spread along the cheek (all of it at B, none at his edge), and
    # the mirrored shape is stretched across to his outline, so both sides meet his edge at the same height.
    left_cheek = np.vstack([A, L["seen"], L["inferred"]])
    f = (A[0] - left_cheek[:, 0]) / (A[0] - left_cheek[-1, 0])
    y_meet = left_cheek[-1, 1]
    xo = np.arange(B[0], F.grey.shape[1], 0.25)
    x_out = xo[int(np.argmax(F.sdist(np.c_[xo, np.full(len(xo), y_meet)]) <= 0))]
    mir = np.c_[B[0] + f * (x_out - B[0]), left_cheek[:, 1] + (1 - f) * (B[1] - A[1])]
    Rr = dict(Rr, seen=np.zeros((0, 2)), inferred=mir[1:], mirrored=True)
    q = mir[1:1 + len(L["seen"])]; tq = np.linalg.svd(q - q.mean(0))[2][0]
    out["image_right"] = dict(out["image_right"], mirrored_from="image_left", seen=Rr["seen"], inferred=Rr["inferred"],
                              rise_deg=float(np.degrees(np.arctan2(abs(tq[1]), abs(tq[0])))))
    raw = np.vstack([L["inferred"][::-1], L["seen"][::-1], under, Rr["inferred"]])
    line = smooth(raw, HEAD_RMS)
    t_seen = cKDTree(L["seen"]); t_under = cKDTree(under); t_mir = cKDTree(Rr["inferred"])
    labels = np.where(t_seen.query(line)[0] < 3, "seen",
                      np.where(t_under.query(line)[0] < 3, "under his mouth (owner-guided)",
                               np.where((t_mir.query(line)[0] < 3) & (line[:, 0] > B[0]),
                                        "mirror of the image-left side (owner-guided)", "inferred")))
    return line, labels, out, under


def fold_line(F):
    g = F.grey
    bulge = ndi.gaussian_filter(g, 8) - ndi.gaussian_filter(g, 60)
    xs = np.arange(160, F.grey.shape[1] - 156, 4.0); Y = np.arange(FOLD_BAND[0], FOLD_BAND[1] + 1, 1.0)
    cost = np.array([ndi.map_coordinates(bulge, [Y - 0.5, np.full(len(Y), x - 0.5)], order=1) for x in xs])
    ins = np.array([F.sdist(np.c_[np.full(len(Y), x), Y]) > 12 for x in xs]); cost[~ins] = 1e3
    path = dp_path(cost, Y, range(-3, 4), step_cost=0.6)
    fold = np.c_[xs, Y[path]]; fold[:, 1] = ndi.gaussian_filter1d(fold[:, 1], 3, mode="nearest")
    fold = fold[F.sdist(fold) > 12]
    tl = fold[0] - fold[3]; tl /= np.linalg.norm(tl); tr = fold[-1] - fold[-4]; tr /= np.linalg.norm(tr)
    raw = np.vstack([to_outline(F, fold[0], tl)[::-1], fold, to_outline(F, fold[-1], tr)])
    line = smooth(raw, FOLD_RMS)
    labels = np.where(F.sdist(line) > 12, "seen", "inferred")
    return line, labels


def regions(F, head, fold):
    H, W = F.grey.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    inside = F.sdist(np.stack([xx, yy], -1)) > 0
    peet = np.array(json.loads((ROOT / "data/lines/peet_line.json").read_text())["sampled_curve"])
    # owner, 2026-11-15: the undercarriage drifted into his left peet (image right) where the peet line
    # stopped short of his outline -> carry the peet line on to his outline at both ends, and take the
    # peets and underfluff exactly from their approved parts (data/strands/parts_peets.json)
    a, b = peet[0], peet[3]; tl = (a - b) / np.linalg.norm(a - b)
    a2, b2 = peet[-1], peet[-4]; tr = (a2 - b2) / np.linalg.norm(a2 - b2)
    peet_full = np.vstack([to_outline(F, a, tl)[::-1], peet, to_outline(F, a2, tr)])

    def below(line):
        o = line[np.argsort(line[:, 0])]; return yy > np.interp(xx, o[:, 0], o[:, 1])
    masks = approved_masks(H, W)
    po = peet_full[np.argsort(peet_full[:, 0])]
    below_peet = below(po) & (xx >= po[:, 0].min()) & (xx <= po[:, 0].max())
    reg = np.zeros((H, W), np.uint8); reg[inside] = 1
    reg[inside & below(head)] = 2; reg[inside & below(fold)] = 3
    reg[inside & below_peet] = 4
    # the approved parts last, so nothing new overrules them (the ears had been coloured head, 2026-11-15)
    for (f, k), m in masks.items():
        reg[m] = APPROVED_PARTS[f]
    # his body outline runs up to ~1 px beyond the approved ear polygons along the ears' sides (two approved
    # outlines differing by a pixel): head pixels touching an ear and above that ear's base are ear edge
    for (f, k), m in masks.items():
        if APPROVED_PARTS[f] != 5:
            continue
        cols = m.any(0); base = np.where(cols, H - 1 - np.argmax(m[::-1], 0), -1)
        base = ndi.maximum_filter1d(base, 5)
        edge = (reg == 1) & ndi.binary_dilation(m, iterations=2) & (yy - 0.5 < base[None, :])
        reg[edge] = 5
    return reg


def leaks(reg):
    """Pixels inside each approved part that carry any other label (must all be 0)."""
    return {k: int((m & (reg != APPROVED_PARTS[f])).sum()) for (f, k), m in approved_masks(*reg.shape).items()}


def sheets(F, head, hl, fold, fl, reg):
    OUT.mkdir(parents=True, exist_ok=True)
    ph = F.photo.astype(float); tint = ph.copy(); m = reg > 0
    col = np.zeros((max(COLOURS) + 1, 3)); [col.__setitem__(k, v) for k, v in COLOURS.items()]
    tint[m] = 0.75 * ph[m] + 0.25 * col[reg[m]]
    pages = []
    for name, (x0, y0, x1, y1), sc in (("body", (60, 170, 1040, 1300), 1), ("zoom", (100, 600, 1000, 1080), 2)):
        im = Image.fromarray(tint[y0:y1, x0:x1].astype(np.uint8)).resize(((x1 - x0) * sc, (y1 - y0) * sc), Image.LANCZOS)
        dr = ImageDraw.Draw(im); P = lambda z: ((z[0] - x0) * sc, (z[1] - y0) * sc)
        for line, lab, c in ((head, hl, (255, 0, 150)), (fold, fl, (0, 90, 255))):
            for i in range(len(line) - 1):
                if lab[i] == "inferred" and (i // 4) % 2:
                    continue
                dr.line([P(line[i]), P(line[i + 1])], fill=c, width=2)
        plain = Image.fromarray(F.photo[y0:y1, x0:x1]).resize(im.size, Image.LANCZOS)
        o = Image.new("RGB", (im.width * 2 + 6, im.height + 40), (255, 255, 255))
        o.paste(plain, (0, 40)); o.paste(im, (im.width + 6, 40)); d = ImageDraw.Draw(o)
        d.text((6, 4), "HEAD (orange) / INTERMEDIATE BNUY (blue) / UNDERCARRIAGE (purple); grey = peets & underfluff, "
                       "green = ears (approved parts, unchanged). Left: the photo, unmarked.", fill=(0, 0, 0))
        d.text((6, 20), "magenta = where his head ends; dark blue = the lower fold. Solid = seen in the photo, or placed "
                        "by the owner's guidance (under his mouth; image-right cheek = mirror of image-left); "
                        "dashed = carried on to his edge.", fill=(0, 0, 0))
        o.save(OUT / f"proposal_{name}.png"); pages.append(o)
    return pages


def main() -> int:
    F = fw.Face()
    pads = wc.muzzle_pads(F, wc.measure_pads(F))
    head, hl, cheeks, under = head_line(F, pads)
    fold, fl = fold_line(F)
    reg = regions(F, head, fold)
    leak = leaks(reg)
    if any(leak.values()):
        raise SystemExit(f"a new region overrules an approved part: {leak}")
    sheets(F, head, hl, fold, fl, reg)
    # checks: his pads (and so his nose, under-nose cheeks and mouth) lie wholly in the head
    ring = pads["ring"]; o = head[np.argsort(head[:, 0])]
    pad_clear = float(np.min(np.interp(ring[:, 0], o[:, 0], o[:, 1]) - ring[:, 1]))
    doc = dict(
        about=__doc__.split("\n\n")[0] + " " + __doc__.split("\n\n")[1],
        photo="data/photos/anchor_front.webp",
        status="proposal (drawn guess), owner review pending",
        head_line=dict(points=np.round(head, 2).tolist(), labels=hl.tolist(),
                       cheeks={k: dict(seen_to=np.round(v["seen"][-1], 1).tolist() if len(v["seen"]) else None,
                                       rise_deg=round(v["rise_deg"], 1), mirrored_from=v.get("mirrored_from"),
                                       inferred_px=int(len(v["inferred"])),
                                       meets_outline=np.round(v["inferred"][-1], 1).tolist() if len(v["inferred"]) else None)
                               for k, v in cheeks.items()},
                       under_mouth=dict(from_=np.round(under[0], 1).tolist(), to=np.round(under[-1], 1).tolist()),
                       pads_above_by_px_min=round(pad_clear, 1)),
        fold_line=dict(points=np.round(fold, 2).tolist(), labels=fl.tolist()),
        pixels={NAMES[k]: int((reg == k).sum()) for k in NAMES},
        checks=dict(approved_parts_wrongly_labelled_px=leak,
                    ear_edge_px_beyond_ear_parts=int(((reg == 5) & ~np.any([m for (f, k), m in approved_masks(
                        *reg.shape).items() if APPROVED_PARTS[f] == 5], 0)).sum()),
                    note=("every approved part (peets, underfluff, ears) keeps its own label; must all be 0. "
                          "ear_edge: pixels inside his body outline, touching an ear above its base, outside "
                          "the ear polygon by ~1 px (the two approved outlines differ by a pixel there)")),
    )
    (ROOT / "data/strands/body_parts.json").write_text(json.dumps(doc, indent=1))
    print(json.dumps({k: v for k, v in doc["head_line"].items() if k != "points" and k != "labels"}, indent=1))
    print("fold meets his outline at", np.round(fold[0], 0).tolist(), np.round(fold[-1], 0).tolist())
    print("pixels:", doc["pixels"])
    print("approved parts wrongly labelled (px):", leak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
