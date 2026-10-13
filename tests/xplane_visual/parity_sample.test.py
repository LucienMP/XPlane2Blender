"""
The X-Plane visual checks: opt-in, since they start X-Plane itself (about three minutes
per mode). Run them with

    python tests.py --xplane

which sets XP2B_XPLANE_TESTS=1 and includes this folder; without it the suite skips it.
X-Plane must be installed (XPLANE_DIR, default E:\\X-Plane 12), closed, with its Web API on.
"""
import os
import subprocess
import sys
import unittest

import bpy

from io_xplane2blender.tests import *

ADDON = os.path.dirname(os.path.abspath(__import__("io_xplane2blender").__file__))
PARITY_PY = os.path.join(ADDON, "xplane_parity", "parity.py")


@unittest.skipUnless(os.environ.get("XP2B_XPLANE_TESTS"), "X-Plane visual checks run only with tests.py --xplane")
class TestParitySample(XPlaneTestCase):
    """The sample scene passes every mode of the visual parity check in X-Plane"""

    work = os.path.join(get_tmp_folder(), "parity_sample")

    def _parity(self, *args):
        command = [sys.executable, PARITY_PY, "--blender", bpy.app.binary_path, *args]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        print(result.stdout[-4000:])
        return result

    def test_1_sample(self) -> None:
        self.assertEqual(self._parity("sample", "--blend", os.path.join(self.work, "sample.blend")).returncode, 0)

    def _run_mode(self, mode):
        result = self._parity("run", os.path.join(self.work, "sample.blend"), "parity_sample", "--mode", mode,
                              "--work", os.path.join(self.work, mode), "--dataref", "sim/cockpit2/controls/flap_ratio=0.75")
        report = os.path.join(self.work, mode, "report.txt")
        self.assertTrue(os.path.exists(report), result.stdout[-2000:])
        text = open(report, encoding="utf-8").read()
        self.assertIn("RESULT: PASS", text, text)
        self.assertEqual(result.returncode, 0)

    def test_2_palette(self) -> None:
        self._run_mode("palette")

    def test_3_textured(self) -> None:
        self._run_mode("textured")

    def test_4_lights(self) -> None:
        self._run_mode("lights")


runTestCases([TestParitySample])
