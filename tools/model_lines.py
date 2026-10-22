"""Step 2: the same lines as his traces, drawn on the model, from each
photo's camera with his head posed as found (head_poses_parts/; the master has
no pose). Model lines: eye = edge of what shows of the eyeball (fur rendered
flat white, eyes black); socket = the model's lid edge (no eye-ring colour
yet, so the same line as the eye); ridge = the model's crease behind/above
the eye (points where the surface bends inward most sharply, near his ridge
line); forehead / muzzle = the model's outline along the stretch his line
covers. Writes checkpoints/cp3/model_lines.json and one overlay per photo
(his lines solid, the model's lines in the same colour, thin, on the render).

usage: model_lines.py SCULPT_DIR OUT_DIR
"""
import json
import sys
from pathlib import Path

import bpy
import cv2
import numpy as np
from PIL import Image
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, str(Path(__file__).parent))
import render_clay as RC  # noqa: E402
from part_score import cameras  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight, neighbours, avg_op, normals  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
COL = {"eye": (255, 0, 60), "socket": (0, 230, 90), "ridge": (0, 160, 255), "forehead": (255, 200, 0),
       "muzzle": (255, 0, 255)}


def posed(V, view, poses, head=True):
    if view not in poses:
        return V
    p = poses[view]
    Rm, t, pv = R.from_rotvec(p["rotvec"]).as_matrix(), np.array(p["shift_m"]), np.array(p.get("pivot", NECK_PIVOT))
    Vp = (V - pv) @ Rm.T + pv + t
    return V + head_weight(V)[:, None] * (Vp - V) if head else Vp


