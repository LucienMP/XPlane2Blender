"""
ATTR_shiny_rat 0 is X-Plane's default, so it's only written to undo an earlier non-zero value (#439)
"""
import re
from typing import List, Tuple

import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *


class TestShinyRatDefault(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        bpy.context.scene.xplane.debug = True  # "# MESH: <name>" comments
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)
        self.root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(self.root)
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY

    def tearDown(self):
        bpy.context.scene.xplane.debug = False
        super().tearDown()

    def add_quad(self, name: str, specular: float, lods=()) -> None:
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
        mat = bpy.data.materials.new(name)
        mat.specular_intensity = specular
        mesh.materials.append(mat)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.parent = self.root
        if lods:
            obj.xplane.override_lods = True
            for i in lods:
                obj.xplane.lod[i] = True

    def export(self) -> Tuple[List[str], List[Tuple[str, float]]]:
        """The ATTR_shiny_rat lines, and the shininess in effect for each mesh's TRIS"""
        out = self.exportExportableRoot(self.root)
        lines, drawn, state, mesh = [], [], 0.0, None
        for line in out.splitlines():
            f = line.split()
            if not f:
                continue
            if f[0] == "ATTR_LOD":
                state = 0.0  # X-Plane resets attributes at each LOD
            elif f[0] == "ATTR_shiny_rat":
                state = float(f[1])
                lines.append(line.strip())
            elif line.strip().startswith("# MESH:"):
                mesh = f[2]
            elif f[0] == "TRIS":
                drawn.append((mesh, state))
        return lines, drawn

    def test_zero_first_not_written(self) -> None:
        self.add_quad("a_dull", 0.0)
        lines, drawn = self.export()
        self.assertEqual(lines, [])
        self.assertEqual(drawn, [("a_dull", 0.0)])

    def test_zero_after_shiny_written(self) -> None:
        self.add_quad("a_shiny", 0.5)
        self.add_quad("b_dull", 0.0)
        lines, drawn = self.export()
        self.assertEqual(lines, ["ATTR_shiny_rat\t0.5", "ATTR_shiny_rat\t0"])
        self.assertEqual(drawn, [("a_shiny", 0.5), ("b_dull", 0.0)])

    def test_zero_after_lod_reset_not_written(self) -> None:
        layer = self.root.xplane.layer
        layer.lods = "2"
        layer.lod[0].near, layer.lod[0].far = 0, 100
        layer.lod[1].near, layer.lod[1].far = 100, 500
        self.add_quad("a_shiny", 0.5, lods=(0,))
        self.add_quad("b_dull", 0.0, lods=(1,))
        lines, drawn = self.export()
        self.assertEqual(lines, ["ATTR_shiny_rat\t0.5"])
        self.assertEqual(drawn, [("a_shiny", 0.5), ("b_dull", 0.0)])


runTestCases([TestShinyRatDefault])
