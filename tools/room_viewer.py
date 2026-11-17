"""An interactive 3D view of Prince's room: one self-contained HTML file (no internet needed).

Shows the room (floor grid, the room's axes at the origin), the anchor camera with the photo on its picture
plane, and the rays through his outline (coloured by part) and through every landmark. Drag to orbit, wheel or
pinch to zoom, right-drag or two fingers to move. "Camera's view" puts your eye exactly where the shown camera
was: every ray then shrinks to a point on the photo (each pixel IS one ray).

Also shows his surface as each depth model measured it (tools/visible_depth.py): every ray of him from that
model's OWN camera, cut at its measured distance, each point coloured as the photo. Nothing invented.

Reads data/cameras.json, data/scene/anchor_rays.json (python tools/scene.py first) and
data/scene/visible_depth_*.json (python tools/visible_depth.py).
Uses three.js r159 (MIT licence, tools/vendor/three-LICENSE.txt), inlined.

Usage: python tools/room_viewer.py -> docs/space/room.html
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/space/room.html"
RAY_EVERY = 3                      # every 3rd outline point (outline points are 2 px apart); every 3rd cut ray drawn
VIS_STEP = 4                       # his surface as measured: one point every 4 photo pixels
REACH_PAST_CM = 16.0

COLOURS = {"head": "#eb8c1e", "intermediate bnuy": "#3ca0e6", "undercarriage": "#8c5ae6", "ears": "#46be5a",
           "top of his head (strip joining his ears)": "#148c3c", "cream peet (his right)": "#dc3232",
           "gray peet (his left)": "#c8aa00", "belly (underfluff tuft)": "#009696"}


def main() -> int:
    cam = json.loads((ROOT / "data/cameras.json").read_text())["anchor_front"]
    rays = json.loads((ROOT / "data/scene/anchor_rays.json").read_text())
    C = np.array(cam["position_cm"]); L = float(np.linalg.norm(C)) + REACH_PAST_CM

    def ends(dirs):
        d = np.array(dirs); t = np.full(len(d), L)
        down = d[:, 1] < -1e-9
        t[down] = np.minimum(t[down], -C[1] / d[down, 1])
        return np.round(C + d * t[:, None], 3).tolist()

    out = next(s for s in rays["sets"] if s["name"] == "his outline")
    idx = list(range(0, len(out["directions_room"]), RAY_EVERY))
    outline = dict(ends=ends([out["directions_room"][i] for i in idx]),
                   colours=[COLOURS.get(out["part_per_point"][i], "#888888") for i in idx])
    lines = [dict(name=s["name"], ends=ends(s["directions_room"])) for s in rays["sets"] if s["name"] != "his outline"]
    lms = [dict(name=s["name"], part=s["part"], kind=s["kind"], end=ends(s["directions_room"])[0]) for s in rays["landmarks"]]
    visible = []                                         # each model's surface, from its own camera (tools/visible_depth.py)
    rgb_full = np.array(Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB"))
    import visible_depth as vd
    tagged = ("eye_his_right", "eye_his_left", "nose_y_centre", "crown_front", "ear_tip_his_right", "ear_tip_his_left",
              "chin_midline", "peet_bottom_his_right", "peet_bottom_his_left")
    for name, colour in (("depthpro", "#e67e22"), ("moge2", "#2e86de")):
        if not (ROOT / f"data/scene/visible_depth_{name}.json").exists():
            continue
        vcam, P, meta = vd.room_points(name)
        pl = meta["placed_in_the_room"]
        H, W = P.shape[:2]
        inner = vd.inside_band(vd.him_mask(H, W))
        ys, xs = np.mgrid[0:H:VIS_STEP, 0:W:VIS_STEP]
        ys, xs = ys.ravel(), xs.ravel(); keep = np.isfinite(P[ys, xs, 0]); ys, xs = ys[keep], xs[keep]
        band = ~inner[ys, xs]
        pts, cols = P[ys, xs], rgb_full[ys, xs] / 255.0
        cd = pl["camera"]
        visible.append(dict(
            name=name, label=vd.NAMES[name], colour=colour,
            camera=dict(C=cd["position_cm"], R=cd["rotation_room_to_camera"], f=cd["focal_px"],
                        cx=cd["principal_point_px"][0], cy=cd["principal_point_px"][1], W=cd["image_size_px"][0],
                        H=cd["image_size_px"][1]),
            p=np.round(pts[~band], 3).ravel().tolist(), c=np.round(cols[~band], 3).ravel().tolist(),
            pe=np.round(pts[band], 3).ravel().tolist(), ce=np.round(cols[band], 3).ravel().tolist(),
            rays=np.round(pts[~band][::60], 3).tolist(),
            tags=[[k.replace("_", " "), pl["landmarks_room_cm"][k]] for k in tagged],
            report=dict(nose=pl["camera_to_nose_cm"], height=pl["camera_height_cm"], top=pl["top_of_head_cm"],
                        eyes=round((pl["eye_heights_cm"]["his_left"] + pl["eye_heights_cm"]["his_right"]) / 2, 1),
                        nosey=pl["nose_height_cm"], ears=pl["ear_tips_cm"], scale=pl["scale_means"])))
    facing = None
    import re as _re
    cam_d = float(_re.search(r"camera to his nose ([0-9.]+) cm", cam["inputs"]["distance"]).group(1))
    fpath = ROOT / "data/scene/facing.json"
    if fpath.exists():                                   # how he is turned (tools/facing.py), drawn where he is
        fd = json.loads(fpath.read_text())
        lmk = {s["name"]: np.array(s["directions_room"][0]) for s in rays["landmarks"]}
        eyes_dir = lmk["eye_his_left"] + lmk["eye_his_right"]; eyes_dir /= np.linalg.norm(eyes_dir)
        E = C + eyes_dir * (cam_d + 2.0)                 # his eyes ~2 cm behind his nose (approximate)
        Xh = np.array(fd["head"]["left_right_axis_room"]); up = np.array([0.0, 1.0, 0.0])
        Yh = up - (up @ Xh) * Xh; Yh /= np.linalg.norm(Yh); Zh = np.cross(Xh, Yh)
        Pb = np.array(fd["body"]["peets_on_the_surface_cm"]); Xb = Pb[0] - Pb[1]; Xb /= np.linalg.norm(Xb)
        Zb = np.cross(Xb, up); mb = Pb.mean(0)
        facing = dict(head=[(E - 2.5 * Xh).tolist(), (E + 2.5 * Xh).tolist(), E.tolist(), (E + 3.5 * Zh).tolist()],
                      body=[Pb[1].tolist(), Pb[0].tolist(), mb.tolist(), (mb + 3.5 * Zb).tolist()],
                      text=fd["summary"]["tipped"] + "; turned " + fd["summary"]["turned"].split(":")[0])
    buf = io.BytesIO()
    Image.open(ROOT / "data/photos/anchor_front.webp").convert("RGB").save(buf, "JPEG", quality=88)
    data = dict(camera=dict(C=C.tolist(), R=cam["rotation_room_to_camera"], f=cam["focal_px"],
                            cx=cam["principal_point_px"][0], cy=cam["principal_point_px"][1],
                            W=cam["image_size_px"][0], H=cam["image_size_px"][1], status=cam["status"]),
                outline=outline, lines=lines, landmarks=lms, facing=facing, visible=visible,
                photo="data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
    three = (ROOT / "tools/vendor/three-0.159.0.min.js").read_text()
    sz = cam["his_size_estimate_cm"]
    camtext = (f"Placed as first remembered: straight on, about six inches from his nose, level, "
               f"{cam['eyes_above_camera_cm']:.1f} cm below his eyes, his peets assumed right under his face. His size "
               f"from it (rough): about {sz['width']:.1f} cm wide, {sz['top_of_head']:.1f} cm to the top of his head, "
               f"ear tips {sz['ear_tips']:.1f} cm. The depth models place the camera further away (owner: \"Maybe I "
               f"misremembered. Either way I trust them\"). Its outline, landmark and part-line rays and the "
               f"blue/red facing lines were worked out with this camera.")
    html = PAGE.replace("/*THREE*/", three).replace("/*DATA*/", json.dumps(data)).replace("/*CAMTEXT*/", camtext)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print("wrote", OUT.relative_to(ROOT), f"{len(html) / 1e6:.2f} MB;", len(idx), "outline rays,", len(lms), "landmarks")
    return 0


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prince's room: his surface as the photo sees it</title>
<style>
 html,body{margin:0;height:100%;background:#aeb3ba;font:14px system-ui,-apple-system,Segoe UI,sans-serif;color:#222;overflow:hidden}
 #ui{position:absolute;left:10px;top:10px;max-width:min(440px,calc(100% - 20px));max-height:calc(100% - 20px);overflow:auto;
     background:rgba(255,255,255,.93);border:1px solid #ddd;border-radius:8px;padding:10px 12px;line-height:1.35;box-sizing:border-box}
 #ui h1{font-size:15px;margin:0 0 4px} #ui p{margin:4px 0;font-size:12.5px;color:#444}
 #ui button{font:inherit;font-size:12.5px;margin:3px 4px 3px 0;padding:4px 8px;border:1px solid #bbb;border-radius:6px;background:#fff;cursor:pointer}
 #ui label{font-size:12.5px;margin-right:10px;white-space:nowrap} #ui details{font-size:12.5px;margin:6px 0}
 .tag{position:absolute;font-size:11.5px;pointer-events:none;white-space:nowrap;text-shadow:0 0 3px #fff,0 0 3px #fff,0 0 2px #fff}
 .key{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 3px 0 6px;vertical-align:-1px}
 #hide{position:absolute;right:10px;top:10px}
</style></head><body>
<div id="ui">
 <h1>Prince's room: his surface, as this photo sees it</h1>
 <p>Centimetres; floor grid 2 cm. <b>+X</b> his left, <b>+Y</b> up, <b>+Z</b> his forward; origin on the surface he sits on,
 under the middle of his peets.</p>
 <p>Every point is one pixel of him: the ray from the camera through that pixel, cut at the distance a depth model
 measured, coloured as the photo. <b>Nothing invented</b>: no smoothing, no filling, nothing he does not show in this
 photo. Each model keeps its own camera (its own lens and distance). One number per model sets the units so he is
 15.5 cm wide (approved). Up: the camera at his eye level, a tiny bit lower (as remembered). Not a model of him.</p>
 <div id="visUI"></div>
 <p id="visNote" style="color:#333"></p>
 <div><button data-v="behind">Whole room</button><button data-v="cam">Camera's view</button>
 <button data-v="angle">Him, from his left-front</button><button data-v="side">His left side</button><button data-v="top">From above</button></div>
 <div><label><input type="checkbox" id="cBand" checked> his outermost 4 px</label><label><input type="checkbox" id="cRays" checked> some rays</label>
 <label><input type="checkbox" id="cTags" checked> labels</label></div>
 <p style="color:#555">His outermost 4 px blend into the removed background, so their distances are least sure.
 In the camera's view the photo is hidden: what you see is his measured surface, every point on its own pixel.</p>
 <details><summary>The camera as first remembered (six inches)</summary>
  <p>/*CAMTEXT*/</p>
  <div><label><input type="checkbox" id="cRem"> show it</label><label><input type="checkbox" id="cOut"> outline rays</label>
  <label><input type="checkbox" id="cLm"> landmark rays</label><label><input type="checkbox" id="cLines"> part-line rays</label>
  <label><input type="checkbox" id="cFace" checked> how he faces</label></div>
  <p><span class="key" style="background:#eb8c1e"></span>head<span class="key" style="background:#3ca0e6"></span>intermediate
  <span class="key" style="background:#8c5ae6"></span>undercarriage<span class="key" style="background:#46be5a"></span>ears
  <span class="key" style="background:#148c3c"></span>top of head<span class="key" style="background:#dc3232"></span>/<span class="key" style="background:#c8aa00"></span>peets
  <span class="key" style="background:#009696"></span>belly<span class="key" style="background:#555"></span>landmarks</p>
  <p id="faceNote" style="color:#1f4fb4"></p>
 </details>
 <p>Drag: turn around. Wheel / pinch: closer. Right-drag / two fingers: move.</p>
</div>
<button id="hide">hide panel</button>
<script>/*THREE*/</script>
<script>
const D = /*DATA*/;
const V = (a)=>new THREE.Vector3(a[0],a[1],a[2]);
const renderer = new THREE.WebGLRenderer({antialias:true}); renderer.setPixelRatio(Math.min(devicePixelRatio,2));
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xaeb3ba);
const view = new THREE.PerspectiveCamera(45, 1, 0.05, 2000);
// ---- room: floor grid (2 cm, darker every 10 cm) and the room's axes at the origin
const grid = new THREE.GridHelper(100, 50, 0x8a8f96, 0x9ca1a8); scene.add(grid);
const grid10 = new THREE.GridHelper(100, 10, 0x6e737a, 0x6e737a); grid10.position.y = 0.002; scene.add(grid10);
function seg(pts, colour){ return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map(V)), new THREE.LineBasicMaterial({color:colour})); }
scene.add(seg([[0,0,0],[4,0,0]],0xd22828)); scene.add(seg([[0,0,0],[0,4,0]],0x28a028)); scene.add(seg([[0,0,0],[0,0,4]],0x2850dc));
// ---- labels: each belongs to a group and shows only when that group is shown
const tags = []; function tag(text, p, colour, group){ const el=document.createElement('div'); el.className='tag'; el.textContent=text; el.style.color=colour||'#111'; document.body.appendChild(el); tags.push({el,p:p.clone(),group}); }
function shown(o){ for(let x=o; x; x=x.parent){ if(!x.visible) return false; } return true; }
tag('origin', V([0,0,0]), '#111', scene); tag('+X his left', V([4.3,0,0]),'#a01818', scene); tag('+Y up', V([0,4.3,0]),'#186818', scene); tag('+Z his forward', V([0,0,4.3]),'#1830a0', scene);
// ---- a camera: its frustum to a picture plane 4 cm out, the photo on that plane, its height and distance on the floor
const photoPlanes = [];   // hidden in the camera's view, so you see his measured surface, not the photo
const tex = new THREE.TextureLoader().load(D.photo, ()=>draw()); tex.colorSpace = THREE.SRGBColorSpace;
function makeCam(c, colour, name){
  const g = new THREE.Group(), C = V(c.C);
  const right = new THREE.Vector3(...c.R[0]), down = new THREE.Vector3(...c.R[1]), fwd = new THREE.Vector3(...c.R[2]);
  const up = down.clone().negate(), back = fwd.clone().negate(), d0 = 4.0;
  // the picture's own pixels, at depth d0, through the camera's principal point (cx, cy)
  const atPx = (u,v)=>C.clone().addScaledVector(fwd, d0).addScaledVector(right, (u-c.cx)/c.f*d0).addScaledVector(down, (v-c.cy)/c.f*d0);
  const K = [atPx(0,0), atPx(c.W,0), atPx(c.W,c.H), atPx(0,c.H)], mat = new THREE.LineBasicMaterial({color:colour});
  K.forEach(k=>g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([C,k]), mat)));
  g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([...K,K[0]]), mat));
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(c.W/c.f*d0, c.H/c.f*d0), new THREE.MeshBasicMaterial({map:tex, side:THREE.DoubleSide}));
  plane.position.copy(atPx(c.W/2, c.H/2)); plane.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, up, back)); g.add(plane);
  const foot = new THREE.Vector3(C.x,0,C.z);
  g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([C, foot, new THREE.Vector3(0,0,0)]), new THREE.LineBasicMaterial({color:0x000000})));
  scene.add(g);
  tag(name, C.clone().addScaledVector(up,1.0), colour, g); tag(C.y.toFixed(1)+' cm up', C.clone().add(foot).multiplyScalar(0.5), '#111', g);
  tag(Math.hypot(C.x,C.z).toFixed(1)+' cm away', foot.clone().multiplyScalar(0.5), '#111', g);
  photoPlanes.push(plane);
  return {g, c, C, right, down, fwd, up, back};
}
function rayGroup(C, ends, colours, opacity){ const pos=[], col=[]; const tmp=new THREE.Color();
  ends.forEach((e,i)=>{ pos.push(C.x,C.y,C.z,e[0],e[1],e[2]); tmp.set(colours? colours[i] : 0x555555); col.push(tmp.r,tmp.g,tmp.b,tmp.r,tmp.g,tmp.b); });
  const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3)); g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({vertexColors:true, transparent:true, opacity:opacity})); }
function points(p, c, size){ const geo=new THREE.BufferGeometry(); geo.setAttribute('position',new THREE.Float32BufferAttribute(p,3)); geo.setAttribute('color',new THREE.Float32BufferAttribute(c,3));
  return new THREE.Points(geo, new THREE.PointsMaterial({size, vertexColors:true, sizeAttenuation:true})); }
// ---- each depth model: its own camera, his surface (every 4th pixel), its outermost-4-px band, some of its cut rays
const bands = [], rayls = [];
const models = (D.visible||[]).map((v,k)=>{
  const m = makeCam(v.camera, v.colour, v.label + "'s camera");
  m.g.add(points(v.p, v.c, 0.11)); const band = points(v.pe, v.ce, 0.11); m.g.add(band); bands.push(band);
  const rl = rayGroup(m.C, v.rays, v.rays.map(()=>v.colour), 0.3); m.g.add(rl); rayls.push(rl);
  v.tags.forEach(t=>tag(t[0], V(t[1]), '#222', m.g));
  m.g.visible = (k===0); m.v = v;
  const lab=document.createElement('label'); lab.innerHTML=`<input type="checkbox" ${k===0?'checked':''}><span class="key" style="background:${v.colour}"></span>${v.label}`;
  lab.querySelector('input').onchange=e=>{ m.g.visible=e.target.checked; note(); draw(); }; document.getElementById('visUI').appendChild(lab);
  return m; });
function note(){ document.getElementById('visNote').innerHTML = models.filter(m=>m.g.visible).map(m=>{ const r=m.v.report;
  return `<b>${m.v.label}</b>: camera ${r.nose} cm from his nose, ${r.height} cm up (his eyes 0.5 cm above it). Him: 15.5 cm wide, top of his head ${r.top} cm up, eyes ${r.eyes}, nose ${r.nosey}, ear tips ${r.ears[0]} / ${r.ears[1]}.`; }).join('<br>') || 'Tick a model to see his surface.'; }
note();
// ---- the camera as first remembered (six inches), with its outline / landmark / part-line rays and the facing lines
const rem = makeCam(D.camera, '#222222', 'camera as first remembered');
const gOut = rayGroup(rem.C, D.outline.ends, D.outline.colours, 0.75); rem.g.add(gOut); gOut.visible=false;
const gLm = rayGroup(rem.C, D.landmarks.map(l=>l.end), null, 0.9); rem.g.add(gLm); gLm.visible=false;
const gLines = new THREE.Group(); D.lines.forEach(l=>gLines.add(rayGroup(rem.C, l.ends.filter((_,i)=>i%4==0), null, 0.35))); gLines.visible=false; rem.g.add(gLines);
D.landmarks.filter(l=>/^(eye_his_(left|right)|nose_y_centre|ear_tip_his_(left|right)|crown_front|chin_midline|belly_front|peet_bottom_his_(left|right))$/.test(l.name))
  .forEach(l=>tag(l.name.replace(/_/g,' '), V(l.end), '#444', gLm));
const gFace = new THREE.Group();
if (D.facing){ const f=D.facing; const L=(a,b,col)=>gFace.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([V(a),V(b)]), new THREE.LineBasicMaterial({color:col})));
  L(f.head[0],f.head[1],0x1f5adc); L(f.head[2],f.head[3],0x1f5adc); L(f.body[0],f.body[1],0xc81e1e); L(f.body[2],f.body[3],0xc81e1e);
  tag('head faces', V(f.head[3]), '#1f5adc', gFace); tag('body faces', V(f.body[3]), '#c81e1e', gFace);
  document.getElementById('faceNote').textContent = 'Blue: his head (left-right axis, and the way it faces). Red: his body, from his peets. ' + f.text + '.'; }
rem.g.add(gFace); rem.g.visible = false;
// ---- views
function activeCam(){ return models.find(m=>m.g.visible) || (rem.g.visible ? rem : (models[0] || rem)); }
let camNow = activeCam();
const target = new THREE.Vector3(); let yaw=0.42, pitch=0.28, dist=60, mode='orbit';
function placeView(){ if(mode==='cam') return; view.position.set(target.x+dist*Math.sin(yaw)*Math.cos(pitch), target.y+dist*Math.sin(pitch), target.z+dist*Math.cos(yaw)*Math.cos(pitch)); view.up.set(0,1,0); view.lookAt(target); view.fov=45; view.updateProjectionMatrix(); }
const VIEWS = {
  behind:a=>{ target.set(0, 7, a.C.z*0.45); yaw=0.55; pitch=0.3; dist=Math.max(45, a.C.length()*1.7); },
  angle: a=>{ target.set(0, 8, 3); yaw=0.75; pitch=0.22; dist=42; },
  side:  a=>{ target.set(0, 8, 3); yaw=Math.PI/2; pitch=0.0; dist=45; },
  top:   a=>{ target.set(0, 0, 3); yaw=0; pitch=1.5; dist=45; } };
function setView(v){ camNow = activeCam();
  photoPlanes.forEach(p=>p.visible = (v!=='cam'));
  if(v==='cam'){ mode='cam'; view.position.copy(camNow.C); view.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(camNow.right, camNow.up, camNow.back)); camProjection(); }
  else { mode='orbit'; VIEWS[v](camNow); placeView(); } draw(); }
// the shown camera's own lens, with its principal point, the picture fitted to the window's height
function camProjection(){ const c=camNow.c, n=view.near, top=c.cy/c.f*n, bottom=-(c.H-c.cy)/c.f*n, mid=((c.W/2-c.cx)/c.f)*n, half=(top-bottom)*view.aspect/2;
  view.projectionMatrix.makePerspective(mid-half, mid+half, top, bottom, n, view.far); view.projectionMatrixInverse.copy(view.projectionMatrix).invert(); }
document.querySelectorAll('#ui button').forEach(b=>b.onclick=()=>setView(b.dataset.v));
let drag=null; const el=renderer.domElement;
el.addEventListener('contextmenu',e=>e.preventDefault());
el.addEventListener('pointerdown',e=>{ drag={x:e.clientX,y:e.clientY,b:e.button}; el.setPointerCapture(e.pointerId); });
el.addEventListener('pointerup',()=>drag=null);
el.addEventListener('pointermove',e=>{ if(!drag||touches.size>1) return; const dx=e.clientX-drag.x, dy=e.clientY-drag.y; drag.x=e.clientX; drag.y=e.clientY; leaveCam();
  if(drag.b===2||e.shiftKey){ pan(dx,dy); } else { yaw-=dx*0.006; pitch=Math.max(-1.5,Math.min(1.55,pitch+dy*0.006)); } placeView(); draw(); });
function leaveCam(){ if(mode==='cam'){ mode='orbit'; photoPlanes.forEach(p=>p.visible=true); const f=camNow.fwd; target.copy(camNow.C).addScaledVector(f,15); dist=15; yaw=Math.atan2(-f.x,-f.z); pitch=Math.asin(-f.y); } }
function pan(dx,dy){ const r=new THREE.Vector3().setFromMatrixColumn(view.matrix,0), u=new THREE.Vector3().setFromMatrixColumn(view.matrix,1); const s=dist*0.0015; target.addScaledVector(r,-dx*s).addScaledVector(u,dy*s); }
el.addEventListener('wheel',e=>{ e.preventDefault(); leaveCam(); dist=Math.max(3,Math.min(400,dist*Math.exp(e.deltaY*0.001))); placeView(); draw(); },{passive:false});
const touches=new Map(); let pinch=null;
el.addEventListener('touchstart',e=>{ for(const t of e.changedTouches) touches.set(t.identifier,{x:t.clientX,y:t.clientY}); if(touches.size===2){ const [a,b]=[...touches.values()]; pinch={d:Math.hypot(a.x-b.x,a.y-b.y),mx:(a.x+b.x)/2,my:(a.y+b.y)/2}; } },{passive:true});
el.addEventListener('touchmove',e=>{ for(const t of e.changedTouches) touches.set(t.identifier,{x:t.clientX,y:t.clientY});
  if(touches.size===2&&pinch){ leaveCam(); const [a,b]=[...touches.values()]; const d=Math.hypot(a.x-b.x,a.y-b.y), mx=(a.x+b.x)/2, my=(a.y+b.y)/2;
    dist=Math.max(3,Math.min(400,dist*pinch.d/d)); pan(mx-pinch.mx,my-pinch.my); pinch={d,mx,my}; placeView(); draw(); } },{passive:true});
el.addEventListener('touchend',e=>{ for(const t of e.changedTouches) touches.delete(t.identifier); if(touches.size<2) pinch=null; },{passive:true});
// ---- toggles, resize, drawing
const tog=(id,obj)=>document.getElementById(id).onchange=e=>{obj.visible=e.target.checked; draw();};
tog('cRem',rem.g); tog('cOut',gOut); tog('cLm',gLm); tog('cLines',gLines); tog('cFace',gFace);
document.getElementById('cBand').onchange=e=>{ bands.forEach(b=>b.visible=e.target.checked); draw(); };
document.getElementById('cRays').onchange=e=>{ rayls.forEach(b=>b.visible=e.target.checked); draw(); };
document.getElementById('cTags').onchange=()=>draw();
document.getElementById('hide').onclick=e=>{ const u=document.getElementById('ui'); const h=u.style.display!=='none'; u.style.display=h?'none':''; e.target.textContent=h?'show panel':'hide panel'; };
function resize(){ renderer.setSize(innerWidth,innerHeight); view.aspect=innerWidth/innerHeight; if(mode==='cam') camProjection(); else view.updateProjectionMatrix(); draw(); }
function draw(){ renderer.render(scene, view); const show=document.getElementById('cTags').checked;
  tags.forEach(t=>{ const q=t.p.clone().project(view); const vis=show&&shown(t.group)&&q.z<1&&Math.abs(q.x)<1.1&&Math.abs(q.y)<1.1;
    t.el.style.display=vis?'':'none'; if(vis){ t.el.style.left=((q.x+1)/2*innerWidth+5)+'px'; t.el.style.top=((1-q.y)/2*innerHeight-14)+'px'; } }); }
addEventListener('resize',resize); setView(new URLSearchParams(location.search).get('view')||'behind'); resize();
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
