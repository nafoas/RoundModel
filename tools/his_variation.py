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

RESULTS SO FAR (2026-11-19): NO MEASURE IS USABLE YET.
- Eyes now fitted as smooth ovals through his lash line (tools/landmarks.py, lesson 34). Right on the anchor;
  on 01 and 18 (same moment) his right eye goes wrong: in 01 the lash-line point lands in the dark where his
  lashes meet the dark couch behind his head (oval far too big); in 18 the rough box cuts off his lashes, so no
  lash-line point is found (oval short). Hence their eye ratio spread (7.1%) is the fitting, not him. Next:
  boxes that hold his lashes, and the dark region kept off a dark background.
- Owner, 2026-11-19: the anchor, 01_front and 18_staring_at_boss are ONE moment (three shots in quick
  succession). So their close agreement (1.5% on the first try) is the measuring's own repeatability, not how
  he varies between moments; and the pose-proof rule's comparison was really against that repeatability. His
  variation between moments must come from photos taken at other moments (owner: replace those two with other
  angles in these tests).
- The 3D measure (eye spacing / eyes to nose): the nose finder's pink piece runs past its box in every photo
  (down the stem of his upper lip), so the nose point depended on the box I drew: not objective. With his head
  lowered (13, 14) his nose hides and the "piece" is faint fur. Next: a nose point that does not depend on the
  box (the same answer when the box is grown).
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
# Rough boxes for his nose: only WHERE TO LOOK; his nose is the pink in it (CIELAB a*, threshold by Otsu's method
# from the box's own pixels: no number of mine), the largest pink piece.
NOSE_BOXES = {
    "data/photos/anchor_front.webp": (460, 640, 640, 800),
    PHOTOS + "01_front.webp": (500, 590, 660, 740),
    PHOTOS + "18_staring_at_boss.webp": (490, 580, 650, 730),
    PHOTOS + "11_looking_up_slight.webp": (420, 300, 600, 450),
    PHOTOS + "12_looking_up_more.webp": (460, 260, 620, 400),
    PHOTOS + "13_looking_down_slight.webp": (480, 920, 650, 1060),
    PHOTOS + "14_looking_down_more.webp": (490, 980, 660, 1120),
}
# The anchor, 01 and 18 are ONE moment (owner, 2026-11-19: three shots in quick succession): their spread is the
# measuring's own repeatability (nothing changed but the camera's position a little), not how he varies.
SAME_MOMENT = {"anchor_front", "01_front", "18_staring_at_boss"}
HEAD = {"anchor_front": "level", "01_front": "level", "18_staring_at_boss": "level", "11_looking_up_slight": "raised",
        "12_looking_up_more": "raised", "13_looking_down_slight": "lowered", "14_looking_down_more": "lowered"}
POSE_PROOF = 2.0     # decided BEFORE running: a measure is pose-proof if its spread over every head pose is at most
#                      twice its spread with his head level (otherwise it is measuring his pose, not him)
FIT_OK_PX = 3.0      # an eye fit further off than this ran into something else (the background): rejected
SPREAD = 2.0          # tolerance = 2 standard deviations of his moment-to-moment spread (95%: a convention)
PATCH_CM = 1.0        # bumpiness: departure from a smooth (quadratic) patch over 1 cm squares
OUT = ROOT / "data/scene/his_variation.json"


def find_nose(rgb, box):
    """His nose in one photo: the largest pink piece in the box (CIELAB a* above Otsu's threshold for the box)."""
    from scipy import ndimage as ndi
    from skimage import color, filters
    x0, y0, x1, y1 = box
    a = color.rgb2lab(rgb[y0:y1, x0:x1])[..., 1]
    thr = float(filters.threshold_otsu(a))
    lab, n = ndi.label(a > thr)
    k = int(np.argmax(ndi.sum(np.ones_like(a), lab, range(1, n + 1)))) + 1
    piece = lab == k
    edge = piece[0].any() or piece[-1].any() or piece[:, 0].any() or piece[:, -1].any()
    m = np.zeros(rgb.shape[:2], bool); m[y0:y1, x0:x1] = piece
    return m, thr, not edge          # found = the pink piece lies inside the box (added 2026-11-19, after 13 and 14:
    #                                  with his head lowered his nose hides and the "piece" is faint fur filling the box)


