"""Map the 18 full-resolution sheet originals: where each camera was relative
to Prince, and which parts of his face and body each photo shows well.

Cameras
  Face photos: solved from hand-placed landmarks (eyes, nostrils, nose tip,
  mouth split, ear tips, peets) against the 3D face from tools/solve_face.py.
  The solve is relative to his HEAD, because he moved his head between shots;
  the head is what these photos are for. A weak prior (rough angle read off
  the photo, ~40 cm distance, phone lens) holds views with few landmarks.
  Back photos (04, 05, 06) show almost no landmarks; their cameras come from
  the Checkpoint 2 silhouette solve of the same photos (sheet panels).

Coverage
  For each region of his body, how directly a camera sees it: the share of
  the region's surface facing the camera, weighted by how squarely. 0 = not
  seen, 1 = seen straight on. Self-occlusion is ignored (his body is close to
  convex, so facing-the-camera is a good proxy).

Outputs: checkpoints/sheet_originals_map/ (cameras.json, coverage.json,
camera_map.png, coverage.png, contact_sheet.png).
"""
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as R

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
import fit_surface as FS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "references/sheet_originals"
OUT = ROOT / "checkpoints/sheet_originals_map"
W_IMG, H_IMG = 1131, 1391
F_PX = H_IMG / 2 / np.tan(np.radians(35) / 2)  # phone lens, ~35 deg vertical

# Landmarks in original pixels (x right, y down), placed on gridded views.
# Left/right are Prince's own.
LM = {
    "01_front": {"eye_R": [375, 420], "eye_L": [735, 395], "nose_tip": [575, 675], "nostril_R": [520, 640],
                 "nostril_L": [635, 640], "mouth_split": [580, 765], "ear_tip_R": [460, 175], "ear_tip_L": [705, 165]},
    "02_front_3q": {"eye_L": [610, 405], "eye_R": [260, 420], "nose_tip": [380, 680], "nostril_R": [330, 650],
                    "nostril_L": [440, 645], "mouth_split": [385, 770], "ear_tip_R": [445, 155], "ear_tip_L": [680, 145]},
    "03_right_profile": {"eye_R": [815, 460], "nose_tip": [1000, 600], "ear_tip_R": [535, 190]},
    "04_back_3q_right": {"eye_R": [790, 360]},
    "05_back": {"ear_tip_L": [450, 140], "ear_tip_R": [660, 145]},
    "06_back_3q_left": {"ear_tip_L": [380, 215], "ear_tip_R": [545, 205]},
    "07_left_profile": {"eye_L": [370, 410], "nose_tip": [185, 525], "ear_tip_L": [650, 230]},
    "08_front_3q_left": {"eye_L": [590, 420], "eye_R": [270, 430], "nose_tip": [380, 675], "nostril_R": [335, 645],
                         "nostril_L": [435, 640], "mouth_split": [385, 765], "ear_tip_R": [465, 180],
                         "ear_tip_L": [640, 170]},
    "09_top_down": {"eye_R": [348, 1000], "eye_L": [672, 1005], "nose_tip": [500, 1225], "ear_tip_R": [440, 650],
                    "ear_tip_L": [665, 660]},
    "10_bottom_up": {"nose_tip": [575, 255], "mouth_split": [575, 320]},
    "11_looking_up_slight": {"eye_R": [370, 245], "eye_L": [665, 245], "nose_tip": [500, 385], "nostril_R": [455, 355],
                             "nostril_L": [545, 355], "mouth_split": [505, 480]},
    "12_looking_up_more": {"eye_R": [385, 235], "eye_L": [705, 220], "nose_tip": [530, 360], "nostril_R": [485, 320],
                           "nostril_L": [580, 320], "mouth_split": [530, 450]},
    "13_looking_down_slight": {"eye_R": [355, 640], "eye_L": [740, 640], "nose_tip": [570, 985], "nostril_R": [500, 960],
                               "nostril_L": [630, 960], "ear_tip_R": [430, 150], "ear_tip_L": [690, 150]},
    "14_looking_down_more": {"eye_R": [335, 755], "eye_L": [730, 710], "nose_tip": [575, 1070], "ear_tip_R": [380, 200],
                             "ear_tip_L": [645, 190]},
    "15_looking_left": {"eye_L": [570, 270], "nose_tip": [285, 405], "mouth_split": [300, 480], "ear_tip_L": [745, 115],
                        "ear_tip_R": [580, 105]},
    "16_looking_right": {"eye_R": [510, 285], "nose_tip": [810, 425], "mouth_split": [810, 510], "ear_tip_R": [360, 125],
                         "ear_tip_L": [520, 110]},
    "17_from_below_da_boss": {"eye_R": [335, 260], "eye_L": [745, 225], "nose_tip": [520, 330], "nostril_R": [470, 290],
                              "nostril_L": [575, 285], "mouth_split": [525, 445]},
    "18_staring_at_boss": {"eye_R": [370, 415], "eye_L": [718, 400], "nose_tip": [565, 660], "nostril_R": [510, 630],
                           "nostril_L": [620, 630], "mouth_split": [570, 755], "ear_tip_R": [450, 190],
                           "ear_tip_L": [675, 180]},
}
# rough reading of each photo: (azimuth deg, + toward his LEFT side; elevation deg)
INIT = {"01_front": (0, 8), "02_front_3q": (25, 8), "03_right_profile": (-80, 12), "07_left_profile": (80, 12),
        "08_front_3q_left": (25, 8), "09_top_down": (0, 80), "10_bottom_up": (0, -75), "11_looking_up_slight": (0, -15),
        "12_looking_up_more": (0, -25), "13_looking_down_slight": (0, 30), "14_looking_down_more": (0, 45),
        "15_looking_left": (-35, 5), "16_looking_right": (35, 5), "17_from_below_da_boss": (0, -40),
        "18_staring_at_boss": (0, 8)}
