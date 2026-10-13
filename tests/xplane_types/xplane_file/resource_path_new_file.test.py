import inspect
import os
import sys
from pathlib import Path
from typing import Tuple

import bpy

from io_xplane2blender import xplane_config
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers

__dirname__ = os.path.dirname(__file__)


class TestResourcePathNewFile(XPlaneTestCase):
    def test_new_file_cwd_1_and_2(self) -> None:
        filename = inspect.stack()[0].function
        os.chdir(__dirname__)
        bpy.ops.wm.read_homefile()

        col = test_creation_helpers.create_datablock_collection("cwd_1_and_2")
        col.xplane.is_exportable_collection = True
        col.xplane.layer.name = filename + ".obj"
        # An absolute path on the drive the OBJ goes to: a path can't be made relative
        # across drives, and CI checks the repository out on D:
        texture = os.path.splitdrive(os.path.abspath(get_tmp_folder()))[0] + "/tex.png"
        col.xplane.layer.texture = texture

        cube = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH", "Cube", collection="cwd_1_and_2"
            )
        )

        bpy.ops.export.xplane_obj(filepath=get_tmp_folder() + f"/{filename}")
        lines = (
            (Path(get_tmp_folder()) / Path(filename).with_suffix(".obj"))
            .read_text()
            .splitlines()
        )

        # This used to be assertTrue(value, message), which passes for any value
        texture_line = next(l for l in lines if l.startswith("TEXTURE\t"))
        expected = os.path.relpath(texture, get_tmp_folder()).replace("\\", "/")
        self.assertEqual(texture_line.split()[1], expected)
        self.assertTrue(expected.endswith("../tex.png"), expected)


runTestCases([TestResourcePathNewFile])
