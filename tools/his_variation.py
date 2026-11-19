"""How much Prince varies between moments, measured from him: the yardsticks for comparing photos.

Owner, 2026-11-19: "We need to determine how to determine objectivity from a little fluffy creature that moves a
lot." Answer: let him set the yardstick. Photos of him from about the same angle, taken at different moments,
show how much a measurement of him changes when only time changes (he moved, fluffed, blinked, the camera
moved). That measured spread is the tolerance: within it, two photos agree; beyond it, the difference is real
and the owner looks. Nothing here is picked by hand.

1. HIS BIOLOGY, between moments: the distance between his eyes / the long diameter of an eye. Both are rigid
   (skull, eyeballs) and the ratio has no units, so each photo's own scale cancels. Each eye: the oval fitted to
   the eyeball's edge (tools/landmarks.py measure_eye; I give only a rough box saying where to look). The
   distance between the eyes in 3D from that photo's measured depth (MoGe-2, its own camera); an eye's size
   from its oval and its distance from the camera.
   Photos: the anchor and the front photos with both eyes clear (data/photos/by_angle/01_front).
2. HIS SURFACE'S OWN BUMPINESS (the anchor's measured surface, tools/visible_depth.py): how far it departs from
   a smooth curved patch over 1 cm squares. Where two photos' surfaces meet, the join may be no steeper than
   this: a disagreement d is spread over a band d / slope wide.

FIRST RESULT (2026-11-19): NEITHER MEASURE IS USABLE YET, as built.
- The eye ratio is not pose-proof: with his head level (anchor, 01, 18) it agrees within about 1.5%, but it
  moves about +20% with his head raised (12) and -33% with it lowered (13, 14). Cause: an eye's size is read
  flat off the picture, and an eye's visible outline changes with the angle it is seen at (lowering his head
  turns his eyes toward the camera: they look bigger and rounder). His skull did not change; the measure did.
  Fix to come: only 3D distances between rigid points (e.g. between his eyes / from his eyes to his nose).
- The bumpiness seam rule fails: the measured surface is far smoother (0.06 mm over 1 cm) than his fur, so the
  rule would spread a 1 mm disagreement over about 8 cm. Replaced (docs/MORE_PHOTOS.md): no blend band; the
  less-sure photo's surface bends (as-rigid-as-possible) to meet the surer one; the anchor never bends.
- An eye fit that ran into the background (photo 11, his right eye: 13 px off) is now rejected (fit > 3 px).

Usage: python tools/his_variation.py -> data/scene/his_variation.json, docs/images/space/his_variation_eyes.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import landmarks as lmk  # noqa: E402
import visible_depth as vd  # noqa: E402

PHOTOS = "data/photos/by_angle/01_front/"
# Rough boxes (x0, y0, x1, y1): only WHERE TO LOOK for each eye, read off the photos (2026-11-19); the oval fit
# measures it. His right eye is on the picture's left.
EYE_BOXES = {
    "data/photos/anchor_front.webp": lmk.EYE_BOXES,
    PHOTOS + "01_front.webp": {"eye_his_right": (320, 350, 430, 470), "eye_his_left": (680, 345, 790, 465)},
    PHOTOS + "18_staring_at_boss.webp": {"eye_his_right": (318, 352, 428, 470), "eye_his_left": (662, 348, 772, 466)},
    PHOTOS + "11_looking_up_slight.webp": {"eye_his_right": (332, 200, 412, 302), "eye_his_left": (624, 200, 704, 302)},
    PHOTOS + "12_looking_up_more.webp": {"eye_his_right": (344, 180, 424, 284), "eye_his_left": (668, 172, 748, 276)},
    PHOTOS + "13_looking_down_slight.webp": {"eye_his_right": (300, 585, 410, 700), "eye_his_left": (687, 577, 797, 693)},
    PHOTOS + "14_looking_down_more.webp": {"eye_his_right": (279, 696, 389, 816), "eye_his_left": (673, 671, 783, 791)},
}
FIT_OK_PX = 3.0      # an eye fit further off than this ran into something else (the background): rejected
SPREAD = 2.0          # tolerance = 2 standard deviations of his moment-to-moment spread (95%: a convention)
PATCH_CM = 1.0        # bumpiness: departure from a smooth (quadratic) patch over 1 cm squares
OUT = ROOT / "data/scene/his_variation.json"


def eyes_in_3d(path, model=None):
    """Both eyes of one photo: ovals (picture) and the eyes' 3D distance / eye size (that photo's own units)."""
    img = Image.open(ROOT / path).convert("RGB")
    lum = np.asarray(img, dtype=float).mean(-1)
    eyes = {k: lmk.measure_eye(lum, box) for k, box in EYE_BOXES[path].items()}
    r = vd.run_moge2(img) if model is None else model(img)
    H, W = lum.shape
    cam = vd.model_camera(r["focal_px"], W, H)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    P = cam.ray_camera(np.c_[xx.ravel(), yy.ravel()]).reshape(H, W, 3) * r["distance_m"][..., None] * 100.0
    out = {}
    for k, e in eyes.items():
        p = vd.point_near(P, e["centre"])
        out[k] = dict(centre_px=np.round(e["centre"], 2).tolist(), semi_axes_px=np.round(e["semi_axes"], 2).tolist(),
                      fit_rms_px=round(e["rms_px"], 2), kept=round(e["kept_fraction"], 2),
                      size=float(2 * e["semi_axes"][0] * p[2] / r["focal_px"]), point=p)
    spacing = float(np.linalg.norm(out["eye_his_left"]["point"] - out["eye_his_right"]["point"]))
    size = (out["eye_his_left"]["size"] + out["eye_his_right"]["size"]) / 2
    for v in out.values():
        v.pop("point"); v["size"] = round(v["size"], 3)
    return dict(eyes=out, ratio=round(spacing / size, 4), spacing=round(spacing, 3), eye_size=round(size, 3),
                units="the photo's own depth units (cancel in the ratio)"), eyes


def bumpiness(name="moge2", patch_cm=PATCH_CM):
    """His measured surface's departure from a smooth quadratic patch over patch_cm squares (cm), away from his
    outline's unsure band and his eyes; and the slope that makes (departure / half a patch)."""
    cam, P, _ = vd.room_points(name)
    H, W = P.shape[:2]
    inner = vd.inside_band(vd.him_mask(H, W), px=30)
    cm_per_px = float(np.nanmedian(np.linalg.norm(P - cam.C, axis=-1)[inner])) / cam.f     # on his surface, facing
    step = int(round(patch_cm / cm_per_px))
    res = []
    for y in range(0, H - step, step):
        for x in range(0, W - step, step):
            m = inner[y:y + step, x:x + step]
            if m.mean() < 0.95:
                continue
            q = P[y:y + step, x:x + step][m]
            c = q.mean(0); u, s, vt = np.linalg.svd(q - c, full_matrices=False)
            a, b, h = (q - c) @ vt[0], (q - c) @ vt[1], (q - c) @ vt[2]
            A = np.c_[np.ones_like(a), a, b, a * a, a * b, b * b]
            coef = np.linalg.lstsq(A, h, rcond=None)[0]
            res.append(float(np.sqrt(np.mean((h - A @ coef) ** 2))))
    res = np.array(res)
    return dict(patch_cm=patch_cm, patch_px=step, patches=len(res),
                departure_cm=dict(median=round(float(np.median(res)), 4), p90=round(float(np.percentile(res, 90)), 4)),
                slope=round(float(np.median(res) / (patch_cm / 2)), 4))


