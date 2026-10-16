"""Render a mesh as plain grey clay from the solved reference cameras, and as a
turntable, with Blender (bpy) + Cycles.

usage: render_clay.py MESH.obj CAMERAS.json OUTDIR [--turntable N] [--views a,b,...]
                      [--samples N] [--scale S]

World convention matches cameras.json: metres, +x his right, +y forward, +z up.
Reference cameras: x right, y down, z forward; rotvec maps world -> camera.
Renders are RGBA with a transparent background, so the alpha is the silhouette.
"""
import argparse
import json
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector
from scipy.spatial.transform import Rotation as R

CENTRE = Vector((0.0, 0.0, 0.08))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    return sc


def load_mesh(path):
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    ob = bpy.context.selected_objects[0]
    for p in ob.data.polygons:
        p.use_smooth = True
    mat = bpy.data.materials.new("clay")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.72, 0.72, 0.72, 1)
    bsdf.inputs["Roughness"].default_value = 0.65
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


def lights(sc):
    world = bpy.data.worlds.new("w")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.35, 0.37, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35
    # big soft overhead light, like the master's even top light
    ld = bpy.data.lights.new("top", "AREA")
    ld.energy = 12
    ld.size = 0.8
    lo = bpy.data.objects.new("top", ld)
    lo.location = (0.1, 0.35, 0.6)
    lo.rotation_euler = (math.radians(35), 0, math.radians(10))
    sc.collection.objects.link(lo)


def set_camera(sc, cam_ob, size, rotvec, pos, f_px):
    w, h = size
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h)
    sc.render.resolution_percentage = 100
    Rwc = R.from_rotvec(rotvec).as_matrix()  # rows: cam x, y(down), z(fwd) in world
    r, d, f = Rwc[0], Rwc[1], Rwc[2]
    rot = np.stack([r, -d, -f], 1)  # blender camera: x right, y up, looks -z
    M = Matrix(((*rot[0], pos[0]), (*rot[1], pos[1]), (*rot[2], pos[2]), (0, 0, 0, 1)))
    cam_ob.matrix_world = M
    cd = cam_ob.data
    cd.sensor_fit = "HORIZONTAL"
    cd.sensor_width = 36.0
    cd.lens = f_px * 36.0 / w
    cd.clip_start = 0.005
    cd.clip_end = 10


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mesh")
    ap.add_argument("cameras")
    ap.add_argument("outdir")
    ap.add_argument("--turntable", type=int, default=0)
    ap.add_argument("--views", default="")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args()

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    sc = reset()
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    load_mesh(a.mesh)
    lights(sc)
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam

    cams = json.loads(Path(a.cameras).read_text())["views"]
    names = [n for n in a.views.split(",") if n] if a.views else list(cams)
    for n in names:
        v = cams[n]
        size = np.array(v["size"]) * a.scale
        set_camera(sc, cam, size, v["rotvec_world_to_cam"], v["camera_position_m"], v["focal_px"] * a.scale)
        sc.render.filepath = str(out / f"{n}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", n, flush=True)

    if a.turntable:
        m = cams["master_front_standing"]
        size = np.array(m["size"]) * 0.5
        f_px = m["focal_px"] * 0.5
        mpos = Vector(m["camera_position_m"])
        rel = mpos - CENTRE
        dist, height = Vector((rel.x, rel.y, 0)).length, rel.z
        for i in range(a.turntable):
            ang = 2 * math.pi * i / a.turntable  # positive = camera moves toward his left
            pos = CENTRE + Vector((-math.sin(ang) * dist, math.cos(ang) * dist, height))
            fwd = (CENTRE - pos).normalized()
            right = fwd.cross(Vector((0, 0, 1))).normalized()
            down = fwd.cross(right)
            Rwc = np.array([right, down, fwd])
            set_camera(sc, cam, size, R.from_matrix(Rwc).as_rotvec(), pos, f_px)
            sc.render.filepath = str(out / f"turntable_{i:03d}.png")
            bpy.ops.render.render(write_still=True)
        print("turntable done", flush=True)


if __name__ == "__main__":
    main()
