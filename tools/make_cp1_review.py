"""Build the Checkpoint 1 review images.

For each wall view: the reference with his traced outline (red), fringe
(blue, white-background views only), whiskers (orange), the hand-placed
landmarks (green dots) and where the solved camera puts those landmarks
(magenta crosses). Plus a camera map seen from above and from the side.
The master is always first and shown at its own, unaltered framing.
"""
import json
from pathlib import Path

import cv2
import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from scipy.spatial.transform import Rotation as R  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CP = ROOT / "checkpoints/cp1"
MASKS = ROOT / "checkpoints/cp1/masks"

ORDER = [
    "master_front_standing",
    "sheet_01_front", "sheet_02_front_3q", "sheet_08_front_3q_left",
    "sheet_07_left_profile", "sheet_03_right_profile",
    "edited_back_3q_left_high", "sheet_06_back_3q_left", "sheet_04_back_3q_right",
    "edited_back", "sheet_05_back",
    "sheet_09_top_down", "sheet_10_bottom_up",
]


def mask_stem(vn, image):
    stem = Path(image).stem
    return f"sheet_{stem}" if vn.startswith("sheet_") else stem


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def project(view, X):
    Rm = R.from_rotvec(view["rotvec_world_to_cam"]).as_matrix()
    Xc = (np.asarray(X) - np.asarray(view["camera_position_m"])) @ Rm.T
    f = view["focal_px"]
    w, h = view["size"]
    return np.stack([f * Xc[:, 0] / Xc[:, 2] + w / 2, f * Xc[:, 1] / Xc[:, 2] + h / 2], 1)


def overlay(vn, view, lm, P3):
    rgb = np.asarray(Image.open(ROOT / view["image"]).convert("RGB")).copy()
    h, w = rgb.shape[:2]
    s = max(1, round(900 / max(w, h))) if max(w, h) < 600 else 1
    if s > 1:
        rgb = cv2.resize(rgb, (w * s, h * s), interpolation=cv2.INTER_LANCZOS4)
    th = max(2, round(2 * max(rgb.shape[:2]) / 1400))
    stem = mask_stem(vn, view["image"])

    def load(tag):
        p = MASKS / f"{stem}.{tag}.png"
        if not p.exists():
            return None
        m = np.asarray(Image.open(p)) > 0
        if s > 1:
            m = cv2.resize(m.astype(np.uint8), (w * s, h * s), interpolation=cv2.INTER_NEAREST) > 0
        return m

    wh = load("whiskers")
    if wh is not None:
        rgb[wh] = (rgb[wh] * 0.3 + np.array([255, 150, 0]) * 0.7).astype(np.uint8)
    for tag, col in (("fringe", (0, 170, 255)), ("outline", (235, 0, 60))):
        m = load(tag)
        if m is not None:
            cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(rgb, cs, -1, col, th)

    pts = lm["points"]
    obs = np.array(list(pts.values()), float) * s
    pred = project(view, [P3[n] for n in pts]) * s
    r = 3 * th
    for (ox, oy), (px, py) in zip(obs, pred):
        cv2.circle(rgb, (int(ox), int(oy)), r, (0, 200, 0), -1)
        cv2.line(rgb, (int(px - r), int(py - r)), (int(px + r), int(py + r)), (230, 0, 230), th)
        cv2.line(rgb, (int(px - r), int(py + r)), (int(px + r), int(py - r)), (230, 0, 230), th)

    im = Image.fromarray(rgb)
    band = max(60, im.height // 12)
    out = Image.new("RGB", (im.width, im.height + band), (255, 255, 255))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    f1, f2 = font(max(14, band // 3)), font(max(11, band // 4))
    d.text((8, im.height + 4), vn.replace("_", " "), fill=(0, 0, 0), font=f1)
    d.text((8, im.height + 4 + band // 2),
           f"tier {view['tier']} | az {view['azimuth_deg']:+.0f}  el {view['elevation_deg']:+.0f}  "
           f"dist {view['distance_m'] * 100:.0f} cm  vfov {view['vertical_fov_deg']:.0f}  "
           f"landmark err {view['mean_error_pct']:.2f}%",
           fill=(60, 60, 60), font=f2)
    return out


def camera_map(cams, P3):
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2))
    P = np.array(list(P3.values()))
    colours = {"master": "#d1003c", "edited": "#0077cc", "sheet": "#555555"}
    for ax, (i, j, title, xl, yl) in zip(axes, [(0, 1, "From above", "x (cm, + = his right)", "y (cm, + = forward)"),
                                                 (1, 2, "From his right side", "y (cm, + = forward)", "z (cm, up)")]):
        ax.scatter(P[:, i] * 100, P[:, j] * 100, s=18, c="k", zorder=3)
        for n, p in P3.items():
            ax.annotate(n, (p[i] * 100, p[j] * 100), fontsize=6, xytext=(2, 2), textcoords="offset points")
        for vn, v in cams.items():
            c = np.array(v["camera_position_m"]) * 100
            col = colours[v["tier"]]
            ax.scatter(c[i], c[j], s=60 if v["tier"] == "master" else 30, c=col, marker="^", zorder=4)
            ax.plot([c[i], 0], [c[j], 8 if j == 2 else 0], color=col, lw=0.6, alpha=0.5)
            ax.annotate(vn.replace("sheet_", "s").replace("edited_", "e:").replace("master_front_standing", "MASTER"),
                        (c[i], c[j]), fontsize=6.5, color=col, xytext=(3, -8), textcoords="offset points")
        ax.set_title(title)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_aspect("equal")
        ax.grid(alpha=0.3)
    fig.suptitle("Checkpoint 1: solved camera positions around Prince (red = master, blue = edited, grey = sheet)")
    fig.tight_layout()
    fig.savefig(CP / "review/camera_map.png", dpi=130)
    plt.close(fig)


def main():
    cams_all = json.loads((CP / "cameras.json").read_text())
    cams, P3 = cams_all["views"], cams_all["points_3d"]
    lms = json.loads((ROOT / "references/landmarks.json").read_text())["views"]
    (CP / "review").mkdir(parents=True, exist_ok=True)
    tiles = []
    for k, vn in enumerate(ORDER):
        im = overlay(vn, cams[vn], lms[vn], P3)
        im.save(CP / f"review/{k:02d}_{vn}.png")
        tiles.append(im)
    # contact sheet of all wall views (master large, first)
    th = 420
    small = [t.resize((round(t.width * th / t.height), th), Image.LANCZOS) for t in tiles[1:]]
    cols = 6
    rows = (len(small) + cols - 1) // cols
    cw = max(t.width for t in small)
    m = tiles[0].resize((round(tiles[0].width * th * 2 / tiles[0].height), th * 2), Image.LANCZOS)
    W = m.width + cols * cw
    sheet = Image.new("RGB", (W, max(m.height, rows * th)), (255, 255, 255))
    sheet.paste(m, (0, 0))
    for i, t in enumerate(small):
        sheet.paste(t, (m.width + (i % cols) * cw, (i // cols) * th))
    sheet.save(CP / "review/all_walls.png")
    camera_map(cams, P3)
    print("wrote", len(tiles), "overlays")


if __name__ == "__main__":
    main()