def eyes_in_3d(path, model=None):
    """Both eyes and his nose in one photo, in 3D from that photo's own depth (its own units): the first try (eye
    spacing / an eye's size, read flat: not pose-proof) and the 3D measure (eye spacing / eyes to nose)."""
    img = Image.open(ROOT / path).convert("RGB")
    rgb = np.asarray(img); lum = rgb.astype(float).mean(-1)
    eyes = {k: lmk.measure_eye(lum, box) for k, box in EYE_BOXES[path].items()}
    nose_mask, nose_thr, nose_found = find_nose(rgb, NOSE_BOXES[path])
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
    EL, ER = out["eye_his_left"]["point"], out["eye_his_right"]["point"]
    spacing = float(np.linalg.norm(EL - ER))
    size = (out["eye_his_left"]["size"] + out["eye_his_right"]["size"]) / 2
    nose3d = np.median(P[nose_mask], axis=0)
    to_nose = float(np.linalg.norm(nose3d - (EL + ER) / 2))
    for v in out.values():
        v.pop("point"); v["size"] = round(v["size"], 3)
    ys, xs = np.nonzero(nose_mask)
    nose = dict(pixels=int(nose_mask.sum()), centre_px=[round(float(xs.mean()) + 0.5, 1), round(float(ys.mean()) + 0.5, 1)],
                pink_threshold_a=round(nose_thr, 2), found=nose_found)
    return dict(eyes=out, nose=nose, head=HEAD[Path(path).stem],
                ratio=round(spacing / size, 4), spacing=round(spacing, 3), eye_size=round(size, 3),
                eyes_to_nose=round(to_nose, 3), ratio_3d=round(spacing / to_nose, 4),
                units="the photo's own depth units (cancel in the ratios)"), dict(eyes=eyes, nose=nose_mask)


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


