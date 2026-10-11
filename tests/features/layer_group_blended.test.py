import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import (
    EXPORT_TYPE_SCENERY,
    LAYER_GROUP_BLENDED,
    LAYER_GROUP_NONE,
    VERSION_1220,
    VERSION_1221,
)


class TestLayerGroupBlended(XPlaneTestCase):
    """The Blended layer group, which only exists in X-Plane 12.21+"""

    def setUp(self):
        super().setUp()
        self.cube = bpy.data.objects["Cube"]
        self.cube.xplane.isExportableRoot = True
        self.cube.xplane.layer.export_type = EXPORT_TYPE_SCENERY

    def _layer_group_lines(self):
        return [
            line.split()
            for line in self.exportExportableRoot(self.cube).splitlines()
            if line.startswith("ATTR_layer_group")
        ]

    def test_blended_exported(self) -> None:
        bpy.context.scene.xplane.version = VERSION_1221
        self.cube.xplane.layer.layer_group = LAYER_GROUP_BLENDED
        self.cube.xplane.layer.layer_group_offset = 2
        self.assertEqual(
            self._layer_group_lines(), [["ATTR_layer_group", "blended", "2"]]
        )

    def test_blended_reset_for_older_versions(self) -> None:
        bpy.context.scene.xplane.version = VERSION_1221
        self.cube.xplane.layer.layer_group = LAYER_GROUP_BLENDED
        bpy.context.scene.xplane.version = VERSION_1220
        self.assertEqual(self.cube.xplane.layer.layer_group, LAYER_GROUP_NONE)
        self.assertEqual(self._layer_group_lines(), [])

    def test_draped_has_no_blended(self) -> None:
        bpy.context.scene.xplane.version = VERSION_1221
        items = self.cube.xplane.layer.bl_rna.properties["layer_group_draped"].enum_items
        self.assertNotIn(LAYER_GROUP_BLENDED, items.keys())


runTestCases([TestLayerGroupBlended])
