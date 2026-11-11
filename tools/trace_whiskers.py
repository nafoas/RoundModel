"""Whisker step, part 1: the whiskers out past his fur (owner order: wisps, then
whiskers, last). Builds on tools/trace_wisps.py.

1. Every whisker is re-traced with wisps.retrace_whisker: it follows its own
   ridge even with other hairs alongside (up to 3 fitted side by side) and
   coasts straight through crossings (<= 8 px).
2. Shared roots: several whiskers can grow from one spot and lie on top of each
   other near the root (measured: the line carries 2-3 whiskers' worth of
   darkness). A whisker whose root end runs into another whisker's line
   (<= MERGE_DIST px, <= MERGE_ANGLE deg, dark all the way across the gap)
   continues along that line to the root. In a shared stretch each whisker keeps
   the width/opacity measured where it is on its own.
3. Fine hairs beside whiskers (light, partly see-through) that the wisp pass
   could not separate are traced as their own strands and classified.
4. The pixel accounting (tools/trace_wisps.account) is re-run: 0 unclassified.

Usage: python tools/trace_whiskers.py [--cached]
Colour note (owner): his whiskers are light; 'opacity' is how strongly a hair
shows against the background, not its colour.
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MPath
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import body_outline as bo  # noqa: E402
import trace_wisps as tw  # noqa: E402
import wisps as w  # noqa: E402

MERGE_DIST, MERGE_ANGLE, MERGE_DARK = 7.0, 30.0, 0.5
FINE_MIN_PX = 25          # leftover groups beside whiskers bigger than this are traced
SCRATCH = Path("/tmp/claude-0/-home-user-roundmodel/13cb371e-6a2f-5cfc-b4e2-a0566b0d035f/scratchpad")


def merge_roots(a, whiskers: list[dict], body: np.ndarray) -> list[str]:
    notes = []
    tb = cKDTree(body)
    for t in whiskers:
        cl = t["centreline"]
        # only the ROOT end (the one nearer his body) can continue along another whisker
        root_is_start = tb.query(cl[0])[0] < tb.query(cl[-1])[0]
        for at_start in (root_is_start,):
            p = cl[0] if at_start else cl[-1]
            q = cl[min(12, len(cl) - 1)] if at_start else cl[max(-13, -len(cl))]
            u = (p - q) / (np.linalg.norm(p - q) + 1e-12)          # heading out of this end
            for o in whiskers:
                if o is t:
                    continue
                oc = o["centreline"]
                d, k = cKDTree(oc).query(p)
                if d > MERGE_DIST or k < 8 or k > len(oc) - 8:
                    continue
                v = oc[min(k + 6, len(oc) - 1)] - oc[max(k - 6, 0)]
                v /= np.linalg.norm(v)
                if np.degrees(np.arccos(min(1.0, abs(float(np.dot(u, v)))))) > MERGE_ANGLE:
                    continue
                fwd = 1 if np.dot(u, v) > 0 else -1                # continue the same way along o
                # join a few px further along o, so the bridge can curve in
                kj = int(np.clip(k + fwd * int(2 * d + 4), 0, len(oc) - 1))
                p1 = oc[kj]
                L = float(np.hypot(*(p1 - p)))
                s = np.linspace(0, 1, max(int(L * 4), 4))[:, None]
                t1 = v * fwd
                h = ((2 * s**3 - 3 * s**2 + 1) * p + (s**3 - 2 * s**2 + s) * u * L
                     + (-2 * s**3 + 3 * s**2) * p1 + (s**3 - s**2) * t1 * L)
                dark = float(np.median(w.sample(a, h)))
                if dark < MERGE_DARK:
                    continue
                t["pre_merge"] = cl.copy()
                rest = oc[kj::fwd] if fwd > 0 else oc[kj::-1]
                ext = np.vstack([h[1:], rest[1:]])
                sg = np.full(len(ext), float(np.median(t["sigma"])))
                op = np.full(len(ext), float(np.median(t["opacity"])))
                if at_start:
                    t["centreline"] = np.vstack([ext[::-1], cl])
                    t["sigma"] = np.r_[sg, t["sigma"]]; t["opacity"] = np.r_[op, t["opacity"]]
                else:
                    t["centreline"] = np.vstack([cl, ext])
                    t["sigma"] = np.r_[t["sigma"], sg]; t["opacity"] = np.r_[t["opacity"], op]
                t["length"] = float(np.hypot(*np.diff(t["centreline"], axis=0).T).sum())
                t["shares_root_with"] = o["id"]
                notes.append(f"{t['id']} continues along {o['id']} to the root from {np.round(p, 1).tolist()} "
                             f"(gap {d:.1f} px, darkness across {dark:.2f})")
                break
            if t.get("shares_root_with"):
                break
    # in a shared stretch, a whisker that is never on its own (its measured
    # opacity there is the sum of several) gets the values of the whisker it shares with
    for t in whiskers:
        for o in whiskers:
            if o.get("shares_root_with") == t["id"] and float(np.median(t["opacity"])) > float(np.median(o["opacity"])) * 1.3:
                t["opacity_note"] = f"opacity measured where it lies on {o['id']}; true value inferred"
    return notes


def separate_shared(a, whiskers: list[dict]) -> list[str]:
    """Where 2-3 whiskers share one root line, fit the photo's cross profile as
    exactly that many whiskers (each with the width/opacity measured where it is
    on its own; only their sideways positions free), so each whisker gets its own
    centre line through the shared stretch."""
    from scipy.optimize import least_squares
    from scipy.ndimage import gaussian_filter1d
    notes = []
    by_id = {t["id"]: t for t in whiskers}
    for base in whiskers:
        members = [t for t in whiskers if t.get("shares_root_with") == base["id"]]
        if not members:
            continue
        group = [base] + members
        bl = w.resample(base["centreline"], 1.0)
        tan = np.gradient(bl, axis=0); tan /= np.linalg.norm(tan, axis=1)[:, None]
        nrm = np.c_[-tan[:, 1], tan[:, 0]]
        trees = {t["id"]: cKDTree(t["centreline"]) for t in group}
        present = np.array([[trees[t["id"]].query(p)[0] < 0.6 for t in group] for p in bl])
        # own (free) width/opacity: where a whisker is not within 1 px of any other group member
        own = {}
        for t in group:
            others = [trees[o["id"]] for o in group if o is not t]
            d = np.min([o.query(t["centreline"])[0] for o in others], axis=0)
            free = d > 1.0
            src = t if free.sum() >= 5 else None
            own[t["id"]] = ((float(np.median(t["sigma"][free])), float(np.median(t["opacity"][free])))
                            if src is not None else None)
        fallback = next(v for v in own.values() if v is not None)
        for k_ in own:
            if own[k_] is None:
                own[k_] = fallback
                by_id[k_]["opacity_note"] = "never on its own: width/opacity taken from the whisker it lies on"
        # side each member approaches from (signed offset of its free part just before it joins)
        side = {}
        for t in group:
            cl = t["centreline"]
            d0, k0 = cKDTree(bl).query(cl)
            free_pts = np.where(d0 > 1.0)[0]
            if len(free_pts) == 0 or t is base:
                side[t["id"]] = 0.0
                continue
            j = free_pts[np.argmin(d0[free_pts])]
            side[t["id"]] = float(np.dot(cl[j] - bl[k0[j]], nrm[k0[j]]))
        s_ax = np.arange(-6, 6.001, 0.25)
        offs = {t["id"]: np.full(len(bl), np.nan) for t in group}
        for i, p in enumerate(bl):
            idx = [g for g, on in enumerate(present[i]) if on]
            if len(idx) < 2:
                continue
            mem = [group[g] for g in idx]
            f = w.sample(a, p[None, :] + s_ax[:, None] * nrm[i][None, :])
            sg = [own[t["id"]][0] for t in mem]; A = [own[t["id"]][1] for t in mem]

            def model(q):
                inv = np.ones_like(s_ax)
                for c, sgi, Ai in zip(q[1:], sg, A):
                    inv *= 1 - Ai * np.exp(-((s_ax - c) ** 2) / (2 * sgi * sgi))
                return q[0] + (1 - q[0]) * (1 - inv)
            c0 = np.linspace(-0.6, 0.6, len(mem)) if len(mem) > 1 else np.zeros(1)
            r = least_squares(lambda q: model(q) - f, np.r_[0.0, c0],
                              bounds=([-0.05] + [-2.5] * len(mem), [0.6] + [2.5] * len(mem)))
            # fixed order across the band for the whole stretch (no crossings): whiskers
            # arriving from one side stay outermost on that side; whiskers arriving in
            # line with the base (|side| < 0.5 px) keep a fixed order between them
            key = lambda t: (0.0 if abs(side[t["id"]]) < 0.5 else side[t["id"]], t["id"])
            for t, c in zip(sorted(mem, key=key), np.sort(r.x[1:])):
                offs[t["id"]][i] = c
        for t in group:
            o = offs[t["id"]]
            ok = ~np.isnan(o)
            if ok.sum() < 3:
                continue
            o_s = o.copy()
            o_s[ok] = gaussian_filter1d(o[ok], 3.0, mode="nearest")
            shared_pts = bl[ok] + nrm[ok] * o_s[ok][:, None]
            # replace this whisker's points on the shared stretch with its own line
            cl = t.get("pre_merge", t["centreline"])
            d, _ = cKDTree(bl[ok]).query(cl)
            keep = d >= 1.0
            new = np.vstack([cl[keep], shared_pts])
            # order along the whisker: by projection on its overall direction
            ax = cl[-1] - cl[0]; ax /= np.linalg.norm(ax)
            order = np.argsort(new @ ax)
            new = new[order]
            t["centreline"] = w.smooth_centreline(w.resample(new, 0.5), rms=0.1)
            n = len(t["centreline"])
            t["sigma"] = np.full(n, own[t["id"]][0]); t["opacity"] = np.full(n, own[t["id"]][1])
            t["length"] = float(np.hypot(*np.diff(t["centreline"], axis=0).T).sum())
            notes.append(f"{t['id']}: own line through the shared stretch, offset from the base line "
                         f"{np.nanmin(o_s):+.2f}..{np.nanmax(o_s):+.2f} px")
    return notes


def fine_hairs(a, inb, ino, inf, strands, outer):
    """Trace leftover groups beside whiskers as their own strands."""
    cls, _ = tw.account(a, inb, ino, inf, strands, outer)
    owned = np.zeros(a.shape, bool)
    for t in strands:
        cl, sg = t["centreline"], t["sigma"]
        x0 = max(0, int(cl[:, 0].min() - 6)); x1 = min(a.shape[1], int(cl[:, 0].max() + 7))
        y0 = max(0, int(cl[:, 1].min() - 6)); y1 = min(a.shape[0], int(cl[:, 1].max() + 7))
        X, Y = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d, j = cKDTree(cl).query(np.c_[X.ravel(), Y.ravel()])
        owned[y0:y1, x0:x1] |= (d <= tw.FOOT_K * sg[j] + tw.FOOT_PAD).reshape(X.shape)
    extra = (cls == "whisker (last step)") & ~owned & (a > tw.PIECE_COV)
    lab, n = ndi.label(extra, structure=np.ones((3, 3), int))
    new = []
    for k in range(1, n + 1):
        m = lab == k
        if m.sum() < FINE_MIN_PX:
            continue
        for seed in w.skeleton_paths(m):
            t = w.trace(a, seed[::2] if len(seed) > 6 else seed)
            if t is None:
                continue
            ys, xs = np.nonzero(m)
            t.update(piece=-k, batch="W", reach=99.0, straight=w.straightness(t["centreline"]))
            new.append(t)
    return new


def main() -> int:
    cache = SCRATCH / "trace_cache.pkl"
    if "--cached" in sys.argv and cache.exists():
        rgb, a, body, outer, inb, ino, inf, strands, refused = pickle.loads(cache.read_bytes())
    else:
        rgb, a, body, outer, inb, ino, inf, strands, refused = tw.run()
    strands = tw.postprocess(strands)
    bp = MPath(body)
    whiskers = [t for t in strands if t["cls"] == "whisker (last step)"]
    for t in whiskers:
        r = w.retrace_whisker(a, t["centreline"], lambda q: bp.contains_point(q))
        t.update(centreline=r["centreline"], sigma=r["sigma"], opacity=r["opacity"], length=r["length"],
                 coasted_px=r["coasted_px"], extended_px=r["extended_px"])
    notes = merge_roots(a, whiskers, body)
    notes += separate_shared(a, whiskers)
    fine = fine_hairs(a, inb, ino, inf, strands, outer)
    for t in fine:
        t["cls"] = w.classify(t, bo.EYE_BOXES)
    fine = [t for t in fine if t["cls"] != "not a hair (blob)"]
    for i, t in enumerate(fine, 1):
        t["id"] = f"W-F{i:02d}"
    strands = strands + fine
    cls, counts = tw.account(a, inb, ino, inf, strands, outer)
    tw.save(rgb, a, body, outer, inb, ino, inf, strands, refused, cls, counts)
    (SCRATCH / "whisker_strands.pkl").write_bytes(pickle.dumps(strands))
    for nmsg in notes:
        print("shared root:", nmsg)
    print("fine hairs beside whiskers:", [(t["id"], t["cls"], round(t["length"], 1)) for t in fine])
    print("whiskers:", len(whiskers), "| coasted px total:", round(sum(t.get("coasted_px", 0) for t in whiskers), 1))
    print("pixels by class (outside the body):", counts)
    return 0 if counts["unclassified"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