def picture(results, found):
    """Each photo's eye ovals (red) and nose (its pink piece outlined in green, its middle a cross), on the photo."""
    from scipy import ndimage as ndi
    font = ImageFont.load_default(size=26)
    tiles = []
    for path, f in zip(results, found):
        im = Image.open(ROOT / path).convert("RGB"); d = ImageDraw.Draw(im)
        for e in f["eyes"].values():
            cx, cy = e["centre"]; a, b = e["semi_axes"]; t = np.radians(e["angle_deg"])
            pts = [(cx + a * np.cos(u) * np.cos(t) - b * np.sin(u) * np.sin(t),
                    cy + a * np.cos(u) * np.sin(t) + b * np.sin(u) * np.cos(t)) for u in np.linspace(0, 2 * np.pi, 120)]
            d.line(pts + [pts[0]], fill=(255, 40, 40), width=2)
        rim = f["nose"] & ~ndi.binary_erosion(f["nose"])
        arr = np.asarray(im).copy(); arr[ndi.binary_dilation(rim)] = (0, 200, 60); im = Image.fromarray(arr); d = ImageDraw.Draw(im)
        nx, ny = results[path]["nose"]["centre_px"]
        d.line([(nx - 12, ny), (nx + 12, ny)], fill=(0, 200, 60), width=3); d.line([(nx, ny - 12), (nx, ny + 12)], fill=(0, 200, 60), width=3)
        xs = [e["centre"][0] for e in f["eyes"].values()] + [nx]; ys = [e["centre"][1] for e in f["eyes"].values()] + [ny]
        box = (int(min(xs)) - 90, int(min(ys)) - 90, int(max(xs)) + 90, int(max(ys)) + 90)
        t = im.crop(box); t = t.resize((600, int(600 * t.height / t.width)))
        dd = ImageDraw.Draw(t); dd.rectangle([0, 0, 600, 34], fill=(255, 255, 255))
        r = results[path]
        dd.text((6, 4), f"{Path(path).stem} ({r['head']}): 3D ratio {r['ratio_3d']:.3f}", fill=(0, 0, 0), font=font)
        tiles.append(t)
    h = max(t.height for t in tiles); cols = 3
    out = Image.new("RGB", (600 * cols, h * ((len(tiles) + cols - 1) // cols)), "white")
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * 600, (i // cols) * h))
    out.save(ROOT / "docs/images/space/his_variation_eyes.png")


def spread(results, key):
    """A measure's spread between moments: every head pose, and head level only (fits that failed left out)."""
    v = {k: r[key] for k, r in results.items()}
    if len(v) < 2:
        return dict(n=len(v), pose_proof=False, note="too few photos measured to say anything")
    allv = np.array(list(v.values())); lev = np.array([v[k] for k in v if Path(k).stem in SAME_MOMENT])
    pct = lambda a: round(100 * float(a.std(ddof=1) / a.mean()), 2)
    by = {h: [round(v[k], 3) for k in v if results[k]["head"] == h] for h in ("level", "raised", "lowered")}
    return dict(n=len(allv), mean=round(float(allv.mean()), 4), spread_percent=pct(allv),
                same_moment_spread_percent=pct(lev) if len(lev) > 1 else None,
                same_moment_is="the anchor, 01 and 18: one moment (owner), so this is the measuring's own "
                                "repeatability, not his variation", by_head=by,
                pose_proof=bool(len(lev) > 1 and pct(allv) <= POSE_PROOF * pct(lev)),
                tolerance_percent=round(SPREAD * pct(allv), 2))


def main() -> int:
    results, found = {}, []
    for path in EYE_BOXES:
        res, f = eyes_in_3d(path)
        results[path] = res; found.append(f)
        print(Path(path).stem, res["head"], "first try", res["ratio"], "3D", res["ratio_3d"], "nose px", res["nose"]["pixels"],
              {k: (v["fit_rms_px"], v["kept"]) for k, v in res["eyes"].items()})
    ok = {k: v for k, v in results.items() if all(e["fit_rms_px"] <= FIT_OK_PX for e in v["eyes"].values())}
    ok3 = {k: v for k, v in ok.items() if v["nose"]["found"]}
    first, three = spread(ok, "ratio"), spread(ok3, "ratio_3d")
    first.pop("tolerance_percent")
    if not three["pose_proof"]:
        three.pop("tolerance_percent", None)
    bump = bumpiness()
    doc = dict(
        about=__doc__.split("\n\n")[0],
        method=__doc__.split("\n\n")[1].replace("\n", " "),
        per_photo=results, rejected_fits=sorted(set(results) - set(ok)),
        nose_not_found=sorted(k for k in ok if not ok[k]["nose"]["found"]),
        pose_proof_rule=f"decided before running: pose-proof if the spread over every head pose is at most {POSE_PROOF:g}x "
                        f"the spread with his head level",
        eyes_3d_between_moments=dict(three, measure="distance between his eyes / from the middle of his eyes to his nose, "
                                                    "both in 3D: rigid points only, no units",
                                     usable=three["pose_proof"],
                                     finding=("NOT usable yet: the nose finder's pink piece runs from his nose down the "
                                              "stem of his upper lip and past the box in every photo, so the 'middle of "
                                              "his nose' depended on where the box was drawn (and with his head lowered, "
                                              "13 and 14, his nose hides: the piece was faint fur). Before that check, "
                                              "head level gave 0.885-0.987 (5.4%). Next: a nose point that does not "
                                              "depend on the box, tested by growing the box.") if not three["pose_proof"] else "",
                                     tolerance_is=f"{SPREAD:g} standard deviations of his spread between moments (95%)"),
        first_try_eyes_flat=dict(first, measure="distance between his eyes (3D) / an eye's long diameter read flat off "
                                                "the picture", usable=False,
                                 finding="follows his head's nod: an eye's flat size changes with the angle it is seen at"),
        surface_bumpiness=dict(bump, usable=False,
                               finding=(f"the measured surface is far smoother than his fur: a seam rule of 'no "
                                        f"steeper than this' would spread a 1 mm disagreement over "
                                        f"{0.1 / bump['slope']:.0f} cm. Not used (docs/MORE_PHOTOS.md: the "
                                        f"less-sure surface bends to meet the surer one instead)")))
    OUT.write_text(json.dumps(doc, indent=1))
    picture(results, found)
    print(json.dumps({k: doc[k] for k in ("rejected_fits", "nose_not_found", "eyes_3d_between_moments")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
