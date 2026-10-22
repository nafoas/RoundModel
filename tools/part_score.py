"""Score each traced part of his eyes and upper face, in every photo it was
traced in: render the sculpt from that photo's camera with its head posed as
he holds it there (head_poses.json; the master is never posed) with flat black
eyes, and compare what shows of each eye with the hand traces in
checkpoints/cp3/part_traces.json.

usage: part_score.py SCULPT_DIR [OUT_DIR]   (OUT_DIR gets one overlay per photo)
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
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import NECK_PIVOT, head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def cameras():
    cams = {}
    m = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())["views"]["master_front_standing"]
    W, H = m["size"]
    cams["master_front_standing"] = dict(image=m["image"], rotvec=m["rotvec_world_to_cam"], pos=m["camera_position_m"],
                                         f=m["focal_px"], c=(W / 2, H / 2))
    for vn, v in json.loads((ROOT / "checkpoints/cp3/side_cameras.json").read_text())["views"].items():
        cams[vn] = dict(image=v["image"], rotvec=v["rotvec_world_to_cam"], pos=v["camera_position_m"],
                        f=v["focal_px"], c=v["principal_px"])
    return cams


def posed_objects(d, view, poses):
    """Mesh data (head, eyes) posed for this view, as numpy arrays."""
    out = {}
    files = {"head": d / "head.obj", **{p.stem: p for p in d.glob("eye_*.obj")}}
    for k, p in files.items():
        V, F = load_obj(p)
        if view in poses:
            Rm, t = R.from_rotvec(poses[view]["rotvec"]).as_matrix(), np.array(poses[view]["shift_m"])
            Vp = (V - NECK_PIVOT) @ Rm.T + NECK_PIVOT + t
            w = head_weight(V)[:, None] if k == "head" else 1.0
            V = V + w * (Vp - V)
        out[k] = (V, F)
    return out


def set_mesh(name, V, F):
    me = bpy.data.objects[name].data
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    me.update()


def main(d, outdir=None):
    d = Path(d)
    traces = json.loads((ROOT / "checkpoints/cp3/part_traces.json").read_text())
    poses = json.loads((ROOT / "checkpoints/cp3/head_poses.json").read_text())
    cams = cameras()
    sc = RC.reset()
    sc.cycles.samples = 2
    sc.cycles.use_denoising = False
    RC.load_mesh(d / "head.obj", name="head")
    for e in sorted(d.glob("eye_*.obj")):
        RC.load_mesh(e, colour=(0, 0, 0), roughness=1.0, name=e.stem)
    names = {o.name.split(".")[0]: o.name for o in bpy.data.objects if o.type == "MESH"}
    RC.lights(sc)
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    results = {}
    for view, parts in traces.items():
        if not isinstance(parts, dict):
            continue
        c = cams[view]
        W, H = Image.open(ROOT / c["image"]).size
        objs = posed_objects(d, view, poses if view != "master_front_standing" else {})
        for k, (V, F) in objs.items():
            set_mesh(names.get(k, k), V, F)
        RC.set_camera(sc, cam, (W, H), c["rotvec"], c["pos"], c["f"])
        cd.shift_x = (c["c"][0] - W / 2) / max(W, H)
        cd.shift_y = (c["c"][1] - H / 2) / max(W, H)
        cd.clip_start = 0.001
        tmp = d / f"_ps_{view}.png"
        sc.render.filepath = str(tmp)
        bpy.ops.render.render(write_still=True)
        img = np.asarray(Image.open(tmp).convert("RGBA")).astype(np.float32)
        dark = (img[..., :3].mean(2) < 80) & (img[..., 3] > 200)
        photo = np.asarray(Image.open(ROOT / c["image"]).convert("RGB")).copy()
        bg = (img[..., :3] * (img[..., 3:4] / 255) + 228 * (1 - img[..., 3:4] / 255)).astype(np.uint8)
        for part, poly in parts.items():
            kind, side = part.split("_")
            if kind not in ("eye",):
                continue
            poly = np.array(poly, np.int32)
            pm = np.zeros((H, W), np.uint8)
            cv2.fillPoly(pm, [poly], 1)
            x, y, w, h = cv2.boundingRect(poly)
            m = max(w, h)
            zone = np.zeros((H, W), bool)
            zone[max(0, y - m):y + h + m, max(0, x - m):x + w + m] = True
            n, lab, st, _ = cv2.connectedComponentsWithStats((dark & zone).astype(np.uint8))
            sm = np.zeros((H, W), np.uint8)
            if n > 1:
                # the component overlapping the trace most (else the largest)
                ov = [((lab == i) & (pm > 0)).sum() for i in range(1, n)]
                i = 1 + (int(np.argmax(ov)) if max(ov) > 0 else int(np.argmax(st[1:, 4])))
                sm = (lab == i).astype(np.uint8)
            iou = (pm & sm).sum() / max(1, (pm | sm).sum())
            # centre offset and size ratio, in px
            def stats(mask):
                ys, xs = np.nonzero(mask)
                return (np.array([xs.mean(), ys.mean()]), np.array([np.ptp(xs) + 1, np.ptp(ys) + 1])) if len(xs) else (None, None)
            cp, sp = stats(pm)
            cs, ss = stats(sm)
            results[f"{view}:{part}"] = dict(iou=float(iou), photo_size=sp.tolist(),
                                            sculpt_size=None if ss is None else ss.tolist(),
                                            offset=None if cs is None else (cs - cp).round(1).tolist())
            for im in (photo, bg):
                for mm, col in ((pm, (235, 0, 60)), (sm, (0, 110, 255))):
                    cs_, _ = cv2.findContours(mm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    cv2.drawContours(im, cs_, -1, col, 2)
        if outdir:
            allp = np.vstack([np.array(p) for p in parts.values()])
            x0, y0 = allp.min(0) - 120
            x1, y1 = allp.max(0) + 120
            x0, y0 = max(0, x0), max(0, y0)
            a = Image.fromarray(photo[y0:y1, x0:x1])
            b = Image.fromarray(bg[y0:y1, x0:x1])
            o = Image.new("RGB", (a.width * 2 + 10, a.height), (255, 255, 255))
            o.paste(a, (0, 0))
            o.paste(b, (a.width + 10, 0))
            Path(outdir).mkdir(parents=True, exist_ok=True)
            o.save(Path(outdir) / f"{view}.png")
    for k, v in results.items():
        print(f"{k:42s} overlap {v['iou'] * 100:5.1f}%  size photo {v['photo_size']} sculpt {v['sculpt_size']}  "
              f"centre off {v['offset']} px")
    (d / "part_scores.json").write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:3])
