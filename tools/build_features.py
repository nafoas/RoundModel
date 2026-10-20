"""Checkpoint 3, step 2: Prince's features on his refined body.

Everything is placed from the master: a feature's position is found by
casting a ray from the master camera through that feature in the photo
onto his body, so it lines up in the master view by construction. Sizes and
angles are then fitted to the master's outline (and, for ears and peets, to
the edited back views, which show them from behind).

  eyes   real eyeball spheres sitting in his head, sized so the part that
         shows matches the dark of each eye in the master
  nose   a soft pad, plus shallow grooves for the nostril V and the Y-split
         of his mouth, traced along the master's lines
  ears   thin rounded flaps (ellipsoids), each fitted on its own: the master
         shows his two ears sitting slightly differently
  peets  four rounded pads, front pair from the master, back pair from the
         back views

The body, ears, peets and nose pad are blended with smooth unions (no seams)
on a 0.7 mm grid and meshed; the grooves are smoothly carved; the eyes stay
separate objects (they need their own materials and rig later).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R
from skimage import measure

sys.path.insert(0, str(Path(__file__).parent))
import fit_surface as FS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CP1 = ROOT / "checkpoints/cp1"
CP2 = ROOT / "checkpoints/cp2"
CP3 = ROOT / "checkpoints/cp3"

H = 0.0007  # grid spacing (m)

# Master pixel positions (x right, y down), read off gridded zooms.
EYE_PX = {"R": (338, 467), "L": (699, 442)}
# extent of the dark of each eye (rim included) in the master: x0, y0, x1, y1
EYE_BOX = {"R": (316, 429, 361, 505), "L": (677, 400, 721, 485)}
NOSE_PX = (540, 718)            # centre of the pink pad, inside the V
GROOVES = [                     # polylines, master pixels
    [(470, 693), (510, 722), (546, 745)],   # nostril V, his right arm
    [(605, 688), (578, 718), (546, 745)],   # nostril V, his left arm
    [(546, 745), (547, 780), (548, 818)],   # philtrum to the mouth split
    [(548, 818), (538, 828), (529, 836)],   # lip, his right
    [(548, 818), (558, 828), (567, 836)],   # lip, his left
]
EAR_BASE_PX = {"R": (440, 290), "L": (650, 285)}
EAR_TIP_PX = {"R": (412, 215), "L": (668, 207)}
FRONT_PEET_PX = {"R": (360, 1205), "L": (680, 1212)}


# ---------------------------------------------------------------- body

class Body:
    def __init__(self):
        meta = json.loads((CP3 / "body_meta.json").read_text())
        self.c = np.array(meta["centre_m"])
        self.dirs, self.F = FS.icosphere(meta["subdiv"])
        self.r = np.load(CP3 / "body_radii.npy")
        self.tree = cKDTree(self.dirs)
        self.sigma = 0.7 * np.median(cKDTree(self.dirs).query(self.dirs, k=2)[0][:, 1])
        self.V = self.c + self.dirs * self.r[:, None]

    def radius(self, d):
        # Gaussian kernel over nearby directions (sigma ~ vertex spacing):
        # smooth, unlike inverse-distance weights, whose kinks showed as a
        # fine hatched texture with sparkles on the surface
        dist, idx = self.tree.query(d, k=16, workers=-1)
        w = np.exp(-(dist / self.sigma) ** 2)
        return (self.r[idx] * w).sum(-1) / w.sum(-1)

    def sdf(self, P):
        v = P - self.c
        n = np.linalg.norm(v, axis=-1)
        return n - self.radius(v / np.maximum(n, 1e-9)[..., None])

    def normal(self, P, e=2e-4):
        g = np.stack([(self.sdf(P + e * np.eye(3)[k]) - self.sdf(P - e * np.eye(3)[k])) / (2 * e)
                      for k in range(3)], -1)
        return g / np.linalg.norm(g, axis=-1, keepdims=True)


# ---------------------------------------------------------------- cameras

class Cam:
    def __init__(self, v):
        self.v = v
        self.R = R.from_rotvec(v["rotvec_world_to_cam"]).as_matrix()
        self.pos = np.array(v["camera_position_m"])
        self.f = v["focal_px"]
        self.w, self.h = v["size"]

    def project(self, X):
        Xc = (np.asarray(X) - self.pos) @ self.R.T
        return np.stack([self.f * Xc[..., 0] / Xc[..., 2] + self.w / 2,
                         self.f * Xc[..., 1] / Xc[..., 2] + self.h / 2], -1)

    def ray(self, px):
        d = np.array([(px[0] - self.w / 2) / self.f, (px[1] - self.h / 2) / self.f, 1.0]) @ self.R
        return d / np.linalg.norm(d)

    def hit(self, body, px):
        """First point where the ray through pixel px meets the body."""
        d = self.ray(px)
        ts = np.arange(0.05, 1.5, 0.0005)
        s = body.sdf(self.pos + ts[:, None] * d)
        k = np.argmax(s < 0)
        if s[k] >= 0:
            return None
        lo, hi = ts[k - 1], ts[k]
        for _ in range(30):
            mid = (lo + hi) / 2
            if body.sdf((self.pos + mid * d)[None])[0] < 0:
                hi = mid
            else:
                lo = mid
        return self.pos + hi * d


def body_silhouette(body, cam):
    P = cam.project(body.V)
    tri = np.round(P[body.F]).astype(np.int32)
    m = np.zeros((int(cam.h), int(cam.w)), np.uint8)
    cv2.fillPoly(m, list(tri), 1)
    # thousands of sub-pixel triangles leave pinholes between them; close
    # them and fill any enclosed gaps so the silhouette is solid
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    ff = m.copy()
    cv2.floodFill(ff, np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8), (0, 0), 1)
    return (m | (1 - ff)) > 0


def mask(name, image):
    stem = Path(image).stem
    p = CP1 / "masks" / (f"sheet_{stem}.outline.png" if name.startswith("sheet_") else f"{stem}.outline.png")
    return np.asarray(Image.open(p)) > 0


# ---------------------------------------------------------------- shapes

def ellipsoid_frame(axis, front):
    """Orthonormal frame: e0 along axis (length), e2 ~ front (thickness)."""
    e0 = axis / np.linalg.norm(axis)
    e2 = front - e0 * (front @ e0)
    e2 /= np.linalg.norm(e2)
    e1 = np.cross(e2, e0)
    return np.stack([e0, e1, e2])


def ellipsoid_points(centre, frame, radii, n=24):
    u, v = np.meshgrid(np.linspace(0, np.pi, n), np.linspace(0, 2 * np.pi, 2 * n))
    loc = np.stack([np.cos(u), np.sin(u) * np.cos(v), np.sin(u) * np.sin(v)], -1).reshape(-1, 3)
    return centre + (loc * radii) @ frame


def ellipsoid_sdf(P, centre, frame, radii, e=2.0):
    """e = 2: ellipsoid; larger e: squarer, rounded-box-like (superellipsoid)."""
    q = np.abs(((P - centre) @ frame.T) / radii)
    return ((q ** e).sum(-1) ** (1 / e) - 1) * radii.min()


def superellipsoid_points(centre, frame, radii, e, n=24):
    u, v = np.meshgrid(np.linspace(-np.pi / 2, np.pi / 2, n), np.linspace(-np.pi, np.pi, 2 * n))
    f = lambda w: np.sign(w) * np.abs(w) ** (2 / e)  # noqa: E731
    loc = np.stack([f(np.sin(u)), f(np.cos(u)) * f(np.cos(v)), f(np.cos(u)) * f(np.sin(v))], -1).reshape(-1, 3)
    return centre + (loc * radii) @ frame


def fill_hull(img_shape, P2):
    m = np.zeros(img_shape, np.uint8)
    hull = cv2.convexHull(np.round(P2).astype(np.int32))
    cv2.fillConvexPoly(m, hull, 1)
    return m > 0


def iou_in(zone, a, b):
    return ((a & b & zone).sum()) / max(1, ((a | b) & zone).sum())


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


# ---------------------------------------------------------------- features

def fit_eyes(body, master):
    """Eyeballs as anatomy, from the face solve and face pass: each sits in a
    socket carved into his head, looking out along its solved direction
    (about 55 deg to the side), cornea standing ~3 mm proud of the lid line.
    Sizes come from the master (see refine_face.py). Reports how the visible
    part of each eye compares with the dark of the eye in the master."""
    shape = json.loads((CP3 / "face_shape.json").read_text())
    eyes = {}
    for side in ("R", "L"):
        e = shape["eyes"][side]
        c = np.array(e["eyeball_centre"])
        re = e["eyeball_radius_m"]
        pts = ellipsoid_points(c, np.eye(3), np.array([re] * 3), 60)
        # visible: outside the head, and facing the master camera
        vis = pts[(body.sdf(pts) > 0) & (np.einsum("ij,ij->i", pts - c, master.pos - pts) > 0)]
        uv = master.project(vis) if len(vis) else np.zeros((1, 2))
        bx = np.array([uv[:, 0].min(), uv[:, 1].min(), uv[:, 0].max(), uv[:, 1].max()])
        err = float(np.sqrt(np.mean((bx - np.array(EYE_BOX[side])) ** 2)))
        eyes[side] = dict(e, centre=c.tolist(), radius_m=re, box_px=bx.round(1).tolist(), box_error_px=err)
        print(f"eye {side}: radius {re * 1000:.1f} mm, lid opening {e['rim_radius_m'] * 2000:.1f} mm across, "
              f"cornea {e['proud_m'] * 1000:.1f} mm proud; visible part vs master: box {bx.round(0).tolist()} "
              f"vs {list(EYE_BOX[side])} ({err:.1f} px)", flush=True)
    return eyes


def fit_ears(body, cams, masks):
    """Each ear is fitted to exactly the part of the outline the body leaves
    uncovered above his head on that side, in the master and the edited back
    views (the sheet photos show his ears larger and differently placed)."""
    views = {"master_front_standing": 10.0, "edited_back": 3.0, "edited_back_3q_left_high": 3.0}
    sils = {k: body_silhouette(body, cams[k]) for k in views}
    master = cams["master_front_standing"]
    P = master.project(body.V)
    ears = {}
    for side, sgn in (("R", 1), ("L", -1)):
        near = np.linalg.norm(P - np.array(EAR_BASE_PX[side]), axis=1) < 25
        base0 = body.V[near][np.argmax(body.V[near][:, 2])]
        targets, cares = {}, {}
        for k in views:
            cam = cams[k]
            b = cam.project(base0)
            hgt, wid = sils[k].shape
            yy, xx = np.mgrid[0:hgt, 0:wid]
            # this ear's half of the head top: above the base, on its side
            other = cam.project(base0 * np.array([-1, 1, 1]))
            mid = (b[0] + other[0]) / 2
            side_px = (xx - mid) * np.sign(b[0] - mid) > 0
            rad = cam.f * 0.05 / np.linalg.norm(base0 - cam.pos)
            region = side_px & (np.hypot(xx - b[0], yy - b[1]) < rad) & (yy < b[1] + 0.3 * rad)
            targets[k] = masks[k] & ~sils[k] & region
            cares[k] = region & ~sils[k]

        def build(p):
            out_t, back_t, yaw, L, W, T, dy, ex = p
            base = base0 + np.array([0, dy, 0])
            axis = np.array([sgn * np.sin(out_t), -np.sin(back_t), np.cos(out_t) * np.cos(back_t)])
            front = R.from_rotvec(axis / np.linalg.norm(axis) * yaw).apply(np.array([0, 1.0, 0]))
            fr = ellipsoid_frame(axis, front)
            radii = np.array([L, W, T])
            return base + fr[0] * L * 0.55, fr, radii, ex

        def err(p):
            if not (0.006 < p[3] < 0.035 and 0.005 < p[4] < 0.025 and 0.0015 < p[5] < 0.006
                    and abs(p[6]) < 0.02 and 2.0 <= p[7] <= 4.0):
                return 10.0
            pts = superellipsoid_points(*build(p), 20)
            e = 0
            for k, w in views.items():
                ear = fill_hull(sils[k].shape, cams[k].project(pts)) & cares[k]
                e += w * (1 - iou_in(cares[k], ear, targets[k]))
            return e / sum(views.values())

        best = None
        for ot in (0.1, 0.35, 0.6):
            for bt in (-0.2, 0.15, 0.5):
                for L in (0.012, 0.02):
                    p = np.array([ot, bt, 0.0, L, 0.012, 0.003, 0.0, 2.6])
                    e = err(p)
                    if best is None or e < best[0]:
                        best = (e, p)
        r = minimize(err, best[1], method="Powell", options={"maxfev": 2500, "xtol": 1e-4, "ftol": 1e-5})
        centre, fr, radii, ex = build(r.x)
        ears[side] = {"centre": centre.tolist(), "frame": fr.tolist(), "radii_m": radii.tolist(), "squareness": float(ex),
                      "params": r.x.tolist(), "target_agreement": float(1 - r.fun)}
        print(f"ear {side}: length {radii[0] * 2000:.0f} mm, width {radii[1] * 2000:.0f} mm, "
              f"thick {radii[2] * 2000:.1f} mm, agreement with uncovered ear outline {(1 - r.fun) * 100:.1f}%",
              flush=True)
    return ears


SKIRT_LIFT = 0.0     # the body keeps tracing the master's bottom; pads sit inside it
FRONT_PEET_RADII = (0.0155, 0.020, 0.0105)  # half width / length / height (m)
BACK_PEET_RADII = (0.0150, 0.025, 0.0110)


def place_peets(body, cams):
    """Peets are placed by direct measurement, not fitted. The camera sits a
    little above him, so the front of his skirt projects lower in the master
    than the floor contact behind it: the master's bottom outline is mostly
    traced by the body itself and can't say where pads go. So:
      front pads  under the master's two peet bumps (ray hit), sized from
                  their width and height in the master
      back pads   where the bottom-up photo shows the back pads
    and the skirt is trimmed SKIRT_LIFT above the floor so the pads are what
    touches down and the notch between the front peets reads."""
    master, bottom = cams["master_front_standing"], cams["sheet_10_bottom_up"]
    zmin = body.V[:, 2].min()
    lm = json.loads((ROOT / "references/landmarks.json").read_text())["views"]["sheet_10_bottom_up"]["points"]
    peets = {}
    fr = np.array(FRONT_PEET_RADII)
    hits = {s: master.hit(body, FRONT_PEET_PX[s]) for s in ("R", "L")}
    fx = (abs(hits["R"][0]) + abs(hits["L"][0])) / 2
    fy = (hits["R"][1] + hits["L"][1]) / 2 - fr[1] * 0.9   # mostly under the skirt
    for s, sgn in (("R", 1), ("L", -1)):
        peets[f"front_{s}"] = {"centre": [sgn * fx, fy, zmin + fr[2]], "radii_m": fr.tolist()}
    br = np.array(BACK_PEET_RADII)
    zb = zmin + br[2]
    pts = []
    for s in ("R", "L"):
        d = bottom.ray(lm[f"peet_B{s}"])
        t = (zb - bottom.pos[2]) / d[2]
        pts.append(bottom.pos + t * d)
    bx = (abs(pts[0][0]) + abs(pts[1][0])) / 2
    by = (pts[0][1] + pts[1][1]) / 2
    for s, sgn in (("R", 1), ("L", -1)):
        peets[f"back_{s}"] = {"centre": [sgn * bx, by, zb], "radii_m": br.tolist()}
    # How far under the skirt each pair sits, and how tall it is, from the
    # bottom of the master (front pair) and the edited back (back pair):
    # body + pads must match that view's outline along its bottom.
    def tuck(name_pair, view, direction):
        cam = cams[view]
        sil = body_silhouette(body, cam)
        m = mask(view, cam.v["image"])
        ys = np.nonzero(m.any(1))[0]
        zone = np.zeros_like(m)
        zone[int(ys.max() - 0.25 * (ys.max() - ys.min())):] = True
        best = None
        for dy in np.linspace(0, 0.02, 11):  # pads stay under the visible bumps
            for hz in np.linspace(0.006, 0.013, 8):
                u = sil.copy()
                for nm in name_pair:
                    c = np.array(peets[nm]["centre"]) + np.array([0, direction * dy, 0])
                    c[2] = zmin + hz
                    rad = np.array(peets[nm]["radii_m"])
                    rad[2] = hz
                    u |= fill_hull(u.shape, cam.project(ellipsoid_points(c, np.eye(3), rad, 16)))
                sc = iou_in(zone, u, m)
                if best is None or sc > best[0]:
                    best = (sc, dy, hz)
        for nm in name_pair:
            peets[nm]["centre"][1] += direction * best[1]
            peets[nm]["centre"][2] = zmin + best[2]
            peets[nm]["radii_m"][2] = best[2]
        print(f"  {name_pair[0][:-2]} pads: tucked {best[1] * 1000:.0f} mm under the skirt, "
              f"{best[2] * 2000:.0f} mm tall; bottom-edge agreement {best[0] * 100:.1f}%", flush=True)

    tuck(("front_R", "front_L"), "master_front_standing", -1)
    tuck(("back_R", "back_L"), "edited_back", +1)
    # check: where do the front pads land in the bottom-up photo?
    chk = {s: float(np.linalg.norm(bottom.project(np.array(peets[f"front_{s}"]["centre"]))
                                   - np.array(lm[f"peet_F{s}"]))) for s in ("R", "L")}
    print(f"peets: front at x=+-{fx * 100:.1f} y={fy * 100:.1f} cm; back at x=+-{bx * 100:.1f} y={by * 100:.1f} cm; "
          f"front pads vs bottom-up photo: {chk['R']:.0f}/{chk['L']:.0f} px (panel is {bottom.w:.0f} px wide)",
          flush=True)
    return peets, zmin + SKIRT_LIFT


def nose_and_grooves(body, master):
    S = master.hit(body, NOSE_PX)
    n = body.normal(S[None])[0]
    # a soft, flat pad: about 1 mm proud of the fur line
    pad = {"centre": (S - n * 0.0025).tolist(), "radii_m": [0.0035, 0.0095, 0.0080], "normal": n.tolist()}
    lines = []
    # grooves are capsules 1.0 mm in radius centred 0.75 mm outside the
    # surface: about 0.25 mm deep and 1.4 mm wide, blended softly. In the
    # master these lines are gentle shading, not cuts; colour (pink nose,
    # dark lip line) carries most of them and comes with the materials.
    def out(h):
        return h + body.normal(h[None])[0] * 0.00085
    for poly in GROOVES:
        pts = []
        for a, b in zip(poly[:-1], poly[1:]):
            for t in np.linspace(0, 1, 12, endpoint=False):
                px = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                h = master.hit(body, px)
                if h is not None:
                    pts.append(out(h))
        h = master.hit(body, poly[-1])
        if h is not None:
            pts.append(out(h))
        lines.append(np.array(pts).tolist())
    return pad, lines


# ---------------------------------------------------------------- assemble

def capsule_sdf(P, a, b, r):
    pa, ba = P - a, b - a
    h = np.clip((pa @ ba) / (ba @ ba), 0, 1)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - r


def assemble(body, ears, peets, pad, lines, eyes, skirt_z):
    lo = body.V.min(0) - 0.03
    hi = body.V.max(0) + 0.03
    lo[2] = body.V[:, 2].min() - 0.004
    axes = [np.arange(lo[k], hi[k], H) for k in range(3)]
    shape = tuple(len(a) for a in axes)
    print("grid", shape, flush=True)
    sdf = np.empty(shape, np.float32)
    zz, yy = np.meshgrid(axes[2], axes[1], indexing="ij")
    pad_frame = ellipsoid_frame(np.array(pad["normal"]), np.array([0, 0, 1.0]))
    for i, x in enumerate(axes[0]):
        P = np.stack([np.full_like(yy, x), yy, zz], -1).transpose(1, 0, 2).reshape(-1, 3)
        d = body.sdf(P) if SKIRT_LIFT == 0 else smax(body.sdf(P), skirt_z - P[:, 2], 0.005)
        for e in ears.values():
            d = smin(d, ellipsoid_sdf(P, np.array(e["centre"]), np.array(e["frame"]), np.array(e["radii_m"]),
                                      e["squareness"]), 0.004)
        for p in peets.values():
            d = smin(d, ellipsoid_sdf(P, np.array(p["centre"]), np.eye(3), np.array(p["radii_m"])), 0.006)
        d = smin(d, ellipsoid_sdf(P, np.array(pad["centre"]), pad_frame, np.array(pad["radii_m"])), 0.003)
        for e in eyes.values():
            c, re = np.array(e["centre"]), e["radius_m"]
            # socket: the fur surface wraps snugly onto the eyeball (no gap,
            # no raised rim: a ring read as goggles); the lid line is the
            # soft crease where fur meets eye, which the face pass shapes
            d = smax(d, -(np.linalg.norm(P - c, axis=1) - re - 0.0001), 0.0004)
        for line in lines:
            L = np.array(line)
            g = np.full(len(P), 1.0)
            for a, b in zip(L[:-1], L[1:]):
                g = np.minimum(g, capsule_sdf(P, a, b, 0.0010))
            d = smax(d, -g, 0.0012)
        sdf[i] = d.reshape(len(axes[1]), len(axes[2]))
    verts, faces, _, _ = measure.marching_cubes(sdf, 0.0, spacing=(H, H, H))
    verts += lo
    return verts, faces


def write_obj(path, verts, faces, header):
    with open(path, "w") as fh:
        fh.write(f"# {header}\n")
        for p in verts:
            fh.write(f"v {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
        for t in faces + 1:
            fh.write(f"f {t[0]} {t[1]} {t[2]}\n")


def eyeball_mesh(c, r, n=48):
    u, v = np.meshgrid(np.linspace(0, np.pi, n), np.linspace(0, 2 * np.pi, 2 * n, endpoint=False), indexing="ij")
    P = np.stack([np.sin(u) * np.cos(v), np.sin(u) * np.sin(v), np.cos(u)], -1).reshape(-1, 3) * r + c
    faces = []
    m = 2 * n
    for i in range(n - 1):
        for j in range(m):
            a, b, c2, d = i * m + j, i * m + (j + 1) % m, (i + 1) * m + j, (i + 1) * m + (j + 1) % m
            faces += [(a, c2, b), (b, c2, d)]
    return P, np.array(faces)


def main():
    body = Body()
    cj = json.loads((CP2 / "cameras_fit.json").read_text())
    cams = {k: Cam(v) for k, v in cj["views"].items()}
    masks = {k: mask(k, v["image"]) for k, v in cj["views"].items()}
    master = cams["master_front_standing"]

    eyes = fit_eyes(body, master)
    pad, lines = nose_and_grooves(body, master)
    ears = fit_ears(body, cams, masks)
    peets, skirt_z = place_peets(body, cams)

    verts, faces = assemble(body, ears, peets, pad, lines, eyes, skirt_z)
    write_obj(CP3 / "prince_cp3_head_body.obj", verts, faces,
              "Prince - Checkpoint 3 grey form: body, ears, peets, nose (metres; +x his right, +y fwd, +z up)")
    for side, e in eyes.items():
        P, Fe = eyeball_mesh(np.array(e["centre"]), e["radius_m"])
        write_obj(CP3 / f"prince_cp3_eye_{side}.obj", P, Fe, f"Prince - eyeball, his {'right' if side == 'R' else 'left'}")
    (CP3 / "features.json").write_text(json.dumps({
        "eyes": eyes, "nose_pad": pad, "grooves_m": lines, "ears": ears, "peets": peets,
        "skirt_bottom_z_m": skirt_z,
        "master_pixels": {"eyes": EYE_PX, "eye_boxes": EYE_BOX, "nose": NOSE_PX, "grooves": GROOVES,
                          "ear_bases": EAR_BASE_PX, "ear_tips": EAR_TIP_PX, "front_peets": FRONT_PEET_PX}},
        indent=1))
    print("mesh", len(verts), "verts", len(faces), "faces")


if __name__ == "__main__":
    main()
