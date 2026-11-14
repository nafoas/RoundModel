"""Completeness check for the face whiskers, by the owner's rule (2026-11-14):
"they are all emanating from his little whisker pads ... they are all pointing towards
the whisker pads, and they are all straight."

1. Pads: on each side, the point the whiskers' nose-end lines converge on (least squares).
2. Each whisker: how far its line passes from its pad centre, how far short of it it ends,
   how much it bows.
3. Outside whiskers at his cheeks with no face part: which face whisker starts on their
   line toward the pad.
4. Face whiskers with no outside part: which traced outside hair (any class) lines up with
   their outer end.
5. A scan of every straight line pointing into each pad (angles 0.5 deg apart, offsets
   +-30 px), scored on the combined view (tools/whisker_fulllength.py), keeping stretches
   that pass the same acceptance as the sweeps and are not on a traced whisker. Control:
   the same scan with lines from points below his cheeks (other angles, same fur).

Usage: python tools/whisker_pads.py  -> data/strands/whisker_pads.json (report printed)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_whiskers as fw  # noqa: E402
import whisker_fulllength as wf  # noqa: E402
import whisker_lineview as lv  # noqa: E402

MID = 549.0
OFF = np.arange(-30, 31, 2.0)
SCAN_LEN, STEP_DEG = 480, 0.5
SECTORS = {"image_left": (150, 230), "image_right": (-50, 30)}   # directions from the pad out across that cheek
CONTROL = {"image_left": ((330.0, 1010.0), (240, 300)), "image_right": ((800.0, 1010.0), (240, 300))}


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def nose_tangent(cl, L=30):
    q = cl[-L:] if len(cl) > L else cl
    t = q[-1] - q[0]
    return cl[-1], t / np.linalg.norm(t)


def side_of(cl):
    return "image_left" if cl[:, 0].mean() < MID else "image_right"


def pads_from(W):
    pads = {}
    for side in SECTORS:
        A = np.zeros((2, 2)); b = np.zeros(2)
        for cl in W.values():
            if side_of(cl) != side:
                continue
            p, t = nose_tangent(cl); M = np.eye(2) - np.outer(t, t)
            A += len(cl) * M; b += len(cl) * M @ p
        pads[side] = np.linalg.solve(A, b)
    return pads


def scan(F, V, known, c, rng, exclude_known=True):
    runs, tot = [], 0
    s = np.arange(0, SCAN_LEN, 1.0)
    for a in np.radians(np.arange(rng[0], rng[1], STEP_DEG)):
        t = np.array([np.cos(a), np.sin(a)]); n = np.array([-t[1], t[0]])
        ka = np.mod(a, np.pi) / (np.pi / lv.NA)
        for o in OFF:
            P = c + o * n + s[:, None] * t
            x = P[:, 0] - lv.X0 - 0.5; y = P[:, 1] - lv.Y0 - 0.5
            ok = (F.sdist(P) >= 14) & F.valid(P[None])[0] & (x >= 0) & (y >= 0) & \
                 (x < lv.X1 - lv.X0 - 1) & (y < lv.Y1 - lv.Y0 - 1)
            if ok.sum() < 40:
                continue
            v = ndi.map_coordinates(V.Z, [np.full(len(P), ka), y, x], order=1, mode="nearest")
            v = np.where(ok, v, np.nan); tot += int(ok.sum())
            for a_, b_ in lv.segments(dict(kind="scan", q=P, c=v)):
                seg = P[a_:b_ + 1]
                if exclude_known and (known.query(seg)[0] <= 3).mean() >= 0.5:
                    continue
                runs.append(seg)
    runs.sort(key=lambda r: -len(r)); keep = []
    for seg in runs:
        if all(fw.overlap(seg, k, 3.0) < 0.4 for k in keep):
            keep.append(seg)
    return keep, tot


def main() -> int:
    F = fw.Face()
    d = json.loads((fw.ROOT / "data/strands/face_whiskers.json").read_text())
    o = json.loads((fw.ROOT / "data/strands/wisps.json").read_text())
    W = {w["id"]: fw.dense(np.array(w["centreline"])) for w in d["whiskers"]}
    pads = pads_from(W)
    print("pads (where his whiskers point):", {k: v.round(0).tolist() for k, v in pads.items()})
    per = []
    for k, cl in W.items():
        side = side_of(cl); c = pads[side]; p, t = nose_tangent(cl)
        ch = cl[-1] - cl[0]; n = np.array([-ch[1], ch[0]]) / np.linalg.norm(ch)
        per.append(dict(id=k, side=side, passes_pad_px=round(abs(cross(t, c - p)), 1),
                        ends_short_of_pad_px=round(float(np.hypot(*(c - p))), 0),
                        bow_px=round(float(np.abs((cl - cl[0]) @ n).max()), 1), chord_px=round(float(np.hypot(*ch)), 0)))
    cont = {w.get("continues") for w in d["whiskers"] if w.get("continues")}
    no_face = []
    for t in o["strands"]:
        if not t["class"].startswith("whisker") or t["id"] in cont:
            continue
        r, th, dist = fw.root_end(np.array(t["centreline"], float), F)
        if dist > fw.CONT_ROOT_DIST or not (fw.CONT_Y[0] <= r[1] <= fw.CONT_Y[1]):
            continue
        u = np.array([np.cos(th), np.sin(th)]); c = pads["image_left" if r[0] < MID else "image_right"]
        best = []
        for k, cl in W.items():
            v = cl[0] - r; along = v @ u
            tk = cl[min(15, len(cl) - 1)] - cl[0]; tk /= np.linalg.norm(tk)
            if 0 < along < 120:
                best.append(dict(face=k, off_line_px=round(abs(cross(u, v)), 1), in_px=round(float(along), 0),
                                 angle_deg=round(float(np.degrees(np.arccos(np.clip(tk @ u, -1, 1)))), 0)))
        best.sort(key=lambda b: b["off_line_px"])
        no_face.append(dict(outside=t["id"], root=np.round(r, 1).tolist(), on_its_line=best[:3]))
    strands = [t for t in o["strands"] if t["class"] in ("wisp", "whisker (last step)", "fringe tip")]
    no_out = []
    for w in d["whiskers"]:
        if w.get("continues"):
            continue
        cl = W[w["id"]]; e = cl[0]; t = cl[0] - cl[min(15, len(cl) - 1)]; t /= np.linalg.norm(t)
        hits = []
        for s in strands:
            sc = np.array(s["centreline"], float)
            seq = sc if abs(F.sdist(sc[0])) < abs(F.sdist(sc[-1])) else sc[::-1]
            q = fw.dense(seq); u = q[min(10, len(q) - 1)] - q[0]
            if np.linalg.norm(u) == 0:
                continue
            u /= np.linalg.norm(u); dist = float(np.hypot(*(seq[0] - e)))
            ang = float(np.degrees(np.arccos(np.clip(u @ t, -1, 1))))
            if dist <= 25 and ang <= 30:
                hits.append(dict(strand=s["id"], cls=s["class"], gap_px=round(dist, 0), angle_deg=round(ang, 0)))
        hits.sort(key=lambda h: h["gap_px"])
        no_out.append(dict(face=w["id"], outer_end_inside_outline_px=round(float(F.sdist(e)), 0), lines_up_with=hits[:3]))
    V = wf.CombinedView(lv.field_lines(d["whiskers"], F))
    known = cKDTree(np.vstack(list(W.values())))
    scans = {}
    for T, FA in ((4.0, 3.0), (3.0, 2.5)):
        lv.T_L, lv.FAINT_L = T, FA
        row = {}
        for side, rng in SECTORS.items():
            found, tot = scan(F, V, known, pads[side], rng)
            ctl, ctot = scan(F, V, known, np.array(CONTROL[side][0]), CONTROL[side][1])
            row[side] = dict(pad_pointing_untraced=[np.round(sg, 1)[::4].tolist() for sg in found],
                             count=len(found), line_px=tot, control_count=len(ctl), control_line_px=ctot)
        scans[f"accept {T} / follow {FA}"] = row
        print(f"scan at {T}/{FA}: " + "; ".join(f"{s}: {r['count']} untraced pad-pointing (control {r['control_count']})"
                                                for s, r in row.items()))
    doc = dict(about=__doc__.split("\n\n")[0], pads={k: np.round(v, 1).tolist() for k, v in pads.items()},
               per_whisker=per, outside_whiskers_without_face_part=no_face,
               face_whiskers_without_outside_part=no_out, pad_scan=scans)
    (fw.ROOT / "data/strands/whisker_pads.json").write_text(json.dumps(doc, indent=1))
    for r in no_face:
        print("no face part:", r["outside"], r["on_its_line"][:1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