# These photos are unmistakably straight side-on / straight down, but the
# landmark solve can't reach those angles: the 3D face it uses has his nose
# only ~2.4 cm ahead of his eyes, while these photos put it ~5 cm ahead (see
# README). Until the face is rebuilt, their angles are read from the photo.
READ_FROM_PHOTO = {"03_right_profile": (-88, 12, 0.5), "07_left_profile": (88, 12, 0.5), "09_top_down": (0, 86, 0.5)}
FROM_CP2 = {"04_back_3q_right": "sheet_04_back_3q_right", "05_back": "sheet_05_back",
            "06_back_3q_left": "sheet_06_back_3q_left"}
TITLES = {"01_front": "front", "02_front_3q": "front 3/4", "03_right_profile": "right profile",
          "04_back_3q_right": "back 3/4 right", "05_back": "back", "06_back_3q_left": "back 3/4 left",
          "07_left_profile": "left profile", "08_front_3q_left": "front 3/4 left", "09_top_down": "top-down",
          "10_bottom_up": "bottom-up", "11_looking_up_slight": "looking up", "12_looking_up_more": "looking up more",
          "13_looking_down_slight": "looking down", "14_looking_down_more": "looking down more",
          "15_looking_left": "looking left", "16_looking_right": "looking right",
          "17_from_below_da_boss": "from below (da boss)", "18_staring_at_boss": "staring at boss"}

# design tokens (reference palette): surfaces, ink, categorical slots, blue ramp
SURF, INK, INK2 = "#fcfcfb", "#0b0b0b", "#52514e"
C_MASTER, C_SHEET, C_BACK = "#2a78d6", "#eb6834", "#1baf7a"
BLUE_RAMP = ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def view_dir(az, el):
    a, e = np.radians(az), np.radians(el)
    return np.array([-np.sin(a) * np.cos(e), np.cos(a) * np.cos(e), np.sin(e)])


def cam_from_params(p, centre):
    az, el, dist, roll, ox, oy = p
    pos = centre + view_dir(az, el) * dist
    fwd = centre - pos
    fwd /= np.linalg.norm(fwd)
    up = np.array([0, 0, 1.0]) if abs(fwd[2]) < 0.95 else np.array([0, 1.0, 0])
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    down = np.cross(fwd, right)
    Rm = np.stack([right, down, fwd])
    Rm = R.from_rotvec(fwd * np.radians(roll)).as_matrix() @ Rm.T
    Rm = Rm.T
    return Rm, pos, np.array([ox, oy])


