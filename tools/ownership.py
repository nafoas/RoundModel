"""Ownership map (tasks/03, "Never let angles overlap", step 1): every point of
his surface owned by exactly one photo, the one that sees it most face-on.

Candidates: every photo with a solved camera and a normal map, except the
master (its estimated normals are not his shape; it stays the reference for
how he looks from the front). A photo can own a point only if the point is
visible in it (not hidden), inside its outline of him away from the edge,
and, for loafed photos, on his head. Score: cos of the angle between the
surface and the line of sight. Owner = best score; then the labels are
cleaned (each point takes the most common owner among its neighbours, a few
rounds) so patches are whole, not speckled.

writes OUT_DIR/owner.npy (index into OWNERS, -1 none), owners.json, and
checkpoints/cp6/ownership.jpg (the surface coloured by owner, through the
master, both profiles, a front 3/4, top-down and back 3/4, with a legend).

usage: python tools/ownership.py MESH.obj OUT_DIR
"""
import json
import sys
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from PIL import Image, ImageDraw
from scipy import ndimage as nd

sys.path.insert(0, str(Path(__file__).parent))
import carve as C  # noqa: E402
from fill_from_photos import POSES, STANDING, unpose, view_mask  # noqa: E402
from maps_model import camera, posed, splat, vertex_normals  # noqa: E402
from refine_side_cameras import load_obj  # noqa: E402
from sculpt import head_weight  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MASTER = "master_front_standing"
OWNERS = ["s01", "s18", "sheet_02_front_3q", "sheet_08_front_3q_left", "sheet_03_right_profile",
          "sheet_07_left_profile", "sheet_09_top_down", "sheet_04_back_3q_right", "e_back_3q_left_high",
          "c02", "c21", "c08", "c10", "c09", "c26", "c03", "c12", "c14", "c19", "c20", "c25", "c06",
          "e_front_blink", "e_front_head_lifted", "e_front_head_lowered", "e_front_peet_lift_right",
          "e_head_turn_left_mouth_closed", "e_front_3q_left_toddle"]
SHOW = [("master", MASTER), ("right profile", "sheet_03_right_profile"), ("left profile", "sheet_07_left_profile"),
        ("front 3/4", "sheet_02_front_3q"), ("top-down", "sheet_09_top_down"), ("back 3/4", "sheet_04_back_3q_right")]


def colours(n):
    import colorsys
    return [tuple(int(255 * c) for c in colorsys.hsv_to_rgb((i * 0.618) % 1, 0.65, 0.95)) for i in range(n)]


