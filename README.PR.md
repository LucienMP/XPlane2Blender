# XPlane2Blender 5.0: Blender 5 support, open pull requests, and fixes for 30 issues

## Summary

XPlane2Blender doesn't work on Blender 5. Exporting any animated scene fails, because Blender 5 removed the old animation API. 

The base of the update was taken from https://forums.x-plane.org/files/file/99499-xplane2blender-v5-unnofficial-for-blender-5/ and then Claude was used to under guidance to make further improvments for issues, enhancements, and changes listed in the upstream github.

This pull request makes XPlane2Blender work on Blender 5. It also:
- includes 7 of the 9 open pull requests, with each author kept as the commit author;
- fixes 29 open issues, and part of #284;
- adds some warnings and two small features;
- was tested with the full test suite on Blender 5.2, and many changes were also checked in X-Plane 12 itself.

Every change is explained in more detail, with links to the commits, in [REVIEW-5.0.md](REVIEW-5.0.md).

**Before merging, please note:**
- **Blender version:** `bl_info` now requires Blender 5.0. The code still reads older (non-slotted) Actions, so lowering this is possible if you want to keep Blender 4.x.
- **Fork-specific files:** the README and REVIEW-5.0.md were written for the fork, and the README points the bug tracker to it. You may want to drop or rewrite those parts.
- **Some exported files change.** The list is under [Changes to exported OBJs](#changes-to-exported-objs).

## Pull requests included

| PR | Author | What it does |
|---|---|---|
| #765 Fix Blender 5.x compatibility for slotted actions API | Rob P (@lehthanis) | The main Blender 5 fix: animation is read through the slot assigned to each object. Extended in this PR to cover bone animation and the dataref keyframe buttons (see #754, #190 below). |
| #767 `ATTR_manip_device` and negative loop values | ILIAS TSELIOS (@airfightergr) | New **Device** manipulator (X-Plane 12.1+), which makes a mesh a touch screen for a cockpit device. "Loop Animation Every" can be negative. |
| #753 "Blended" layer group for glass scenery | Connor Russell (@Connor-Russell) | Adds X-Plane 12.2.1 as a target and the **Blended** layer group. Fixed here: its reset when switching to an older version never ran on Blender 5, and ignored root objects. |
| #759 Decal dither parameter | Connor Russell | A *Dither Strength* for each detail texture (decal). The default is 0, so nothing changes for existing files. |
| #760 Relative directory without a file name | Connor Russell | An OBJ name ending in `/` exports into that folder, named after the root. |
| #761 Material errors with hierarchies across collections | Connor Russell | Material checks only look at objects actually exported in that OBJ, so there are no more false "incompatible material" errors. |
| #764 Scene report CSV | Rob P (@lehthanis) | **Export Scene Report (CSV)** lists every dataref and manipulator in the scene. Only its own commits were taken; it also contained a copy of #765. |

**Not included:**
- **#714:** it fixes the experimental importer, which isn't in `master`.
- **#681:** it links the README to an old 4.2 importer build.

## Fixes

Each fix is listed as **Problem**, **Fix** and **Tests**.

### Blender 5 and animation

**#758: XP2B 4.4.0 breakage in Blender 5**
- **Problem:** exporting any animated scene fails on Blender 5 with `'Action' object has no attribute 'fcurves'`.
- **Fix:** #765, as above. Animation is read through each object's slot.
- **Tests:** the whole suite runs on Blender 5.2. A new test checks that two objects sharing one Action, each through its own slot, export only their own animation.

**#754, #743, #762: bone dataref animation**
- **Problem:** bone dataref keyframes are stored in the armature data's slot. The exporter and the keyframe buttons looked in the wrong place, so bone animation wasn't exported, also on Blender 4.4 and 4.5.
- **Fix:** bone keyframes are found and edited through the armature data's slot.
- **Tests:** a new test checks adding, removing and exporting dataref keyframes on objects and bones.

**#190: wrong animation after removing a dataref**
- **Problem:** **Remove Dataref** left that dataref's keyframes behind. The next dataref then inherited them, so the exported animation was wrong.
- **Fix:** removing a dataref deletes its keyframes and renumbers the later ones, on objects and on bones. Bone dataref keyframes are now linear, like object ones.
- **Tests:** the same new keyframe test.

**#738: dataref values on the Bone tab aren't coloured**
- **Problem:** Blender can't colour (keyed or animated) a value stored on a bone by an add-on. This is a Blender limitation, [Blender #48975](https://projects.blender.org/blender/blender/issues/48975).
- **Fix:** a workaround. The Bone panel shows ◆ on a keyframe and ◇ when the value is animated, and turns the field red when the value was changed without re-keying.
- **Tests:** checked by hand in Blender's UI.

**#565: material Specular is hidden in Blender 5**
- **Problem:** `ATTR_shiny_rat` comes from the material's Specular. Blender 5 materials always use nodes, so Blender shows that setting nowhere.
- **Fix:** Specular is shown in the X-Plane material panel.
- **Tests:** checked in Blender's UI.

**#643, #516: Show/Hide on a bone isn't exported**
- **Problem:** the Bone tab lets you add Show/Hide, but it was never exported.
- **Fix:** it's written in the bone's animation block, so it shows or hides everything under the bone. Custom animation attributes on bones are exported too.
- **Tests:** a new test checks the output. In X-Plane 12, a box under a bone with a date-driven hide was hidden, and a control box stayed visible.

**(no issue) An Action with no slot chosen**
- **Problem:** an Action assigned with none of its slots chosen animates nothing, and the export said nothing about it.
- **Fix:** the export warns, once per object or armature, and says where to choose the slot.
- **Tests:** a new test.

### Export output

**#763: attributes only apply to the first LOD**
- **Problem:** X-Plane resets attributes at each `ATTR_LOD`, but they were only written once. For example, `ATTR_light_level` only applied to the first LOD.
- **Fix:** attributes are written again in each LOD.
- **Tests:** a new test. One existing test fixture had recorded the bug, and was corrected.

**#730: LODs make an OBJ with no geometry**
- **Problem:** with LODs on, objects that weren't assigned to any LOD were left out silently.
- **Fix:** a new root setting, **Objects in No LOD**, decides what happens, and the export warns, naming the objects. The choices:
  - **All Distances** (the default): in every LOD. With additive LODs, only the farthest LOD, because X-Plane draws every additive LOD in range.
  - **First LOD**.
  - **Not Exported**: the old behaviour.
  
  Objects with *Override LODs* on but nothing ticked are still left out on purpose, as before.
- **Tests:** a new test. Upstream's `test_AllIgnored` now checks "Not Exported". In X-Plane 12, the unassigned object now draws, and a box listed in two additive LODs drew twice.

**#709: vertices aren't shared between objects**
- **Problem:** with **Optimize** on, duplicate vertices were only merged within each object, so files with repeated parts were much bigger than needed.
- **Fix:** duplicates are merged across the whole OBJ.
- **Tests:** every test output that changed was expanded triangle by triangle, and draws exactly the same geometry. One fixture was regenerated. Checked in X-Plane 12.

**#439: `ATTR_shiny_rat 0` is written although it's the default**
- **Problem:** the line does nothing, because X-Plane starts at 0.
- **Fix:** it's only written to undo an earlier value, including after each `ATTR_LOD`.
- **Tests:** a new test. In X-Plane 12, no line and an explicit 0 rendered exactly the same.

**#741: symlinked textures**
- **Problem:** the texture path in the OBJ followed a symlink to its target.
- **Fix:** the symlink's own path is kept.
- **Tests:** no new automated test; the existing texture tests pass.

**(no issue) Custom spill lights give no light in X-Plane 12**
- **Problem:** X-Plane 12 reads a custom spill's size as an intensity in candela (`500cd`). XPlane2Blender wrote the size in metres, which gives little or no light.
- **Fix:** for X-Plane 12 targets, the light's Intensity is written in candela. Older targets are unchanged.
- **Tests:** test fixtures for both targets. In X-Plane 12, the old export left the ground dark and the new one lights it.

### Errors and messages

**#751: an empty root cancels the whole export with no message**
- **Fix:** the empty root is skipped with a warning. The status bar shows whether the export worked.
- **Tests:** no new automated test; the existing export tests pass.

**#752, #704: error in the Rain panel with nothing selected**
- **Fix:** the Rain panel and the wiper bake work with no active object.
- **Tests:** no new automated test; the existing rain tests pass.

**#725: DataRefs.txt can't be read on some Windows PCs** (partly fixed)
- **Fix:** the file is read as UTF-8, whatever the Windows language settings.
- **Not fixed:** one bad line still makes the whole file fail.

### New warnings

| Issue | Warning |
|---|---|
| #473, #577 | A texture path with a space. X-Plane only reads up to the space. |
| #285 | A mesh with no UV map in a textured OBJ. It shows as one colour, and some graphics cards draw it unpredictably. |
| #515 | Camera Collision in an Aircraft OBJ. Only cockpit objects use it (OBJ8 spec). Scenery types already refused it. |
| #279 | Slope Limit values outside −90 to 90 degrees, or a minimum above its maximum. The fields now also keep to that range. |
| #368, #489 | An Instanced Scenery Object that X-Plane won't instance: any animation, custom billboard lights, custom spills with a dataref, or named or parameterized lights with a software version in `lights.txt`. Each rule was checked in X-Plane 12 with 10,000 copies. |
| #370 | The old VLIGHT light types (Default, Flashing, Pulsing, Strobe, Traffic) are deprecated, because their position ignores parenting and animation. |

### X-Plane 12 features

**#621: mouse wheel on Drag Rotate manipulators**
- **Fix:** a Wheel setting, written as `ATTR_manip_wheel`.
- **Tests:** a new test. The export loads in X-Plane 12 without errors.

**#284: conditions** (partly done)
- **Problem:** the condition list was missing `SCENERY_SHADOWS`, the one condition Laminar's own scenery uses (a fake shadow under `IF NOT SCENERY_SHADOWS`).
- **Fix:** **Scenery Shadows** was added. The tooltips say that HDR and Version 10.x are always on in X-Plane 12.
- **Not done:** `ELSE` / `ELSE IF`. X-Plane 12 accepts them, but none of 24,714 OBJs in an X-Plane 12 install uses them.
- **Tests:** a new test. In X-Plane 12, both `IF` and `IF NOT` versions behave correctly.

### UI and tools

**#766: an empty X-Plane panel on the Data tab**
- **Fix:** the panel only appears for lights and empties, the only types that have settings there.
- **Tests:** a new test.

**#710: `tests.py` and `run.py` don't work on Windows**
- **Problem:** the scripts dropped the system environment. On Windows, git also checks out the `addons/modules` symlink as a plain text file, so Blender couldn't find the add-on.
- **Fix:** the environment is kept, and a link to the add-on is made in the temp folder when needed.
- **Tests:** `python tests.py` runs the whole suite on Windows: 628 test cases, 0 failures.

## Other changes

- **Blender 5 compatibility:**
  - Opening old .blend files works again. The updater used dictionary-style access that Blender 5 hides.
  - The wiper gradient bake works with current Cycles.
  - Python 3.12+ warnings are fixed.
- **`lights.txt`:** the bundled copy is now X-Plane 12.4.4's, so the 13 lights added since, such as the runway inset lights, are recognised.
- **New feature, publishing OBJs in `library.txt`:**
  - each root can be published under a library path, optionally by season (`EXPORT_SEASON`);
  - only a marked block of `library.txt` is changed;
  - seasons were checked in X-Plane 12 in both hemispheres.
- **Test helper:** `XP2B_TEST_OUTPUT_DIR` saves every test's output, for comparing exporter changes and regenerating fixtures.
- **`tools/xplane12_instancing_test`:** a tool that runs these checks in X-Plane itself.

## Changes to exported OBJs

Most files export exactly as before. These change:

- **Multi-LOD files:** attributes are repeated in each LOD (#763).
- **Files with LODs and unassigned objects:** those objects are now exported (#730).
- **Files with Optimize on:** fewer vertices, with identical geometry (#709).
- **Some files:** redundant `ATTR_shiny_rat 0` lines are gone (#439).
- **X-Plane 12 targets with custom spill lights:** the size is written as an intensity in candela (`5000cd`).

## Testing

- **Blender 5.2.2 LTS:** all 175 test files pass, including 15 new ones. Upstream's own `tests.py` also passes on Windows: 628 test cases.
- **Before this PR**, upstream `master` passed 35 of 160 test files on Blender 5.2.
- **X-Plane 12.4.4 and 12.4.3:** instancing, light intensities, conditions, seasons and the fixes above were checked in the sim with the tool in `tools/xplane12_instancing_test`. Its README has every result.
- **UI:** every X-Plane panel was drawn without errors for a mesh, a light and an armature.
- **Not tested:** Blender versions other than 5.2, and macOS and Linux.

## Not fixed

- **#701:** a custom `ATTR_light_level` on a parent is reset for each child. It's understood, but fixing it changes output, so it needs your decision.
- **#461, #576:** design choices. The findings are in REVIEW-5.0.md.
- **#755:** not reproducible on X-Plane 12.4.4.

## Second pass: bugs without an issue

After the fixes above, the whole add-on was read looking for unreported bugs. The results are in [REVIEW-5.0.md section 7](REVIEW-5.0.md#7-second-pass-code-audit). The most important: mirrored (negative-scale) meshes exported inside out (#747, which an earlier test couldn't detect), `ATTR_hud_reset` and `ATTR_poly_os 0` were never written, attributes set inside an `IF` block were assumed to still be in effect after `ENDIF`, custom attribute weights had been ignored since 4.1, texture paths were wrong when exporting with File > Export to another folder, and a light aimed exactly opposite its lights.txt direction got a zero rotation axis. Seven crashes became error messages.

## Issues closed by this PR

Fixes #758, fixes #754, fixes #743, fixes #762, fixes #190, fixes #763, fixes #751, fixes #752, fixes #704, fixes #565, fixes #741, fixes #473, fixes #577, fixes #370, fixes #738, fixes #368, fixes #489, fixes #621, fixes #730, fixes #643, fixes #516, fixes #709, fixes #439, fixes #285, fixes #515, fixes #279, fixes #766, fixes #710, fixes #747

Closes #765, closes #767, closes #753, closes #759, closes #760, closes #761, closes #764

🤖 Generated with [Claude Code](https://claude.com/claude-code)