def project(Rm, pos, off, X):
    Xc = (np.atleast_2d(X) - pos) @ Rm.T
    return np.stack([F_PX * Xc[:, 0] / Xc[:, 2] + W_IMG / 2 + off[0], F_PX * Xc[:, 1] / Xc[:, 2] + H_IMG / 2 + off[1]], 1)


def model_points():
    fs = json.loads((ROOT / "checkpoints/cp3/face_solve.json").read_text())
    P = {k: np.array(v) for k, v in fs["points_master_pose_m"].items()}
    cp2 = json.loads((ROOT / "checkpoints/cp2/cameras_fit.json").read_text())
    for k in ("ear_tip_R", "ear_tip_L"):
        P[k] = np.array(cp2["points_3d"][k])
    return P, cp2


def solve(name, P):
    lm = LM[name]
    keys = [k for k in lm if k in P]
    X = np.array([P[k] for k in keys])
    obs = np.array([lm[k] for k in keys], float)
    centre = np.array([0, 0.05, 0.10])  # his head
    az0, el0 = INIT[name]

    def res(p):
        Rm, pos, off = cam_from_params(p, centre)
        r = [(project(Rm, pos, off, X) - obs).ravel() / H_IMG * 100]
        # weak priors: rough angle, ~40 cm, photo roughly centred on his head
        # views with few landmarks (profiles) lean more on the photo's
        # obvious angle: three points can't separate turn from distance
        k = 25.0 if len(keys) >= 5 else 10.0
        r.append([(p[0] - az0) / k, (p[1] - el0) / k, np.log(p[2] / 0.4) / 0.5, p[3] / 30,
                  p[4] / 300, p[5] / 300])
        return np.concatenate(r)

    best = None
    lo = [-200, -89, 0.15, -200, -600, -600]
    hi = [200, 89, 1.2, 200, 600, 600]
    for daz in (-15, 0, 15):
        for roll0 in (-90, 0, 90, 180):
            x0 = np.clip([az0 + daz, np.clip(el0, -88, 88), 0.4, roll0 if abs(el0) > 60 else roll0 / 6, 0, 0],
                         np.array(lo) + 1e-6, np.array(hi) - 1e-6)
            s = least_squares(res, x0, loss="soft_l1", bounds=(lo, hi))
            if best is None or s.cost < best.cost:
                best = s
    Rm, pos, off = cam_from_params(best.x, centre)
    err = np.linalg.norm(project(Rm, pos, off, X) - obs, axis=1)
    return {"azimuth_deg": round(float(best.x[0]), 1), "elevation_deg": round(float(best.x[1]), 1),
            "distance_m": round(float(best.x[2]), 3), "roll_deg": round(float(best.x[3]), 1),
            "camera_position_m": pos.round(4).tolist(), "landmarks_used": keys,
            "rms_px": round(float(np.sqrt(np.mean(err ** 2))), 1), "source": "landmarks (head-relative)",
            "R": Rm.tolist(), "offset_px": off.tolist()}


