import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import LIGHT_AUTOMATIC, LIGHT_DEFAULT
from io_xplane2blender.xplane_helpers import logger


class TestVLightDeprecated(XPlaneTestCase):
    """Old VLIGHT light types still export, with a deprecation warning (#370)"""

    def _export(self, light_type: str):
        root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(root)
        root.xplane.isExportableRoot = True
        light = bpy.data.objects["Light"]
        light.parent = root
        light.data.xplane.type = light_type
        out = self.exportExportableRoot(root)
        warnings = [w["message"] for w in logger.findWarnings() if "deprecated" in w["message"]]
        return out, warnings

    def test_default_light_warns(self) -> None:
        out, warnings = self._export(LIGHT_DEFAULT)
        self.assertIn("VLIGHT", out)
        self.assertEqual(len(warnings), 1)
        self.assertIn("'Light' uses the deprecated Default light type", warnings[0])

    def test_automatic_light_does_not_warn(self) -> None:
        out, warnings = self._export(LIGHT_AUTOMATIC)
        self.assertNotIn("VLIGHT", out)
        self.assertEqual(warnings, [])

    def test_default_is_labelled_deprecated(self) -> None:
        items = bpy.types.Light.bl_rna.properties["xplane"].fixed_type.bl_rna.properties["type"].enum_items
        self.assertIn("(deprecated)", items[LIGHT_DEFAULT].name)


runTestCases([TestVLightDeprecated])
