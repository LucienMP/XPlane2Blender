# XPlane2Blender 5.0: Blender 5 support, open pull requests, fixes for 44 issues, and a check in X-Plane

## In plain words

- **It works on Blender 5.** Before this, any animated model failed to export.
- **Seven community pull requests are included**, each under its author's name.
- **44 open issues are closed: bugs and feature requests.** Animation on bones exports again, removing a dataref no longer breaks the animation of the next one, levels of detail keep their settings, and mirrored parts are no longer inside out.
- **The exporter warns about more mistakes before X-Plane finds them:** misspelt datarefs, a missing `[0]` on an array dataref, missing or odd-sized textures, a scene unit scale that isn't metres, and models X-Plane won't instance.
- **Small things that save time:** after a failed export, the objects the errors name are selected and the log opens with one click; a progress cursor during long exports; a search list for light names; arrows to reorder datarefs.
- **Smaller, faster OBJs:** animations that don't actually move are written as one fixed step, and with Optimize on, triangles are ordered so the graphics card reuses more of its work.
- **`ELSE` and `ELSE IF` conditions**, so one object can replace another when a condition is off.
- **Check in X-Plane:** a button that exports the model, photographs it in X-Plane, renders the same views in Blender and shows them side by side with the differences in red. It checks shapes, textures and lights.
- **Tested:** 704 automated tests pass on Blender 5.2, a GitHub Actions workflow runs them on every push, and the changes that affect what X-Plane draws were checked in X-Plane 12 itself.

## Summary

XPlane2Blender doesn't work on Blender 5. Exporting any animated scene fails, because Blender 5 removed the old animation API. 

The base of the update was taken from https://forums.x-plane.org/files/file/99499-xplane2blender-v5-unnofficial-for-blender-5/ and then Claude was used to under guidance to make further improvments for issues, enhancements, and changes listed in the upstream github.

This pull request makes XPlane2Blender work on Blender 5. It also:
- includes 7 of the 9 open pull requests, with each author kept as the commit author;
- closes 44 open issues: 28 bugs from the issue list, #747 found by a code audit, #284 completed, and 14 feature requests; #725 is partly fixed;
- adds warnings, small features, export optimisations, and a visual check against X-Plane;
- was tested with the full test suite on Blender 5.2, and many changes were also checked in X-Plane 12 itself.

Every change is explained in more detail, with links to the commits, in [REVIEW-5.0.md](REVIEW-5.0.md).

