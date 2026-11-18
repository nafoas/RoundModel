"""How Prince is being looked at in the anchor photo: how his head and body are turned and tipped relative
to the camera (owner, 2026-11-16: "place the camera about six inches away ... exactly as it was when I
captured it, and then determine what way he is being looked at").

The camera: the room's camera for this photo (data/cameras.json anchor_front: since 2026-11-17 the depth
model's, MoGe-2; tools/scene.py). Then, from the photo:
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
- HEAD FROM HIS MEASURED SURFACE (since 2026-11-18; the answer): the same questions read from where the depth
  model (MoGe-2, tools/visible_depth.py) puts each point of him: (1) mirror pairs in 3D (eyes, nostril wings, lip
  corners): the line from one to the other runs along his left-right axis; (2) the way each eye faces (a plane
  through its measured surface): two mirror-image eyes face equally far to each side; (3) his nose against the
  middle of his eyes, less what his tip alone does. Left out, with reasons: the mouth corners (only 1.7 cm apart)
  and the ear bases (on his outline, where distances are least sure). His nod: as measured slopes (there is no
  "level" for a rabbit's head to measure it against); a later photo can be compared with them.
The photo-only head reading (the mirror pairs as rays, the eye ovals) is kept as a record: it read his tip as
part of a turn, and swings with the lens.

Uncertainty: every landmark is wobbled by its own uncertainty (data/strands/landmarks.json, sure_px, as 2
standard deviations), each pair is left out in turn, and the camera is varied (the other depth model's lens;
tilted 2 deg up and down).

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
from prince.space import Camera, rot_x  # noqa: E402
import scene as sc  # noqa: E402

HEAD_PAIRS = [("eye_his_left", "eye_his_right"), ("nostril_wing_his_left", "nostril_wing_his_right"),
              ("mouth_corner_his_left", "mouth_corner_his_right"), ("lip_corner_his_left", "lip_corner_his_right"),
              ("ear_base_inner_his_left", "ear_base_inner_his_right"),
              ("ear_base_outer_his_left", "ear_base_outer_his_right")]
UP = np.array([0.0, 1.0, 0.0])
SURFACE_MODEL = "moge2"                  # owner, 2026-11-17: the one that looks like a rabbit
SURFACE_PAIRS = [("eye_his_left", "eye_his_right"), ("nostril_wing_his_left", "nostril_wing_his_right"),
                 ("lip_corner_his_left", "lip_corner_his_right")]
SURFACE_LEFT_OUT = {
    "mouth corners": "only 1.7 cm apart: a 1 mm error in depth is 3.5 deg of turn",
    "ear bases (inner and outer)": "on his outline, in the outer band whose distances are least sure (inner pair: 52 deg)"}
EYE_REGION = 0.7                         # each eye's surface: inside 0.7 x its oval (steady from 0.5 to 0.9)


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
    """Turn: + = toward his left (his left side further from a camera in front of him). Tip: + = his left side up.
    X must be a unit direction (its tip is read as arcsin of its height)."""
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


def eye_facing(P, eye, cam, scale=EYE_REGION):
    """Which way an eye faces, from its measured surface: the plane through its 3D points inside `scale` x its oval.
    Returns (degrees toward his left, degrees up, number of points)."""
    H, W = P.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    (cx, cy), (a, b) = eye["at_px"], eye["oval"]["semi_axes_px"]; ang = np.radians(eye["oval"]["long_axis_angle_deg"])
    dx, dy = xx - cx, yy - cy
    u = dx * np.cos(ang) + dy * np.sin(ang); v = -dx * np.sin(ang) + dy * np.cos(ang)
    pts = P[(u / (a * scale)) ** 2 + (v / (b * scale)) ** 2 <= 1]; pts = pts[np.isfinite(pts[:, 0])]
    c = pts.mean(0); n = np.linalg.svd(pts - c, full_matrices=False)[2][2]
    if n @ (cam.C - c) < 0:
        n = -n
    return float(np.degrees(np.arctan2(n[0], n[2]))), float(np.degrees(np.arcsin(np.clip(n[1], -1, 1)))), len(pts)


def from_surface(lm, rng, runs=300):
    """His head's turn, tip and nod read from his measured surface (see the top of this file)."""
    import visible_depth as vd
    cam, P, _ = vd.room_points(SURFACE_MODEL)
    pt = lambda uv: vd.point_near(P, uv)

    def pairs(wobble=False):
        out = {}
        for a, b in SURFACE_PAIRS:
            ua, ub = np.array(lm[a]["at_px"], float), np.array(lm[b]["at_px"], float)
            if wobble:
                ua = ua + rng.normal(0, lm[a]["sure_px"] / 2, 2); ub = ub + rng.normal(0, lm[b]["sure_px"] / 2, 2)
            v = pt(ua) - pt(ub)
            out[a.replace("_his_left", "")] = turn_tip(v / np.linalg.norm(v))       # turn_tip needs a unit direction
        return out
    pr = pairs()
    tip = float(np.mean([v[1] for v in pr.values()]))
    eyes = {k: eye_facing(P, lm[k], cam) for k in ("eye_his_left", "eye_his_right")}
    (azl, ell, nl), (azr, elr, nr) = eyes["eye_his_left"], eyes["eye_his_right"]
    E = (pt(lm["eye_his_left"]["at_px"]) + pt(lm["eye_his_right"]["at_px"])) / 2
    d = pt(lm["nose_y_centre"]["at_px"]) - E
    tip_shift = -d[1] * np.sin(np.radians(tip))                   # his tip alone moves his nose this far to his left
    nose_turn = float(np.degrees(np.arctan2(d[0] - tip_shift, d[2])))
    readings = {f"{k} pair (3D)": round(v[0], 1) for k, v in pr.items()}
    readings["the way his two eyes face"] = round((azl + azr) / 2, 1)
    readings["his nose against the middle of his eyes, less his tip"] = round(nose_turn, 1)
    turn = float(np.median(list(readings.values())))
    wob = []
    for _ in range(runs):
        w = pairs(wobble=True)
        wob.append((np.median([v[0] for v in w.values()] + [(azl + azr) / 2, nose_turn]), np.mean([v[1] for v in w.values()])))
    wob = np.array(wob)
    X = np.array([np.cos(np.radians(tip)) * np.cos(np.radians(turn)), np.sin(np.radians(tip)),
                  -np.cos(np.radians(tip)) * np.sin(np.radians(turn))])
    slope = lambda v: round(float(np.degrees(np.arctan2(-v[1], np.hypot(v[0], v[2])))), 1)
    nod = dict(
        eyes_middle_to_nose_slopes_below_level_deg=slope(d),
        nose_to_chin_slopes_below_level_deg=slope(pt(lm["chin_midline"]["at_px"]) - pt(lm["nose_y_centre"]["at_px"])),
        eyes_face_up_deg=dict(his_left=round(ell, 1), his_right=round(elr, 1), mean=round((ell + elr) / 2, 1)),
        meaning="no photo shows his head 'level', so his nod is kept as these measured slopes; a later photo of him "
                "is compared against them. (A plane through the front of his face was tried and not used: his muzzle "
                "is round, so it depends on the window drawn.)")
    return dict(turned_deg=round(turn, 1), tipped_deg=round(tip, 1),
                meaning="turned + = toward his own left (his nose toward the picture's right); tipped + = his left side up",
                from_model=f"{SURFACE_MODEL} (data/scene/visible_depth_{SURFACE_MODEL}.json)",
                turn_readings_deg=readings, turned_is="the middle (median) reading",
                tip_per_pair_deg={k: round(v[1], 1) for k, v in pr.items()},
                eyes_face_to_the_sides_deg=dict(his_left=round(azl, 1), his_right=round(-azr, 1),
                                                points_used=[nl, nr], region=f"{EYE_REGION} x each eye's oval"),
                nose_against_eyes_cm=dict(to_his_left=round(float(d[0]), 2), of_which_his_tip=round(float(tip_shift), 2)),
                left_out=SURFACE_LEFT_OUT,
                landmark_wobble_2sd=dict(turned=np.percentile(wob[:, 0], [2.5, 97.5]).round(1).tolist(),
                                         tipped=np.percentile(wob[:, 1], [2.5, 97.5]).round(1).tolist()),
                left_right_axis_room=np.round(X, 5).tolist(), nod=nod)


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
    # the camera varied: the other depth model's lens (Depth Pro, set aside), and tilted 2 deg up and down
    photo = Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB")
    other_f = json.loads((ROOT / "data/scene/visible_depth_depthpro.json").read_text())["lens_px"]
    across = []
    for f in (cam.f, other_f):
        for tilt in (-2.0, 0.0, 2.0):
            c2 = Camera(R=rot_x(np.radians(tilt)) @ cam.R, C=cam.C, f=f, cx=cam.cx, cy=cam.cy, width=cam.width,
                        height=cam.height)
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
    surf = from_surface(lm, rng)
    sturn, stip = surf["turned_deg"], surf["tipped_deg"]
    rd = surf["turn_readings_deg"].values()
    doc = dict(
        about=__doc__.split("\n\n")[0], camera="data/cameras.json anchor_front (the depth model's camera, MoGe-2)",
        head=surf,
        head_photo_only=dict(
                  superseded=("2026-11-18 by the head read from his measured surface ('head'). From the picture alone: "
                              "his nose sits right of the middle of his eyes, but his 5 deg tip does most of that; the "
                              "mirror pairs as rays swing with the lens (7.8 deg with the six-inch camera, 12.7 with "
                              "this one) and lean on the mouth, lip corners and ear bases; the eye ovals differ (5.3) "
                              "though the eyes' measured surfaces face equally far to each side"),
                  turned_deg=round(turn, 1), tipped_deg=round(tip, 1),
                  meaning="turned + = toward his own left (his nose toward the picture's right, his right cheek nearer "
                          "the camera); tipped + = his left side up (a little head tilt toward his right)",
                  left_right_axis_room=np.round(X, 5).tolist(),
                  pair_misfit_deg={f"{a.replace('_his_left', '')}": round(float(m), 2) for (a, b), m in zip(HEAD_PAIRS, misfit)},
                  landmark_wobble_2sd={"turned": [round(float(np.percentile(mc[:, 0], 2.5)), 1), round(float(np.percentile(mc[:, 0], 97.5)), 1)],
                                       "tipped": [round(float(np.percentile(mc[:, 1], 2.5)), 1), round(float(np.percentile(mc[:, 1], 97.5)), 1)]},
                  leave_one_pair_out=loo,
                  camera_varied={"turned": [round(float(across[:, 0].min()), 1), round(float(across[:, 0].max()), 1)],
                                          "tipped": [round(float(across[:, 1].min()), 1), round(float(across[:, 1].max()), 1)]}),
        eyes_check_photo_only=eyes,
        body=dict(turned_deg=round(body_turn, 1), peets_on_the_surface_cm=np.round(peets_on_surface, 2).tolist(),
                  camera_varied=[round(float(across[:, 2].min()), 1), round(float(across[:, 2].max()), 1)],
                  note=("from the lowest point of each peet (view-dependent points, on a soft surface): a rough "
                        "reading of his body's turn")),
        head_relative_to_body_turned_deg=round(sturn - body_turn, 1),
        eyes_and_nostrils_only=dict(turned_tipped_deg=t2, landmark_wobble_2sd_turned=np.percentile(mc2[:, 0], [2.5, 97.5]).round(1).tolist(),
                                    note="the two pairs that fit best (misfit < 0.5 deg); two pairs alone leave the turn loose"),
        summary=dict(
            tipped=(f"his left side up, about {stip:.0f} deg (measured surface {min(surf['tip_per_pair_deg'].values()):.0f}-"
                    f"{max(surf['tip_per_pair_deg'].values()):.0f}; the photo alone {tip:.0f}): SOLID"),
            turned=(f"hardly at all: {abs(sturn):.1f} deg toward his {'left' if sturn >= 0 else 'right'}, square to the "
                    f"camera within about {max(abs(min(rd)), abs(max(rd))):.0f} deg: read from his measured surface "
                    f"(readings {min(rd):+.1f} to {max(rd):+.1f}: his eyes, nostril wings and lip corners in 3D, the way "
                    f"his two eyes face, his nose against his eyes). The photo alone said 5-13 deg toward his left: it "
                    f"read his tip as part of a turn"),
            body=f"rough: about {abs(body_turn):.0f} deg toward his {'right' if body_turn < 0 else 'left'} (from his peets' lowest points)",
            head_vs_body=(f"his body is turned about {abs(body_turn):.0f} deg toward his right and his head is square to "
                          f"the camera, so on his body his head is turned about {abs(sturn - body_turn):.0f} deg toward "
                          f"his left, and tipped"),
            nod=(f"the line from between his eyes to his nose slopes {surf['nod']['eyes_middle_to_nose_slopes_below_level_deg']:.0f} "
                 f"deg below level; his eyes face about {surf['nod']['eyes_face_up_deg']['mean']:.0f} deg up (measured "
                 f"slopes: no photo shows his head level)")),
        camera_tilt_note=("tipped is measured against the camera's level; the owner remembers holding it straight on. "
                          "His peets' line does not tip the same way, so the tip is his head, not the phone"))
    (ROOT / "data/scene/facing.json").write_text(json.dumps(doc, indent=1))
    sheet(photo, lm, cam, np.array(surf["left_right_axis_room"]), Xb, peets_on_surface, doc)
    print(json.dumps({k: doc[k] for k in ("head", "body", "head_relative_to_body_turned_deg", "summary")}, indent=1))
    return 0


