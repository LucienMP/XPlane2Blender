"""
#284 in X-Plane: XPlane2Blender's IF / ELSE IF / ELSE chains, an always-taken ELSE, and
Laminar's IF NOT SCENERY_SHADOWS, with scenery shadows on (the user's setting, quality 4)
and off (shadow quality 0, which settings.txt ties to the SCENERY_SHADOWS condition).
Blender shows the branches X-Plane should draw; the shapes check compares them.

Opt-in: python tests.py --xplane (X-Plane closed, Web API on).
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
class TestParityConditions(XPlaneTestCase):
    work = os.path.join(get_tmp_folder(), "parity_conditions")

    def _parity(self, *args):
        command = [sys.executable, PARITY_PY, "--blender", bpy.app.binary_path, *args]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace")
        print(result.stdout[-4000:])
        return result

    def _check(self, name, *args):
        blend = os.path.join(self.work, "sample.blend")
        work = os.path.join(self.work, name)
        result = self._parity("run", blend, "parity_sample", "--work", work, "--condition", "VERSION10=1", *args)
        report = os.path.join(work, "report.txt")
        self.assertTrue(os.path.exists(report), result.stdout[-2000:])
        text = open(report, encoding="utf-8").read()
        self.assertIn("RESULT: PASS", text, text)
        self.assertEqual(result.returncode, 0)
        model = open(os.path.join(work, "model.obj")).read()
        lines = [l.strip() for l in model.splitlines()]
        # The ELSE IF branch is written as ELSE plus a nested IF (X-Plane 12.4.3 ran a
        # real ELSE IF even when the IF before it was taken)
        self.assertNotIn("ELSE IF VERSION10", lines)
        at = lines.index("IF SCENERY_SHADOWS")
        self.assertEqual([l for l in lines[at:] if l and l.split()[0] in ("IF", "ELSE", "ENDIF")][:6],
                         ["IF SCENERY_SHADOWS", "ELSE", "IF VERSION10", "ELSE", "ENDIF", "ENDIF"])
        self.assertIn("IF NOT SCENERY_SHADOWS", lines)

    def test_1_sample(self) -> None:
        blend = os.path.join(self.work, "sample.blend")
        self.assertEqual(self._parity("sample", "--kind", "conditions", "--blend", blend).returncode, 0)

    def test_2_scenery_shadows_on(self) -> None:
        self._check("shadows_on", "--condition", "SCENERY_SHADOWS=1")

    def test_3_scenery_shadows_off(self) -> None:
        self._check("shadows_off", "--condition", "SCENERY_SHADOWS=0", "--xplane-pref", "renopt_shadow_quality_04=0")


runTestCases([TestParityConditions])