**Before merging, please note:**
- **Blender version:** `bl_info` now requires Blender 5.0. The code still reads older (non-slotted) Actions, so lowering this is possible if you want to keep Blender 4.x.
- **Fork-specific files:** the README and REVIEW-5.0.md were written for the fork, and the README points the bug tracker to it. You may want to drop or rewrite those parts.
- **Some exported files change.** The list is under [Changes to exported OBJs](#changes-to-exported-objs).
- **A compiled file is committed:** `io_xplane2blender/xplane_parity/plugin/win.xpl`, the X-Plane plugin Check in X-Plane needs (200 KB, Windows). Its source and build script are next to it, and the CI workflow rebuilds it for release packages.
- **New files outside the add-on:** `.github/workflows/ci.yml` (tests, plugin build, release packages) and an opt-in test folder, `tests/xplane_visual`, which starts X-Plane.
- **Data model version 125:** new properties (the light search window, Else Of). Older files update as usual.

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

**#284: conditions**
- **Problem:** the condition list was missing `SCENERY_SHADOWS`, the one condition Laminar's own scenery uses (a fake shadow under `IF NOT SCENERY_SHADOWS`).
- **Fix:** **Scenery Shadows** was added. The tooltips say that HDR and Version 10.x are always on in X-Plane 12. `ELSE` and `ELSE IF` came later, under [Enhancements](#x-plane-features).
- **Tests:** a new test. In X-Plane 12, both `IF` and `IF NOT` versions behave correctly.

### UI and tools

**#766: an empty X-Plane panel on the Data tab**
- **Fix:** the panel only appears for lights and empties, the only types that have settings there.
- **Tests:** a new test.

**#710: `tests.py` and `run.py` don't work on Windows**
- **Problem:** the scripts dropped the system environment. On Windows, git also checks out the `addons/modules` symlink as a plain text file, so Blender couldn't find the add-on.
- **Fix:** the environment is kept, and a link to the add-on is made in the temp folder when needed.
- **Tests:** `python tests.py` runs the whole suite on Windows: 628 test cases, 0 failures.

## Enhancements (feature requests)

These were open feature requests. Each is small and independent.

### New checks when exporting

**#344, #68, #345: datarefs are checked**
- **Problem:** a misspelt dataref, or an array dataref without `[n]`, exports without complaint and simply doesn't work in X-Plane.
- **Change:** the export checks every dataref the OBJ uses (animations, show/hide on objects and bones, lights, light levels, manipulators, thermal sources, wipers) against X-Plane 12.4's `DataRefs.txt`, now bundled. It warns, once per OBJ, about a `sim/` dataref that isn't in the file, an array used without an element, an element past the end, an element on a non-array, and a space in the path. The same hint shows under the dataref field in the panels. Picking an array dataref in the search window fills in `[0]`. A plugin's own datarefs can't be in the file, so only their shape is checked.
- **Tests:** a new test with 14 cases. The parser now reads `float[56][10]` and `byte[]`, which X-Plane 12.4's file uses.

**#403: textures are checked**
- **Change:** every texture, decal, thermal and wiper texture path warns when it isn't a PNG or DDS, isn't on disk, doesn't start like a PNG or DDS file, or isn't a power of two in each dimension. Only the file's header is read.
- **Tests:** a new test with 8 cases, including a `//` path, which Windows read as a network share at first.

**#466: unit scale**
- **Change:** a scene Unit Scale other than 1 warns on export and in the Scene panel. OBJ coordinates are Blender units read as metres, so at 0.01 a length Blender shows as 1 m exports as 100 m.
- **Tests:** in the reorder test below.

### Working with the exporter

**#140, #239: find the problem after a failed export**
- **Change:** a failed export selects the objects its errors name (a bone's name selects its armature). The error popup shows how many errors and warnings there were and the first three, with **Open Export Log** and **Select Objects In Log** buttons; both are also in the Scene panel.
- **Tests:** a new test.

**#354: export progress**
- **Change:** the mouse cursor shows Blender's progress indicator and the status bar says which root is being collected or written. Cancelling isn't possible: Blender can't redraw during an operator.
- **Tests:** a new test.

**#561: light name search**
- **Change:** a search window next to the light Name field, like the dataref one, listing every light in `lights.txt` with its parameters, and which old lights don't work as Automatic lights.
- **Tests:** a new test.

**#401: reorder datarefs**
- **Change:** up and down arrows next to each dataref on the Object and Bone tabs. A dataref keeps its keyframes when it moves. Show/Hide are written, and X-Plane applies them, in this order.
- **Tests:** a new test, for objects and bones.

### Smaller, faster OBJs

**#253, #653, #562: animations that don't move**
- **Problem:** with two datarefs on one object, each dataref's keyframe table samples the object's position at its own keyframes. When only one of them moves it, the other's table has the same value on every row, and X-Plane still evaluates it every frame.
- **Change:** such a table is written as one fixed `ANIM_trans` or `ANIM_rotate` in the same place. By the OBJ spec it's the same transform. An all-zero table is dropped, as before. #235 is partly covered by this.
- **Tests:** a new test with 4 cases.

**#134: triangle order**
- **Change:** with **Optimize** on, each object's triangles are reordered for the graphics card's vertex cache (Tom Forsyth's method). The same triangles are drawn with fewer vertex shader runs: a shuffled 180,000-triangle grid went from 3.0 to 0.67 cache misses per triangle. It costs about 2 seconds per 100,000 triangles at export.
- **Tests:** a new test checks the same triangles come out, wound the same way, with fewer misses. Two fixtures were regenerated after a script confirmed they hold the same triangles.

### X-Plane features

**#284: `ELSE` and `ELSE IF`** (completes the issue)
- **Change:** an object's new **Else Of** setting names the object it's the alternative to. It's written in the `ELSE` of that object's `IF`, or as an `ELSE IF` when it has a condition of its own; several alternatives make a chain ending in one `ELSE`. The `IF` object needs exactly one condition and no animation, and both need the same parent; otherwise the export says why. Attributes are tracked separately in each branch.
- **Tests:** a new test with 8 cases. X-Plane 12.4.4 accepts `ELSE`, `ELSE IF` and `ELSE IF NOT`.

## Check in X-Plane

A button in the Scene panel answers one question: **does X-Plane draw the exported OBJ the way Blender shows the model?**

How a designer uses it:
1. Once: set the X-Plane folder in the add-on's preferences, and allow incoming traffic in X-Plane's network settings.
2. Close X-Plane, select the root, pose the model, and press **Check in X-Plane**. Choose a check: Shapes, Textures or Lights.
3. About three minutes later a window opens: one row per camera view, Blender on the left, X-Plane in the middle, differences in red on the right. The Scene panel says PASS or FAIL and which lines failed.

What happens in between: the add-on exports a copy of the scene, starts X-Plane, and a small plugin places the model in a black box at midnight, sets its datarefs and takes screenshots from six angles. Blender renders the same six views, and the pictures are compared colour by colour. Nothing in the .blend changes. During the check, other X-Plane plugins are moved aside so their windows don't appear in the screenshots, and put back afterwards.

The three checks:
- **Shapes:** every material becomes a flat colour, then shape, position, animation pose, show/hide and face direction are compared exactly.
- **Textures:** the model keeps its texture, which checks the UV mapping. X-Plane changes colours a little, so this check is loose.
- **Lights:** each light's position and colour. X-Plane's glow and spill have nothing to compare with in Blender, so spill is only reported as present or not.

It's also a command-line tool (`io_xplane2blender/xplane_parity/parity.py`) and an opt-in part of the test suite: `python tests.py --xplane`. The details, including what went wrong on the way there, are in [io_xplane2blender/xplane_parity/README.md](io_xplane2blender/xplane_parity/README.md). On the sample model, all three checks pass: shapes match to the pixel, textures agree on 91 to 93% of the model, and the light is within 8 pixels. The check also found a real modelling mistake while it was being built: faces wound inside out, which Blender draws and X-Plane hides.

## Continuous integration and release packages

`.github/workflows/ci.yml` runs on every push:
- the whole test suite, on Windows with Blender 5.2.2;
- a build of the X-Plane plugin from its source, with Laminar's SDK;
- the add-on zip, made by `mkbuild.py` with the freshly built plugin;
- on a tag starting with `v`, a GitHub release with that zip attached.

The X-Plane checks can't run there, since they need X-Plane installed.

## Other changes

- **Blender 5 compatibility:**
  - Opening old .blend files works again. The updater used dictionary-style access that Blender 5 hides.
  - The wiper gradient bake works with current Cycles.
  - Python 3.12+ warnings are fixed.
- **`lights.txt`:** the bundled copy is now X-Plane 12.4.4's, so the 13 lights added since, such as the runway inset lights, are recognised.
- **`DataRefs.txt`:** the bundled copy is now X-Plane 12.4's, with 389 datarefs added since the old one.
- **New feature, publishing OBJs in `library.txt`:**
  - each root can be published under a library path, optionally by season (`EXPORT_SEASON`);
  - only a marked block of `library.txt` is changed;
  - seasons were checked in X-Plane 12 in both hemispheres.
- **Test helper:** `XP2B_TEST_OUTPUT_DIR` saves every test's output, for comparing exporter changes and regenerating fixtures.
- **`tools/xplane12_instancing_test`:** a tool that runs the instancing and lighting checks in X-Plane itself. It now refuses to start while X-Plane is running.
- **`tests.py`:** `--xplane` adds the X-Plane checks; one test that only passed with the repository on drive C: now passes anywhere.

## Changes to exported OBJs

Most files export exactly as before. These change:

- **Multi-LOD files:** attributes are repeated in each LOD (#763).
- **Files with LODs and unassigned objects:** those objects are now exported (#730).
- **Files with Optimize on:** fewer vertices, with identical geometry (#709).
- **Some files:** redundant `ATTR_shiny_rat 0` lines are gone (#439).
- **X-Plane 12 targets with custom spill lights:** the size is written as an intensity in candela (`5000cd`).
- **Objects with a second dataref that doesn't move them:** that dataref's keyframe table becomes one fixed `ANIM_trans` or `ANIM_rotate` (#253).
- **Files with Optimize on:** triangles are in a different order, the same triangles (#134).
- **Files that use the new Else Of setting:** `ELSE` / `ELSE IF` lines (#284). Nothing changes for files that don't.

## Testing

- **Blender 5.2.2 LTS:** all 189 test files pass, 704 test cases, including 26 new files. Upstream's own `tests.py` also passes on Windows, and the same suite runs in GitHub Actions on every push.
- **Before this PR**, upstream `master` passed 35 of 160 test files on Blender 5.2.
- **X-Plane 12.4.4 and 12.4.3:** instancing, light intensities, conditions, seasons and the fixes above were checked in the sim with the tool in `tools/xplane12_instancing_test`. Its README has every result. Check in X-Plane passed all three of its checks on its sample model in X-Plane 12.4.3.
- **UI:** every X-Plane panel was drawn without errors for a mesh, a light and an armature.
- **Not tested:** Blender versions other than 5.2, and macOS and Linux (the Check in X-Plane plugin is Windows only).
- **Not yet checked in X-Plane:** the static animation change (#253) and `ELSE` chains (#284) exported by XPlane2Blender. Check in X-Plane can now do this in a few minutes each.

## Not fixed

- **#701:** a custom `ATTR_light_level` on a parent is reset for each child. It's understood, but fixing it changes output, so it needs your decision.
- **#461, #576:** design choices. The findings are in REVIEW-5.0.md.
- **#755:** not reproducible on X-Plane 12.4.4.

## Second pass: bugs without an issue

After the fixes above, the whole add-on was read looking for unreported bugs. The results are in [REVIEW-5.0.md section 7](REVIEW-5.0.md#7-second-pass-code-audit). The most important: mirrored (negative-scale) meshes exported inside out (#747, which an earlier test couldn't detect), `ATTR_hud_reset` and `ATTR_poly_os 0` were never written, attributes set inside an `IF` block were assumed to still be in effect after `ENDIF`, custom attribute weights had been ignored since 4.1, texture paths were wrong when exporting with File > Export to another folder, and a light aimed exactly opposite its lights.txt direction got a zero rotation axis. Seven crashes became error messages.

## Issues closed by this PR

Fixes #758, fixes #754, fixes #743, fixes #762, fixes #190, fixes #763, fixes #751, fixes #752, fixes #704, fixes #565, fixes #741, fixes #473, fixes #577, fixes #370, fixes #738, fixes #368, fixes #489, fixes #621, fixes #730, fixes #643, fixes #516, fixes #709, fixes #439, fixes #285, fixes #515, fixes #279, fixes #766, fixes #710, fixes #747, fixes #284, fixes #344, fixes #68, fixes #345, fixes #403, fixes #466, fixes #140, fixes #239, fixes #354, fixes #561, fixes #401, fixes #253, fixes #653, fixes #562, fixes #134

Closes #765, closes #767, closes #753, closes #759, closes #760, closes #761, closes #764

🤖 Generated with [Claude Code](https://claude.com/claude-code)