def main(d, outdir):
    d, outdir = Path(d), Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    T = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
    poses = {f.stem: json.loads(f.read_text()) for f in (ROOT / "checkpoints/cp3/head_poses_parts").glob("*.json")}
    cams = cameras()
    V, F = load_obj(d / "head.obj")
    eyesV = {p.stem: load_obj(p) for p in sorted(d.glob("eye_*.obj"))}
    # concave crease strength per vertex (for the ridge)
    rows, cols, deg = neighbours(F, len(V))
    lap = avg_op(rows, cols, deg) @ V - V
    crease = np.einsum("ij,ij->i", lap, normals(V, F))  # >0: point lies below its neighbours (concave)

    sc = RC.reset()
    sc.cycles.samples = 2
    sc.cycles.use_denoising = False
    hob = RC.load_mesh(d / "head.obj", name="head")
    mt = hob.data.materials[0].node_tree
    em = mt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    mt.links.new(em.outputs["Emission"], mt.nodes["Material Output"].inputs["Surface"])
    eobs = {k: RC.load_mesh(d / f"{k}.obj", colour=(0, 0, 0), roughness=1.0, name=k) for k in eyesV}
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    result = {}
    for view, parts in T.items():
        if not isinstance(parts, dict) or view not in cams:
            continue
        c = cams[view]
        W, H = Image.open(ROOT / c["image"]).size
        Vp = posed(V, view, poses)
        hob.data.vertices.foreach_set("co", Vp.astype(np.float32).ravel())
        hob.data.update()
        for k, (Ve, Fe) in eyesV.items():
            eobs[k].data.vertices.foreach_set("co", posed(Ve, view, poses, head=False).astype(np.float32).ravel())
            eobs[k].data.update()
        RC.set_camera(sc, cam, (W, H), c["rotvec"], c["pos"], c["f"])
        cd.shift_x = (c["c"][0] - W / 2) / max(W, H)
        cd.shift_y = (c["c"][1] - H / 2) / max(W, H)
        cd.clip_start = 0.001
        tmp = outdir / f"_flat_{view}.png"
        sc.render.filepath = str(tmp)
        bpy.ops.render.render(write_still=True)
        img = np.asarray(Image.open(tmp).convert("RGBA")).astype(np.float32)
        dark = ((img[..., :3].mean(2) < 80) & (img[..., 3] > 200)).astype(np.uint8)
        sil = (img[..., 3] > 127).astype(np.uint8)
        Rc = R.from_rotvec(c["rotvec"]).as_matrix()
        Xc = (Vp - np.asarray(c["pos"])) @ Rc.T
        uv = c["f"] * Xc[:, :2] / Xc[:, 2:3] + np.asarray(c["c"])
        lines = {}
        for part, poly in parts.items():
            kind = part.split("_")[0]
            P = np.array(poly)
            if kind in ("eye", "socket"):
                # the model's eye region nearest his traced eye
                x, y, w, h = cv2.boundingRect(P.astype(np.int32))
                m = max(w, h)
                zone = np.zeros((H, W), np.uint8)
                zone[max(0, y - m):y + h + m, max(0, x - m):x + w + m] = 1
                n, lab, st, _ = cv2.connectedComponentsWithStats(dark & zone)
                if n > 1:
                    tm = np.zeros((H, W), np.uint8)
                    cv2.fillPoly(tm, [P.astype(np.int32)], 1)
                    ov = [((lab == i) & (tm > 0)).sum() for i in range(1, n)]
                    i = 1 + (int(np.argmax(ov)) if max(ov) > 0 else int(np.argmax(st[1:, 4])))
                    cs, _ = cv2.findContours((lab == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    lines[part] = max(cs, key=cv2.contourArea)[:, 0].tolist()
            elif kind in ("forehead", "muzzle"):
                # the model's outline points nearest each of his line points
                cs, _ = cv2.findContours(sil, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                C = np.vstack([cc_[:, 0] for cc_ in cs])
                near = [C[np.argmin(np.linalg.norm(C - p, axis=1))] for p in P]
                i0 = [int(np.argmin(np.linalg.norm(C - p, axis=1))) for p in (P[0], P[-1])]
                a, b = sorted(i0)
                seg = C[a:b + 1] if (b - a) < len(C) / 2 else np.vstack([C[b:], C[:a + 1]])
                lines[part] = seg.tolist()
            elif kind == "ridge":
                # crease points on the visible surface near his ridge line
                vis_side = np.einsum("ij,ij->i", normals(Vp, F), np.asarray(c["pos"]) - Vp) > 0
                dist = np.min(np.linalg.norm(uv[:, None, :] - P[None, :, :], axis=2), axis=1)
                cand = vis_side & (dist < 40) & (crease > np.percentile(crease, 97))
                pts = uv[cand]
                if len(pts) > 3:
                    order = np.argsort(pts @ (P[-1] - P[0]))
                    lines[part] = pts[order].tolist()
        result[view] = lines
        # overlay: photo with his lines | flat model render with the model's lines
        ph = np.asarray(Image.open(ROOT / c["image"]).convert("RGB")).copy()
        bg = (img[..., :3] * (img[..., 3:4] / 255) + 200 * (1 - img[..., 3:4] / 255)).astype(np.uint8).copy()
        for part, poly in parts.items():
            kind = part.split("_")[0]
            closed = kind in ("eye", "socket")
            cv2.polylines(ph, [np.array(poly, np.int32)], closed, COL[kind], 3)
            cv2.polylines(bg, [np.array(poly, np.int32)], closed, COL[kind], 1)
            if part in lines:
                L = np.array(lines[part], np.int32)
                if kind == "ridge":
                    for q in L:
                        cv2.circle(bg, tuple(q), 2, COL[kind], -1)
                else:
                    cv2.polylines(bg, [L], closed, COL[kind], 3)
        allp = np.vstack([np.array(p) for p in parts.values()])
        x0, y0 = np.maximum(allp.min(0) - 80, 0).astype(int)
        x1, y1 = (allp.max(0) + 80).astype(int)
        a_, b_ = Image.fromarray(ph[y0:y1, x0:x1]), Image.fromarray(bg[y0:y1, x0:x1])
        s_ = 480 / a_.height
        a_, b_ = a_.resize((int(a_.width * s_), 480)), b_.resize((int(b_.width * s_), 480))
        o = Image.new("RGB", (a_.width * 2 + 10, 480), (255, 255, 255))
        o.paste(a_, (0, 0))
        o.paste(b_, (a_.width + 10, 0))
        o.save(outdir / f"{view}.png")
    (ROOT / "checkpoints/cp3/model_lines.json").write_text(json.dumps(result))


if __name__ == "__main__":
    main(*sys.argv[1:3])
