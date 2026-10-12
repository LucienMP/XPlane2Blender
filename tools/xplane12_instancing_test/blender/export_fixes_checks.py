"""
XPlane2Blender exports for the X-Plane checks of the 5.0 fixes (scenes fixes_* in scenes.py):

- x_730_sel_all / x_730_sel_skip / x_730_add_all: a green box in no LOD (#730), in selective LODs with
  "All Distances" and "Not Exported", and in additive LODs with "All Distances"
- x_643_hidden / x_643_shown: a white box under an armature bone that has Show/Hide (#643, #516),
  ANIM_hide by sim/time/local_date_days in 100..200 (hidden on day 172) or 0..50 (shown)
- x_709_opt / x_709_noopt: two animated blue boxes sharing their vertices with Optimize on (#709), and
  the same export with Optimize off; they must look identical

    blender -b --factory-startup --addons io_xplane2blender --python export_fixes_checks.py -- OBJECTS_DIR
"""
import math
import os
import sys

import bpy

from io_xplane2blender.tests import test_creation_helpers as tch
from io_xplane2blender.xplane_constants import (
    LOD_UNASSIGNED_ALL,
    LOD_UNASSIGNED_SKIP,
    VERSION_1200,
)
from io_xplane2blender.xplane_types import xplane_file

out_dir = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
QUAD = {"red": (0.02, 0.52, 0.48, 0.98), "green": (0.52, 0.52, 0.98, 0.98),
        "blue": (0.02, 0.02, 0.48, 0.48), "white": (0.52, 0.02, 0.98, 0.48)}

tch.delete_everything()
# Saved next to the OBJs, so the OBJs' texture path is just "vtex.png"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "xp2b_fixes_checks.blend"))
bpy.context.scene.xplane.version = VERSION_1200


def box_mesh(name, colour, size=3.0, height=3.0):
    """A box standing on the ground (Blender Z up), every face mapped to one colour"""
    s = size / 2
    v = [(x, y, z) for z in (0, height) for y in (-s, s) for x in (-s, s)]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(v, [], faces)
    uv = mesh.uv_layers.new()
    u0, v0, u1, v1 = QUAD[colour]
    for poly in mesh.polygons:
        for corner, li in zip([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], poly.loop_indices):
            uv.data[li].uv = corner
    mesh.materials.append(bpy.data.materials.get("box") or bpy.data.materials.new("box"))
    return mesh


def new_obj(name, data, parent=None, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = location
    return obj


def new_root(name):
    root = new_obj(name, None)
    root.xplane.isExportableRoot = True
    root.xplane.layer.name = name
    root.xplane.layer.export_type = "scenery"
    root.xplane.layer.texture = "vtex.png"
    return root


def export(root):
    xp = xplane_file.createFileFromBlenderRootObject(root, bpy.context.scene.view_layers[0])
    text = xp.write()
    with open(os.path.join(out_dir, root.name + ".obj"), "w", newline="\n") as f:
        f.write(text)
    counts = next(l for l in text.splitlines() if l.startswith("POINT_COUNTS"))
    print("EXPORTED", root.name, counts.split()[1:], "lines:", len(text.splitlines()))
    return text


# --- #730 -------------------------------------------------------------------
for name, lods, mode in (
    ("x_730_sel_all", [(0, 1000), (1000, 5000)], LOD_UNASSIGNED_ALL),
    ("x_730_sel_skip", [(0, 1000), (1000, 5000)], LOD_UNASSIGNED_SKIP),
    ("x_730_add_all", [(0, 1000), (0, 5000)], LOD_UNASSIGNED_ALL),
):
    root = new_root(name)
    layer = root.xplane.layer
    layer.lods = str(len(lods))
    for i, (near, far) in enumerate(lods):
        layer.lod[i].near, layer.lod[i].far = near, far
    layer.lod_unassigned = mode
    new_obj(name + "_box", box_mesh(name + "_box", "green"), root)
    text = export(root)
    print("   ", [l for l in text.splitlines() if l.startswith(("ATTR_LOD", "TRIS")) or "TRIS" in l])

# --- #643 / #516 ------------------------------------------------------------
for name, v1, v2 in (("x_643_hidden", 100, 200), ("x_643_shown", 0, 50)):
    root = new_root(name)
    arm = tch.create_datablock_armature(tch.DatablockInfo("ARMATURE", name + "_arm", parent_info=tch.ParentInfo(root)))
    bone = arm.data.bones[0]
    dataref = bone.xplane.datarefs.add()
    dataref.path = "sim/time/local_date_days"
    dataref.anim_type = "hide"
    dataref.show_hide_v1, dataref.show_hide_v2 = v1, v2
    box = new_obj(name + "_box", box_mesh(name + "_box", "white"))
    box.parent = arm
    box.parent_type = "BONE"
    box.parent_bone = bone.name
    # Parenting to a bone puts the child at the bone's tail; keep the box on the ground at the root
    bpy.context.view_layer.update()
    box.matrix_world = root.matrix_world.copy()
    text = export(root)
    print("   ", [l.strip() for l in text.splitlines() if "ANIM" in l or "TRIS" in l])

# --- #709 -------------------------------------------------------------------
shared = box_mesh("x_709_box", "blue", size=1.5, height=1.5)
roots_709 = []
for name in ("x_709_opt", "x_709_noopt"):
    root = new_root(name)
    for x in (-1.5, 1.5):
        obj = new_obj(f"{name}_box_{x}", shared, root, location=(x, 0, 0))
        dataref = obj.xplane.datarefs.add()
        dataref.path = "sim/time/local_date_days"
        for frame, value, angle in ((1, 0, 0.0), (2, 365, math.pi)):
            dataref.value = value
            obj.rotation_euler = (0, 0, angle)
            obj.keyframe_insert(data_path="xplane.datarefs[0].value", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    roots_709.append(root)
# The Export button clears the exporter's keyframe cache; calling it directly after an earlier
# export must too, or the new animation isn't seen
xplane_file._all_keyframe_infos.clear()
bpy.context.scene.frame_set(1)
for root, optimize in zip(roots_709, (True, False)):
    bpy.context.scene.xplane.optimize = optimize
    export(root)
bpy.context.scene.xplane.optimize = False