def picture(results, ovals):
    font = ImageFont.load_default(size=26)
    tiles = []
    for path, (res, eyes) in zip(results, ovals):
        im = Image.open(ROOT / path).convert("RGB"); d = ImageDraw.Draw(im)
        for e in eyes.values():
            cx, cy = e["centre"]; a, b = e["semi_axes"]; t = np.radians(e["angle_deg"])
            s = np.linspace(0, 2 * np.pi, 120)
            pts = [(cx + a * np.cos(u) * np.cos(t) - b * np.sin(u) * np.sin(t),
                    cy + a * np.cos(u) * np.sin(t) + b * np.sin(u) * np.cos(t)) for u in s]
            d.line(pts + [pts[0]], fill=(255, 40, 40), width=2)
        ys = [e["centre"][1] for e in eyes.values()]; xs = [e["centre"][0] for e in eyes.values()]
        box = (int(min(xs)) - 110, int(min(ys)) - 110, int(max(xs)) + 110, int(max(ys)) + 110)
        t = im.crop(box); t = t.resize((700, int(700 * t.height / t.width)))
        dd = ImageDraw.Draw(t); dd.rectangle([0, 0, 700, 34], fill=(255, 255, 255))
        dd.text((6, 4), f"{Path(path).stem}: ratio {results[path]['ratio']:.3f}", fill=(0, 0, 0), font=font)
        tiles.append(t)
    h = max(t.height for t in tiles)
    out = Image.new("RGB", (700 * 2, h * ((len(tiles) + 1) // 2)), "white")
    for i, t in enumerate(tiles):
        out.paste(t, ((i % 2) * 700, (i // 2) * h))
    out.save(ROOT / "docs/images/space/his_variation_eyes.png")


def main() -> int:
    results, ovals = {}, []
    for path in EYE_BOXES:
        res, eyes = eyes_in_3d(path)
        results[path] = res; ovals.append((res, eyes))
        print(Path(path).stem, res["ratio"], {k: (v["fit_rms_px"], v["kept"]) for k, v in res["eyes"].items()})
    ok = {k: v for k, v in results.items() if all(e["fit_rms_px"] <= FIT_OK_PX for e in v["eyes"].values())}
    r = np.array([v["ratio"] for v in ok.values()])
    level = np.array([ok[k]["ratio"] for k in ok if Path(k).stem in ("anchor_front", "01_front", "18_staring_at_boss")])
    sd = float(r.std(ddof=1))
    bump = bumpiness()
    doc = dict(
        about=__doc__.split("\n\n")[0],
        method=__doc__.split("\n\n")[1].replace("\n", " "),
        eyes_between_moments=dict(
            measure="distance between his eyes (3D) / an eye's long diameter: rigid, no units",
            per_photo=results, rejected_fits=sorted(set(results) - set(ok)), n=len(r),
            mean=round(float(r.mean()), 4), sd=round(sd, 4), spread_percent=round(100 * sd / float(r.mean()), 2),
            head_level_only=dict(n=len(level), spread_percent=round(100 * float(level.std(ddof=1) / level.mean()), 2),
                                 range=[round(float(level.min()), 3), round(float(level.max()), 3)]),
            usable=False,
            finding=("NOT a tolerance: the measure follows his head's nod (level 4.6-4.7, raised 5.7, lowered "
                     "3.1-3.3), because an eye's size read flat off the picture changes with the angle it is seen "
                     "at. Next: only 3D distances between rigid points.")),
        surface_bumpiness=dict(bump, usable=False,
                               finding=(f"the measured surface is far smoother than his fur: a seam rule of 'no "
                                        f"steeper than this' would spread a 1 mm disagreement over "
                                        f"{0.1 / bump['slope']:.0f} cm. Not used (docs/MORE_PHOTOS.md: the "
                                        f"less-sure surface bends to meet the surer one instead)")))
    OUT.write_text(json.dumps(doc, indent=1))
    picture(results, ovals)
    print(json.dumps({k: v for k, v in doc["eyes_between_moments"].items() if k != "per_photo"}, indent=1))
    print(json.dumps(bump, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
