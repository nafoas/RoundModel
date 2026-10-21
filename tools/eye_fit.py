"""Feedback loop for eye placement: render front (master) and right profile,
measure where the dark of each eye lands, nudge the eyeball centres, repeat.
Front fixes left/right and up/down; the profile fixes forward/back (depth).
Prints every iteration; writes the result into sculpt/head_log.json."""
import json, subprocess, sys
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, 'tools')
import sculpt as S

PY = '.venv/bin/python'
MASTER = {'R': (338, 467), 'L': (699, 442)}  # dark centre incl. the eye-ring
PROFILE_R = (815, 460)
m = S.Master()


def run(cmd):
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def blob(img_rgba, box):
    x0, y0, x1, y1 = box
    a = img_rgba[y0:y1, x0:x1]
    d = ((a[..., :3].mean(2) < 45) & (a[..., 3] > 200)).astype(np.uint8)
    n, l, st, c = cv2.connectedComponentsWithStats(d, 8)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, 4]))
    return np.array([c[i][0] + x0, c[i][1] + y0]), st[i, 2:4]


def measure():
    run(f'{PY} tools/sculpt.py sculpt/head_log.json work/sc')
    run(f'{PY} tools/preview.py work/sc/head.obj work/sc/ef.png --eyes work/sc/eye_R.obj work/sc/eye_L.obj '
        f'--crop 250 330 830 900 --scale 1 --samples 4 --keep-raw')
    front = np.asarray(Image.open('work/sc/ef.raw.png').convert('RGBA'))
    run(f'{PY} tools/render_clay.py work/sc/head.obj checkpoints/cp2/cameras_fit.json work/efp '
        f'--views sheet_03_right_profile --samples 4 --scale 4.5045 --eyes work/sc/eye_R.obj work/sc/eye_L.obj')
    prof = np.asarray(Image.open('work/efp/sheet_03_right_profile.png').convert('RGBA'))
    out = {}
    for s, (u, v) in MASTER.items():
        out[s] = blob(front, (u - 70, v - 80, u + 70, v + 80))
    p = blob(prof, (PROFILE_R[0] - 31 - 150, PROFILE_R[1] - 150, PROFILE_R[0] - 31 + 150, PROFILE_R[1] + 150))
    out['prof'] = (p[0] + np.array([31.5, 0]), p[1]) if p else None
    return out


def main(iters):
    for it in range(iters):
        L = json.load(open('sculpt/head_log.json'))
        meas = measure()
        msg = []
        for s in ('R', 'L'):
            st = [x for x in L['steps'] if x['op'] == 'eye' and x['side'] == s][0]
            c = np.array(st['front']) - np.array(st['axis']) * st['radius'] if 'centre' not in st else np.array(st['centre'])
            got = meas[s]
            if got is None:
                msg.append(f'{s}: not visible'); continue
            err = np.array(MASTER[s]) - got[0]
            dist = np.linalg.norm(c - m.pos)
            mpp = dist / m.f
            move = (m.R[0] * err[0] + m.R[1] * err[1]) * mpp * 0.8
            if s == 'R' and meas['prof'] is not None:
                perr = PROFILE_R[0] - meas['prof'][0][0]  # + = photo eye further forward
                move += np.array([0, 1.0, 0]) * perr * (0.5 / 4820) * 0.8
            c = c + move
            st['centre'] = c.round(5).tolist()
            msg.append(f'{s}: front at {got[0].round(0)} size {got[1]} (target {MASTER[s]})')
        # mirror depth/height of R onto L's depth so they stay symmetric in depth
        L['steps'] = L['steps']
        json.dump(L, open('sculpt/head_log.json', 'w'), indent=1)
        pr = meas['prof']
        msg.append(f'profile R eye at {pr[0].round(0) if pr else None} size {pr[1] if pr else None} (target {PROFILE_R}, ~100 px)')
        print(f'iter {it}: ' + ' | '.join(msg), flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]))
