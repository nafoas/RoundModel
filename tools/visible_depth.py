"""What the anchor photo sees of him, and how far away it is: every ray cut at a measured distance.

Owner's plan (2026-11-16): "Have it invent absolutely nothing." Every area of him is governed by exactly one
photo (later photos will cover other areas, with no overlap). From THIS photo: the depth of ONLY what is
visible, nothing else; shown like the rays in the room, "each ray ... brought to the exact distance calculated",
so the rays show his surface. Don't model him.

How:
1. Measure (slow; only with --measure): two independent depth models, each given the photo exactly as it is,
   each giving one distance per pixel and its own estimate of the camera's lens: Depth Pro (Apple,
   apple/DepthPro-hf) and MoGe-2 (Microsoft, Ruicheng/moge-2-vitl-normal). Kept for the pixels of him (inside
   his outline, data/strands/body_outline.json). No smoothing, no filling, no merging the two models.
2. Place in the room (owner, 2026-11-16, "Either way I trust them"): each model with ITS OWN camera, never ours:
   its own lens and its own rays (it assumes the picture's centre is straight ahead), straight on (not turned,
   not rolled). Every ray of him from that camera, cut at that model's distance. One single number per model
   changes its units so he is his approved width (15.5 cm, owner-approved): the shape is untouched. Which way
   is up: the model cannot know, and the photo was cropped, so its centre is not where the camera aimed
   (lesson 26); the whole thing is turned (rigidly, shape untouched) so the camera sits where the owner
   remembers it: "basically exactly at his eye level. Maybe just a tiny bit lower" (0.5 cm). The surface he
   sits on goes through the bottoms of his peets, the origin under their middle.
   Checks the model was not told (reported only, never used to change anything): how far the camera was from
   his nose (owner: about six inches), the top of his head (owner-approved 12.7 cm), how level his peets come
   out, which way the cropped picture's centre points.

Usage: python tools/visible_depth.py [--measure [depthpro|moge2]]
       -> data/scene/visible_depth_<model>.png (16-bit distances) + .json (camera, scale, checks)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from prince.space import Camera  # noqa: E402

OUT_IMG = ROOT / "docs/images/space"
MODELS = {"depthpro": "apple/DepthPro-hf", "moge2": "Ruicheng/moge-2-vitl-normal"}
NAMES = {"depthpro": "Depth Pro (Apple)", "moge2": "MoGe-2 (Microsoft)"}
WIDTH_CM = 15.5          # his width, OWNER-approved 2026-11-16 (sets his size; the model cannot tell size here)
EYES_ABOVE_CAMERA_CM = 0.5  # OWNER: "basically exactly at his eye level. Maybe just a tiny bit lower" (sets which way is up)
EDGE_INSET_PX = 4        # his outline's outermost pixels blend into the removed background: width read 4 px inside
NEAR_PX = 3              # a landmark's 3D point: the median of the pixels of him within 3 px (6 for a peet bottom)


def load(p):
    return json.loads((ROOT / p).read_text())


def him_mask(H, W):
    """Pixels of him: inside his body outline (his ears and peets included; whiskers and wisps outside it are not)."""
    from matplotlib.path import Path as MP
    outline = np.array(load("data/strands/body_outline.json")["sampled_curve"])
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    return MP(outline).contains_points(np.c_[xx.ravel(), yy.ravel()]).reshape(H, W)


def run_depthpro(img):
    """Depth Pro: distance (m) from its camera to every pixel, and its own lens estimate."""
    import torch
    from transformers import AutoImageProcessor, DepthProForDepthEstimation
    proc = AutoImageProcessor.from_pretrained(MODELS["depthpro"])
    model = DepthProForDepthEstimation.from_pretrained(MODELS["depthpro"]).eval()
    inputs = proc(images=img, return_tensors="pt")
    with torch.no_grad():
        out = model(**inputs)
    post = proc.post_process_depth_estimation(out, target_sizes=[(img.height, img.width)])[0]
    z = post["predicted_depth"].float().numpy()                   # metres along its camera's axis
    f = float(post["focal_length"])                               # pixels, for this picture's size
    H, W = z.shape
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    X = (xx - W / 2) / f * z; Y = (yy - H / 2) / f * z
    dist = np.sqrt(X * X + Y * Y + z * z)                          # straight-line distance to each pixel's spot
    return dict(distance_m=dist, focal_px=f, fov_deg=float(post.get("field_of_view", np.nan)))


def run_moge2(img):
    """MoGe-2: a 3D point (m) for every pixel in its own camera, and its own lens estimate."""
    import torch
    from moge.model.v2 import MoGeModel
    model = MoGeModel.from_pretrained(MODELS["moge2"]).eval()
    t = torch.tensor(np.asarray(img, dtype=np.float32) / 255.0).permute(2, 0, 1)
    with torch.no_grad():
        out = model.infer(t, use_fp16=False)                     # full precision (half precision needs a GPU)
    P = out["points"].numpy()                                       # (H, W, 3) metres, its camera
    K = out["intrinsics"].numpy()                                   # normalised: fx in picture widths
    dist = np.linalg.norm(P, axis=-1)
    return dict(distance_m=dist, focal_px=float(K[0, 0] * img.width), valid=out["mask"].numpy().astype(bool))


def save_distance(name, dist_cm, mask):
    """Distance map as a 16-bit picture (units of 0.01 cm = 0.1 mm; 0 = not him)."""
    a = np.where(mask & np.isfinite(dist_cm), np.clip(np.round(dist_cm * 100), 1, 65535), 0).astype(np.uint16)
    Image.fromarray(a).save(ROOT / f"data/scene/visible_depth_{name}.png")


def measure(name, img, mask):
    """Run one model on the photo; save its distances for the pixels of him, and what it said about itself."""
    t0 = time.time()
    r = (run_depthpro if name == "depthpro" else run_moge2)(img)
    dist_cm = r["distance_m"] * 100.0
    save_distance(name, dist_cm, mask)
    meta = dict(about=__doc__.split("\n\n")[0], model=MODELS[name], photo="data/photos/anchor_front.webp",
                file=f"data/scene/visible_depth_{name}.png",
                units="16-bit: distance from the model's camera to each pixel of him, in 0.01 of the model's own cm; "
                      "0 = not him",
                lens_px=round(r["focal_px"], 2), principal_point="the picture's centre (as the model assumes)",
                pixels_of_him=int(mask.sum()), seconds=round(time.time() - t0, 1),
                invented="nothing: no smoothing, filling or merging; only what this photo sees")
    if "valid" in r:
        meta["model_says_invalid_px_of_him"] = int((mask & ~r["valid"]).sum())
    (ROOT / f"data/scene/visible_depth_{name}.json").write_text(json.dumps(meta, indent=1))


def model_camera(f, W, H, up_deg=0.0):
    """A model's own camera, before it is moved into the room: its lens, its rays (the picture's centre straight
    ahead), straight on, the picture's centre tilted up by up_deg (negative: down)."""
    return Camera.orbit([0, 0, -1.0], 1.0, pitch_deg=-up_deg, f=f, width=W, height=H)


