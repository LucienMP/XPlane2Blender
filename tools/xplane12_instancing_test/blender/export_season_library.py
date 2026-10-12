"""
End-to-end check of the library.txt export: XPlane2Blender exports seasonal boxes into the test
pack and writes its library.txt, publishing them under lib/xp2btest/season_box.obj (the path the
season DSFs place). Green for spring and summer, blue for autumn, white for winter. The green box
also has a dark plate in front of it under IF NOT SCENERY_SHADOWS, to check X-Plane loads the
condition.

    blender -b --factory-startup --addons io_xplane2blender --python export_season_library.py -- PACK_DIR [no_winter] [plate_if]
"""
import os
import sys

import bpy

pack = sys.argv[sys.argv.index("--") + 1]
no_winter = "no_winter" in sys.argv
# plate_if: draw the plate when scenery shadows are ON instead (IF SCENERY_SHADOWS), to check it shows
plate_if = "plate_if" in sys.argv

# UV quadrants of vtex.png, as make_visual_objects.py paints it
QUAD = {"green": (0.52, 0.52, 0.98, 0.98), "blue": (0.02, 0.02, 0.48, 0.48), "white": (0.52, 0.02, 0.98, 0.48),
        "red": (0.02, 0.52, 0.48, 0.98)}
VARIANTS = {"green": ("spr", "sum"), "blue": ("fal",), "white": ("win",)}


def box(name, colour, size=(3, 3, 3), offset=(0, 0, 0)):
    """A box standing on the ground, Blender Z up, with every face mapped to one colour"""
    sx, sy, sz = size[0] / 2, size[1] / 2, size[2]
    ox, oy, oz = offset
    v = [(ox + x, oy + y, oz + z) for z in (0, sz) for y in (-sy, sy) for x in (-sx, sx)]
    faces = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(v, [], faces)
    uv = mesh.uv_layers.new()
    u0, v0, u1, v1 = QUAD[colour]
    for poly in mesh.polygons:
        for corner, li in zip([(u0, v0), (u1, v0), (u1, v1), (u0, v1)], poly.loop_indices):
            uv.data[li].uv = corner
    mesh.materials.append(bpy.data.materials.get("box") or bpy.data.materials.new("box"))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj)
# The .blend is saved in the pack, so library.txt's block is named after it and paths are relative to it
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(pack, "xp2b_season_test.blend"))

for colour, seasons in VARIANTS.items():
    root = bpy.data.objects.new(f"xp2b_{colour}", None)
    bpy.context.collection.objects.link(root)
    root.xplane.isExportableRoot = True
    layer = root.xplane.layer
    layer.name = f"objects/xp2b_season_{colour}"
    layer.export_type = "scenery"
    layer.texture = "objects/vtex.png"
    lib = layer.library
    lib.enabled = not (no_winter and colour == "white")
    lib.virtual_path = "lib/xp2btest/season_box.obj"
    lib.seasonal = True
    for s in seasons:
        setattr(lib, f"season_{s}", True)
    box(f"{colour}_box", colour).parent = root
    if colour == "green":
        # A low red plate in front of the box, only drawn when scenery shadows are off
        plate = box("shadow_plate", "red", size=(3, 1.2, 0.3), offset=(0, -2.5, 0))
        plate.parent = root
        cond = plate.xplane.conditions.add()
        cond.variable = "SCENERY_SHADOWS"
        cond.value = plate_if

result = bpy.ops.scene.export_to_relative_dir(initial_dir=".")
print("EXPORT", result)
print(bpy.data.texts["xplane2blender.log"].as_string())
print(open(os.path.join(pack, "library.txt"), encoding="utf8").read())
