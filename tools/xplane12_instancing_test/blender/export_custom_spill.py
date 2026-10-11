"""Exports the custom spill test root with XPlane2Blender for an X-Plane 11.30 and an X-Plane 12 target."""
import sys
import bpy
from io_xplane2blender.xplane_types import xplane_file
from io_xplane2blender.tests import TemporarilyMakeRootExportable
from io_xplane2blender.xplane_utils import xplane_lights_txt_parser
from io_xplane2blender.xplane_constants import VERSION_1130, VERSION_1200

out_dir = sys.argv[sys.argv.index("--") + 1]
xplane_lights_txt_parser.parse_lights_file()
root = bpy.data.objects.get("light_spill_custom_size") or bpy.data.collections["light_spill_custom_size"]
for light in bpy.data.lights:
    light.xplane.param_intensity_new = 5000
for version, name in ((VERSION_1130, "x_xp2b_spill_xp11"), (VERSION_1200, "x_xp2b_spill_xp12")):
    bpy.context.scene.xplane.version = version
    with TemporarilyMakeRootExportable(root, bpy.context.scene.view_layers[0]):
        xp = xplane_file.createFileFromBlenderRootObject(root, bpy.context.scene.view_layers[0])
    text = xp.write()
    open(f"{out_dir}/{name}.obj", "w", newline="\n").write(text)
    print(name, [l.strip() for l in text.splitlines() if "LIGHT_SPILL_CUSTOM" in l])
