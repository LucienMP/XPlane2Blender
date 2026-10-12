import inspect

from typing import Tuple
import os
import sys

import bpy
from io_xplane2blender import xplane_config, xplane_constants
from io_xplane2blender.tests import *

__dirname__ = os.path.dirname(__file__)

def filterLines(line:Tuple[str])->bool:
    return (isinstance(line[0],str)
             and ("ATTR_LOD" in line[0]
                  or "TRIS" in line[0]))


class TestLodOverridesApplied(XPlaneTestCase):
    def _assert_root(self, filename:str)->None:
        """
        Tests both types of Exportable Roots at the same time as sub tests
        """
        for fname in [filename[5:], filename[5:].replace("_object","")]:
            with self.subTest(fname=fname):
                self.assertExportableRootExportEqualsFixture(
                    fname,
                    os.path.join(__dirname__, "fixtures", filename + ".obj"),
                    filterLines,
                    filename,
                )

    def test_AllIgnored(self)->None:
        # Nothing here has Override LODs. Since 5.0 such objects go in every LOD by default (#730);
        # "Not Exported" keeps the old behaviour this fixture records (lod_unassigned.test.py covers the rest)
        bpy.data.collections["AllIgnored"].xplane.layer.lod_unassigned = xplane_constants.LOD_UNASSIGNED_SKIP
        bpy.data.objects["AllIgnored_object"].xplane.layer.lod_unassigned = xplane_constants.LOD_UNASSIGNED_SKIP
        filename = inspect.stack()[0].function
        self._assert_root(filename)

    def test_IncludeAndIgnore(self)->None:
        filename = inspect.stack()[0].function
        self._assert_root(filename)

    def test_NestedDuplicateOverrides(self)->None:
        filename = inspect.stack()[0].function
        self._assert_root(filename)

    def test_NonSequentialOverrides(self)->None:
        filename = inspect.stack()[0].function
        self._assert_root(filename)

    def test_NoOverridesTakesParents(self)->None:
        filename = inspect.stack()[0].function
        self._assert_root(filename)

    def test_OverridesAppliedToAllChildren(self)->None:
        filename = inspect.stack()[0].function
        self._assert_root(filename)

    def test_OverridesCombined(self)->None:
        filename = inspect.stack()[0].function
        self._assert_root(filename)

    def test_ExportableObjectOverride_object_special_1_2_3(self)->None:
        filename = inspect.stack()[0].function
        self.assertExportableRootExportEqualsFixture(
            filename[5:],
            os.path.join(__dirname__, "fixtures", filename + ".obj"),
            filterLines,
            filename,
        )

runTestCases([TestLodOverridesApplied])