def surface_camera_frame(name):
    """Every pixel of him as a 3D point in the model's own camera frame (x right, y down, z forward), in the
    model's own units: its ray (own lens) cut at its distance. (H, W, 3); NaN where not him."""
    meta = load(f"data/scene/visible_depth_{name}.json")
    dist = np.array(Image.open(ROOT / meta["file"])).astype(float) / 100.0
    H, W = dist.shape
    cam = model_camera(meta["lens_px"], W, H)
    yy, xx = np.mgrid[0:H, 0:W] + 0.5
    ray = cam.ray_camera(np.c_[xx.ravel(), yy.ravel()]).reshape(H, W, 3)
    return np.where((dist > 0)[..., None], ray * dist[..., None], np.nan), cam, meta


def room_points(name):
    """Every pixel of him in the room, as placed (data/scene/visible_depth_<name>.json): (camera, P (H, W, 3), meta)."""
    Pc, _, meta = surface_camera_frame(name)
    pl = meta["placed_in_the_room"]
    cam = Camera.from_dict(pl["camera"])
    return cam, (pl["scale"] * Pc) @ cam.R + cam.C, meta


def width_across(Pc, mask, y, inset=EDGE_INSET_PX, rows=3):
    """His width across his widest outline (camera x), from the pixels `inset` px inside his outline on each
    side, median over the rows y-rows..y+rows."""
    left, right = [], []
    for r in range(y - rows, y + rows + 1):
        on = np.flatnonzero(mask[r] & np.isfinite(Pc[r, :, 0]))
        if len(on) > 2 * inset:
            left.append(Pc[r, on[0] + inset, 0]); right.append(Pc[r, on[-1] - inset, 0])
    return float(np.median(right) - np.median(left))


