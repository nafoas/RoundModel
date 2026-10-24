"""Prince's base shape as a lofted surface (tasks/02, "Base shape, done
properly"): cross-sections along his length, driven by smooth guide curves.

Along his length u in [0, 1] (rump to nose, y from y_rear to y_nose) each
cross-section is a rounded section in the x-z plane:
  - half-width  w(u)   (the plan-view outline, what you see from above)
  - top         top(u) and underside bot(u)   (the side profile)
  - the height of the widest point, as a fraction f(u) from bot to top
  - roundness of the upper and lower halves, n_up(u), n_lo(u): 2 is an
    ellipse, larger is fuller (straighter sides, flatter top/base)
Every guide curve is a smooth spline through a few control values; the
ends of the body close smoothly (the width and height go to zero as a
rounded cap). The curves, not the surface, are what get fitted.

usage:
  python tools/loft.py init  PARAMS.json            # starting curves from the old mesh's sections
  python tools/loft.py build PARAMS.json OUTDIR     # mesh -> OUTDIR/head.obj (+ eyes, ears)
  python tools/loft.py fit   PARAMS.json OUT.json   # fit the curves to his outlines
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import CubicSpline
from scipy.optimize import minimize
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parents[1]
CURVES = ["w", "top", "bot", "f", "n_up", "n_lo"]
K = 9  # control values per curve, evenly spaced along his length


# ---------------------------------------------------------------- the surface

def cap(u, p_rear, p_front):
    """Rounded closing at both ends: 0 at the tips, 1 away from them."""
    a = np.clip(u / 0.22, 0, 1)
    b = np.clip((1 - u) / 0.22, 0, 1)
    ca = np.sqrt(1 - (1 - a) ** 2) ** p_rear
    cb = np.sqrt(1 - (1 - b) ** 2) ** p_front
    return ca * cb


def curves(P, u):
    uk = np.linspace(0, 1, K)
    return {c: CubicSpline(uk, np.asarray(P[c], float), bc_type="natural")(u) for c in CURVES}


def surface(P, nu=140, nphi=96):
    """Vertices (nu*nphi + 2 tips) and faces of the lofted body."""
    t = np.linspace(0, 1, nu)
    u = 0.5 - 0.5 * np.cos(np.pi * t)  # denser near the ends, where it curves most
    C = curves(P, u)
    e = cap(u, P.get("p_rear", 1.0), P.get("p_front", 1.0))
    y = P["y_rear"] + (P["y_nose"] - P["y_rear"]) * u
    w = np.maximum(C["w"], 1e-4) * e
    top, bot = C["top"], C["bot"]
    mid = bot + np.clip(C["f"], 0.05, 0.95) * (top - bot)
    # the section shrinks toward its own middle at the tips
    zc_tip = mid
    top = zc_tip + (top - zc_tip) * e
    bot = zc_tip + (bot - zc_tip) * e
    phi = np.linspace(0, 2 * np.pi, nphi, endpoint=False)
    c, s = np.cos(phi), np.sin(phi)
    V = np.zeros((nu, nphi, 3))
    for i in range(nu):
        nu_, nl_ = max(C["n_up"][i], 1.2), max(C["n_lo"][i], 1.2)
        n = np.where(s >= 0, nu_, nl_)
        V[i, :, 0] = w[i] * np.sign(c) * np.abs(c) ** (2 / n)
        V[i, :, 1] = y[i]
        zz = np.abs(s) ** (2 / n)
        V[i, :, 2] = np.where(s >= 0, mid[i] + (top[i] - mid[i]) * zz, mid[i] - (mid[i] - bot[i]) * zz)
    V = V.reshape(-1, 3)
    F = []
    for i in range(nu - 1):
        for j in range(nphi):
            a, b = i * nphi + j, i * nphi + (j + 1) % nphi
            c_, d = a + nphi, b + nphi
            F += [(a, c_, b), (b, c_, d)]
    return V, np.array(F)


def write_obj(path, V, F):
    with open(path, "w") as fh:
        fh.write("".join(f"v {a:.6f} {b:.6f} {c:.6f}\n" for a, b, c in V))
        fh.write("".join(f"f {a + 1} {b + 1} {c + 1}\n" for a, b, c in F))


def ellipsoid(c, r, rot_deg, n1=24, n2=48):
    a, b = np.meshgrid(np.linspace(0, np.pi, n1), np.linspace(0, 2 * np.pi, n2), indexing="ij")
    P = np.stack([np.sin(a) * np.cos(b), np.sin(a) * np.sin(b), np.cos(a)], -1).reshape(-1, 3) * r
    P = P @ R.from_euler("xyz", rot_deg, degrees=True).as_matrix().T + c
    F = []
    for i in range(n1 - 1):
        for j in range(n2 - 1):
            p, q, s_, t_ = i * n2 + j, i * n2 + j + 1, (i + 1) * n2 + j, (i + 1) * n2 + j + 1
            F += [(p, s_, q), (q, s_, t_)]
    return P, np.array(F)


def extras(P):
    """Eyes and ears (placeholders: the eyes come from the eye fit, the ears
    are only blocked in until their own step)."""
    out = []
    for e in P.get("eyes", []):
        out.append(("eye_" + e["side"],) + ellipsoid(np.array(e["centre"]), e["radius"], [0, 0, 0]))
    for e in P.get("ears", []):
        c = np.array(e["centre"])
        for side, sx in (("R", 1), ("L", -1)):
            rx, ry, rz = e["rot"]
            out.append(("ear_" + side,) + ellipsoid(c * [sx, 1, 1], np.array(e["radii"]), [rx, ry * sx, rz * sx]))
    return out


def build(P, outdir):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    V, F = surface(P)
    meshes = [(V, F)]
    for name, Ve, Fe in extras(P):
        if name.startswith("ear"):
            meshes.append((Ve, Fe))
        else:
            write_obj(out / f"{name}.obj", Ve, Fe)
    Vs, Fs, o = [], [], 0
    for Vm, Fm in meshes:
        Vs.append(Vm)
        Fs.append(Fm + o)
        o += len(Vm)
    write_obj(out / "head.obj", np.vstack(Vs), np.vstack(Fs))
    return V, F


# ---------------------------------------------------------------- his outlines

def views():
    """(name, camera, his mask, weight). Top-down weighs most (his
    circumference), then the master, then the right profile and back."""
    cams = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]
    side = json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"]
    W = {"sheet_09_top_down": 3.0, "master_front_standing": 2.0, "sheet_03_right_profile": 1.0,
         "sheet_04_back_3q_right": 1.0, "sheet_05_back": 1.0, "sheet_02_front_3q": 0.7,
         "sheet_08_front_3q_left": 0.7, "sheet_01_front": 0.7, "sheet_06_back_3q_left": 0.6,
         "sheet_07_left_profile": 0.4}
    out = []
    for name, wgt in W.items():
        if name in side:
            c = side[name]
            mask = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{name}.png")) > 127
            cam = dict(rot=c["rotvec_world_to_cam"], pos=c["camera_position_m"], f=c["focal_px"], pp=c["principal_px"])
        elif name == "master_front_standing":
            c = cams[name]
            mask = np.asarray(Image.open(ROOT / "checkpoints/cp4/outlines/master_front_standing.png")) > 127
            cam = dict(rot=c["rotvec_world_to_cam"], pos=c["camera_position_m"], f=c["focal_px"],
                       pp=[mask.shape[1] / 2, mask.shape[0] / 2])
        else:
            c = cams[name]
            panel = name.replace("sheet_02_front_3q", "sheet_02_front_3q_right")
            mask = np.asarray(Image.open(ROOT / f"checkpoints/cp1/masks/{panel}.outline.png").convert("L")) > 127
            cam = dict(rot=c["rotvec_world_to_cam"], pos=c["camera_position_m"], f=c["focal_px"],
                       pp=[mask.shape[1] / 2, mask.shape[0] / 2])
        pose = ROOT / f"checkpoints/cp3/head_poses_parts/{name}.json"
        cam["pose"] = json.loads(pose.read_text()) if pose.exists() else None
        out.append((name, cam, mask, wgt))
    return out


def posed(V, pose):
    """His head as he holds it in that photo (the head turns on the neck; the
    body stays)."""
    if pose is None:
        return V
    from sculpt import NECK_PIVOT, head_weight
    hw = head_weight(V)
    Rm = R.from_rotvec(pose["rotvec"]).as_matrix()
    Vp = (V - NECK_PIVOT) @ Rm.T + NECK_PIVOT + np.asarray(pose["shift_m"])
    return V + hw[:, None] * (Vp - V)


def silhouette(V, F, cam, shape, scale):
    Rc = R.from_rotvec(cam["rot"]).as_matrix()
    Xc = (V - np.asarray(cam["pos"])) @ Rc.T
    uv = cam["f"] * Xc[:, :2] / Xc[:, 2:3] + np.asarray(cam["pp"])
    uv = np.round(uv * scale * 4).astype(np.int32)  # 2 bits of sub-pixel precision
    m = np.zeros(shape, np.uint8)
    cv2.fillPoly(m, list(uv[F]), 1, lineType=cv2.LINE_8, shift=2)
    return m.astype(bool)


def prepare(target_px=320):
    out = []
    for name, cam, mask, wgt in views():
        s = target_px / max(mask.shape)
        small = cv2.resize(mask.astype(np.uint8), (round(mask.shape[1] * s), round(mask.shape[0] * s)),
                           interpolation=cv2.INTER_AREA) > 0
        out.append((name, cam, small, wgt, s))
    return out


def score(P, prepared, detail=False):
    V, F = surface(P, nu=70, nphi=48)
    ex = [(Ve, Fe) for name, Ve, Fe in extras(P) if name.startswith("ear")]
    tot, parts = 0.0, {}
    for name, cam, H, wgt, s in prepared:
        Vp = posed(V, cam["pose"])
        M = silhouette(Vp, F, cam, H.shape, s)
        for Ve, Fe in ex:
            M |= silhouette(posed(Ve, cam["pose"]), Fe, cam, H.shape, s)
        x = (M ^ H).sum() / H.sum()
        parts[name] = x
        tot += wgt * x
    if detail:
        return tot, parts
    return tot


# ---------------------------------------------------------------- start and fit

def init_from_mesh(path):
    """Starting curves: sections of the old outline-fitted mesh (its outline
    was right, its form was not; the curves only start there)."""
    from refine_side_cameras import load_obj
    V, _ = load_obj(path)
    y0, y1 = V[:, 1].min(), V[:, 1].max()
    P = {"y_rear": float(y0), "y_nose": float(y1), "p_rear": 1.0, "p_front": 1.0}
    uk = np.linspace(0, 1, K)
    vals = {c: [] for c in CURVES}
    for u in uk:
        uu = np.clip(u, 0.06, 0.94)
        y = y0 + (y1 - y0) * uu
        S = V[np.abs(V[:, 1] - y) < 0.004]
        w = np.abs(S[:, 0]).max()
        top, bot = S[:, 2].max(), S[:, 2].min()
        zw = S[np.argmax(np.abs(S[:, 0])), 2]
        vals["w"].append(float(w))
        vals["top"].append(float(top))
        vals["bot"].append(float(bot))
        vals["f"].append(float(np.clip((zw - bot) / max(top - bot, 1e-3), 0.1, 0.9)))
        vals["n_up"].append(2.4)
        vals["n_lo"].append(2.8)
    P.update(vals)
    return P


def pack(P, free):
    return np.concatenate([np.atleast_1d(np.asarray(P[k], float)) for k in free])


def unpack(P, x, free):
    Q = json.loads(json.dumps(P))
    i = 0
    for k in free:
        n = np.size(P[k])
        v = x[i:i + n]
        Q[k] = v.tolist() if isinstance(P[k], list) else float(v[0])
        i += n
    return Q


def smoothness(P):
    """Curves stay smooth: bending of each guide curve, scaled to its size."""
    pen = 0.0
    for c, sc in (("w", 0.01), ("top", 0.01), ("bot", 0.01), ("f", 0.1), ("n_up", 0.5), ("n_lo", 0.5)):
        v = np.asarray(P[c])
        pen += np.sum((np.diff(v, 2) / sc) ** 2)
    return pen


def fit(P, out, rounds=4):
    prepared = prepare()
    free = ["y_rear", "y_nose"] + CURVES + ["p_rear", "p_front"]
    lam = 0.002

    def obj(x):
        Q = unpack(P, x, free)
        return score(Q, prepared) + lam * smoothness(Q)

    x = pack(P, free)
    best = obj(x)
    print("start", round(best, 4), {k: round(v, 3) for k, v in score(P, prepared, True)[1].items()})
    for r in range(rounds):
        res = minimize(obj, x, method="Powell", options={"maxiter": 3000, "xtol": 1e-4, "ftol": 1e-5})
        x = res.x
        Q = unpack(P, x, free)
        t, parts = score(Q, prepared, True)
        print(f"round {r}: {res.fun:.4f}", {k: round(v, 3) for k, v in parts.items()}, flush=True)
        Path(out).write_text(json.dumps(Q, indent=1))
        if best - res.fun < 1e-4:
            break
        best = res.fun
    return unpack(P, x, free)


def main():
    cmd = sys.argv[1]
    if cmd == "init":
        P = init_from_mesh(ROOT / "checkpoints/cp3/prince_cp3_head_body.obj")
        old = json.loads((ROOT / "models/prince_parts.json").read_text())
        P["eyes"] = old["eyes"]
        ear = [p for p in old["parts"] if p["name"] == "ear"][0]
        P["ears"] = [{"centre": ear["centre"], "radii": ear["radii"], "rot": ear["rot"]}]
        Path(sys.argv[2]).write_text(json.dumps(P, indent=1))
        print(json.dumps({k: P[k] for k in CURVES}, indent=None))
    elif cmd == "build":
        P = json.loads(Path(sys.argv[2]).read_text())
        build(P, sys.argv[3])
    elif cmd == "score":
        P = json.loads(Path(sys.argv[2]).read_text())
        t, parts = score(P, prepare(), True)
        print(round(t, 4), {k: round(v, 3) for k, v in parts.items()})
    elif cmd == "fit":
        P = json.loads(Path(sys.argv[2]).read_text())
        fit(P, sys.argv[3])


if __name__ == "__main__":
    main()