def regions(P):
    meta = json.loads((ROOT / "checkpoints/cp3/body_meta.json").read_text())
    c = np.array(meta["centre_m"])
    d, F = FS.icosphere(meta["subdiv"])
    r = np.load(ROOT / "checkpoints/cp3/body_radii.npy")
    V = c + d * r[:, None]
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    near = lambda p, rad: np.linalg.norm(V - p, axis=1) < rad  # noqa: E731
    z0, z1 = V[:, 2].min(), V[:, 2].max()
    zr = (V[:, 2] - z0) / (z1 - z0)
    eyes = near(P["eye_R"], 0.011) | near(P["eye_L"], 0.011)
    nose = near(P["nose_tip"], 0.011) | near(P["nostril_R"], 0.007) | near(P["nostril_L"], 0.007)
    mouth = near(P["mouth_split"], 0.012) & ~nose
    eye_mid = (P["eye_R"] + P["eye_L"]) / 2
    bridge = near((eye_mid + P["nose_tip"]) / 2 + np.array([0, 0.004, 0.006]), 0.016) & ~eyes & ~nose
    ears = near(P["ear_tip_R"], 0.02) | near(P["ear_tip_L"], 0.02)
    face_zone = near(P["nose_tip"], 0.055) & (V[:, 1] > 0.03)
    cheeks = face_zone & (np.abs(V[:, 0]) > 0.02) & (V[:, 2] < P["eye_R"][2] - 0.008) & ~eyes & ~nose & ~mouth
    chin = near(P["mouth_split"] - np.array([0, 0.008, 0.02]), 0.018) & ~mouth
    crown = (zr > 0.82) & ~ears & ~face_zone
    used = eyes | nose | mouth | bridge | ears | cheeks | chin | crown
    front = (N[:, 1] > 0.5) & ~used
    bib = front & (zr > 0.25) & (zr <= 0.6)
    skirt = front & (zr <= 0.25)
    back = (N[:, 1] < -0.5) & ~used & (zr > 0.12)
    sides = (np.abs(N[:, 0]) > 0.6) & ~used & ~bib & ~skirt & ~back & (zr > 0.12)
    under = (zr < 0.06) | (N[:, 2] < -0.7)
    regs = {"right eye": eyes, "left eye": eyes, "nose pad": nose, "mouth / Y-split": mouth, "nose bridge": bridge, "cheeks": cheeks,
            "chin": chin, "right ear": ears, "left ear": ears, "top of head": crown, "chest bib": bib, "lower skirt": skirt,
            "sides": sides, "back": back, "underside & peets": under}
    return V, N, regs


def special_normals():
    """Eyes look ~55 deg out to the side (face solve); ears are thin flaps
    facing up, a little forward and out, seen from either side."""
    fs = json.loads((ROOT / "checkpoints/cp3/face_shape.json").read_text())
    eyes = [(np.array(fs["eyes"][k]["surface_point"]), np.array(fs["eyes"][k]["axis"])) for k in ("R", "L")]
    _, cp2 = model_points()
    ears = []
    for k, sgn in (("ear_tip_R", 1), ("ear_tip_L", -1)):
        n = np.array([0.3 * sgn, 0.45, 0.84])
        ears.append((np.array(cp2["points_3d"][k]), n / np.linalg.norm(n)))
    return eyes, ears


def coverage(V, N, regs, Rm, pos):
    out = {}
    eyes, ears = special_normals()
    for names, items, two_sided in ((("right eye", "left eye"), eyes, False), (("right ear", "left ear"), ears, True)):
        for name, (p, n) in zip(names, items):
            to = pos - p
            c = float(to @ n / np.linalg.norm(to))
            out[name] = abs(c) if two_sided else max(c, 0.0)
    for k, m in regs.items():
        if k in out:
            continue
        if m.sum() == 0:
            out[k] = 0.0
            continue
        to = pos - V[m]
        to /= np.linalg.norm(to, axis=1, keepdims=True)
        cosang = np.einsum("ij,ij->i", to, N[m])
        out[k] = float(np.clip(cosang, 0, 1).mean())
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    P, cp2 = model_points()
    cams = {}
    for n in LM:
        if n in READ_FROM_PHOTO:
            az, el, dist = READ_FROM_PHOTO[n]
            centre = np.array([0, 0.05, 0.10])
            Rm, pos, _ = cam_from_params([az, el, dist, 0, 0, 0], centre)
            cams[n] = {"azimuth_deg": az, "elevation_deg": el, "distance_m": dist,
                       "camera_position_m": pos.round(4).tolist(), "R": Rm.tolist(), "rms_px": None,
                       "source": "angle read from the photo (landmark solve disagrees; see README)",
                       "landmark_solve": {k: v for k, v in solve(n, P).items() if k not in ("R", "offset_px")}}
        elif n in FROM_CP2:
            v = cp2["views"][FROM_CP2[n]]
            cams[n] = {"azimuth_deg": v["azimuth_deg"], "elevation_deg": v["elevation_deg"],
                       "distance_m": v["distance_m"], "camera_position_m": v["camera_position_m"],
                       "R": R.from_rotvec(v["rotvec_world_to_cam"]).as_matrix().tolist(),
                       "source": "Checkpoint 2 silhouette solve of the same photo (sheet panel)", "rms_px": None}
        else:
            cams[n] = solve(n, P)
        c = cams[n]
        print(f"{n:24s} az {c['azimuth_deg']:+7.1f} el {c['elevation_deg']:+6.1f} d {c['distance_m'] * 100:5.1f} cm "
              f"rms {c['rms_px']} px")
    V, N, regs = regions(P)
    cov = {n: coverage(V, N, regs, np.array(c["R"]), np.array(c["camera_position_m"])) for n, c in cams.items()}
    mv = cp2["views"]["master_front_standing"]
    cov["MASTER"] = coverage(V, N, regs, None, np.array(mv["camera_position_m"]))
    (OUT / "cameras.json").write_text(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("R", "offset_px")}
                                                   for k, v in cams.items()}, indent=1))
    (OUT / "coverage.json").write_text(json.dumps(cov, indent=1))
    camera_map(cams, mv)
    coverage_chart(cov, list(regs))
    contact_sheet(cams, P)