def sheet(photo, lm, cam, X, Xb, peets, doc):
    s = 1
    W, H = photo.size
    im = photo.copy().convert("RGB"); d = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=22); small = ImageFont.load_default(size=17)
    for a, b in HEAD_PAIRS:                                  # orange: the pairs read in 3D; grey: left out
        col = (235, 120, 0) if (a, b) in SURFACE_PAIRS else (150, 150, 150)
        pa, pb = lm[a]["at_px"], lm[b]["at_px"]
        d.line([tuple(pa), tuple(pb)], fill=col, width=3)
        for p in (pa, pb):
            d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], outline=col, width=2)
    pa, pb = lm["peet_bottom_his_left"]["at_px"], lm["peet_bottom_his_right"]["at_px"]
    d.line([tuple(pa), tuple(pb)], fill=(200, 30, 30), width=3)
    # his head's left-right axis, drawn through the middle of his eyes where the depth model measured them
    E = (sc.lm_point(cam, lm, "eye_his_left") + sc.lm_point(cam, lm, "eye_his_right")) / 2
    q = cam.project([E - 2.5 * X, E + 2.5 * X])
    d.line([tuple(q[0]), tuple(q[1])], fill=(0, 90, 220), width=4)
    lvl = cam.project([E - 2.5 * np.array([1.0, 0, 0]), E + 2.5 * np.array([1.0, 0, 0])])
    d.line([tuple(lvl[0]), tuple(lvl[1])], fill=(120, 120, 120), width=2)
    h = doc["head"]
    rd = list(h["turn_readings_deg"].values()); nod = h["nod"]
    d.rectangle([0, 0, W, 196], fill=(255, 255, 255))
    d.text((10, 6), f"Head (from his measured surface): tipped {h['tipped_deg']:.1f} deg, his left side up: solid.",
           fill=(0, 0, 0), font=small)
    d.text((10, 32), f"Turned hardly at all: {abs(h['turned_deg']):.1f} deg toward his {'left' if h['turned_deg'] >= 0 else 'right'} "
                     f"(readings {min(rd):+.1f} to {max(rd):+.1f}). The photo alone said 5-13: it took his tip for a turn.",
           fill=(0, 0, 0), font=small)
    d.text((10, 58), f"Body (from his peets, rough): turned {abs(doc['body']['turned_deg']):.1f} deg toward his "
                     f"{'right' if doc['body']['turned_deg'] < 0 else 'left'}; so on his body his head turns "
                     f"{abs(doc['head_relative_to_body_turned_deg']):.0f} deg toward his left.", fill=(0, 0, 0), font=small)
    d.text((10, 84), f"Nod (measured slopes): the line from between his eyes to his nose drops {nod['eyes_middle_to_nose_slopes_below_level_deg']:.0f} deg "
                     f"below level; his eyes face {nod['eyes_face_up_deg']['mean']:.0f} deg up.", fill=(0, 0, 0), font=small)
    d.text((10, 120), "orange: mirror pairs read in 3D; grey: left out (too close together, or on his outline); red: his peets' "
                      "lowest points;", fill=(60, 60, 60), font=small)
    d.text((10, 142), "blue: his head's left-right axis; grey line: level (the camera's left-right).", fill=(60, 60, 60), font=small)
    d.text((10, 164), "Camera: the depth model's (MoGe-2), straight on, about 24.5 cm away, a touch below his eyes.",
           fill=(60, 60, 60), font=small)
    # top view: camera, his body axis (at his peets), his head axis (at his eyes)
    view = Camera.orbit([0, 0, 13.5], 200, yaw_deg=0, pitch_deg=89.5, f=4300, width=620, height=880)
    c = sc.Canvas(view, scale=2)
    for x in np.arange(-10, 10.01, 1):
        c.line(np.c_[np.full(2, x), np.zeros(2), [-6, 33]], (205, 205, 200) if x % 2 else (175, 175, 170))
    for z in np.arange(-6, 33.01, 1):
        c.line(np.c_[[-10, 10], np.zeros(2), np.full(2, z)], (205, 205, 200) if z % 2 else (175, 175, 170))
    foot = cam.C * [1, 0, 1]
    tri = [foot + cam.right * 0.8 + cam.forward * [1, 0, 1] * 1.2, foot, foot - cam.right * 0.8 + cam.forward * [1, 0, 1] * 1.2]
    c.line(tri, (0, 0, 0), 2)
    nose = sc.lm_point(cam, lm, "nose_y_centre")
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
    c.text([-9.6, 0, -5.4], "seen from above, 1 cm grid", (40, 40, 40))
    c.text([-9.6, 0, -4.4], "(his eyes and nose where the depth model measured them)", (90, 90, 90), small=True)
    top = c.im.resize((620, 880), Image.LANCZOS)
    out = Image.new("RGB", (W + 640, H), (255, 255, 255)); out.paste(im, (0, 0)); out.paste(top, (W + 10, 210))
    out.save(sc.OUT_IMG / "facing.png")


if __name__ == "__main__":
    raise SystemExit(main())
