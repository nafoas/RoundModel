"""Draw the structure lines of Prince's face on the master: the edges,
creases, ridges and soft form changes that the face models are built from.

Lines were traced by hand on contrast-enhanced, gridded zooms of the master
(work/lines/*). Solid = a line you can see in the photo (an edge or a dark
crease). Dashed = a soft form change read from the shading (where the surface
turns), less exact by nature. A second panel shows the photo's shading
contours (lines of equal brightness), computed rather than traced, as the
evidence for the dashed lines.

All coordinates are master pixels. Output: checkpoints/face_lines/.
"""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "checkpoints/face_lines"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# reference palette categorical slots, ink and surface
INK, INK2, SURF = (11, 11, 11), (82, 81, 78), (252, 252, 251)
COL = {"ears": (98, 80, 214), "eyes": (42, 120, 214), "nose": (235, 104, 52), "mouth": (213, 81, 129),
       "lower": (27, 175, 122), "form": (82, 81, 78)}

# (group, name, points, dashed, closed)
LINES = [
    ("ears", "1 right ear edge", [(365, 300), (372, 255), (392, 222), (420, 210), (447, 218), (468, 240), (478, 262)], False, False),
    ("ears", "2 right ear base (joins head)", [(378, 292), (425, 277), (478, 262)], True, False),
    ("ears", "3 left ear edge", [(612, 250), (630, 226), (655, 210), (683, 206), (705, 222), (718, 255), (728, 295)], False, False),
    ("ears", "4 left ear base (joins head)", [(612, 250), (668, 266), (728, 295)], True, False),
    ("eyes", "5 right eye (dark of the eye)", [(345, 418), (358, 440), (361, 470), (352, 500), (335, 512), (320, 500), (316, 470), (325, 440)], False, True),
    ("eyes", "6 right upper lid / lashes", [(300, 410), (325, 400), (350, 405), (366, 420)], False, False),
    ("eyes", "7 right brow (socket rim)", [(292, 396), (330, 374), (372, 388), (392, 420)], True, False),
    ("eyes", "8 right under-eye smudge", [(316, 514), (326, 540), (347, 552)], False, False),
    ("eyes", "9 left eye (dark of the eye)", [(690, 396), (712, 410), (722, 440), (720, 470), (705, 488), (685, 482), (672, 455), (675, 420)], False, True),
    ("eyes", "10 left upper lid / lashes", [(664, 390), (690, 378), (716, 385), (732, 401)], False, False),
    ("eyes", "11 left brow (socket rim)", [(648, 386), (690, 360), (731, 370), (752, 396)], True, False),
    ("eyes", "12 left under-eye smudge", [(705, 490), (726, 506), (756, 520)], False, False),
    ("form", "13 forehead midline (fur parting)", [(545, 288), (544, 420), (543, 560)], True, False),
    ("nose", "14 right nose-bridge flank", [(455, 470), (480, 540), (505, 600)], True, False),
    ("nose", "15 left nose-bridge flank", [(630, 470), (602, 540), (577, 600)], True, False),
    ("nose", "16 top of the nose pad", [(455, 690), (468, 632), (503, 600), (540, 594), (580, 600), (613, 632), (628, 690)], True, False),
    ("nose", "17 right nostril (arm of the V)", [(455, 690), (490, 713), (520, 734), (545, 748)], False, False),
    ("nose", "18 left nostril (arm of the V)", [(628, 690), (598, 713), (570, 734), (545, 748)], False, False),
    ("mouth", "19 philtrum (nose to mouth)", [(545, 748), (546, 790), (548, 818)], False, False),
    ("mouth", "20 right upper lip", [(548, 818), (525, 830), (500, 838)], False, False),
    ("mouth", "21 left upper lip", [(548, 818), (572, 830), (597, 838)], False, False),
    ("mouth", "22 right whisker pad", [(455, 690), (436, 740), (444, 800), (480, 836)], True, False),
    ("mouth", "23 left whisker pad", [(628, 690), (652, 740), (645, 800), (612, 836)], True, False),
    ("mouth", "24 under the lips (chin crease)", [(400, 835), (470, 851), (545, 857), (620, 851), (690, 834)], False, False),
    ("lower", "25 chin meets chest bib", [(360, 880), (450, 906), (545, 916), (640, 906), (730, 880)], True, False),
    ("lower", "26 bib meets lower skirt", [(280, 1000), (420, 1030), (545, 1040), (670, 1030), (810, 1000)], True, False),
    ("lower", "27 right front peet", [(272, 1135), (265, 1182), (288, 1214), (340, 1228), (408, 1224), (442, 1205), (452, 1188)], False, False),
    ("lower", "28 skirt hem between the peets", [(452, 1188), (520, 1194), (598, 1190)], False, False),
    ("lower", "29 left front peet", [(598, 1190), (606, 1220), (650, 1233), (720, 1235), (764, 1222), (774, 1186), (772, 1150)], False, False),
]
SPECKS = [(655, 1218), (676, 1223), (692, 1216)]  # dark specks on the left front peet


def smooth(pts, closed, n=16):
    """Catmull-Rom spline through the points."""
    P = np.array(pts, float)
    if closed:
        P = np.vstack([P[-1], P, P[0], P[1]])
    else:
        P = np.vstack([P[0], P, P[-1]])
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def draw_poly(d, pts, col, width, dashed):
    if not dashed:
        d.line([tuple(p) for p in pts], fill=col, width=width, joint="curve")
        return
    seg, gap, acc, on, cur = 14, 9, 0.0, True, [tuple(pts[0])]
    for a, b in zip(pts[:-1], pts[1:]):
        L = np.linalg.norm(b - a)
        s = 0.0
        while s < L:
            step = min((seg if on else gap) - acc, L - s)
            s += step
            acc += step
            q = tuple(a + (b - a) * (s / L))
            if on:
                cur.append(q)
            if acc >= (seg if on else gap):
                if on and len(cur) > 1:
                    d.line(cur, fill=col, width=width)
                on, acc, cur = not on, 0.0, [q]
    if on and len(cur) > 1:
        d.line(cur, fill=col, width=width)


