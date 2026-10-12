"""
Objects nobody assigned to an LOD (#730): neither they nor a parent use Override LODs.
They used to be left out silently; now the root's "Objects in No LOD" decides, with a warning.
Objects with Override LODs on but no LOD ticked stay left out, as upstream intended.
"""
import re
from typing import Dict, List

import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.xplane_constants import (
    LOD_UNASSIGNED_ALL,
    LOD_UNASSIGNED_FIRST,
    LOD_UNASSIGNED_SKIP,
)

SELECTIVE = [(0, 100), (100, 500)]
ADDITIVE = [(0, 100), (0, 500)]


class TestLodUnassigned(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        bpy.context.scene.xplane.debug = True  # "# MESH: <name>" comments show which objects were written
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj)
        quad = bpy.data.meshes.get("quad") or bpy.data.meshes.new("quad")
        if not quad.polygons:
            quad.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
            quad.materials.append(bpy.data.materials.new("mat"))
        self.root = bpy.data.objects.new("root", None)
        bpy.context.collection.objects.link(self.root)
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY
        for name, override, buckets in (
            ("free", False, ()),  # nobody assigned it: #730
            ("near_only", True, (0,)),
            ("explicit_none", True, ()),  # Override LODs on, nothing ticked: left out on purpose
        ):
            obj = bpy.data.objects.new(name, quad)
            bpy.context.collection.objects.link(obj)
            obj.parent = self.root
            obj.xplane.override_lods = override
            for i in buckets:
                obj.xplane.lod[i] = True

    def tearDown(self):
        bpy.context.scene.xplane.debug = False
        super().tearDown()

    def _export(self, lods: List[tuple], mode: str) -> Dict[str, List[str]]:
        """Returns, for each ATTR_LOD section, the names of the meshes written in it"""
        layer = self.root.xplane.layer
        layer.lods = str(len(lods))
        for i, (near, far) in enumerate(lods):
            layer.lod[i].near, layer.lod[i].far = near, far
        layer.lod_unassigned = mode
        out = self.exportExportableRoot(self.root)
        sections = {}
        current = None
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("ATTR_LOD"):
                current = " ".join(line.split()[1:])
                sections[current] = []
            m = re.match(r"# MESH: (\S+)", line)
            if m and current:
                sections[current].append(m.group(1))
        return sections

    def test_all_distances_selective(self) -> None:
        self.assertEqual(
            self._export(SELECTIVE, LOD_UNASSIGNED_ALL),
            {"0 100": ["free", "near_only"], "100 500": ["free"]},
        )
        warnings = [w["message"] for w in logger.findWarnings()]
        self.assertTrue(any("aren't in any LOD" in w and "free" in w for w in warnings), warnings)
        self.assertFalse(any("explicit_none" in w for w in warnings), warnings)
        logger.clearMessages()

    def test_all_distances_additive(self) -> None:
        # Additive LODs overlap: X-Plane draws every LOD in range, so only the farthest one
        self.assertEqual(
            self._export(ADDITIVE, LOD_UNASSIGNED_ALL),
            {"0 100": ["near_only"], "0 500": ["free"]},
        )
        logger.clearMessages()

    def test_first_lod(self) -> None:
        self.assertEqual(
            self._export(SELECTIVE, LOD_UNASSIGNED_FIRST),
            {"0 100": ["free", "near_only"], "100 500": []},
        )
        logger.clearMessages()

    def test_not_exported(self) -> None:
        self.assertEqual(
            self._export(SELECTIVE, LOD_UNASSIGNED_SKIP),
            {"0 100": ["near_only"], "100 500": []},
        )
        self.assertTrue(any("not exported" in w["message"] for w in logger.findWarnings()))
        logger.clearMessages()

    def test_no_lods_unaffected(self) -> None:
        self.root.xplane.layer.lods = "0"
        out = self.exportExportableRoot(self.root)
        self.assertEqual(sorted(re.findall(r"# MESH: (\S+)", out)), ["explicit_none", "free", "near_only"])


runTestCases([TestLodUnassigned])