def camera_map(cams, mv):
    fig, axes = plt.subplots(1, 2, figsize=(14, 7), facecolor=SURF)
    for ax, (title, horiz, vert, hl, vl) in zip(axes, [
            ("Seen from above", 0, 1, "his right  <-  x (cm)  ->  his left", "behind  <-  y (cm)  ->  in front"),
            ("Seen from his right side", 1, 2, "behind  <-  y (cm)  ->  in front", "below  <-  z (cm)  ->  above")]):
        ax.set_facecolor(SURF)
        flip = -1 if horiz == 0 else 1  # draw his left on the right of the plot
        body = plt.Circle((0, 8.5 if vert == 2 else 0), 9, color="#e9e8e4", zorder=1)
        ax.add_patch(body)
        ax.annotate("Prince", (0, 8.5 if vert == 2 else 0), ha="center", va="center", color=INK2, fontsize=10)
        if horiz == 0:
            ax.annotate("nose", (0, 10.5), ha="center", color=INK2, fontsize=8)
        else:
            ax.annotate("nose", (10.5, 9), ha="left", color=INK2, fontsize=8)
        for n, c in cams.items():
            p = np.array(c["camera_position_m"]) * 100
            col = C_BACK if "Checkpoint 2" in c["source"] else C_SHEET
            x, y = flip * p[horiz], p[vert]
            ax.plot([x, 0], [y, 8.5 if vert == 2 else 0], color=col, lw=0.8, alpha=0.35, zorder=2)
            ax.scatter([x], [y], s=46, color=col, edgecolors=SURF, linewidths=2, zorder=4)
            ax.annotate(n[:2], (x, y), xytext=(5, 4), textcoords="offset points", fontsize=8.5, color=INK)
        p = np.array(mv["camera_position_m"]) * 100
        ax.scatter([flip * p[horiz]], [p[vert]], s=110, marker="*", color=C_MASTER, edgecolors=SURF, linewidths=1.5,
                   zorder=5)
        ax.annotate("MASTER", (flip * p[horiz], p[vert]), xytext=(6, -12), textcoords="offset points", fontsize=9,
                    color=INK, weight="bold")
        ax.set_title(title, color=INK, fontsize=13, loc="left")
        ax.set_xlabel(hl, color=INK2)
        ax.set_ylabel(vl, color=INK2)
        ax.set_aspect("equal")
        ax.grid(color="#e4e3df", lw=0.6)
        for s in ax.spines.values():
            s.set_color("#d8d7d2")
        ax.tick_params(colors=INK2)
    handles = [plt.Line2D([], [], marker="*", ls="", color=C_MASTER, markersize=12, label="master (immutable)"),
               plt.Line2D([], [], marker="o", ls="", color=C_SHEET, markersize=8,
                          label="original, solved from face landmarks (relative to his head)"),
               plt.Line2D([], [], marker="o", ls="", color=C_BACK, markersize=8,
                          label="original, from the Checkpoint 2 silhouette solve (back views)")]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=10, labelcolor=INK)
    fig.suptitle("Where each of the 18 originals was taken from (numbers = photo number)", color=INK, fontsize=15,
                 x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0.06, 1, 0.95))
    fig.savefig(OUT / "camera_map.png", dpi=130, facecolor=SURF)
    plt.close(fig)