def label_pos(pts):
    P = np.array(pts, float)
    return P[len(P) // 2]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rgb = np.asarray(Image.open(ROOT / "references/master/master_front_standing.webp").convert("RGB")).astype(np.float32)
    base = Image.fromarray((rgb * 0.62 + 255 * 0.38).astype(np.uint8))
    S = 2  # draw at 2x for clean lines
    big = base.resize((base.width * S, base.height * S), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    m = np.asarray(Image.open(ROOT / "checkpoints/cp1/masks/master_front_standing.outline.png")) > 0
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=len)[:, 0, :] * S
    d.line([tuple(p) for p in np.vstack([c, c[:1]])], fill=(60, 60, 60), width=3)
    fnum = ImageFont.truetype(FONT, 26)
    placed = []
    for grp, name, pts, dashed, closed in LINES:
        P = smooth(pts, closed) * S
        draw_poly(d, P, COL[grp], 6, dashed)
        num = name.split()[0]
        lp = label_pos(smooth(pts, closed)) * S
        # nudge the number off the line, away from the face centre
        v = lp - np.array([545, 700]) * S
        v = v / (np.linalg.norm(v) + 1e-6)
        q = lp + v * 34
        for p in placed:
            if np.linalg.norm(q - p) < 44:
                q = q + v * 40
        placed.append(q)
        w = 22 if len(num) == 1 else 30
        d.ellipse([q[0] - w, q[1] - 20, q[0] + w, q[1] + 20], fill=SURF, outline=COL[grp], width=3)
        d.text((q[0], q[1]), num, fill=INK, font=fnum, anchor="mm")
    for s in SPECKS:
        d.ellipse([s[0] * S - 6, s[1] * S - 6, s[0] * S + 6, s[1] * S + 6], fill=COL["lower"])
    drawing = big.resize(base.size, Image.LANCZOS)
    drawing.save(OUT / "face_lines.png")

    # shading contours (computed), the evidence for the dashed lines
    lum = rgb.mean(2) / 255
    inner = cv2.erode(m.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    b = cv2.GaussianBlur(lum, (0, 0), 10)
    iso = (rgb * 0.62 + 255 * 0.38).astype(np.uint8).copy()
    for L in np.percentile(b[inner], np.linspace(5, 95, 14)):
        cs2, _ = cv2.findContours(((b > L) & inner).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        cv2.drawContours(iso, [k for k in cs2 if len(k) > 80], -1, (98, 80, 214), 2)
    Image.fromarray(iso).save(OUT / "shading_contours.png")

    # legend sheet: master | lines | shading contours, plus the key
    H = base.height
    W = base.width
    key_w = 760
    sheet = Image.new("RGB", (W * 3 + key_w + 40, H + 120), SURF)
    sheet.paste(Image.fromarray(rgb.astype(np.uint8)), (0, 120))
    sheet.paste(drawing, (W + 10, 120))
    sheet.paste(Image.fromarray(iso), (2 * W + 20, 120))
    ds = ImageDraw.Draw(sheet)
    ft, fs, fk = ImageFont.truetype(FONT, 40), ImageFont.truetype(FONT, 24), ImageFont.truetype(FONT, 23)
    ds.text((10, 20), "Prince's face: structure lines on the master", fill=INK, font=ft)
    ds.text((10, 74), "master (immutable)", fill=INK2, font=fs)
    ds.text((W + 20, 74), "traced lines: solid = visible edge or crease, dashed = soft form change", fill=INK2, font=fs)
    ds.text((2 * W + 30, 74), "shading contours (computed): where the surface turns", fill=INK2, font=fs)
    x0, y = 3 * W + 40, 140
    groups = [("ears", "Ears"), ("eyes", "Eyes"), ("form", "Forehead"), ("nose", "Nose"), ("mouth", "Mouth & muzzle"),
              ("lower", "Chin, bib, skirt, peets")]
    for g, title in groups:
        ds.text((x0, y), title, fill=INK, font=fs)
        y += 34
        for grp, name, pts, dashed, closed in LINES:
            if grp != g:
                continue
            if dashed:
                for k in range(3):
                    ds.line([(x0 + k * 18, y + 12), (x0 + k * 18 + 11, y + 12)], fill=COL[g], width=5)
            else:
                ds.line([(x0, y + 12), (x0 + 47, y + 12)], fill=COL[g], width=5)
            ds.text((x0 + 62, y), name, fill=INK, font=fk)
            y += 32
        y += 12
    ds.ellipse([x0 + 15, y + 6, x0 + 27, y + 18], fill=COL["lower"])
    ds.text((x0 + 62, y), "dark specks on the left front peet", fill=INK, font=fk)
    sheet.save(OUT / "face_lines_sheet.png")
    (OUT / "face_lines.json").write_text(json.dumps(
        {"_about": "Master pixels (x right, y down). Left/right are Prince's own. dashed = soft form change.",
         "lines": [{"group": g, "name": n, "points": p, "dashed": dsh, "closed": cl} for g, n, p, dsh, cl in LINES],
         "peet_specks": SPECKS}, indent=1))


if __name__ == "__main__":
    main()
