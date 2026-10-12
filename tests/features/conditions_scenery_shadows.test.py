from pathlib import Path

import bpy

from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import CONDITION_SCENERY_SHADOWS, EXPORT_TYPE_SCENERY


class TestConditionsSceneryShadows(XPlaneTestCase):
    """SCENERY_SHADOWS conditions, e.g. Laminar's fake ground shadow when scenery shadows are off"""

    def setUp(self):
        super().setUp()
        self.root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(self.root)
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = EXPORT_TYPE_SCENERY
        self.cube = bpy.data.objects["Cube"]
        self.cube.parent = self.root
        self.cube.xplane.conditions.clear()

    def _export(self, must_be_on: bool) -> str:
        condition = self.cube.xplane.conditions.add()
        condition.variable = CONDITION_SCENERY_SHADOWS
        condition.value = must_be_on
        return self.exportExportableRoot(self.root)

    def test_if_not_scenery_shadows(self) -> None:
        out = self._export(False)
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        start = lines.index("IF NOT SCENERY_SHADOWS")
        end = lines.index("ENDIF", start)
        self.assertTrue(any(l.startswith("TRIS") for l in lines[start:end]))
        with open(get_tmp_folder() / Path("conditions_if_not_scenery_shadows.obj"), "w") as f:
            f.write(out)  # For loading in X-Plane

    def test_if_scenery_shadows(self) -> None:
        out = self._export(True)
        self.assertIn("IF SCENERY_SHADOWS", [l.strip() for l in out.splitlines()])


runTestCases([TestConditionsSceneryShadows])