def coverage_chart(cov, regnames):
    rows = ["MASTER"] + list(LM)
    M = np.array([[cov[r][g] for g in regnames] for r in rows])
    cmap = LinearSegmentedColormap.from_list("blue", BLUE_RAMP)
    fig, ax = plt.subplots(figsize=(14, 9.5), facecolor=SURF)
    ax.set_facecolor(SURF)
    ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0] + 1):
        ax.axhline(i - 0.5, color=SURF, lw=2)
    for j in range(M.shape[1] + 1):
        ax.axvline(j - 0.5, color=SURF, lw=2)
    for i, r in enumerate(rows):
        best = M[i].argsort()[::-1][:2] if r != "MASTER" else []
        for j in range(M.shape[1]):
            v = M[i, j]
            if v >= 0.45 or j in best:
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                        color=SURF if v > 0.55 else INK)
    ax.set_xticks(range(len(regnames)), regnames, rotation=35, ha="right", color=INK)
    ax.set_yticks(range(len(rows)), ["MASTER (immutable)"] + [f"{r[:2]}  {TITLES[r]}" for r in rows[1:]], color=INK)
    ax.axhline(0.5, color=C_MASTER, lw=2.5)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("What each photo shows: how squarely it sees each part of him "
                 "(0 = not visible, 1 = straight on; numbers shown where it sees well)",
                 color=INK, fontsize=12, loc="left")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.01)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=INK2)
    fig.tight_layout()
    fig.savefig(OUT / "coverage.png", dpi=130, facecolor=SURF)
    plt.close(fig)


def contact_sheet(cams, P):
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 17)
    tiles = []
    for n in LM:
        im = Image.open(SRC / f"{n}.webp").convert("RGB")
        d = ImageDraw.Draw(im)
        c = cams[n]
        if "offset_px" in c:
            pts = {k: P[k] for k in LM[n] if k in P}
            proj = project(np.array(c["R"]), np.array(c["camera_position_m"]), np.array(c["offset_px"]),
                           np.array(list(pts.values())))
            for (k, uv), q in zip(pts.items(), proj):
                o = LM[n][k]
                d.ellipse([o[0] - 9, o[1] - 9, o[0] + 9, o[1] + 9], outline="#1baf7a", width=4)
                d.line([q[0] - 8, q[1] - 8, q[0] + 8, q[1] + 8], fill="#e87ba4", width=4)
                d.line([q[0] - 8, q[1] + 8, q[0] + 8, q[1] - 8], fill="#e87ba4", width=4)
        else:
            for k, o in LM[n].items():
                d.ellipse([o[0] - 9, o[1] - 9, o[0] + 9, o[1] + 9], outline="#1baf7a", width=4)
        im = im.resize((377, 464), Image.LANCZOS)
        t = Image.new("RGB", (377, 534), SURF)
        t.paste(im, (0, 0))
        dd = ImageDraw.Draw(t)
        dd.text((8, 470), f"{n[:2]}  {TITLES[n]}", fill=INK, font=font)
        dd.text((8, 500), f"az {c['azimuth_deg']:+.0f}  el {c['elevation_deg']:+.0f}  {c['distance_m'] * 100:.0f} cm",
                fill=INK2, font=small)
        tiles.append(t)
    sheet = Image.new("RGB", (6 * 377 + 50, 3 * 534 + 40), SURF)
    for i, t in enumerate(tiles):
        sheet.paste(t, (10 + (i % 6) * 385, 10 + (i // 6) * 544))
    sheet.save(OUT / "contact_sheet.png")


if __name__ == "__main__":
    main()
