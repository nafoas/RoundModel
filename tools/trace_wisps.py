"""Run the wisp step over all of Prince and account for every pixel.

1. Inventory: hair-like pieces outside the body, the intermediate fur band and
   the tuft fuzz (coverage > 0.08, connected, >= 8 px).
2. Each piece is assigned to the outline batch (B1..B6, as for the outline
   review) of its nearest outline tile, split into hair paths, traced
   (tools/wisps.py), de-duplicated across the whole body and classified.
3. Accounting (owner, 2026-11-11: "make sure everything gets a classification in
   the end, and it isn't left out"): every non-background pixel outside the body
   is assigned to exactly one class; anything unassigned is reported.

Writes data/strands/wisps.json and data/strands/accounting.json, and review
images docs/images/wisps_B*_*.png and docs/images/accounting.png.
Usage: python tools/trace_wisps.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402
import wisps as w  # noqa: E402

PIECE_COV, PIECE_MIN = 0.08, 8
BG_COV = 0.05            # below this a pixel is background
FOOT_K, FOOT_PAD = 2.5, 1.0
TIP_DIST = 10.0          # px from the fur band's outer edge: fringe tips / halo
NEAR = 20.0              # px: leftover groups this close to a traced hair go to the nearest
BATCHES = {"B1": (1, 20), "B2": (21, 40), "B3": (41, 60), "B4": (61, 80), "B5": (81, 100), "B6": (101, 108)}
CLASS_COLOURS = {"intermediate fur": (255, 190, 90), "peet & tuft fringe": (200, 160, 60),
                 "tuft fuzz": (255, 120, 220), "wisp": (230, 0, 120),
                 "whisker (last step)": (40, 90, 255), "lash (reserved)": (0, 170, 0),
                 "fringe tip / halo": (150, 110, 60), "unclassified": (255, 0, 0)}


def load():
    rgb = np.asarray(Image.open("data/photos/anchor_front.webp").convert("RGB"))
    a = bo.coverage(rgb)
    H, W = a.shape
    body = np.array(json.loads(Path("data/strands/body_outline.json").read_text())["sampled_curve"])
    outer = np.array(json.loads(Path("data/strands/intermediate_fur.json").read_text())["outer_sampled_curve"])
    fz = json.loads(Path("data/strands/tuft_fuzz.json").read_text())["regions"]
    yy, xx = np.mgrid[:H, :W]
    P = np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]
    inb = MPath(body).contains_points(P).reshape(H, W)
    ino = MPath(outer).contains_points(P).reshape(H, W)
    inf = np.zeros((H, W), bool)
    for r in fz:
        inf |= MPath(np.array(r)).contains_points(P).reshape(H, W)
    return rgb, a, body, outer, inb, ino, inf


def tile_batch(led) -> tuple[np.ndarray, list]:
    cen, bat = [], []
    for t in led["tiles"]:
        if t["id"][0] != "T":
            continue
        n = int(t["id"][1:])
        cen.append(((t["x0"] + t["x1"]) / 2, (t["y0"] + t["y1"]) / 2))
        bat.append(next(k for k, (lo, hi) in BATCHES.items() if lo <= n <= hi))
    return np.array(cen), bat


def run():
    rgb, a, body, outer, inb, ino, inf = load()
    bp = MPath(body)
    led = json.loads(Path("data/strands/ledger.json").read_text())
    cen, bat = tile_batch(led)
    tcen = cKDTree(cen)
    cand = (a > PIECE_COV) & ~inb & ~ino & ~inf
    lab, n = ndi.label(cand, structure=np.ones((3, 3), int))
    sizes = ndi.sum(cand, lab, range(1, n + 1))
    dist_o = ndi.distance_transform_edt(~ino)
    strands, refused = [], []
    for k in range(1, n + 1):
        if sizes[k - 1] < PIECE_MIN:
            continue
        m = lab == k
        ys, xs = np.nonzero(m)
        batch = bat[tcen.query([xs.mean() + 0.5, ys.mean() + 0.5])[1]]
        for seed in w.skeleton_paths(m):
            ii = np.clip(seed[:, 1].astype(int), 0, a.shape[0] - 1)
            jj = np.clip(seed[:, 0].astype(int), 0, a.shape[1] - 1)
            reach = float(dist_o[ii, jj].max())
            t = w.trace(a, seed[::2] if len(seed) > 6 else seed, lambda q: bp.contains_point(q))
            if t is None:
                refused.append({"piece": k, "batch": batch, "path_px": len(seed),
                                "from": seed[0].round(1).tolist(), "to": seed[-1].round(1).tolist()})
                continue
            t.update(piece=int(k), batch=batch, reach=reach, straight=w.straightness(t["centreline"]))
            strands.append(t)
    strands = w.dedupe(strands)
    return rgb, a, body, outer, inb, ino, inf, strands, refused


# Owner-guided strands. The rogue wisp above his right eye (owner 2026-11-07:
# "a little rogue piece of wispy fur, not an eyebrow"): it leaves the bump in the
# outline at about (315, 384) and runs left; an eyebrow whisker crossing it at
# x ~ 293 splits its trace in two, so the two pieces are joined.
OWNER_GUIDED = [{"name": "rogue wisp above his right eye", "class": "wisp",
                 "pieces_near": [(307.0, 385.0), (280.0, 387.6)], "max_dist": 3.0,
                 "source": "owner 2026-11-07, outline bump above his right eye"}]


def postprocess(strands):
    from scipy.spatial import cKDTree
    for t in strands:
        t["cls"] = w.classify(t, bo.EYE_BOXES)
        t.pop("owner_guided", None)
    for g in OWNER_GUIDED:
        hits = []
        for p in g["pieces_near"]:
            ds = [cKDTree(t["centreline"]).query(p)[0] for t in strands]
            i = int(np.argmin(ds))
            if ds[i] <= g["max_dist"] and i not in hits:
                hits.append(i)
        if not hits:
            continue
        joined = strands[hits[0]]
        for i in hits[1:]:
            joined = w.join(joined, strands[i])
        joined["cls"] = g["class"]; joined["owner_guided"] = g["name"] + " (" + g["source"] + ")"
        strands = [t for k, t in enumerate(strands) if k not in hits] + [joined]
    strands.sort(key=lambda t: (t["batch"], t["centreline"][:, 1].mean()))
    counters = {}
    for t in strands:
        counters[t["batch"]] = counters.get(t["batch"], 0) + 1
        t["id"] = f"{t['batch']}-S{counters[t['batch']]:02d}"
    return strands


def account(a, inb, ino, inf, strands, outer):
    """One class per non-background pixel outside the body. Leftovers touching a
    traced hair belong to that hair (its base, tip or a junction); leftovers
    near a hair (<= NEAR px) go to the nearest; anything else stays unclassified."""
    H, W = a.shape
    cls = np.full((H, W), "", dtype=object)
    sid = np.full((H, W), -1, int)
    bg = a < BG_COV
    out = ~inb & ~bg
    cls[out & inf] = "tuft fuzz"
    yy, xx = np.mgrid[:H, :W]
    below_peet = (bo.peet_weight(np.c_[xx.ravel() + 0.5, yy.ravel() + 0.5]) >= 0.5).reshape(H, W)
    cls[out & ino & (cls == "") & below_peet] = "peet & tuft fringe"
    cls[out & ino & (cls == "")] = "intermediate fur"
    best = np.full((H, W), np.inf)
    labs = []
    for i, t in enumerate(strands):
        lab = "fringe tip / halo" if t["cls"] in ("fringe tip", "not a hair (blob)") else t["cls"]
        labs.append(lab)
        cl, sg = t["centreline"], t["sigma"]
        x0 = max(0, int(cl[:, 0].min() - 8)); x1 = min(W, int(cl[:, 0].max() + 9))
        y0 = max(0, int(cl[:, 1].min() - 8)); y1 = min(H, int(cl[:, 1].max() + 9))
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d, j = cKDTree(cl).query(np.c_[X.ravel(), Y.ravel()])
        d = d.reshape(X.shape); r = (FOOT_K * sg[j] + FOOT_PAD).reshape(X.shape)
        sub = out[y0:y1, x0:x1] & (cls[y0:y1, x0:x1] == "") & (d <= r) & (d < best[y0:y1, x0:x1])
        cls[y0:y1, x0:x1][sub] = lab
        sid[y0:y1, x0:x1][sub] = i
        best[y0:y1, x0:x1][sub] = d[sub]
    rest = out & (cls == "")
    near_fur = ndi.distance_transform_edt(~ino) <= TIP_DIST
    cls[rest & near_fur] = "fringe tip / halo"
    extra = {}
    rest = out & (cls == "")
    lab_r, n_r = ndi.label(rest, structure=np.ones((3, 3), int))
    owned = sid >= 0
    tree_all = None
    for k in range(1, n_r + 1):
        m = lab_r == k
        grow = ndi.binary_dilation(m, iterations=2)
        ring = grow & owned
        if ring.any():
            ids, cnt = np.unique(sid[ring], return_counts=True)
            i = int(ids[np.argmax(cnt)]); how = "touching"
        elif (grow & ((cls == "fringe tip / halo") | (cls == "intermediate fur") | (cls == "peet & tuft fringe"))).any():
            cls[m] = "fringe tip / halo"      # faint halo of a fringe tip, just past TIP_DIST
            continue
        else:
            if tree_all is None:
                pts = np.vstack([t["centreline"] for t in strands]); owner_of = np.concatenate(
                    [np.full(len(t["centreline"]), j) for j, t in enumerate(strands)])
                tree_all = cKDTree(pts)
            ys, xs = np.nonzero(m)
            d, j = tree_all.query(np.c_[xs + 0.5, ys + 0.5])
            if d.min() > NEAR:
                continue
            i = int(owner_of[j[np.argmin(d)]]); how = "near"
        cls[m] = labs[i]; sid[m] = i
        e = extra.setdefault(strands[i]["id"], {"pixels": 0, "groups": 0, "how": set()})
        e["pixels"] += int(m.sum()); e["groups"] += 1; e["how"].add(how)
    cls[out & (cls == "")] = "unclassified"
    for t in strands:
        e = extra.get(t["id"])
        t["extra_pixels"] = {"pixels": e["pixels"], "groups": e["groups"], "how": sorted(e["how"])} if e else None
    counts = {k: int((cls == k).sum()) for k in CLASS_COLOURS}
    return cls, counts


def save(rgb, a, body, outer, inb, ino, inf, strands, refused, cls, counts):
    def ser(t):
        return {"id": t["id"], "batch": t["batch"], "class": t["cls"], "piece": t["piece"],
                "length_px": round(t["length"], 2), "straightness": round(t["straight"], 4),
                "reach_past_fur_px": round(t["reach"], 2),
                "median_sigma_px": round(float(np.median(t["sigma"])), 3),
                "median_opacity": round(float(np.median(t["opacity"])), 3),
                "extended_px": t["extended_px"],
                "extra_pixels_beyond_trace": t.get("extra_pixels"),
                "owner_guided": t.get("owner_guided"),
                "joined_gap_px": t.get("joined_gap_px"),
                "centreline": [[round(float(x), 3), round(float(y), 3)] for x, y in t["centreline"][::2]],
                "sigma": [round(float(v), 3) for v in t["sigma"][::2]],
                "opacity": [round(float(v), 3) for v in t["opacity"][::2]],
                "status": ("self-checked, awaiting owner review" if t["cls"] == "wisp"
                           else "provisional (handled in its own step)" if t["cls"] in ("whisker (last step)", "lash (reserved)")
                           else "classified")}
    out = {"about": "Strand-by-strand traces of everything hair-like outside the body, fur band and tuft fuzz "
                    "(tools/trace_wisps.py, tools/wisps.py). Centreline sub-pixel; sigma = Gaussian width (px); "
                    "opacity = coverage at the centre. Batches B1-B6 follow the outline review batches.",
           "photo": "data/photos/anchor_front.webp",
           "rules": {"wisp_reach_px": w.WISP_REACH,
                     "whisker": {"min_len": w.WHISKER_LEN, "min_straight": w.WHISKER_STRAIGHT, "min_opacity": w.WHISKER_OPAC},
                     "ridge_drop": w.RIDGE_DROP, "max_turn_deg": w.MAX_TURN, "blob_sigma": w.BLOB_SIGMA,
                     "min_len": w.MIN_LEN, "eye_pad_px": w.EYE_PAD},
           "class_counts": {c: sum(t["cls"] == c for t in strands) for c in sorted({t["cls"] for t in strands})},
           "strands": [ser(t) for t in strands],
           "refused_paths": refused}
    Path("data/strands/wisps.json").write_text(json.dumps(out, indent=1))
    Path("data/strands/accounting.json").write_text(json.dumps(
        {"about": "Every non-background pixel (coverage >= %.2f) outside the body outline, by class. "
                  "Inside the body: ears, peets, tuft (parts files) and head + undercarriage (to be split); "
                  "face whiskers and lashes inside the outline get coloured in their own steps." % BG_COV,
         "pixels_by_class": counts}, indent=1))
    # accounting image
    im = rgb.astype(float).copy()
    for k, c in CLASS_COLOURS.items():
        m = cls == k
        im[m] = im[m] * 0.3 + np.array(c) * 0.7
    Image.fromarray(im.astype(np.uint8)).save("docs/images/accounting.png")


def sheets(a, body, outer, strands, batch):
    ws = [t for t in strands if t["batch"] == batch and t["cls"] == "wisp"]
    if not ws:
        return []
    files = []
    R, Z = 16, 12
    for k in range(0, len(ws), 10):
        sub = ws[k:k + 10]
        rows = (len(sub) + 4) // 5
        P = 2 * R * Z
        sheet = Image.new("RGB", (5 * (P + 6), rows * (P + 6)), (255, 255, 255))
        for i, t in enumerate(sub):
            cl = t["centreline"]
            cx, cy = cl.mean(0).astype(int)
            x0, y0, x1, y1 = cx - R, cy - R, cx + R, cy + R
            g = (255 * (1 - np.clip(a[max(0, y0):y1, max(0, x0):x1] / 0.6, 0, 1))).astype(np.uint8)
            c = Image.fromarray(np.stack([g] * 3, 2)).resize((g.shape[1] * Z, g.shape[0] * Z), Image.NEAREST)
            dr = ImageDraw.Draw(c)
            for gx in range(g.shape[1] + 1):
                dr.line([(gx * Z, 0), (gx * Z, g.shape[0] * Z)], fill=(236, 236, 236))
            for gy in range(g.shape[0] + 1):
                dr.line([(0, gy * Z), (g.shape[1] * Z, gy * Z)], fill=(236, 236, 236))
            dr.line([((x - x0) * Z, (y - y0) * Z) for x, y in body], fill=(0, 120, 255), width=1)
            dr.line([((x - x0) * Z, (y - y0) * Z) for x, y in outer], fill=(255, 170, 0), width=1)
            for o in strands:
                if o is not t and o["cls"] != "not a hair (blob)":
                    dr.line([((x - x0) * Z, (y - y0) * Z) for x, y in o["centreline"]], fill=(120, 120, 255), width=1)
            dr.line([((x - x0) * Z, (y - y0) * Z) for x, y in cl], fill=(255, 0, 120), width=2)
            dr.rectangle([0, 0, 170, 16], fill=(255, 255, 255))
            dr.text((3, 2), f"{t['id']} ({cx},{cy}) op {np.median(t['opacity']):.2f}", fill=(0, 0, 0))
            r_, c_ = divmod(i, 5)
            sheet.paste(c, (c_ * (P + 6), r_ * (P + 6)))
        f = f"docs/images/wisps_{batch}_{k // 10 + 1}.png"
        sheet.save(f); files.append(f)
    return files


def main() -> int:
    import pickle
    cache = Path("/tmp/claude-0/-home-user-roundmodel/13cb371e-6a2f-5cfc-b4e2-a0566b0d035f/scratchpad/trace_cache.pkl")
    if "--cached" in sys.argv and cache.exists():
        rgb, a, body, outer, inb, ino, inf, strands, refused = pickle.loads(cache.read_bytes())
        strands = postprocess(strands)
    else:
        res = run()
        if cache.parent.exists():
            cache.write_bytes(pickle.dumps(res))
        rgb, a, body, outer, inb, ino, inf, strands, refused = res
    strands = postprocess(strands)
    cls, counts = account(a, inb, ino, inf, strands, outer)
    save(rgb, a, body, outer, inb, ino, inf, strands, refused, cls, counts)
    for b in BATCHES:
        bs = [t for t in strands if t["batch"] == b]
        print(b, {c: sum(t["cls"] == c for t in bs) for c in sorted({t["cls"] for t in bs})}, sheets(a, body, outer, strands, b))
    print("refused paths:", len(refused))
    print("pixels by class (outside the body):", counts)
    return 0 if counts["unclassified"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
