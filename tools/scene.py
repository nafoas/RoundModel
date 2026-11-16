"""Prince's 3D room, the anchor camera in it, and every part of him as rays (3D grounding, steps 1 and 3).

The room is defined in prince/space.py (centimetres; floor y = 0; +X his left, +Y up, +Z his forward;
origin on the floor under the front of his peets, in his midline plane).

Step 1 here: place the anchor camera in the room. Its lens and its distance from him are NOT known yet
(the photo carries no camera data and the background is removed), so this placement is PROVISIONAL and
made from three named placeholder inputs, each to be replaced in step 4 by a measurement:
  1. the lens: a 26 mm-equivalent phone main camera, picture not cropped, centre of the picture on the axis;
  2. his size: his widest outline is PROVISIONAL_WIDTH_CM across;
  3. the camera's height: "camera at roughly his eye/nose height, very slightly above" (docs/PRINCE_SPEC.md):
     the line of sight to his nose points NOSE_RAY_DOWN_DEG below level.
Everything measured in the photo stays in picture pixels (exact); everything in the room is recomputed from
those pixels whenever the camera changes.

Step 3 here: every part and boundary of him as RAYS from the anchor camera: his outline (where his surface
is edge-on to the camera: the line of sight grazes him there), the approved part lines and part outlines,
and every landmark. A ray fixes a direction, not a depth: he is somewhere along each one (step 5).

Usage: python tools/scene.py -> data/cameras.json, data/scene/anchor_rays.json, docs/images/space/room_*.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from prince.space import Camera, focal_px_from_35mm  # noqa: E402

OUT_IMG = ROOT / "docs/images/space"
PROVISIONAL_F35_MM = 26.0
PROVISIONAL_WIDTH_CM = 12.0
NOSE_RAY_DOWN_DEG = 5.0
FAR_PAST_ORIGIN_CM = 16.0          # drawn rays reach this far past the camera-to-origin distance (drawing only)
PART_COLOURS = {"head": (235, 140, 30), "intermediate bnuy": (60, 160, 230), "undercarriage": (140, 90, 230),
                "ears": (70, 190, 90), "top of his head (strip joining his ears)": (20, 140, 60),
                "cream peet (his right)": (220, 50, 50), "gray peet (his left)": (200, 170, 0),
                "belly (underfluff tuft)": (0, 150, 150), "line": (40, 40, 40)}


def load(p):
    return json.loads((ROOT / p).read_text())


def resample(curve, step):
    seg = np.hypot(*np.diff(curve, axis=0).T); s = np.r_[0, np.cumsum(seg)]
    u = np.arange(0, s[-1], step)
    return np.c_[np.interp(u, s, curve[:, 0]), np.interp(u, s, curve[:, 1])]


# ---------------------------------------------------------------- step 1: the anchor camera
def widest_outline(outline):
    """His widest outline: the row where his outline is widest (left and right crossings)."""
    best = (0, None)
    for y in np.arange(outline[:, 1].min() + 1, outline[:, 1].max() - 1, 0.5):
        a, b = outline[:-1], outline[1:]
        m = (a[:, 1] - y) * (b[:, 1] - y) <= 0
        m &= a[:, 1] != b[:, 1]
        xs = a[m, 0] + (y - a[m, 1]) / (b[m, 1] - a[m, 1]) * (b[m, 0] - a[m, 0])
        if len(xs) >= 2 and xs.max() - xs.min() > best[0]:
            best = (xs.max() - xs.min(), (xs.min(), xs.max(), y))
    return best


def anchor_camera(W, H, lm, outline):
    f = focal_px_from_35mm(PROVISIONAL_F35_MM, W, H)
    nose = np.array(lm["nose_y_centre"]["at_px"]); contact = np.array(lm["floor_contact_midpoint"]["at_px"])
    below_axis = np.degrees(np.arctan((nose[1] - H / 2) / f))
    pitch = NOSE_RAY_DOWN_DEG - below_axis                     # camera tipped down by this much
    cam = Camera.orbit([0, 0, 0], 1.0, pitch_deg=pitch, f=f, width=W, height=H)
    cam.C = np.zeros(3)
    width_px, (xl, xr, yw) = widest_outline(outline)
    depth = f * PROVISIONAL_WIDTH_CM / width_px                  # camera-axis depth of his front, from his width
    P = cam.point_at_depth([contact], [depth])[0]               # the floor contact, seen from a camera at 0
    cam.C = -P                                                  # ... is the room's origin
    inputs = dict(
        lens=f"PROVISIONAL: {PROVISIONAL_F35_MM} mm-equivalent phone main camera, picture not cropped, its centre "
             f"on the camera's axis -> focal length {f:.1f} px",
        his_width=f"PROVISIONAL: his widest outline ({width_px:.1f} px, at y {yw:.1f}) is {PROVISIONAL_WIDTH_CM} cm "
                  f"across, at the depth of his front",
        camera_height=f"PROVISIONAL: the line of sight to his nose points {NOSE_RAY_DOWN_DEG} deg below level "
                      f"(docs/PRINCE_SPEC.md: camera at roughly his eye/nose height, very slightly above)",
        facing="PROVISIONAL: camera straight in front of him (yaw 0), not turned (roll 0); step 4 measures both",
        origin="the floor under floor_contact_midpoint (data/strands/landmarks.json)")
    replace_with = ["the phone model, zoom, and whether the photo was cropped (or its focal length from the "
                    "original's photo info)", "his real width across his widest outline (cm)",
                    "roughly how high and how far the phone was", "or: a sheet of paper flat where he sat, "
                    "photographed from the same spot and zoom"]
    return cam, dict(inputs=inputs, replace_in_step_4_with=replace_with,
                     widest_outline_px=dict(width=round(width_px, 2), left=round(xl, 2), right=round(xr, 2), y=round(yw, 2)),
                     depth_of_his_front_cm=round(depth, 3))


# ---------------------------------------------------------------- step 3: rays
def part_at(reg, names, uv, inward=None, reach=6):
    """The part a picture point belongs to: the label at it, or the nearest label within `reach` px."""
    H, W = reg.shape; out = []
    for p in uv:
        c, r = int(p[0]), int(p[1]); lab = 0
        for rad in range(0, reach + 1):
            win = reg[max(r - rad, 0):r + rad + 1, max(c - rad, 0):c + rad + 1]
            v = win[win > 0]
            if len(v):
                vals, cnt = np.unique(v, return_counts=True); lab = int(vals[np.argmax(cnt)]); break
        out.append(names.get(lab, "none"))
    return out


def build_rays(cam, lm):
    import body_parts as bp
    import face_whiskers as fw
    F = fw.Face()
    lines = load("data/lines/body_parts_lines.json")
    reg = bp.regions(F, np.array(lines["head_line"]["sampled_curve"]), np.array(lines["fold_line"]["sampled_curve"]))
    names = {1: "head", 2: "intermediate bnuy", 3: "undercarriage", 5: "ears", 6: "cream peet (his right)",
             7: "belly (underfluff tuft)", 8: "gray peet (his left)"}
    outline_doc = load("data/strands/body_outline.json")
    outline = resample(np.array(outline_doc["sampled_curve"]), 2.0)
    parts = part_at(reg, names, outline)
    ib = sorted([lm["ear_base_inner_his_right"]["at_px"][0], lm["ear_base_inner_his_left"]["at_px"][0]])
    top = outline[:, 1] < lm["ear_base_inner_his_right"]["at_px"][1] + 8
    for i in np.flatnonzero((outline[:, 0] > ib[0]) & (outline[:, 0] < ib[1]) & top):
        parts[i] = "top of his head (strip joining his ears)"

    def entry(name, uv, part, source, status, kind, per_point_part=None):
        uv = np.asarray(uv, float)
        e = dict(name=name, part=part, source=source, status=status, kind=kind,
                 picture_px=np.round(uv, 2).tolist(),
                 directions_camera=np.round(cam.ray_camera(uv), 6).tolist(),
                 directions_room=np.round(cam.ray(uv), 6).tolist())
        if per_point_part is not None:
            e["part_per_point"] = per_point_part
        return e

    sets = [entry("his outline", outline, "per point", "data/strands/body_outline.json",
                  outline_doc["status"] + "; its top-of-head stretch is owner-approved (data/lines/approved_top_of_head.json)",
                  "grazing: the line of sight just touches his surface here, so his surface is edge-on to the "
                  "camera along these rays (it turns away from the camera at his outline)", parts)]
    for key, part in (("head_line", "head / intermediate bnuy"), ("fold_line", "intermediate bnuy / undercarriage")):
        sets.append(entry(key.replace("_", " "), resample(np.array(lines[key]["sampled_curve"]), 2.0), part,
                          "data/lines/body_parts_lines.json", lines["status"], "a curve on his surface"))
    peet = load("data/lines/peet_line.json")
    sets.append(entry("peet line", resample(np.array(peet["sampled_curve"]), 2.0), "body / peets & belly",
                      "data/lines/peet_line.json", peet["status"], "a curve on his surface"))
    bases = load("data/strands/ear_bases.json")
    for side, key in (("his right", "ear_image_left_base"), ("his left", "ear_image_right_base")):
        sets.append(entry(f"ear base ({side})", resample(np.array(bases[key]), 2.0), "ears / head",
                          "data/strands/ear_bases.json", bases["status"], "a curve on his surface"))
    for f, rename in (("data/strands/parts_ears.json", {"ear_image_left": ("ear (his right)", "ears"),
                                                      "ear_image_right": ("ear (his left)", "ears")}),
                      ("data/strands/parts_peets.json", {"cream_peet_image_left": ("cream peet (his right)", "cream peet (his right)"),
                                                       "gray_peet_image_right": ("gray peet (his left)", "gray peet (his left)"),
                                                       "underfluff_tuft": ("belly (underfluff tuft)", "belly (underfluff tuft)")})):
        d = load(f)
        for k, (nm, part) in rename.items():
            sets.append(entry(nm + " outline", resample(np.array(d["parts"][k]["exterior"]), 2.0), part, f,
                              d["status"], "a part's outline in the picture (partly grazing, partly a curve on him)"))
    lmk = [entry(k, [v["at_px"]], v["part"], "data/strands/landmarks.json", "first pass, owner review pending",
                 v["kind"]) for k, v in lm.items()]
    # self-check: every ray, taken out to any depth, lands back on its own pixel
    err = 0.0
    for e in sets + lmk:
        uv = np.array(e["picture_px"]); d = np.array(e["directions_room"])
        for depth in (5.0, 40.0):
            P = cam.C + d * (depth / (d @ cam.forward))[:, None]
            err = max(err, float(np.abs(cam.project(P) - uv).max()))
    return sets, lmk, err, reg, F


# ---------------------------------------------------------------- drawing the room
class Canvas:
    def __init__(self, view: Camera, scale=2):
        self.v = view; self.s = scale
        self.im = Image.new("RGB", (view.width * scale, view.height * scale), (250, 250, 248))
        self.d = ImageDraw.Draw(self.im)
        self.font = ImageFont.load_default(size=13 * scale)
        self.small = ImageFont.load_default(size=10 * scale)

    def P(self, X):
        return self.v.project(np.atleast_2d(X)) * self.s

    def line(self, pts, fill, width=1):
        q = self.P(pts)
        ok = np.isfinite(q).all(1)
        for a, b, oa, ob in zip(q[:-1], q[1:], ok[:-1], ok[1:]):
            if oa and ob:
                self.d.line([tuple(a), tuple(b)], fill=fill, width=width * self.s)

    def text(self, X, s, fill=(0, 0, 0), small=False, dx=6, dy=-6):
        q = self.P(X)[0]
        if np.isfinite(q).all():
            self.d.text((q[0] + dx * self.s, q[1] + dy * self.s), s, fill=fill, font=self.small if small else self.font)

    def photo_on_plane(self, photo, corners3d):
        q = self.P(corners3d)                                    # where the picture's corners land in this view
        W, H = photo.size
        src = np.array([[0, 0], [W, 0], [W, H], [0, H]], float)
        A = []; bvec = []
        for (x, y), (u, v) in zip(q, src):                       # output (x, y) -> input (u, v)
            A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); bvec.append(u)
            A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); bvec.append(v)
        coef = np.linalg.solve(np.array(A), np.array(bvec))
        warped = photo.transform(self.im.size, Image.PERSPECTIVE, tuple(coef), Image.BILINEAR)
        mask = Image.new("L", self.im.size, 0); ImageDraw.Draw(mask).polygon([tuple(p) for p in q], fill=255)
        self.im.paste(warped, (0, 0), mask)

    def done(self, path):
        self.im.resize((self.v.width, self.v.height), Image.LANCZOS).save(path)


def draw_room(cam, sets, lm, photo, depth_front, path, view, title):
    c = Canvas(view)
    # floor grid, 2 cm squares (darker every 10 cm), around him and under the camera
    zmax = max(cam.C[2] + 6, 10)
    for x in np.arange(-24, 24.01, 2):
        c.line(np.c_[np.full(2, x), np.zeros(2), [-24, zmax]], (190, 190, 185) if x % 10 else (150, 150, 145))
    for z in np.arange(-24, zmax + 0.01, 2):
        c.line(np.c_[[-24, 24], np.zeros(2), np.full(2, z)], (190, 190, 185) if z % 10 else (150, 150, 145))
    # rays: his outline (coloured by part), from the camera to the floor or a little past his front
    out = next(e for e in sets if e["name"] == "his outline")
    d = np.array(out["directions_room"]); parts = out["part_per_point"]
    tfar = np.full(len(d), np.linalg.norm(cam.C) + FAR_PAST_ORIGIN_CM)     # same length for every ray: no flat end
    tfloor = np.where(d[:, 1] < -1e-9, -cam.C[1] / np.minimum(d[:, 1], -1e-9), np.inf)
    t = np.minimum(tfar, tfloor)
    for i in range(0, len(d), 9):
        c.line([cam.C, cam.C + d[i] * t[i]], PART_COLOURS.get(parts[i], (120, 120, 120)))
    # the camera and the photo on its picture plane, 3 cm in front of it
    W, H = cam.width, cam.height
    corners = cam.point_at_depth([[0, 0], [W, 0], [W, H], [0, H]], np.full(4, 4.0))
    c.photo_on_plane(photo, corners)
    for k in range(4):
        c.line([cam.C, corners[k]], (30, 30, 30), 1)
    c.line(np.vstack([corners, corners[:1]]), (30, 30, 30), 1)
    # landmark rays (thin, dark), as long as the outline's
    for k, v in lm.items():
        r = cam.ray([v["at_px"]])[0]; tt = np.linalg.norm(cam.C) + FAR_PAST_ORIGIN_CM
        if r[1] < 0:
            tt = min(tt, -cam.C[1] / r[1])
        c.line([cam.C, cam.C + r * tt], (90, 90, 90), 1)
    # the camera's height and distance, as dimension lines on the floor
    foot = np.array([cam.C[0], 0.0, cam.C[2]])
    c.line([cam.C, foot], (0, 0, 0), 1); c.line([foot, np.zeros(3)], (0, 0, 0), 1)
    c.text((cam.C + foot) / 2, f"{cam.C[1]:.1f} cm", (0, 0, 0), small=True)
    c.text(foot / 2, f"{np.hypot(cam.C[0], cam.C[2]):.1f} cm", (0, 0, 0), small=True, dy=6)
    # the room's axes at the origin
    for ax, col, lab in ((np.array([4.0, 0, 0]), (210, 40, 40), "+X his left"),
                         (np.array([0, 4.0, 0]), (40, 160, 40), "+Y up"),
                         (np.array([0, 0, 4.0]), (40, 80, 220), "+Z his forward")):
        c.line([np.zeros(3), ax], col, 2); c.text(ax, lab, col, small=True)
    c.text(np.zeros(3), "origin", (0, 0, 0), small=True, dx=-40, dy=8)
    c.text(cam.C, "anchor camera (PROVISIONAL)", (0, 0, 0), small=True, dx=-60, dy=-34)
    c.d.text((10, 8), title, fill=(0, 0, 0), font=c.font)
    c.d.text((10, 8 + 34), "Coloured rays: his outline by part (head orange, intermediate blue, undercarriage purple, "
                           "ears green, peets red/yellow, belly teal); grey: landmarks. Grid: 2 cm.", fill=(60, 60, 60), font=c.small)
    c.d.text((10, 8 + 62), "He is somewhere along every ray; where (his depth) is step 5. Camera numbers are "
                           "PROVISIONAL until step 4.", fill=(60, 60, 60), font=c.small)
    c.done(path)


def main() -> int:
    photo = Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB")
    W, H = photo.size
    lmdoc = load("data/strands/landmarks.json"); lm = lmdoc["landmarks"]
    outline = np.array(load("data/strands/body_outline.json")["sampled_curve"])
    cam, prov = anchor_camera(W, H, lm, outline)
    sets, lmk, err, reg, F = build_rays(cam, lm)
    camdoc = {"about": "Cameras in Prince's room (prince/space.py). One entry per photo.",
              "anchor_front": dict(photo="data/photos/anchor_front.webp",
                                   status="PROVISIONAL placement (step 1): lens, his size and camera height are "
                                          "placeholders until step 4", **cam.to_dict(), **prov)}
    (ROOT / "data/cameras.json").write_text(json.dumps(camdoc, indent=1))
    (ROOT / "data/scene").mkdir(exist_ok=True)
    raydoc = dict(about=__doc__.split("\n\n")[0], camera="data/cameras.json: anchor_front (PROVISIONAL)",
                  room="prince/space.py: cm; floor y = 0; +X his left, +Y up, +Z his forward",
                  rule="every pixel is a ray from the camera, never a point on a flat sheet; depth is not decided here",
                  reprojection_max_error_px=err, sets=sets, landmarks=lmk)
    (ROOT / "data/scene/anchor_rays.json").write_text(json.dumps(raydoc))
    OUT_IMG.mkdir(parents=True, exist_ok=True)
    depth_front = prov["depth_of_his_front_cm"]
    tgt = np.array([0.0, 5.0, cam.C[2] * 0.45])
    views = (("room_behind.png", Camera.orbit(cam.C + [0, 1.0, -9.0], 30, yaw_deg=24, pitch_deg=16, f=900, width=1100,
                                              height=800),
              "Prince's room, seen from behind and above the anchor camera"),
             ("room_side.png", Camera.orbit(tgt + [0, 0, 0], 260, yaw_deg=90, pitch_deg=2, f=4400, width=1100, height=700),
              "Seen from his left side (far away, so nearly flat): heights and distances"),
             ("room_top.png", Camera.orbit(tgt, 260, yaw_deg=0, pitch_deg=89, f=4000, width=900, height=900),
              "Seen from straight above: where the camera stands and which way it looks"))
    for name, view, title in views:
        draw_room(cam, sets, lm, photo, depth_front, OUT_IMG / name, view, title)
    yaw, pitch, roll = cam.angles()
    print("anchor camera (PROVISIONAL):", dict(position_cm=np.round(cam.C, 2).tolist(), focal_px=round(cam.f, 1),
                                               yaw=round(yaw, 2), pitch=round(pitch, 2), roll=round(roll, 2)))
    print("depth of his front:", depth_front, "cm; widest outline:", prov["widest_outline_px"])
    print("rays:", {e["name"]: len(e["picture_px"]) for e in sets}, "+", len(lmk), "landmarks")
    print("reprojection max error (px):", err)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