def inside_band(mask, px=EDGE_INSET_PX):
    """Pixels of him more than `px` px inside his outline (the outer band blends into the removed background)."""
    from scipy import ndimage
    return ndimage.distance_transform_edt(mask) > px


def point_near(P, uv, reach=NEAR_PX):
    """The 3D point at a picture position: the median of the points of him within `reach` px."""
    H, W = P.shape[:2]
    x, y = uv
    y0, y1, x0, x1 = int(max(y - reach, 0)), int(min(y + reach + 1, H)), int(max(x - reach, 0)), int(min(x + reach + 1, W))
    yy, xx = np.mgrid[y0:y1, x0:x1] + 0.5
    near = (xx - x) ** 2 + (yy - y) ** 2 <= reach ** 2
    pts = P[y0:y1, x0:x1][near]
    pts = pts[np.isfinite(pts[:, 0])]
    return np.median(pts, axis=0) if len(pts) else np.full(3, np.nan)


def place(name, mask, lm, widest_y):
    """Put one model's measured surface into the room with its own camera; return (camera, points (H, W, 3) in the
    room, scale, report)."""
    Pc, cam, meta = surface_camera_frame(name)
    own_width = width_across(Pc, mask, widest_y)
    s = WIDTH_CM / own_width                                     # one number: his approved width, shape untouched
    eyes_c = s * (point_near(Pc, lm["eye_his_left"]["at_px"]) + point_near(Pc, lm["eye_his_right"]["at_px"])) / 2
    lo, hi = -30.0, 30.0                                          # which way is up: his eyes 0.5 cm above the camera
    for _ in range(60):
        mid_deg = (lo + hi) / 2
        above = (eyes_c @ model_camera(cam.f, cam.width, cam.height, mid_deg).R)[1]
        lo, hi = (mid_deg, hi) if above < EYES_ABOVE_CAMERA_CM else (lo, mid_deg)   # tilting up lifts his eyes
    cam = model_camera(cam.f, cam.width, cam.height, (lo + hi) / 2)
    P = (s * Pc) @ cam.R                                          # room directions, camera at the origin for now
    inset = {"crown_front": EDGE_INSET_PX, "ear_tip_his_left": EDGE_INSET_PX, "ear_tip_his_right": EDGE_INSET_PX,
             "peet_bottom_his_left": -EDGE_INSET_PX, "peet_bottom_his_right": -EDGE_INSET_PX}  # read inside the edge
    pts = {k: point_near(P, (v["at_px"][0], v["at_px"][1] + inset.get(k, 0))) for k, v in lm.items()
           if v["kind"] == "surface point" or k in inset or k == "belly_front"}
    pr, pl = pts["peet_bottom_his_right"], pts["peet_bottom_his_left"]
    mid = (pr + pl) / 2
    cam.C = -mid                                                  # the surface through his peet bottoms; origin under their middle
    P = P + cam.C
    pts = {k: v - mid for k, v in pts.items()}
    pr, pl = pts["peet_bottom_his_right"], pts["peet_bottom_his_left"]
    him = P[mask & np.isfinite(P[..., 0])]
    inner = P[inside_band(mask) & np.isfinite(P[..., 0])]
    eyes = (pts["eye_his_left"] + pts["eye_his_right"]) / 2
    nose = pts["nose_y_centre"]
    r2 = lambda v: round(float(v), 2)
    widths = {f"{i} px in": r2(s * width_across(Pc, mask, widest_y, i))
              for i in (2, 4, 8)}
    report = dict(
        scale=round(s, 6),
        scale_means=f"the model's own units x {s:.4f}: the model alone made him {own_width:.1f} cm wide; one number "
                    f"brings him to his approved {WIDTH_CM} cm (his shape is not changed)",
        width_read_at=f"his widest outline (picture row {widest_y}), {EDGE_INSET_PX} px inside it on each side "
                      f"(the outermost pixels blend into the removed background); read 2 / 4 / 8 px inside, he "
                      f"would be {widths['2 px in']} / {widths['4 px in']} / {widths['8 px in']} cm wide at this scale",
        camera_to_nose_cm=r2(np.linalg.norm(nose - cam.C)),
        camera_height_cm=r2(cam.C[1]),
        his_eyes_above_camera_cm=r2(eyes[1] - cam.C[1]),
        picture_centre_points=f"{abs(cam.angles()[1]):.1f} deg {'down' if cam.angles()[1] > 0 else 'up'}: the "
                              f"cropped picture's centre is not where the camera aimed (lesson 26)",
        eye_heights_cm=dict(his_right=r2(pts["eye_his_right"][1]), his_left=r2(pts["eye_his_left"][1])),
        nose_height_cm=r2(nose[1]),
        top_of_head_cm=r2(pts["crown_front"][1]),
        ear_tips_cm=[r2(pts["ear_tip_his_right"][1]), r2(pts["ear_tip_his_left"][1])],
        edge_landmarks_read=f"{EDGE_INSET_PX} px inside his outline (top of head, ear tips, peet bottoms)",
        peet_bottoms_cm=dict(note="the surface goes through the middle of the two; how far each is above it",
                             his_right=r2(pr[1]), his_left=r2(pl[1])),
        lowest_point_of_him_cm=dict(all=r2(him[:, 1].min()), more_than_4_px_inside=r2(inner[:, 1].min())),
        highest_point_of_him_cm=dict(all=r2(him[:, 1].max()), more_than_4_px_inside=r2(inner[:, 1].max())),
        deepest_point_behind_nose_cm=dict(all=r2(nose[2] - him[:, 2].min()),
                                          more_than_4_px_inside=r2(nose[2] - inner[:, 2].min())),
        behind_nose_cm={k: r2(nose[2] - pts[k][2]) for k in
                        ("eye_his_right", "eye_his_left", "chin_midline", "fold_midline", "crown_front", "belly_front")},
        landmarks_room_cm={k: np.round(v, 3).tolist() for k, v in sorted(pts.items())},
        owner_remembered=dict(camera_to_nose_cm=15.24, camera="basically exactly at his eye level, maybe a tiny bit "
                              "lower; level, maybe ever so slightly up", top_of_head_floor_cm=12.7))
    return cam, P, s, report


