"""Exports an Automatic spot_params_bb_pm light with XPlane2Blender (the #755 case)."""
import math, sys
import bpy
from io_xplane2blender.xplane_types import xplane_file
from io_xplane2blender.xplane_utils import xplane_lights_txt_parser
from io_xplane2blender.tests import TemporarilyMakeRootExportable

out_dir = sys.argv[sys.argv.index("--") + 1]
xplane_lights_txt_parser.parse_lights_file()
root = bpy.data.objects.new("root", None)
bpy.context.collection.objects.link(root)
for name in ("Cube", "Camera", "Light"):
    bpy.data.objects.remove(bpy.data.objects[name])
data = bpy.data.lights.new("spot", "SPOT")
data.spot_size = math.radians(90)
data.xplane.type = "automatic"
data.xplane.name = "spot_params_bb_pm"
data.xplane.param_intensity_new = 5000
light = bpy.data.objects.new("spot", data)
bpy.context.collection.objects.link(light)
light.parent = root
light.location = (0, 0, 3.5)   # Blender Z up = X-Plane Y up
light.rotation_euler = (math.radians(-90), 0, 0)  # aim along Blender -Y = X-Plane +Z (toward the camera)
bpy.context.view_layer.update()
with TemporarilyMakeRootExportable(root, bpy.context.scene.view_layers[0]):
    text = xplane_file.createFileFromBlenderRootObject(root, bpy.context.scene.view_layers[0]).write()
open(f"{out_dir}/x_xp2b_spot_auto.obj", "w", newline="\n").write(text)
print("EXPORTED", [l.strip() for l in text.splitlines() if l.strip().startswith(("LIGHT", "ANIM"))])
