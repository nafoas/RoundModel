"""Fit the eyes to every photo at once: small changes to each eye's centre,
facing angle, the lid opening and the fur round it (the eye size
is measured in the profile photo, not fitted), kept only when they raise the
combined part score (part_score.py; the master's eyes count double, the
three-quarter's half-hidden far eye half). Coordinate search, one change at a
time; every try is logged.

usage: eye_opt.py ROUNDS     (writes the best log to sculpt/head_log.json)
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
WEIGHTS = {"master_front_standing:eye_R": 2, "master_front_standing:eye_L": 2,
           "sheet_02_front_3q:eye_R": 0.5}
LOG = ROOT / "sculpt/head_log.json"
TRIES = ROOT / "work/eye_opt_tries.jsonl"


def eye(L, s):
    return [x for x in L["steps"] if x["op"] == "eye" and x["side"] == s][0]


def sockets(L):
    return [x for x in L["steps"] if x["op"] == "socket"]


def yaw_pitch(ax):
    ax = np.asarray(ax) / np.linalg.norm(ax)
    return np.degrees(np.arctan2(abs(ax[0]), ax[1])), np.degrees(np.arcsin(ax[2]))


def set_axis(st, yaw, pitch):
    s = 1 if st["side"] == "R" else -1
    a, p = np.radians(yaw), np.radians(pitch)
    st["axis"] = [round(s * np.sin(a) * np.cos(p), 5), round(np.cos(a) * np.cos(p), 5), round(np.sin(p), 5)]


# parameter: (name, step, apply(L, delta))
def p_centre(side, k):
    def f(L, d):
        st = eye(L, side)
        st["centre"][k] = round(st["centre"][k] + d, 5)
    return f


def p_yaw(side):
    def f(L, d):
        st = eye(L, side)
        y, p = yaw_pitch(st["axis"])
        set_axis(st, y + d, p)
    return f


def p_pitch(L, d):
    for s in ("R", "L"):
        st = eye(L, s)
        y, p = yaw_pitch(st["axis"])
        set_axis(st, y, p + d)


def p_socket(key, side=None):
    def f(L, d):
        for st in sockets(L):
            if side == "L":
                o = st.setdefault("mirror_overrides", {})
                o[key] = round(o.get(key, st[key]) + d, 5)
            else:
                st[key] = round(st[key] + d, 5)
                if "mirror_overrides" in st and key in st["mirror_overrides"]:
                    st["mirror_overrides"][key] = round(st["mirror_overrides"][key] + d, 5)
    return f


def p_lidfur(key):
    def f(L, d):
        for st in L["steps"]:
            if st["op"] == "lid_fur":
                st[key] = round(max(st[key] + d, 0.0), 5) if key != "brow_deg" else st[key] + d
    return f


def p_radius(L, d):
    for s in ("R", "L"):
        st = eye(L, s)
        ax = np.asarray(st["axis"]) / np.linalg.norm(st["axis"])
        st["radius"] = round(st["radius"] + d, 5)
        # keep the front of the eye where it is
        st["centre"] = (np.asarray(st["centre"]) - ax * d).round(5).tolist()


PARAMS = [
    ("hood", 0.001, p_lidfur("hood")),
    ("rim_v", 0.0006, p_socket("rim_v")),
    ("rim_h", 0.0006, p_socket("rim_h")),
    ("proud", 0.0006, p_socket("proud")),
    ("R z", 0.0008, p_centre("R", 2)), ("L z", 0.0008, p_centre("L", 2)),
    ("R x", 0.0008, p_centre("R", 0)), ("L x", 0.0008, p_centre("L", 0)),
    ("R y", 0.0010, p_centre("R", 1)), ("L y", 0.0010, p_centre("L", 1)),
    ("R yaw", 3.0, p_yaw("R")), ("L yaw", 3.0, p_yaw("L")),
    ("pitch", 3.0, p_pitch),
    ("hood", 0.001, p_lidfur("hood")),
    ("cheek", 0.001, p_lidfur("cheek")),
    ("brow", 0.001, p_lidfur("brow")),
    ("brow dir", 15.0, p_lidfur("brow_deg")),
    ("lid band", 0.002, p_lidfur("band")),
    ("L rim_h", 0.0006, p_socket("rim_h", "L")),
    ("L rim_v", 0.0006, p_socket("rim_v", "L")),
]


def evaluate(L, tag):
    d = ROOT / "work/opt"
    tmp = ROOT / "work/opt_log.json"
    tmp.write_text(json.dumps(L, indent=1))
    subprocess.run([PY, str(ROOT / "tools/sculpt.py"), str(tmp), str(d)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([PY, str(ROOT / "tools/part_score.py"), str(d)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([PY, str(ROOT / "tools/zone_score.py"), str(d)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sc = json.loads((d / "part_scores.json").read_text())
    zones = json.loads((d / "zone_scores.json").read_text())
    sys.path.insert(0, str(ROOT / "tools"))
    from smooth_score import score as smooth
    p95, _ = smooth(d, tmp)
    eyes_ = sum(WEIGHTS.get(k, 1) * v["iou"] for k, v in sc.items()) / sum(WEIGHTS.get(k, 1) for k in sc)
    zone_mm = float(np.mean([ab for _, ab in zones.values()]))
    # 1 mm of outline off costs as much as 5% of eye overlap; a 0.01 mm rise
    # in the bend percentile (walls, notches, flaps) as much as 1%
    tot = eyes_ - 0.05 * zone_mm - 1.0 * p95
    for k, (_, ab) in zones.items():
        sc["zone:" + k.split(":")[1][:20]] = {"iou": -ab}
    sc["bend p95"] = {"iou": -p95}
    with open(TRIES, "a") as fh:
        fh.write(json.dumps({"tag": tag, "score": tot, "parts": {k: round(v["iou"], 3) for k, v in sc.items()}}) + "\n")
    return tot, sc


def main(rounds):
    best = json.loads(LOG.read_text())
    bs, parts = evaluate(best, "start")
    print(f"start {bs * 100:.2f}", flush=True)
    steps = {n: s for n, s, _ in PARAMS}
    for r in range(rounds):
        improved = False
        for name, _, f in PARAMS:
            for sgn in (+1, -1):
                L = copy.deepcopy(best)
                f(L, sgn * steps[name])
                s, sc = evaluate(L, f"r{r} {name} {sgn * steps[name]:+g}")
                if s > bs + 0.0005:
                    best, bs, parts = L, s, sc
                    LOG.write_text(json.dumps(best, indent=1))
                    improved = True
                    print(f"round {r}: {name} {sgn * steps[name]:+g} -> {bs * 100:.2f}  "
                          + " ".join(f"{k[-14:]} {v['iou'] * 100:.0f}" for k, v in sc.items()),
                          flush=True)
                    break
        if not improved:
            for n in steps:
                steps[n] /= 2
            print(f"round {r}: no gain, halving steps", flush=True)
    print(f"final {bs * 100:.2f}", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]))