def picture(placed, rgb):
    """Side and top views of each model's measured surface (his left side; from above), same scale, for the docs.
    Every 3rd pixel of him, coloured as the photo; the surface he sits on and the origin marked."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(2, 2, figsize=(12, 12), facecolor="#aeb3ba")
    for row, (name, (cam, P, rep)) in enumerate(placed.items()):
        ys, xs = np.mgrid[0:P.shape[0]:3, 0:P.shape[1]:3]
        q = P[ys, xs].reshape(-1, 3); c = (rgb[ys, xs].reshape(-1, 3) / 255.0)
        ok = np.isfinite(q[:, 0]); q, c = q[ok], c[ok]
        # seen from his left (at +X): his forward is to the LEFT; seen from above with his forward up the page: his left
        # is on the page's LEFT. Both need the horizontal axis reversed, or the picture is a mirror image.
        for col, (i, j, title, xl, yl) in enumerate(((2, 1, "from his left side (his forward is to the left)", "z: his forward (cm)", "y: up (cm)"),
                                                    (0, 2, "from above (his forward is up; his left on the left)", "x: his left (cm)", "z: his forward (cm)"))):
            a_ = ax[row, col]; a_.set_facecolor("#aeb3ba")
            order = np.argsort(q[:, 0] if col == 0 else q[:, 1])      # nearer the viewer drawn last
            a_.scatter(q[order, i], q[order, j], s=0.6, c=c[order], linewidths=0)
            if col == 0:
                a_.axhline(0, color="#333", lw=1)
                a_.annotate(f"camera (off to the left): {rep['camera_to_nose_cm']:.1f} cm from his nose, {cam.C[1]:.1f} cm up",
                            xy=(0.02, 0.97), xycoords="axes fraction", ha="left", va="top", fontsize=10)
            a_.plot([0], [0], "k+", ms=12)
            a_.set_xlim(18, -12) if col == 0 else a_.set_xlim(14, -14)          # reversed: not a mirror image
            a_.set_ylim(-3, 25) if col == 0 else a_.set_ylim(-12, 18)
            a_.set_aspect("equal"); a_.grid(color="#9ca1a8", lw=0.5)
            a_.set_title(f"{NAMES[name]}: {title}", fontsize=11); a_.set_xlabel(xl); a_.set_ylabel(yl)
    fig.suptitle("His surface as the anchor photo sees it: each pixel's ray cut at the measured distance (nothing invented). "
                 "\nEach model with its own camera; one number per model makes him 15.5 cm wide; + = origin", fontsize=11)
    fig.tight_layout()
    out = OUT_IMG / "visible_depth_side_top.png"
    fig.savefig(out, dpi=110, facecolor=fig.get_facecolor()); plt.close(fig)
    print("wrote", out.relative_to(ROOT))


def compare_picture(placed):
    """Both models overlaid in the same views (from his left side; from above), tinted by model, so they are
    compared on top of each other, not across panels. Every 3rd pixel of him; nose, eyes and peet bottoms marked."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tint = {"depthpro": "#e67e22", "moge2": "#2e86de"}
    fig, ax = plt.subplots(1, 2, figsize=(14, 7.4), facecolor="white")
    for name, (cam, P, rep) in placed.items():
        q = P[::3, ::3].reshape(-1, 3); q = q[np.isfinite(q[:, 0])]
        L = rep["landmarks_room_cm"]
        marks = np.array([L[k] for k in ("nose_y_centre", "eye_his_right", "eye_his_left",
                                         "peet_bottom_his_right", "peet_bottom_his_left")])
        for a_, (i, j) in zip(ax, ((2, 1), (0, 2))):
            a_.scatter(q[:, i], q[:, j], s=0.5, c=tint[name], alpha=0.25, linewidths=0)
            a_.scatter(marks[:, i], marks[:, j], s=60, c=tint[name], edgecolors="black", linewidths=0.8, zorder=5)
    for a_, title, xl, yl, xlim, ylim in (
            (ax[0], "from his left side (his forward is to the left)", "z: his forward (cm)", "y: up (cm)", (18, -14), (-3, 24)),
            (ax[1], "from above (his forward is up; his left on the left)", "x: his left (cm)", "z: his forward (cm)", (14, -14), (-14, 16))):
        a_.set_xlim(*xlim); a_.set_ylim(*ylim); a_.set_aspect("equal"); a_.grid(color="#dddddd", lw=0.5)
        a_.set_title(title, fontsize=11); a_.set_xlabel(xl); a_.set_ylabel(yl)
    ax[0].axhline(0, color="#333", lw=1)
    for name in placed:
        ax[1].scatter([], [], s=60, c=tint[name], edgecolors="black", label=NAMES[name])
    ax[1].legend(loc="lower right", fontsize=10)
    fig.suptitle("The two depth models on top of each other, both 15.5 cm wide, origin under the middle of his peets.\n"
                 "Big dots: his nose, eyes and peet bottoms. Nothing invented: every dot is one pixel of him.", fontsize=11)
    fig.tight_layout()
    out = OUT_IMG / "visible_depth_compare.png"
    fig.savefig(out, dpi=110); plt.close(fig)
    print("wrote", out.relative_to(ROOT))