def main():
    mesh, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    C.ALIGN = json.loads((ROOT / "checkpoints/cp4/view_align.json").read_text())
    V, F = load_obj(mesh)
    _, _, mpose = camera(MASTER)
    Vold = unpose(V, mpose)
    hw = head_weight(Vold)
    score = np.full((len(OWNERS), len(V)), -1.0)
    used = []
    for k, name in enumerate(OWNERS):
        if not (ROOT / f"checkpoints/cp5/maps/{name}/normals.npy").exists():
            continue
        try:
            proj, _, pose = camera(name)
        except Exception:  # noqa: BLE001
            continue
        if (POSES / f"{name}.json").exists():
            pose = json.loads((POSES / f"{name}.json").read_text())
        mask, head_only = view_mask(name)
        mask = nd.binary_erosion(mask, iterations=12)
        H, W = mask.shape
        Vp = posed(Vold, pose)
        uv, z = proj(Vp)
        (_,), zb = splat(Vp, F, [np.zeros(len(V), np.int8)], proj, H, W)
        px = np.round(uv).astype(int)
        ok = (px[:, 0] >= 0) & (px[:, 0] < W) & (px[:, 1] >= 0) & (px[:, 1] < H) & (z > 0)
        pi = np.where(ok, px[:, 1], 0), np.where(ok, px[:, 0], 0)
        ok &= (np.abs(z - zb[pi]) < 0.002) & mask[pi]
        if head_only or name not in STANDING:
            ok &= hw > 0.6
        N = vertex_normals(Vp, F)
        sight = proj.pos - Vp
        sight /= np.linalg.norm(sight, axis=1, keepdims=True)
        c = np.einsum("ij,ij->i", N, sight)
        score[k] = np.where(ok & (c > 0.3), c, -1.0)
        used.append(name)
        print(f"{name}: can own {(score[k] > 0).sum()} points", flush=True)
    owner = np.where(score.max(0) > 0, score.argmax(0), -1)
    # whole patches: majority of neighbours, a few rounds
    E = np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    A = sp.csr_matrix((np.ones(2 * len(E)), (np.r_[E[:, 0], E[:, 1]], np.r_[E[:, 1], E[:, 0]])), shape=(len(V), len(V)))
    A = (A + sp.eye(len(V))).tocsr()
    for _ in range(8):
        votes = np.zeros((len(OWNERS), len(V)))
        for k in range(len(OWNERS)):
            m = (owner == k).astype(float)
            if m.any():
                votes[k] = A @ m
        votes[score <= 0] = -1  # never given to a photo that can't see it
        best = votes.argmax(0)
        owner = np.where(votes.max(0) > 0, best, owner)
    np.save(out / "owner.npy", owner)
    counts = {OWNERS[k]: int((owner == k).sum()) for k in range(len(OWNERS)) if (owner == k).any()}
    (out / "owners.json").write_text(json.dumps({"owners": OWNERS, "points": counts, "none": int((owner < 0).sum())}, indent=1))
    print("owned points:", counts, "none:", int((owner < 0).sum()), flush=True)
    # picture
    col = np.array(colours(len(OWNERS)) + [(60, 60, 60)], float) / 255
    vc = col[np.where(owner >= 0, owner, len(OWNERS))]
    tiles = []
    for title, view in SHOW:
        proj, _, pose = camera(view)
        if view != MASTER and (POSES / f"{view}.json").exists():
            pose = json.loads((POSES / f"{view}.json").read_text())
        photo = json.loads((ROOT / f"checkpoints/cp5/maps/{view}/light.json").read_text())["photo"]
        Wi, Hi = Image.open(ROOT / photo).size
        Vp = posed(Vold, pose)
        N = vertex_normals(Vp, F)
        sight = proj.pos - Vp
        sight /= np.linalg.norm(sight, axis=1, keepdims=True)
        shade = (0.45 + 0.55 * np.clip(np.einsum("ij,ij->i", N, sight), 0, 1))[:, None]
        (img,), z = splat(Vp, F, [vc * shade], proj, Hi, Wi)
        im = (np.nan_to_num(img, nan=1.0).clip(0, 1) * 255).astype(np.uint8)
        t = Image.fromarray(im)
        t.thumbnail((420, 420))
        tiles.append((title, t))
    T = 420
    sheet = Image.new("RGB", (3 * (T + 6), 2 * (T + 26) + 30 + 22 * ((len(counts) + 2) // 3)), "white")
    d = ImageDraw.Draw(sheet)
    for i, (title, t) in enumerate(tiles):
        x, y = (i % 3) * (T + 6), (i // 3) * (T + 26)
        d.text((x + 4, y + 2), title, fill=(0, 0, 0), font_size=18)
        sheet.paste(t, (x, y + 24))
    y0 = 2 * (T + 26) + 10
    for j, (name, n) in enumerate(sorted(counts.items(), key=lambda kv: -kv[1])):
        k = OWNERS.index(name)
        x, y = (j % 3) * (T + 6) + 6, y0 + (j // 3) * 22
        d.rectangle([x, y + 3, x + 16, y + 17], fill=tuple(int(255 * c) for c in col[k]))
        d.text((x + 22, y), f"{name} ({n})", fill=(0, 0, 0), font_size=16)
    sheet.save(ROOT / "checkpoints/cp6/ownership.jpg", quality=88)


if __name__ == "__main__":
    main()
