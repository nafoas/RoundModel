"""Clean a marching-cubes mesh in Blender: merge near-duplicate vertices,
dissolve degenerate sliver triangles, and relax the surface very slightly.
Marching cubes leaves thousands of slivers whose noisy normals sparkle as
white specks under light; the relax moves the surface well under 0.1 mm.

usage: clean_mesh.py IN.obj OUT.obj
"""
import sys

import bpy  # must be imported before bmesh
import bmesh  # noqa: E402


def main(src, dst):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=src, forward_axis="Y", up_axis="Z")
    ob = bpy.context.selected_objects[0]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    n0 = len(bm.faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=2e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.35, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    bm.to_mesh(ob.data)
    print(f"faces {n0} -> {len(bm.faces)}")
    bm.free()
    for p in ob.data.polygons:
        p.use_smooth = True
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.wm.obj_export(filepath=dst, export_selected_objects=True, forward_axis="Y", up_axis="Z",
                          export_materials=False, export_uv=False, export_normals=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