def main() -> int:
    img = Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB")
    W, H = img.size
    lm = load("data/strands/landmarks.json")["landmarks"]
    mask = him_mask(H, W)
    args = sys.argv[1:]
    if "--measure" in args:
        for name in [a for a in args if a in MODELS] or list(MODELS):
            measure(name, img, mask)
            print("measured", name)
    from scene import widest_outline                              # his outline only: no camera involved
    widest_y = int(widest_outline(np.array(load("data/strands/body_outline.json")["sampled_curve"]))[1][2])
    placed = {}
    for name in MODELS:
        cam, P, s, report = place(name, mask, lm, widest_y)
        meta = load(f"data/scene/visible_depth_{name}.json")
        meta["placed_in_the_room"] = dict(
            how="each pixel of him: the ray from THIS model's own camera (below: its own lens and rays, straight on) "
                "cut at this model's distance x scale. Up: turned so his eyes are 0.5 cm above the camera (owner: "
                "'basically exactly at his eye level. Maybe just a tiny bit lower'). The surface he sits on (y = 0) "
                "goes through the middle of his two peet bottoms; the origin is under that middle. Checks are "
                "reported only: nothing was changed to meet them.",
            camera=cam.to_dict(), **report)
        (ROOT / f"data/scene/visible_depth_{name}.json").write_text(json.dumps(meta, indent=1))
        placed[name] = (cam, P, report)
        print(name, json.dumps({k: v for k, v in report.items() if k not in ("landmarks_room_cm",)}, indent=1))
    picture(placed, np.asarray(img))
    compare_picture(placed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
