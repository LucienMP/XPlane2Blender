"""
Texture checks on export (#403): a texture that isn't a PNG or DDS, isn't on disk,
isn't really a PNG/DDS, or isn't a power of two in each dimension warns, naming
the OBJ and the path as entered
"""
import os
import struct
from pathlib import Path
from typing import List

import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.xplane_types.xplane_header import XPlaneHeader

__dirname__ = Path(__file__).parent
WHITE_128 = (__dirname__.parent / "lights" / "white.png").resolve()


def texture_warnings() -> List[str]:
    return [w["message"] for w in logger.findWarnings() if ": texture '" in w["message"]]


def write_dds(path: Path, width: int, height: int) -> Path:
    """A DDS header only, enough for the size check"""
    header = b"DDS " + struct.pack("<III", 124, 0x1007, height) + struct.pack("<I", width)
    path.write_bytes(header + bytes(128 - len(header)))
    return path


class TestTextureChecks(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.root = test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "root")
        )
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY
        self.cube = test_creation_helpers.create_datablock_mesh(
            test_creation_helpers.DatablockInfo(
                "MESH", "cube", parent_info=test_creation_helpers.ParentInfo(self.root)
            )
        )
        self.cube.data.uv_layers.new()
        self.tmp = Path(get_tmp_folder())
        logger.clearMessages()

    def _export_with(self, **layer_props) -> List[str]:
        for name, value in layer_props.items():
            setattr(self.root.xplane.layer, name, value)
        self.exportExportableRoot(self.root)
        return texture_warnings()

    def test_power_of_two_png_passes(self) -> None:
        self.assertEqual(self._export_with(texture=str(WHITE_128)), [])

    def test_missing_texture_warns(self) -> None:
        missing = str(self.tmp / "not_here.png")
        warnings = self._export_with(texture=missing)
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("wasn't found", warnings[0])
        self.assertIn("not_here.png", warnings[0])

    def test_non_power_of_two_png_warns(self) -> None:
        image = bpy.data.images.new("npot", 6, 4)
        path = self.tmp / "npot.png"
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
        bpy.data.images.remove(image)
        warnings = self._export_with(texture_lit=str(path))
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("is 6x4, not a power of two", warnings[0])

    def test_dds_sizes(self) -> None:
        good = write_dds(self.tmp / "good.dds", 256, 1024)
        bad = write_dds(self.tmp / "bad.dds", 200, 256)
        warnings = self._export_with(texture=str(good), texture_normal=str(bad))
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("'" + str(bad) + "' is 200x256", warnings[0])

    def test_wrong_file_type_warns(self) -> None:
        # .pss is an allowed resource type, but not for a texture
        warnings = self._export_with(texture=str(self.tmp / "particles.pss"))
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("must be a PNG or DDS", warnings[0])

    def test_not_really_a_png_warns(self) -> None:
        fake = self.tmp / "fake.png"
        fake.write_bytes(b"not an image at all")
        warnings = self._export_with(texture=str(fake))
        self.assertEqual(len(warnings), 1, warnings)
        self.assertIn("doesn't start like a PNG", warnings[0])

    def test_read_image_size(self) -> None:
        self.assertEqual(XPlaneHeader.read_image_size(str(WHITE_128)), (128, 128))
        self.assertEqual(XPlaneHeader.read_image_size(str(write_dds(self.tmp / "s.dds", 512, 64))), (512, 64))
        self.assertIsNone(XPlaneHeader.read_image_size(str(self.tmp / "nope.png")))


runTestCases([TestTextureChecks])
