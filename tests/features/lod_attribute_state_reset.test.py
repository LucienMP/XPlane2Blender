import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import EXPORT_TYPE_SCENERY


class TestLODAttributeStateReset(XPlaneTestCase):
    """
    X-Plane resets the attribute state at each ATTR_LOD, so attributes must
    be written again in every LOD bucket, not just the first (#763)
    """

    def test_light_level_in_every_lod(self) -> None:
        for name in ("Camera", "Light"):
            bpy.data.objects.remove(bpy.data.objects[name])
        coll = bpy.data.collections["Collection"]
        coll.xplane.is_exportable_collection = True
        layer = coll.xplane.layer
        layer.export_type = EXPORT_TYPE_SCENERY
        while len(layer.lod) < 2:
            layer.lod.add()
        layer.lods = "2"
        layer.lod[0].near, layer.lod[0].far = 0, 1000
        layer.lod[1].near, layer.lod[1].far = 0, 5000

        cube = bpy.data.objects["Cube"]
        cube.xplane.override_lods = True
        cube.xplane.lod[0] = cube.xplane.lod[1] = True
        mat = cube.active_material
        mat.xplane.lightLevel = True
        mat.xplane.lightLevel_dataref = "sim/test/light"

        out = self.exportExportableRoot(coll)
        lods = out.split("ATTR_LOD")[1:]
        self.assertEqual(len(lods), 2)
        for lod in lods:
            self.assertIn("ATTR_light_level", lod)
            self.assertIn("sim/test/light", lod)


runTestCases([TestLODAttributeStateReset])
