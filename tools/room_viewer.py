"""An interactive 3D view of Prince's room: one self-contained HTML file (no internet needed).

Shows the room (floor grid, the room's axes at the origin), the anchor camera with the photo on its picture
plane, and the rays through his outline (coloured by part) and through every landmark. Drag to orbit, wheel or
pinch to zoom, right-drag or two fingers to move. "Camera's view" puts your eye exactly where the anchor camera
was: every ray then shrinks to a point on the photo (each pixel IS one ray).

Reads data/cameras.json and data/scene/anchor_rays.json (python tools/scene.py first).
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
RAY_EVERY = 3                      # every 3rd outline point (outline points are 2 px apart)
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
                outline=outline, lines=lines, landmarks=lms, facing=facing,
                photo="data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
    three = (ROOT / "tools/vendor/three-0.159.0.min.js").read_text()
    html = PAGE.replace("/*THREE*/", three).replace("/*DATA*/", json.dumps(data))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    print("wrote", OUT.relative_to(ROOT), f"{len(html) / 1e6:.2f} MB;", len(idx), "outline rays,", len(lms), "landmarks")
    return 0


PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prince's room (3D grounding, provisional camera)</title>
<style>
 html,body{margin:0;height:100%;background:#f7f7f4;font:14px system-ui,-apple-system,Segoe UI,sans-serif;color:#222;overflow:hidden}
 #ui{position:absolute;left:10px;top:10px;max-width:min(430px,calc(100% - 20px));background:rgba(255,255,255,.92);
     border:1px solid #ddd;border-radius:8px;padding:10px 12px;line-height:1.35}
 #ui h1{font-size:15px;margin:0 0 4px} #ui p{margin:4px 0;font-size:12.5px;color:#444}
 #ui button{font:inherit;font-size:12.5px;margin:3px 4px 3px 0;padding:4px 8px;border:1px solid #bbb;border-radius:6px;background:#fff;cursor:pointer}
 #ui label{font-size:12.5px;margin-right:10px;white-space:nowrap}
 .tag{position:absolute;font-size:11.5px;pointer-events:none;white-space:nowrap;text-shadow:0 0 3px #fff,0 0 3px #fff}
 .key{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 3px 0 6px;vertical-align:-1px}
 #hide{position:absolute;right:10px;top:10px}
</style></head><body>
<div id="ui">
 <h1>Prince's room</h1>
 <p>Centimetres. Floor grid 2 cm. <b>+X</b> his left, <b>+Y</b> up, <b>+Z</b> his forward; origin on the floor under the
 front of his peets. Every pixel of the photo is a ray from the camera: he is somewhere along each one (how far is a later step).
 The camera is placed as the owner remembers the shot (straight on, about six inches from his nose, a touch below his eye
 level). Lens: the shortest that fits, which makes him a little fluffy rabbit (about 12 cm wide, 10.5 cm to the top of his
 head); any longer lens would make him too small.</p>
 <p><span class="key" style="background:#eb8c1e"></span>head<span class="key" style="background:#3ca0e6"></span>intermediate
 <span class="key" style="background:#8c5ae6"></span>undercarriage<span class="key" style="background:#46be5a"></span>ears
 <span class="key" style="background:#148c3c"></span>top of head<span class="key" style="background:#dc3232"></span>/<span class="key" style="background:#c8aa00"></span>peets
 <span class="key" style="background:#009696"></span>belly<span class="key" style="background:#555"></span>landmarks</p>
 <div><button data-v="behind">Behind the camera</button><button data-v="cam">Camera's view</button>
 <button data-v="side">His left side</button><button data-v="top">From above</button></div>
 <div><label><input type="checkbox" id="cOut" checked> outline rays</label><label><input type="checkbox" id="cLm" checked> landmark rays</label>
 <label><input type="checkbox" id="cLines"> part-line rays</label><label><input type="checkbox" id="cTags" checked> labels</label>
 <label><input type="checkbox" id="cFace" checked> how he faces</label></div>
 <p id="faceNote" style="color:#1f4fb4"></p>
 <p>Drag: turn around. Wheel / pinch: closer. Right-drag / two fingers: move.</p>
</div>
<button id="hide">hide panel</button>
<script>/*THREE*/</script>
<script>
const D = /*DATA*/;
const V = (a)=>new THREE.Vector3(a[0],a[1],a[2]);
const renderer = new THREE.WebGLRenderer({antialias:true}); renderer.setPixelRatio(Math.min(devicePixelRatio,2));
document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0xf7f7f4);
const view = new THREE.PerspectiveCamera(45, 1, 0.05, 2000);
// ---- room: floor grid (2 cm, darker every 10 cm) and the room's axes at the origin
const grid = new THREE.GridHelper(60, 30, 0x999999, 0xd0d0cc); scene.add(grid);
const grid10 = new THREE.GridHelper(60, 6, 0x888888, 0x9a9a96); grid10.position.y = 0.002; scene.add(grid10);
function seg(pts, colour, width){ const g = new THREE.BufferGeometry().setFromPoints(pts.map(V));
  return new THREE.Line(g, new THREE.LineBasicMaterial({color:colour, linewidth:width||1})); }
scene.add(seg([[0,0,0],[4,0,0]],0xd22828)); scene.add(seg([[0,0,0],[0,4,0]],0x28a028)); scene.add(seg([[0,0,0],[0,0,4]],0x2850dc));
// ---- the anchor camera: its axes, frustum to a picture plane 4 cm out, and the photo on that plane
const c = D.camera, C = V(c.C);
const right = new THREE.Vector3(...c.R[0]), down = new THREE.Vector3(...c.R[1]), fwd = new THREE.Vector3(...c.R[2]);
const up = down.clone().negate(), back = fwd.clone().negate();
const d0 = 4.0, w = c.W/c.f*d0, h = c.H/c.f*d0;
// the picture plane: the picture's own pixels, at depth d0 (the camera aimed at (cx, cy), NOT the picture's centre)
const atPx = (u,v)=>C.clone().addScaledVector(fwd, d0).addScaledVector(right, (u-c.cx)/c.f*d0).addScaledVector(down, (v-c.cy)/c.f*d0);
const centre = atPx(c.W/2, c.H/2);
const corner = (sx,sy)=>atPx(sx<0?0:c.W, sy>0?0:c.H);
const K = [corner(-1,1),corner(1,1),corner(1,-1),corner(-1,-1)];
const fr = new THREE.Group();
K.forEach(k=>fr.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([C,k]), new THREE.LineBasicMaterial({color:0x222222}))));
fr.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([...K,K[0]]), new THREE.LineBasicMaterial({color:0x222222})));
scene.add(fr);
const tex = new THREE.TextureLoader().load(D.photo, ()=>draw()); tex.colorSpace = THREE.SRGBColorSpace;
const plane = new THREE.Mesh(new THREE.PlaneGeometry(w,h), new THREE.MeshBasicMaterial({map:tex, side:THREE.DoubleSide}));
plane.position.copy(centre); plane.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, up, back)); scene.add(plane);
// height and distance of the camera, as lines on the floor
const foot = new THREE.Vector3(C.x,0,C.z);
scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([C,foot,new THREE.Vector3(0,0,0)]), new THREE.LineBasicMaterial({color:0x000000})));
// ---- rays
function rayGroup(ends, colours, opacity){ const pos=[], col=[]; const tmp=new THREE.Color();
  ends.forEach((e,i)=>{ pos.push(C.x,C.y,C.z,e[0],e[1],e[2]); tmp.set(colours? colours[i] : 0x555555); col.push(tmp.r,tmp.g,tmp.b,tmp.r,tmp.g,tmp.b); });
  const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3)); g.setAttribute('color',new THREE.Float32BufferAttribute(col,3));
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({vertexColors:true, transparent:true, opacity:opacity})); }
const gOut = rayGroup(D.outline.ends, D.outline.colours, 0.75); scene.add(gOut);
const gLm = rayGroup(D.landmarks.map(l=>l.end), null, 0.9); scene.add(gLm);
const gLines = new THREE.Group(); D.lines.forEach(l=>gLines.add(rayGroup(l.ends.filter((_,i)=>i%4==0), null, 0.35))); gLines.visible=false; scene.add(gLines);
// how he faces (tools/facing.py): blue = his head's left-right axis and the way his head faces; red = his body (from his peets)
const gFace = new THREE.Group();
if (D.facing){ const f=D.facing; const L=(a,b,col)=>gFace.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints([V(a),V(b)]), new THREE.LineBasicMaterial({color:col})));
  L(f.head[0],f.head[1],0x1f5adc); L(f.head[2],f.head[3],0x1f5adc); L(f.body[0],f.body[1],0xc81e1e); L(f.body[2],f.body[3],0xc81e1e);
  document.getElementById('faceNote').textContent = 'Blue: his head (left-right axis, and the way it faces). Red: his body, from his peets. ' + f.text + '.'; }
scene.add(gFace);
// ---- labels
const tags = []; function tag(text, p, colour){ const el=document.createElement('div'); el.className='tag'; el.textContent=text; el.style.color=colour||'#111'; document.body.appendChild(el); tags.push({el,p:p.clone()}); }
tag('origin', new THREE.Vector3(0,0,0)); tag('+X his left', V([4.3,0,0]),'#c02020'); tag('+Y up', V([0,4.3,0]),'#208020'); tag('+Z his forward', V([0,0,4.3]),'#2040c0');
tag('anchor camera', C.clone().addScaledVector(up,1.0));
if (D.facing){ tag('head faces', V(D.facing.head[3]), '#1f5adc'); tag('body faces', V(D.facing.body[3]), '#c81e1e'); } tag(C.y.toFixed(1)+' cm up', C.clone().add(foot).multiplyScalar(0.5));
tag(Math.hypot(C.x,C.z).toFixed(1)+' cm away', foot.clone().multiplyScalar(0.5));
D.landmarks.filter(l=>/^(eye_his_(left|right)|nose_y_centre|ear_tip_his_(left|right)|crown_front|chin_midline|belly_front|peet_bottom_his_(left|right))$/.test(l.name))
  .forEach(l=>tag(l.name.replace(/_/g,' '), V(l.end), '#444'));
// ---- orbit control (drag = turn, wheel/pinch = zoom, right-drag/two fingers = move)
const target = new THREE.Vector3(0,5,C.z*0.45); let yaw=0.42, pitch=0.28, dist=60, mode='orbit';
function placeView(){ if(mode==='cam') return; view.position.set(target.x+dist*Math.sin(yaw)*Math.cos(pitch), target.y+dist*Math.sin(pitch), target.z+dist*Math.cos(yaw)*Math.cos(pitch)); view.up.set(0,1,0); view.lookAt(target); view.fov=45; view.updateProjectionMatrix(); }
const VIEWS = { behind:()=>{target.copy(C).add(V([0,1,-9])); yaw=0.42; pitch=0.28; dist=32;},
  side:()=>{target.set(0,5,C.z*0.45); yaw=Math.PI/2; pitch=0.03; dist=70;},
  top:()=>{target.set(0,0,C.z*0.45); yaw=0; pitch=1.5; dist=75;} };
function setView(v){ if(v==='cam'){ mode='cam'; view.position.copy(C); view.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(right, up, back));
    camProjection(); } else { mode='orbit'; VIEWS[v](); placeView(); } draw(); }
// the anchor camera's own lens: off-centre aim point, picture fitted to the window's height
function camProjection(){ const n=view.near, top=c.cy/c.f*n, bottom=-(c.H-c.cy)/c.f*n, mid=((c.W/2-c.cx)/c.f)*n, half=(top-bottom)*view.aspect/2;
  view.projectionMatrix.makePerspective(mid-half, mid+half, top, bottom, n, view.far); view.projectionMatrixInverse.copy(view.projectionMatrix).invert(); }
document.querySelectorAll('#ui button').forEach(b=>b.onclick=()=>setView(b.dataset.v));
let drag=null; const el=renderer.domElement;
el.addEventListener('contextmenu',e=>e.preventDefault());
el.addEventListener('pointerdown',e=>{ drag={x:e.clientX,y:e.clientY,b:e.button}; el.setPointerCapture(e.pointerId); });
el.addEventListener('pointerup',()=>drag=null);
el.addEventListener('pointermove',e=>{ if(!drag||touches.size>1) return; const dx=e.clientX-drag.x, dy=e.clientY-drag.y; drag.x=e.clientX; drag.y=e.clientY; leaveCam();
  if(drag.b===2||e.shiftKey){ pan(dx,dy); } else { yaw-=dx*0.006; pitch=Math.max(-1.5,Math.min(1.55,pitch+dy*0.006)); } placeView(); draw(); });
function leaveCam(){ if(mode==='cam'){ mode='orbit'; target.copy(C).addScaledVector(fwd,15); dist=15; yaw=Math.atan2(-fwd.x,-fwd.z); pitch=Math.asin(-fwd.y); } }
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
tog('cOut',gOut); tog('cLm',gLm); tog('cLines',gLines); tog('cFace',gFace);
document.getElementById('cTags').onchange=()=>draw();
document.getElementById('hide').onclick=e=>{ const u=document.getElementById('ui'); const h=u.style.display!=='none'; u.style.display=h?'none':''; e.target.textContent=h?'show panel':'hide panel'; };
function resize(){ renderer.setSize(innerWidth,innerHeight); view.aspect=innerWidth/innerHeight; if(mode==='cam') camProjection(); else view.updateProjectionMatrix(); draw(); }
function draw(){ renderer.render(scene, view); const show=document.getElementById('cTags').checked;
  tags.forEach(t=>{ const q=t.p.clone().project(view); const vis=show&&q.z<1&&Math.abs(q.x)<1.1&&Math.abs(q.y)<1.1;
    t.el.style.display=vis?'':'none'; if(vis){ t.el.style.left=((q.x+1)/2*innerWidth+5)+'px'; t.el.style.top=((1-q.y)/2*innerHeight-14)+'px'; } }); }
addEventListener('resize',resize); setView('behind'); resize();
</script></body></html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
