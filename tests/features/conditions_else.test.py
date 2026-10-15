"""
ELSE / ELSE IF conditions (#284): an object's "Else Of" setting writes it in the
ELSE of that object's IF, or an ELSE IF when it has a condition of its own.
X-Plane 12.4.4 accepts ELSE, ELSE IF and ELSE IF NOT (checked in the harness scene
conditionals_day).
"""
from typing import List

import bpy

from io_xplane2blender import xplane_constants
from io_xplane2blender.tests import *
from io_xplane2blender.tests import test_creation_helpers
from io_xplane2blender.tests.test_creation_helpers import KeyframeInfo

KEPT = {"IF", "ELSE", "ENDIF", "TRIS", "ATTR_hard", "ATTR_no_hard", "ANIM_begin", "ANIM_end"}


class TestConditionsElse(XPlaneTestCase):
    def setUp(self):
        super().setUp()
        test_creation_helpers.delete_everything()
        self.root = test_creation_helpers.create_datablock_empty(
            test_creation_helpers.DatablockInfo("EMPTY", "root")
        )
        self.root.xplane.isExportableRoot = True
        self.root.xplane.layer.export_type = xplane_constants.EXPORT_TYPE_SCENERY
        self.objects = {}
        for name in ("a_if", "b_else", "c_elseif", "d_after"):
            obj = test_creation_helpers.create_datablock_mesh(
                test_creation_helpers.DatablockInfo(
                    "MESH", name, parent_info=test_creation_helpers.ParentInfo(self.root)
                )
            )
            obj.xplane.override_weight = True
            obj.xplane.weight = len(self.objects)
            self.objects[name] = obj
        self.a, self.b, self.c, self.d = (self.objects[n] for n in ("a_if", "b_else", "c_elseif", "d_after"))
        self._condition(self.a, xplane_constants.CONDITION_GLOBAL_SHADOWS, True)
        self.b.xplane.else_of = self.a
        self.c.xplane.else_of = self.a
        self._condition(self.c, xplane_constants.CONDITION_VERSION10, False)
        logger.clearMessages()

    def _condition(self, obj, variable, value) -> None:
        condition = obj.xplane.conditions.add()
        condition.variable = variable
        condition.value = value

    def _lines(self) -> List[str]:
        """The directives that matter, whitespace normalised to single spaces"""
        out = self.exportExportableRoot(self.root)
        lines = [" ".join(l.split()) for l in out.splitlines()]
        return [l for l in lines if l and l.split()[0] in KEPT]

    def _animate(self, obj) -> None:
        test_creation_helpers.set_animation_data(obj, [
            KeyframeInfo(idx=1, dataref_path="sim/graphics/animation/sin_wave_2", dataref_value=0.0, location=(0, 0, 0)),
            KeyframeInfo(idx=2, dataref_path="sim/graphics/animation/sin_wave_2", dataref_value=1.0, location=(1, 0, 0)),
        ])

    def _errors(self) -> List[str]:
        self.exportExportableRoot(self.root)
        errors = [e["message"] for e in logger.findErrors()]
        logger.clearMessages()
        return errors

    def test_else_and_else_if_chain(self) -> None:
        self.assertEqual(
            self._lines(),
            [
                # The index table is in name order, the directives in written order.
                # The ELSE IF is a nested IF: X-Plane 12.4.3 ran an ELSE IF branch
                # even when the IF before it was taken
                "IF GLOBAL_SHADOWS",
                "TRIS 0 36",  # a_if
                "ELSE",
                "IF NOT VERSION10",
                "TRIS 72 36",  # c_elseif
                "ELSE",
                "TRIS 36 36",  # b_else
                "ENDIF",
                "ENDIF",
                "TRIS 108 36",  # d_after
            ],
        )

    def test_else_branch_can_be_animated(self) -> None:
        self._animate(self.b)
        lines = self._lines()
        self.assertEqual(lines[5:11], ["ELSE", "ANIM_begin", "TRIS 36 36", "ANIM_end", "ENDIF", "ENDIF"])

    def test_attribute_state_restarts_per_branch(self) -> None:
        hard = bpy.data.materials.new("hard")
        hard.xplane.surfaceType = xplane_constants.SURFACE_TYPE_CONCRETE
        self.a.data.materials[0] = hard
        lines = self._lines()
        # ATTR_hard inside the IF only; the branches start from the state before it,
        # so they need no ATTR_no_hard; after ENDIF the next object resets it, since
        # X-Plane may have run the IF branch
        self.assertEqual(lines.index("ATTR_hard concrete"), lines.index("IF GLOBAL_SHADOWS") + 1)
        self.assertEqual(lines.count("ATTR_no_hard"), 1)
        self.assertGreater(lines.index("ATTR_no_hard"), lines.index("ENDIF"))
        self.assertLess(lines.index("ATTR_no_hard"), lines.index("TRIS 108 36"))

    def test_if_object_must_have_one_condition(self) -> None:
        self._condition(self.a, xplane_constants.CONDITION_VERSION10, True)
        errors = self._errors()
        self.assertEqual(len(errors), 2, errors)  # b and c both complain
        self.assertIn("exactly one condition", errors[0])

    def test_if_object_cannot_be_animated(self) -> None:
        self._animate(self.a)
        errors = self._errors()
        self.assertTrue(errors and all("is animated" in e for e in errors), errors)

    def test_else_must_be_sibling(self) -> None:
        self.b.parent = self.d
        errors = self._errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("same parent", errors[0])

    def test_only_one_unconditional_else(self) -> None:
        self.d.xplane.else_of = self.a
        errors = self._errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("Only one can be the ELSE", errors[0])

    def test_else_of_an_else_is_an_error(self) -> None:
        self.d.xplane.else_of = self.b
        errors = self._errors()
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("is itself an Else object", errors[0])


runTestCases([TestConditionsElse])
