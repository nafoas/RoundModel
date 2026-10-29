"""The same maps from the model (docs/MEASURING.md step D), and the comparison
with his photo (step E), for photos with a solved camera.

The model is seen through the photo's own camera (master: checkpoints/cp2 +
his head pose there; others: checkpoints/cp4/cams/<view>.json with the head
turn solved there), pixel for pixel: its surface direction (same frame as
the photo's map: x right, y up, z toward the camera), its depth, and his fur
lit by the light found in that photo (checkpoints/cp5/maps/<view>/light.json).

Then, where both the photo's fur and the model are seen:
- the angle between his surface direction and the model's (degrees), as a
  map and per part (forehead and brow, eyes and sockets, muzzle, cheeks,
  chest, body);
- the shading difference: his fur brightness minus the model's under his
  light (red: he is brighter there than the model would be);
- the photo's relative depth against the model's depth (ordering).

The surface is drawn by splatting dense points over every triangle (nearest
wins per pixel), so no renderer is needed.

writes checkpoints/cp5/compare/<view>/ model_normals.npy, model_depth.npy,
part.npy, compare.jpg (photo | his normals | model normals | angle | shading
difference) and numbers.json.

usage: python tools/maps_model.py MODEL_DIR VIEW [VIEW ...]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PARTS = ["forehead and brow", "eyes and sockets", "muzzle", "cheeks", "chest", "body"]


def camera(view):
    """Projection function (P -> uv, depth) and the world-to-camera rotation;
    his head posed as in that photo."""
    p = ROOT / f"checkpoints/cp4/cams/{view}.json"
    if p.exists():
        c = json.loads(p.read_text())
        Rc = R.from_rotvec(c["rotvec_world_to_cam"]).as_matrix()
        pos, f, pp = np.asarray(c["camera_position_m"]), c["focal_px"], np.asarray(c["principal_px"])
        pose = c.get("head_pose")

        def proj(P):
            X = (P - pos) @ Rc.T
            return f * X[:, :2] / X[:, 2:3] + pp, X[:, 2]
        return proj, Rc, pose
    cam, _ = C.view_data(view)
    Rc = R.from_rotvec(cam["rot"]).as_matrix()

    def proj(P):
        X = (P - np.asarray(cam["pos"])) @ Rc.T
        return C.project(P, cam), X[:, 2]
    a = cam.get("align")
    if a:  # the per-photo roll turns the image: turn the normals with it
        th = np.radians(a["roll_deg"])
        Rroll = np.array([[np.cos(th), -np.sin(th), 0], [np.sin(th), np.cos(th), 0], [0, 0, 1]])
        Rc = Rroll @ Rc
    return proj, Rc, cam["pose"]


def posed(V, pose):
    if not pose:
        return V
    hw = head_weight(V)
    Rm = R.from_rotvec(pose["rotvec"]).as_matrix()
    Pp = (V - NECK_PIVOT) @ Rm.T + NECK_PIVOT + np.asarray(pose.get("shift_m", [0, 0, 0]))
    return V + hw[:, None] * (Pp - V)


def vertex_normals(V, F):
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def part_labels(V):
    """His parts, by where they are on him at rest."""
    L3 = json.loads((ROOT / "checkpoints/cp4/landmarks3d.json").read_text())
    E = json.loads((ROOT / "checkpoints/cp4/eyes.json").read_text())
    fr = json.loads((ROOT / "checkpoints/cp4/frame.json").read_text())
    x = V[:, 0] - fr["x_m"]
    eyes = [np.asarray(E[s]["centre"]) for s in "RL"]
    ez = eyes[0][2]
    nose = np.asarray(L3["nose_tip"])
    hw = head_weight(V)
    lab = np.full(len(V), 5)  # body
    head = hw > 0.6
    lab[(V[:, 1] > 0.02) & (V[:, 2] < nose[2] - 0.012) & (V[:, 2] > 0.0) & (np.abs(x) < 0.05)] = 4  # chest
    lab[head & (V[:, 2] < ez) & (np.abs(x) > 0.016)] = 3  # cheeks
    lab[head & (V[:, 2] >= ez - 0.004) & (V[:, 1] > 0.0)] = 0  # forehead and brow
    lab[np.linalg.norm(V - nose, axis=1) < 0.024] = 2  # muzzle
    for e in eyes:
        lab[np.linalg.norm(V - e, axis=1) < 0.017] = 1  # eyes and sockets
    return lab


def splat(V, F, vals, proj, H, W, per_px=1.5):
    """Dense points over every triangle, projected; nearest wins per pixel.
    Returns the pixel maps of `vals` (list of per-vertex arrays) and depth."""
    uv, z = proj(V)
    A = np.abs(np.cross(np.c_[uv[F[:, 1]] - uv[F[:, 0]], np.zeros(len(F))],
                        np.c_[uv[F[:, 2]] - uv[F[:, 0]], np.zeros(len(F))])[:, 2]) / 2
    n = np.clip(np.ceil(np.sqrt(A * per_px * 2)), 1, 40).astype(int)  # samples per edge
    outs = [np.full((H, W) + np.shape(v)[1:], np.nan) for v in vals]
    zbuf = np.full((H, W), np.inf)
    for k in np.unique(n):
        idx = np.nonzero(n == k)[0]
        a, b = np.meshgrid(np.arange(k + 1), np.arange(k + 1), indexing="ij")
        ok = a + b <= k
        w1, w2 = a[ok] / k, b[ok] / k
        w0 = 1 - w1 - w2
        Fi = F[idx]
        for s in range(0, len(idx), 4000):
            Fs = Fi[s:s + 4000]
            P_uv = (w0[None, :, None] * uv[Fs[:, 0]][:, None] + w1[None, :, None] * uv[Fs[:, 1]][:, None]
                    + w2[None, :, None] * uv[Fs[:, 2]][:, None]).reshape(-1, 2)
            P_z = (w0[None] * z[Fs[:, 0]][:, None] + w1[None] * z[Fs[:, 1]][:, None]
                   + w2[None] * z[Fs[:, 2]][:, None]).ravel()
            px = np.round(P_uv).astype(int)
            good = (px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < H)
            px, P_z = px[good], P_z[good]
            nearest = np.argmax(np.stack([w0, w1, w2]), 0)  # vertex nearest each sample
            vid = np.take_along_axis(Fs, np.broadcast_to(nearest, (len(Fs), len(nearest))), 1).ravel()[good]
            bw = np.stack([np.broadcast_to(w, (len(Fs), len(w))).ravel()[good] for w in (w0, w1, w2)], 1)
            vids3 = np.repeat(Fs, len(w0), 0)[good]
            order = np.argsort(-P_z)  # far first, near last: near wins
            lin = px[order, 1] * W + px[order, 0]
            zf = zbuf.ravel()
            closer = P_z[order] < zf[lin]
            lin, ordc = lin[closer], order[closer]
            if not len(ordc):
                continue
            zf[lin] = P_z[ordc]
            for o, v in zip(outs, vals):
                of = o.reshape(H * W, *np.shape(v)[1:])
                if np.asarray(v).dtype.kind in "iu":
                    of[lin] = np.asarray(v)[vid[ordc]]
                else:
                    of[lin] = (bw[ordc, :, None] * np.asarray(v)[vids3[ordc]].reshape(len(ordc), 3, -1)).sum(1).squeeze()
    return outs, zbuf


def main():
    md = Path(sys.argv[1])
    V0, F0 = load_obj(md / "head.obj")
    parts = [(V0, F0)]
    for e in sorted(md.glob("eye_*.obj")):
        parts.append(load_obj(e))
    for view in sys.argv[2:]:
        mp = ROOT / f"checkpoints/cp5/maps/{view}"
        light = json.loads((mp / "light.json").read_text())
        img = Image.open(ROOT / light["photo"]).convert("RGB")
        rgb = np.asarray(img).astype(float)
        H, W = rgb.shape[:2]
        proj, Rc, pose = camera(view)
        Ns, Ds, Ls = [], [], []
        for i, (V, F) in enumerate(parts):
            Vp = posed(V, pose)
            N = vertex_normals(Vp, F) @ Rc.T  # camera frame, y down, z forward
            N = N * np.array([1, -1, -1])  # -> x right, y up, z toward the camera
            lab = part_labels(V) if i == 0 else np.full(len(V), 1)
            (nm, lb), z = splat(Vp, F, [N, lab], proj, H, W)
            Ns.append(nm)
            Ls.append(lb)
            Ds.append(z)
        z = np.min(np.stack(Ds), 0)
        which = np.argmin(np.stack(Ds), 0)
        Nm = np.take_along_axis(np.stack(Ns), which[None, ..., None], 0)[0]
        lab = np.take_along_axis(np.stack(Ls), which[None], 0)[0]
        seen = np.isfinite(z)
        Nm /= np.maximum(np.linalg.norm(np.nan_to_num(Nm), axis=-1, keepdims=True), 1e-9)
        Np = np.load(mp / "normals.npy").astype(float)
        fur = np.asarray(Image.open(mp / "fur.png")) > 0
        outline = np.asarray(Image.open(ROOT / f"checkpoints/cp4/outlines/{view}.png").convert("L")) > 127
        both = seen & fur & nd.binary_erosion(seen, iterations=4)
        ang = np.full((H, W), np.nan)
        ang[both] = np.degrees(np.arccos(np.clip((np.nan_to_num(Nm[both]) * Np[both]).sum(-1), -1, 1)))
        Ld = np.asarray(light["light_dir"])
        gray = rgb.mean(-1) / 255
        shade_model = light["ambient"] + light["directional"] * (np.nan_to_num(Nm) @ Ld)
        shade_photo = light["ambient"] + light["directional"] * (Np @ Ld)
        sdiff = np.where(both, gray - shade_model, np.nan)
        # depth ordering: rank agreement of nearness inside both
        Dp = np.load(mp / "depth.npy")
        ii = np.nonzero(both.ravel())[0][:: max(1, both.sum() // 20000)]
        from scipy.stats import spearmanr
        rho = spearmanr(Dp.ravel()[ii], -z.ravel()[ii]).statistic  # photo depth is nearness
        nums = {"view": view, "angle_deg_median": round(float(np.nanmedian(ang)), 1),
                "depth_order_agreement": round(float(rho), 2),
                "outline_overlap": round(float((seen & outline).sum() / (seen | outline).sum()), 3),
                "parts": {}}
        for k, name in enumerate(PARTS):
            m = both & (lab == k)
            if m.sum() > 200:
                a = ang[m]
                # which way the model faces too much: mean of (model - photo) normals, in degrees
                d = np.degrees(np.nanmean(np.nan_to_num(Nm[m]) - Np[m], 0))
                nums["parts"][name] = {"pixels": int(m.sum()), "angle_median_deg": round(float(np.median(a)), 1),
                                       "model_minus_his_xyz_deg": np.round(d, 1).tolist(),
                                       "shading_his_minus_model": round(float(np.nanmean(sdiff[m])), 3)}
        out = ROOT / f"checkpoints/cp5/compare/{view}"
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "model_normals.npy", np.nan_to_num(Nm).astype(np.float16))
        np.save(out / "model_depth.npy", z.astype(np.float32))
        np.save(out / "part.npy", np.nan_to_num(lab, nan=-1).astype(np.int8))
        (out / "numbers.json").write_text(json.dumps(nums, indent=1))
        # sheet
        def nimg(N, m):
            im = ((np.nan_to_num(N) * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
            im[~m] = 255
            return Image.fromarray(im)
        a = np.nan_to_num(ang / 40).clip(0, 1)
        av = np.stack([255 * a, 255 * (1 - a), np.full_like(a, 60)], -1).astype(np.uint8)
        av[~both] = 255
        s = np.nan_to_num(sdiff / 0.15).clip(-1, 1)
        sv = np.stack([np.where(s < 0, 255 * (1 + s), 255), 255 * (1 - np.abs(s)), np.where(s > 0, 255 * (1 - s), 255)], -1).astype(np.uint8)
        sv[~both] = 255
        tiles = [img.copy(), nimg(Np, outline), nimg(Nm, seen), Image.fromarray(av), Image.fromarray(sv)]
        names = ["his photo", "his surface (photo)", "model surface (same camera)", "angle between (green 0, red 40+ deg)", "shading: red he is brighter"]
        T = 420
        sheet = Image.new("RGB", (5 * (T + 6), T + 22), "white")
        d = ImageDraw.Draw(sheet)
        for i, (t, nme) in enumerate(zip(tiles, names)):
            t.thumbnail((T, T))
            sheet.paste(t, (i * (T + 6), 22))
            d.text((i * (T + 6) + 4, 4), nme, fill=(0, 0, 0))
        sheet.save(out / "compare.jpg", quality=85)
        print(json.dumps(nums), flush=True)


if __name__ == "__main__":
    main()
