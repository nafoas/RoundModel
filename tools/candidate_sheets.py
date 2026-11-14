"""Review sheets for the grey-area face-whisker candidates ("uncertain: owner sorts
manually"), one per candidate, so the owner can sort them (owner, 2026-11-14:
"help me discern these by showing a few views of each of them, both with this view
and his base image").

Each sheet: a locator (where on his face), the measurements, then the same crop in
four views, unmarked (top row) and marked (bottom row):
  1. the photo as it is (base image);
  2. the photo with its brightness stretched (slow shading evened out) and its real
     colour added back at true strength (stretching the colour channels made false
     blue/yellow/pink casts);
  3. grey with the contrast evened out (12 px), as in the combined view;
  4. the line view (combined; darker = more whisker-like along the whisker directions).
Marks never cover the line: dashed cyan guides 5 px either side of the candidate,
thin magenta guides 5 px either side of known whiskers (its parent, if it is a
possible continuation, in solid magenta with its name).

Usage: python tools/candidate_sheets.py   -> docs/images/candidates/L??.png + candidates.pdf
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_whiskers as fw  # noqa: E402
import whisker_fulllength as wf  # noqa: E402
import whisker_lineview as lv  # noqa: E402

OUT = fw.ROOT / "docs/images/candidates"

# What I see on each sheet (2026-11-14), to help the owner; NOT a decision. The owner sorts these.
READS = {
    "L05": "looks to me like the inner edge of his fur band (it runs along the outline). Its test score is high, "
           "but the test also rewards a long edge like the band's, so the number can't settle it",
    "L08": "a faint line below his right eye in the stretched photo and the line view; possible",
    "L09": "follows one of the dark strokes beside his mouth: the same kind of line as L02/L06, which you said are whiskers",
    "L10": "a dark line between B2-S02 and B2-S08 in the stretched photo and evened views; likely a whisker",
    "L11": "a line between B2-S08 and B2-S16 shows in the stretched photo; the test can't judge it (every search "
           "beside it lands on those two whiskers)",
    "L12": "B5-S17's curve seems to carry on in the line view, but the test does not support it, and its last "
           "part runs into his nose's dark edge",
    "L13": "short (27 px), runs along the edge of a dark patch; I see no line",
    "L14": "faint at best beyond FW-06's end; I can't see a clear line",
    "L15": "faint at best beyond B2-S08's end; I can't see a clear line",
    "L16": "I see no line beyond B2-S16's end",
    "L17": "a darker streak carries on from FW-10 in the stretched and evened views; plausible",
    "L18": "crosses many fur streaks; I see no single line beyond FW-12",
    "L19": "I can't see a clear line beyond B2-S02's end",
}
PANEL_W = 380
MARGIN = 28
GUIDE = 5.0


def stretch(a, lo=1, hi=99):
    l, h = np.percentile(a, [lo, hi])
    return np.clip((a - l) / max(h - l, 1e-6) * 255, 0, 255).astype(np.uint8)


def main() -> int:
    F = fw.Face()
    doc = json.loads((fw.ROOT / "data/strands/face_whiskers.json").read_text())
    V = wf.CombinedView(lv.field_lines(doc["whiskers"], F))
    A = np.full(F.grey.shape, -np.inf)
    A[lv.Y0:lv.Y1, lv.X0:lv.X1] = V.along_view()
    line_view = np.clip(255 - np.clip(A, 0, 8) / 8 * 255, 0, 255).astype(np.uint8)
    g = F.grey; m = ndi.gaussian_filter(g, 12); sd = np.sqrt(ndi.gaussian_filter((g - m) ** 2, 12) + 1e-6)
    evened = (g - m) / sd
    shade = ndi.gaussian_filter(g, 20)
    rgb_flat = F.photo.astype(float) * (np.mean(g) / np.maximum(shade, 1.0))[..., None]

    def flat_rgb(y0, y1, x0, x1):
        """brightness: slow shading divided out, then stretched; colour: his real colour
        offsets added back at their true strength (never amplified)"""
        a = rgb_flat[y0:y1, x0:x1]
        lum = a.mean(2)
        l, h = np.percentile(lum, [1, 99])
        lum_s = np.clip((lum - l) / max(h - l, 1e-6) * 255, 0, 255)
        chroma = F.photo[y0:y1, x0:x1].astype(float) - F.photo[y0:y1, x0:x1].astype(float).mean(2, keepdims=True)
        return np.clip(lum_s[..., None] + chroma, 0, 255).astype(np.uint8)
    W = {w["id"]: fw.dense(np.array(w["centreline"])) for w in doc["whiskers"]}
    cands = [c for c in doc["line_view_candidates"] if c["verdict"] != lv.WHISKER]
    # locator base: his face, downscaled
    fx0, fy0, fx1, fy1 = 110, 380, 1010, 1000
    loc_sc = 380 / (fx1 - fx0)
    loc_base = Image.fromarray(F.photo[fy0:fy1, fx0:fx1]).resize((380, int((fy1 - fy0) * loc_sc)), Image.LANCZOS)
    OUT.mkdir(parents=True, exist_ok=True)
    pages = []
    for c in cands:
        q = fw.dense(np.array(c["points"]))
        parent = W.get(c.get("continues") or "")
        pts = [q] + ([parent[np.argsort(np.hypot(*(parent - q[0]).T))[:60]]] if parent is not None else [])
        allp = np.vstack(pts)
        x0, y0 = np.floor(allp.min(0) - MARGIN).astype(int); x1, y1 = np.ceil(allp.max(0) + MARGIN).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0)
        sc = float(np.clip(PANEL_W / (x1 - x0), 1.5, 5.0))
        pw, ph = int((x1 - x0) * sc), int((y1 - y0) * sc)
        crop = F.photo[y0:y1, x0:x1].astype(float)
        views = [
            ("photo as it is", crop.astype(np.uint8)),
            ("photo, brightness stretched (true colour)", flat_rgb(y0, y1, x0, x1)),
            ("contrast evened out (12 px)", stretch(evened[y0:y1, x0:x1])),
            ("line view (combined)", line_view[y0:y1, x0:x1]),
        ]
        P = lambda z: ((z[0] - x0) * sc, (z[1] - y0) * sc)

        def guides(dr, line, col, dash, width=1):
            if len(line) < 3:
                return
            t = np.gradient(line, axis=0); t /= np.linalg.norm(t, axis=1, keepdims=True) + 1e-12
            n = np.c_[-t[:, 1], t[:, 0]]
            for sg in (-1, 1):
                gl = line + sg * GUIDE * n
                if dash:
                    for i in range(0, len(gl) - 3, 6):
                        dr.line([P(gl[i]), P(gl[i + 3])], fill=col, width=width)
                else:
                    dr.line([P(z) for z in gl], fill=col, width=width)

        cols = []
        for title, a in views:
            im = Image.fromarray(a).convert("RGB").resize((pw, ph), Image.LANCZOS)
            top = im.copy(); ImageDraw.Draw(top).text((5, 4), title, fill=(255, 0, 150))
            mk = im.copy(); dr = ImageDraw.Draw(mk)
            for k, wl in W.items():
                inside = (wl[:, 0] >= x0) & (wl[:, 0] < x1) & (wl[:, 1] >= y0) & (wl[:, 1] < y1)
                if inside.sum() < 5:
                    continue
                is_parent = k == c.get("continues")
                guides(dr, wl, (255, 0, 150) if is_parent else (200, 120, 200), False, 2 if is_parent else 1)
                i = np.flatnonzero(inside)[len(np.flatnonzero(inside)) // 2]
                dr.text(P(wl[i] + np.array([0, -GUIDE - 9])), k, fill=(255, 0, 150) if is_parent else (170, 90, 170))
            guides(dr, q, (0, 200, 255), True, 2)
            dr.text(P(q[len(q) // 2] + np.array([0, GUIDE + 3])), c["id"], fill=(0, 160, 230))
            dr.text((5, 4), title + " (marked)", fill=(255, 0, 150))
            cols.append((top, mk))
        grid = Image.new("RGB", (4 * pw + 3 * 6, 2 * ph + 6), (30, 30, 30))
        for i, (top, mk) in enumerate(cols):
            grid.paste(top, (i * (pw + 6), 0)); grid.paste(mk, (i * (pw + 6), ph + 6))
        # header: locator + facts
        loc = loc_base.copy(); dl = ImageDraw.Draw(loc)
        dl.rectangle([((x0 - fx0) * loc_sc, (y0 - fy0) * loc_sc), ((x1 - fx0) * loc_sc, (y1 - fy0) * loc_sc)],
                     outline=(0, 200, 255), width=2)
        hdr = Image.new("RGB", (max(grid.width, 900), loc.height + 10), (245, 245, 245))
        hdr.paste(loc, (5, 5)); dh = ImageDraw.Draw(hdr)
        L = float(np.hypot(*np.diff(q, axis=0).T).sum())
        lines = [f"{c['id']}  -  uncertain: owner sorts manually",
                 f"possible continuation of {c['continues']} at its {c['at_end']} end" if c.get("continues")
                 else "possible whisker on its own",
                 f"length ~{L:.0f} px; from ({q[0][0]:.0f}, {q[0][1]:.0f}) to ({q[-1][0]:.0f}, {q[-1][1]:.0f})",
                 ("side-by-side test: untestable (every search beside it lies on a neighbouring whisker or the fur band)"
                  if c["margin"] is None else
                  f"side-by-side test: beats searches beside it by {c['margin']:+.2f} "
                  f"(plain fur reaches 0.94 one time in 20; a confirmed whisker stretch must beat that)"),
                 f"why it is uncertain: {c['reason']}",
                 f"my read (not a decision; you sort it): {READS.get(c['id'], 'not looked at yet')}",
                 "",
                 "top row: unmarked.  bottom row: dashed cyan = this candidate (guides 5 px either side, line left clear);",
                 "magenta = known whiskers (bold = its parent).  Cyan box on the left: where this is on his face.",
                 f"scale x{sc:.1f}"]
        for i, t in enumerate(lines):
            dh.text((400, 10 + 18 * i), t, fill=(20, 20, 20))
        page = Image.new("RGB", (max(grid.width, hdr.width), hdr.height + grid.height + 6), (255, 255, 255))
        page.paste(hdr, (0, 0)); page.paste(grid, (0, hdr.height + 6))
        page.save(OUT / f"{c['id']}.png"); pages.append(page)
        print(c["id"], page.size)
    if pages:
        pages[0].save(OUT / "candidates.pdf", save_all=True, append_images=pages[1:], resolution=110)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
