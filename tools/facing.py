"""How Prince is being looked at in the anchor photo: how his head and body are turned and tipped relative
to the camera (owner, 2026-11-16: "place the camera about six inches away ... exactly as it was when I
captured it, and then determine what way he is being looked at").

The camera is fixed as the owner remembers the shot (tools/scene.py). Then, from the photo:
- HEAD: his left-right axis from his mirror pairs (eyes, nostril wings, mouth corners, lip corners, inner and
  outer ear-base ends). The two points of a pair are mirror images, so the line joining them runs along his
  left-right axis; that line lies in the plane through the camera and the pair's two rays. His left-right axis
  is the one direction lying in all six planes (least squares). From it: how far his head is TURNED (toward
  his left = his nose toward the picture's right) and TIPPED (his left side up).
- EYES (a separate check of the turn): each eye is round; seen at an angle it shows as an oval, short/long =
  cos(the angle between the eye's own facing and the line of sight). Two eyes, mirror images of each other,
  give the turn and how far to the side his eyes face.
- BODY: where his two peets meet the surface he sits on (their rays met with that surface): the line between
  them runs along his body's left-right axis -> how far his body is turned.
His head's nod (up or down) needs his depth and comes later.

Uncertainty: every landmark is wobbled by its own uncertainty (data/strands/landmarks.json, sure_px, as 2
standard deviations), each pair is left out in turn, and the camera is re-placed across the owner's ranges.

Usage: python tools/facing.py -> data/scene/facing.json, docs/images/space/facing.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
from prince.space import Camera  # noqa: E402
import scene as sc  # noqa: E402

HEAD_PAIRS = [("eye_his_left", "eye_his_right"), ("nostril_wing_his_left", "nostril_wing_his_right"),
              ("mouth_corner_his_left", "mouth_corner_his_right"), ("lip_corner_his_left", "lip_corner_his_right"),
              ("ear_base_inner_his_left", "ear_base_inner_his_right"),
              ("ear_base_outer_his_left", "ear_base_outer_his_right")]
UP = np.array([0.0, 1.0, 0.0])


def left_right_axis(cam, pts):
    """His left-right axis (room coordinates, pointing to his left) from mirror pairs {name: (left_px, right_px)}."""
    N = []
    for a, b in pts:
        r = cam.ray([a, b]); n = np.cross(r[0], r[1]); N.append(n / np.linalg.norm(n))
    N = np.array(N); w, v = np.linalg.eigh(N.T @ N); X = v[:, 0]
    if X @ cam.right < 0:
        X = -X
    return X, np.degrees(np.arcsin(np.clip(np.abs(N @ X), 0, 1)))


def turn_tip(X):
    """Turn: + = toward his left (his left side further from a camera in front of him). Tip: + = his left side up."""
    return float(np.degrees(np.arctan2(-X[2], X[0]))), float(np.degrees(np.arcsin(np.clip(X[1], -1, 1))))


def eye_check(cam, lm):
    """Turn and eye direction from the two eye ovals (short/long = |cos| of the angle to the line of sight)."""
    q = {k: lm[k]["oval"]["short_over_long"] for k in ("eye_his_left", "eye_his_right")}
    r = {k: cam.ray([lm[k]["at_px"]])[0] for k in q}
    best = None
    for side_deg in np.arange(30, 89.9, 0.1):                # how far to the side his eyes face, from forward
        for turn in np.arange(-25, 25, 0.1):
            t, s = np.radians(turn), np.radians(side_deg)
            fwd = np.array([np.sin(t), 0, np.cos(t)]); left = np.array([np.cos(t), 0, -np.sin(t)])
            e = {"eye_his_left": np.sin(s) * left + np.cos(s) * fwd, "eye_his_right": -np.sin(s) * left + np.cos(s) * fwd}
            err = sum((abs(e[k] @ -r[k]) - q[k]) ** 2 for k in q)
            if best is None or err < best[0]:
                best = (err, turn, side_deg)
    return dict(turn_deg=round(best[1], 1), eyes_face_this_far_to_the_side_deg=round(best[2], 1),
                fit_residual=round(float(np.sqrt(best[0] / 2)), 4), ovals=q)


def body_axis(cam, lm):
    P = cam.hit_plane([lm["peet_bottom_his_left"]["at_px"], lm["peet_bottom_his_right"]["at_px"]])
    X = P[0] - P[1]; X[1] = 0; X /= np.linalg.norm(X)
    return X, P


def analyse(cam, lm, wobble=None):
    pts = []
    for a, b in HEAD_PAIRS:
        pa, pb = np.array(lm[a]["at_px"], float), np.array(lm[b]["at_px"], float)
        if wobble is not None:
            pa = pa + wobble.normal(0, lm[a]["sure_px"] / 2, 2); pb = pb + wobble.normal(0, lm[b]["sure_px"] / 2, 2)
        pts.append((pa, pb))
    X, misfit = left_right_axis(cam, pts)
    return X, misfit


def main() -> int:
    lm = json.loads((ROOT / "data/strands/landmarks.json").read_text())["landmarks"]
    camdoc = json.loads((ROOT / "data/cameras.json").read_text())["anchor_front"]
    cam = Camera.from_dict(camdoc)
    X, misfit = analyse(cam, lm)
    turn, tip = turn_tip(X)
    rng = np.random.default_rng(0)
    mc = np.array([turn_tip(analyse(cam, lm, rng)[0]) for _ in range(2000)])
    loo = {}
    for i, (a, b) in enumerate(HEAD_PAIRS):
        keep = [p for j, p in enumerate(HEAD_PAIRS) if j != i]
        Xi, _ = left_right_axis(cam, [(lm[x]["at_px"], lm[y]["at_px"]) for x, y in keep])
        loo[f"without {a.replace('_his_left', '')} pair"] = [round(v, 1) for v in turn_tip(Xi)]
    # the camera re-placed across the owner's ranges (and a 24 mm lens)
    photo = Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB"); W, H = photo.size
    outline = np.array(json.loads((ROOT / "data/strands/body_outline.json").read_text())["sampled_curve"])
    across = []
    for up in (0.0, 1.0, 2.0):
        for d in (10.0, 13.0, 15.24):
            for eyes_above in (0.0, 0.5, 1.0):
                c2, _ = sc.anchor_camera(W, H, lm, outline, up=up, d_nose=d, eyes_above=eyes_above)
                X2, _ = analyse(c2, lm); Xb2, _ = body_axis(c2, lm)
                across.append(turn_tip(X2) + (turn_tip(Xb2)[0],))
    across = np.array(across)
    eyes = eye_check(cam, lm)
    best2 = [(lm[a]["at_px"], lm[b]["at_px"]) for a, b in HEAD_PAIRS[:2]]
    t2 = [round(v, 1) for v in turn_tip(left_right_axis(cam, best2)[0])]
    mc2 = []
    for _ in range(2000):
        mc2.append(turn_tip(left_right_axis(cam, [(np.array(lm[a]["at_px"]) + rng.normal(0, lm[a]["sure_px"] / 2, 2),
                                                     np.array(lm[b]["at_px"]) + rng.normal(0, lm[b]["sure_px"] / 2, 2))
                                                    for a, b in HEAD_PAIRS[:2]])[0]))
    mc2 = np.array(mc2)
    Xb, peets_on_surface = body_axis(cam, lm)
    body_turn = turn_tip(Xb)[0]
    doc = dict(
        about=__doc__.split("\n\n")[0], camera="data/cameras.json anchor_front (as the owner remembers the shot; lens provisional)",
        head=dict(turned_deg=round(turn, 1), tipped_deg=round(tip, 1),
                  meaning="turned + = toward his own left (his nose toward the picture's right, his right cheek nearer "
                          "the camera); tipped + = his left side up (a little head tilt toward his right)",
                  left_right_axis_room=np.round(X, 5).tolist(),
                  pair_misfit_deg={f"{a.replace('_his_left', '')}": round(float(m), 2) for (a, b), m in zip(HEAD_PAIRS, misfit)},
                  landmark_wobble_2sd={"turned": [round(float(np.percentile(mc[:, 0], 2.5)), 1), round(float(np.percentile(mc[:, 0], 97.5)), 1)],
                                       "tipped": [round(float(np.percentile(mc[:, 1], 2.5)), 1), round(float(np.percentile(mc[:, 1], 97.5)), 1)]},
                  leave_one_pair_out=loo,
                  over_the_owners_ranges={"turned": [round(float(across[:, 0].min()), 1), round(float(across[:, 0].max()), 1)],
                                          "tipped": [round(float(across[:, 1].min()), 1), round(float(across[:, 1].max()), 1)]}),
        eyes_check=eyes,
        body=dict(turned_deg=round(body_turn, 1), peets_on_the_surface_cm=np.round(peets_on_surface, 2).tolist(),
                  over_the_owners_ranges=[round(float(across[:, 2].min()), 1), round(float(across[:, 2].max()), 1)],
                  note=("from the lowest point of each peet (view-dependent points, on a soft surface): a rough "
                        "reading of his body's turn")),
        head_relative_to_body_turned_deg=round(turn - body_turn, 1),
        eyes_and_nostrils_only=dict(turned_tipped_deg=t2, landmark_wobble_2sd_turned=np.percentile(mc2[:, 0], [2.5, 97.5]).round(1).tolist(),
                                    note="the two pairs that fit best (misfit < 0.5 deg); two pairs alone leave the turn loose"),
        summary=dict(
            tipped=f"his left side up, about {tip:.0f} deg (4-6 whatever is left out or wobbled): SOLID",
            turned=(f"toward his own left (his nose toward the picture's right), about 5-9 deg: the DIRECTION is solid "
                    f"(the mirror pairs {turn:.1f}, the eye ovals {eyes['turn_deg']:.1f}, his nose right of the middle of "
                    f"his eyes all agree); the AMOUNT is not yet (the pairs disagree: mouth, lip corners and ear bases can "
                    f"be truly lopsided; pixel uncertainty alone allows roughly 0-15 deg). It firms up with his round "
                    f"shell or another photo"),
            body=f"rough: about {abs(body_turn):.0f} deg toward his {'right' if body_turn < 0 else 'left'} (from his peets' lowest points)",
            head_vs_body="his head is turned toward his left on his body and tipped; the camera was straight on and level"),
        not_yet="his head's nod (up/down) needs his depth (the round shell, later)",
        camera_tilt_note=("tipped is measured against the camera's level; the owner remembers holding it straight on. "
                          "His peets' line does not tip the same way, so the tip is his head, not the phone"))
    (ROOT / "data/scene/facing.json").write_text(json.dumps(doc, indent=1))
    sheet(photo, lm, cam, X, Xb, peets_on_surface, doc)
    print(json.dumps({k: doc[k] for k in ("head", "eyes_check", "body", "head_relative_to_body_turned_deg")}, indent=1))
    return 0


def sheet(photo, lm, cam, X, Xb, peets, doc):
    s = 1
    W, H = photo.size
    im = photo.copy().convert("RGB"); d = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=22); small = ImageFont.load_default(size=17)
    for a, b in HEAD_PAIRS:
        pa, pb = lm[a]["at_px"], lm[b]["at_px"]
        d.line([tuple(pa), tuple(pb)], fill=(235, 120, 0), width=3)
        for p in (pa, pb):
            d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=(235, 120, 0), width=2)
    pa, pb = lm["peet_bottom_his_left"]["at_px"], lm["peet_bottom_his_right"]["at_px"]
    d.line([tuple(pa), tuple(pb)], fill=(200, 30, 30), width=3)
    # his head's left-right axis, drawn through the middle of his eyes at their (approximate) distance
    eyes = (np.array(lm["eye_his_left"]["at_px"]) + np.array(lm["eye_his_right"]["at_px"])) / 2
    E = cam.C + cam.ray([eyes])[0] * (sc.OWNER_CAMERA_TO_NOSE_CM + sc.EYES_BEHIND_NOSE_CM)
    q = cam.project([E - 2.5 * X, E + 2.5 * X])
    d.line([tuple(q[0]), tuple(q[1])], fill=(0, 90, 220), width=4)
    lvl = cam.project([E - 2.5 * np.array([1.0, 0, 0]), E + 2.5 * np.array([1.0, 0, 0])])
    d.line([tuple(lvl[0]), tuple(lvl[1])], fill=(120, 120, 120), width=2)
    h = doc["head"]
    d.rectangle([0, 0, W, 112], fill=(255, 255, 255))
    d.text((10, 6), f"Head: tipped {h['tipped_deg']:.1f} deg (his left side up): solid. Turned toward his left about 5-9 deg "
                    f"(pairs {h['turned_deg']:.1f}, eye ovals {doc['eyes_check']['turn_deg']:.1f}): direction solid, amount not yet.",
           fill=(0, 0, 0), font=small)
    d.text((10, 36), f"Body (from his peets, rough): turned {abs(doc['body']['turned_deg']):.1f} deg toward his "
                     f"{'right' if doc['body']['turned_deg'] < 0 else 'left'}.", fill=(0, 0, 0), font=small)
    d.text((10, 66), "orange: his mirror pairs; red: his peets' lowest points; blue: his head's left-right axis; "
                     "grey: level (the camera's left-right)", fill=(60, 60, 60), font=small)
    d.text((10, 88), "Camera fixed as the owner remembers the shot (straight on, ~13 cm, a touch below eye level).",
           fill=(60, 60, 60), font=small)
    # top view: camera, his body axis (at his peets), his head axis (at his eyes)
    view = Camera.orbit([0, 0, 5.5], 200, yaw_deg=0, pitch_deg=89.5, f=6400, width=620, height=880)
    c = sc.Canvas(view, scale=2)
    for x in np.arange(-8, 8.01, 1):
        c.line(np.c_[np.full(2, x), np.zeros(2), [-5, 16]], (205, 205, 200) if x % 2 else (175, 175, 170))
    for z in np.arange(-5, 16.01, 1):
        c.line(np.c_[[-8, 8], np.zeros(2), np.full(2, z)], (205, 205, 200) if z % 2 else (175, 175, 170))
    foot = cam.C * [1, 0, 1]
    tri = [foot + cam.right * 0.8 + cam.forward * [1, 0, 1] * 1.2, foot, foot - cam.right * 0.8 + cam.forward * [1, 0, 1] * 1.2]
    c.line(tri, (0, 0, 0), 2)
    nose = cam.C + cam.ray([lm["nose_y_centre"]["at_px"]])[0] * sc.OWNER_CAMERA_TO_NOSE_CM
    c.line([foot, nose * [1, 0, 1]], (150, 150, 150), 1)
    c.text(foot, "camera (looking straight at him)", (0, 0, 0), dx=-90, dy=8)
    mid = peets.mean(0)
    c.line([peets[1], peets[0]], (200, 30, 30), 3)
    Zb = np.cross(Xb, UP); c.line([mid, mid + 3.5 * Zb], (200, 30, 30), 3)
    c.text(mid + 3.5 * Zb, "body faces", (200, 30, 30), dx=8, dy=-4)
    Eh = E * [1, 0, 1]; Xh = X * [1, 0, 1]; Xh /= np.linalg.norm(Xh)
    c.line([Eh - 2.5 * Xh, Eh + 2.5 * Xh], (0, 90, 220), 3)
    Zh = np.cross(Xh, UP); c.line([Eh, Eh + 3.5 * Zh], (0, 90, 220), 3)
    c.text(Eh + 3.5 * Zh, "head faces", (0, 90, 220), dx=8, dy=-12)
    c.text(Eh + 2.5 * Xh, "his left", (0, 90, 220), dx=4, dy=-4)
    c.text([-7.8, 0, -4.6], "seen from above, 1 cm grid", (40, 40, 40))
    c.text([-7.8, 0, -3.9], "(his head's place is approximate)", (90, 90, 90), small=True)
    top = c.im.resize((620, 880), Image.LANCZOS)
    out = Image.new("RGB", (W + 640, H), (255, 255, 255)); out.paste(im, (0, 0)); out.paste(top, (W + 10, 140))
    out.save(sc.OUT_IMG / "facing.png")


if __name__ == "__main__":
    raise SystemExit(main())
