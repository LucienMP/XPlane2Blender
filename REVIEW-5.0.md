# XPlane2Blender 5.0: review of the unofficial Blender 5 port and of upstream contributions

This document records where the 5.0 code came from: who wrote each part, what was adopted, what was left out and why, and what each change does for users.

The unofficial forum port reviewed in section 2 is kept unchanged on the branch [`reference/chatgpt-port-as-received`](https://github.com/LucienMP/XPlane2Blender/tree/reference/chatgpt-port-as-received) for comparison.

**About the `#numbers`:** every `#123` here refers to the **original repository, [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender)**, not to this fork. Each one is linked. Commit messages on this fork also mention these numbers, but there GitHub links them to this fork, which has no issues of its own.

**Commit links** point to commits on this fork's `master`.

## Contents
0. [At a glance](#at-a-glance)
1. [Where the code came from](#1-where-the-code-came-from)
2. [Review of the unofficial ChatGPT-assisted port](#2-review-of-the-unofficial-chatgpt-assisted-port)
3. [Upstream pull requests](#3-upstream-pull-requests)
4. [Upstream issues](#4-upstream-issues)
5. [Other changes made for 5.0](#5-other-changes-made-for-50)
6. [How 5.0 was tested](#6-how-50-was-tested)
7. [Second pass: code audit](#7-second-pass-code-audit)
8. [Enhancements and Check in X-Plane](#8-enhancements-and-check-in-x-plane-13-october-2026)
9. [Appendix: triage of all open upstream issues](#appendix-triage-of-all-open-upstream-issues-october-2026)

---

## At a glance

**What 5.0 contains** (details in sections 3 to 5 and 8):
- **Blender 5 support:** animation export with Blender 5's slotted Actions, including bone dataref animation and Actions shared by several objects through their slots; older .blend files update correctly; wiper baking works with current Cycles; the material panel shows Specular again.
- **29 upstream issues fixed in the first pass, and [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) partly (completed later, below):**
  - Blender 5 and animation: [#758](https://github.com/X-Plane/XPlane2Blender/issues/758), [#754](https://github.com/X-Plane/XPlane2Blender/issues/754), [#743](https://github.com/X-Plane/XPlane2Blender/issues/743), [#762](https://github.com/X-Plane/XPlane2Blender/issues/762), [#190](https://github.com/X-Plane/XPlane2Blender/issues/190), [#738](https://github.com/X-Plane/XPlane2Blender/issues/738), [#565](https://github.com/X-Plane/XPlane2Blender/issues/565).
  - Export correctness: [#763](https://github.com/X-Plane/XPlane2Blender/issues/763) (attributes in every LOD), [#730](https://github.com/X-Plane/XPlane2Blender/issues/730) (objects in no LOD), [#643](https://github.com/X-Plane/XPlane2Blender/issues/643) and [#516](https://github.com/X-Plane/XPlane2Blender/issues/516) (bone Show/Hide), [#709](https://github.com/X-Plane/XPlane2Blender/issues/709) (shared vertices), [#439](https://github.com/X-Plane/XPlane2Blender/issues/439) (redundant `ATTR_shiny_rat 0`), [#741](https://github.com/X-Plane/XPlane2Blender/issues/741) (symlinked textures).
  - Errors and messages: [#751](https://github.com/X-Plane/XPlane2Blender/issues/751), [#752](https://github.com/X-Plane/XPlane2Blender/issues/752), [#704](https://github.com/X-Plane/XPlane2Blender/issues/704), [#725](https://github.com/X-Plane/XPlane2Blender/issues/725) (partly).
  - New warnings: [#473](https://github.com/X-Plane/XPlane2Blender/issues/473) and [#577](https://github.com/X-Plane/XPlane2Blender/issues/577) (spaces in texture paths), [#285](https://github.com/X-Plane/XPlane2Blender/issues/285) (no UV map), [#515](https://github.com/X-Plane/XPlane2Blender/issues/515) (Camera Collision on aircraft), [#279](https://github.com/X-Plane/XPlane2Blender/issues/279) (Slope Limit), [#368](https://github.com/X-Plane/XPlane2Blender/issues/368) and [#489](https://github.com/X-Plane/XPlane2Blender/issues/489) (Instanced Scenery that X-Plane won't instance), [#370](https://github.com/X-Plane/XPlane2Blender/issues/370) (VLIGHT deprecated).
  - X-Plane 12 features: [#621](https://github.com/X-Plane/XPlane2Blender/issues/621) (mouse wheel on Drag Rotate), [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) (`SCENERY_SHADOWS` condition).
  - UI and tooling: [#766](https://github.com/X-Plane/XPlane2Blender/issues/766) (empty Data panel), [#710](https://github.com/X-Plane/XPlane2Blender/issues/710) (test runner on Windows).
- **Found while testing, no upstream issue:** custom spill lights gave no light in X-Plane 12; fixed.
- **15 feature requests done after the audit, and [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) completed** (section 8):
  - New checks on export: datarefs against X-Plane 12.4's `DataRefs.txt`, including a missing `[0]` on array datarefs ([#344](https://github.com/X-Plane/XPlane2Blender/issues/344), [#68](https://github.com/X-Plane/XPlane2Blender/issues/68), [#345](https://github.com/X-Plane/XPlane2Blender/issues/345)); textures that are missing, not PNG or DDS, or not a power of two ([#403](https://github.com/X-Plane/XPlane2Blender/issues/403)); a scene Unit Scale that isn't 1 ([#466](https://github.com/X-Plane/XPlane2Blender/issues/466)).
  - Easier to use: a failed export selects the objects its errors name and opens its log in one click ([#140](https://github.com/X-Plane/XPlane2Blender/issues/140), [#239](https://github.com/X-Plane/XPlane2Blender/issues/239)); a progress cursor and status text during export ([#354](https://github.com/X-Plane/XPlane2Blender/issues/354)); a light name search window ([#561](https://github.com/X-Plane/XPlane2Blender/issues/561)); arrows to reorder datarefs ([#401](https://github.com/X-Plane/XPlane2Blender/issues/401)).
  - **Smaller, faster OBJs:** keyframe tables that don't move are written as one static step ([#253](https://github.com/X-Plane/XPlane2Blender/issues/253), [#653](https://github.com/X-Plane/XPlane2Blender/issues/653), [#562](https://github.com/X-Plane/XPlane2Blender/issues/562); [#235](https://github.com/X-Plane/XPlane2Blender/issues/235) partly); with Optimize on, triangles are ordered for the GPU's vertex cache ([#134](https://github.com/X-Plane/XPlane2Blender/issues/134)).
  - `ELSE` and `ELSE IF` conditions through an object's "Else Of" setting, completing [#284](https://github.com/X-Plane/XPlane2Blender/issues/284).
- **Check in X-Plane** (section 8): a Scene panel button that exports the model, photographs it in X-Plane from six angles, renders the same views in Blender and opens them side by side with the differences in red. Three checks: shapes, textures and lights. Also a command-line tool and an opt-in part of the test suite (`tests.py --xplane`). The X-Plane plugin it needs is in the add-on package.
- **CI and release packages:** a GitHub Actions workflow runs the test suite on every push (Blender 5.2.2, Windows), builds the X-Plane plugin from source, packages the add-on zip, and publishes a GitHub release for tags starting with `v`. All its jobs pass.
- **7 of 9 upstream pull requests adopted:** [#765](https://github.com/X-Plane/XPlane2Blender/pull/765), [#767](https://github.com/X-Plane/XPlane2Blender/pull/767), [#753](https://github.com/X-Plane/XPlane2Blender/pull/753), [#759](https://github.com/X-Plane/XPlane2Blender/pull/759), [#760](https://github.com/X-Plane/XPlane2Blender/pull/760), [#761](https://github.com/X-Plane/XPlane2Blender/pull/761), [#764](https://github.com/X-Plane/XPlane2Blender/pull/764).
- **New features:** publishing OBJs in `library.txt`, including seasonal variants; the "Objects in No LOD" setting; the bundled `lights.txt` updated to X-Plane 12.4.4's and `DataRefs.txt` to X-Plane 12.4's.
- **Checked in X-Plane 12** (12.4.4 and 12.4.3), not only in the test suite: the instancing rules, light intensities, conditions, seasons and `library.txt`, and the later export fixes ([tool and results](https://github.com/LucienMP/XPlane2Blender/tree/master/tools/xplane12_instancing_test)). Check in X-Plane passed all three of its checks on its sample model ([results](https://github.com/LucienMP/XPlane2Blender/tree/master/io_xplane2blender/xplane_parity#results-on-the-sample-x-plane-1243-13-october-2026)).

**Still outstanding:**
- **Needs a decision:** [#701](https://github.com/X-Plane/XPlane2Blender/issues/701) (a parent's `ATTR_light_level`), [#461](https://github.com/X-Plane/XPlane2Blender/issues/461) (`GLOBAL_specular` with normal maps), [#576](https://github.com/X-Plane/XPlane2Blender/issues/576) (`NEG_DIR_MAG`), and `none` for custom spills without a dataref. Findings and options are in [section 4](#needs-your-decision).
- **Not started:** [#497](https://github.com/X-Plane/XPlane2Blender/issues/497) (unused bone Weight; upstream decided to remove it), [#746](https://github.com/X-Plane/XPlane2Blender/issues/746) and [#338](https://github.com/X-Plane/XPlane2Blender/issues/338) (packaging as a Blender Extension).
- **31 feature requests** of the 46 in the appendix (section D), and about 80 open issues that don't apply to 5.0 (appendix, section E).
- **Pull requests not adopted:** [#714](https://github.com/X-Plane/XPlane2Blender/pull/714) and [#681](https://github.com/X-Plane/XPlane2Blender/pull/681), both for the experimental importer, which isn't in 5.0.
- **Untested in X-Plane:** `IF NOT SCENERY_SHADOWS` with scenery shadows turned off in the graphics settings; the static keyframe tables ([#253](https://github.com/X-Plane/XPlane2Blender/issues/253)) and `ELSE` chains ([#284](https://github.com/X-Plane/XPlane2Blender/issues/284)) as XPlane2Blender exports them. Check in X-Plane can now check the last two in a few minutes each.
- **Check in X-Plane limits:** its plugin is Windows only; spill lights are only reported as present or absent; one sample model so far.

---

## 1. Where the code came from

| Source | Authors | Link | Used in 5.0? |
|---|---|---|---|
| **XPlane2Blender**, the original add-on (GPL-3.0) | Ted Greene, Ben Supnik, Amy Parent, Maya F. Eroğlu, and contributors (Laminar Research / X-Plane) | <https://github.com/X-Plane/XPlane2Blender> | **Yes, as the base.** 5.0 starts from upstream `master` at commit [`ee03ed6`](https://github.com/X-Plane/XPlane2Blender/commit/ee03ed6a96601199d7bccf3d65fb1378664e828e) ("Start 4.5.0 development"). |
| **"xplane2blender v5 unnofficial for Blender 5+"**, an unofficial port by xjs36uk, made with ChatGPT's help, posted in the *Utilities* file section of the X-Plane.Org forums in April 2026 | **xjs36uk** (X-Plane.Org forum user). The port's own `bl_info` still credits the original authors. | <https://forums.x-plane.org/files/file/99499-xplane2blender-v5-unnofficial-for-blender-5> | **No, not merged.** It was reviewed in full (section 2). Its central idea was right, but a cleaner implementation of the same fix (#765) was used instead. |
| **Open pull requests** on X-Plane/XPlane2Blender | Rob P, ILIAS TSELIOS, Connor Russell, galvedro, outbaacker | [open pull requests](https://github.com/X-Plane/XPlane2Blender/pulls) | 7 of 9 adopted (section 3) |
| **Open issues** on X-Plane/XPlane2Blender | Various reporters, listed per issue | [open issues](https://github.com/X-Plane/XPlane2Blender/issues) | 29 fixed, 1 partly done, 2 not reproducible, 3 for your decision, #701 investigated and left open, the rest triaged (section 4 and the appendix) |
| **Fixes and tests for 5.0** | Lucien Murray-Pitts ([LucienMP](https://github.com/LucienMP)), with Claude Code (commits carry a `Co-Authored-By: Claude` trailer) | <https://github.com/LucienMP/XPlane2Blender> | Yes, sections 3–5 |

### What the forum port contains
- **Base:** upstream tag [`v4.4.0-rc-1`](https://github.com/X-Plane/XPlane2Blender/tree/v4.4.0-rc-1). The forum page says it was adapted from version 4.4.0, and the files match that tag except for the port's own changes.
- **Changed files:**
  - `xplane_helpers.py`, `xplane_ops.py`, `xplane_types/xplane_bone.py` and `xplane_types/xplane_file.py`: the actual changes.
  - `xplane_config.py`: build number only.
  - `xplane_props.py`: one blank line.
- **Notes:** it came with an OpenOffice document, `xplane2blender-V5-unofficial-changes.odt`. It describes the port as "fully working for both bones and empties" and says print statements "are necessary for Blender to commit the values".
- **On the reference branch:** commit [`a826e7f`](https://github.com/LucienMP/XPlane2Blender/commit/a826e7f0e02d0c779202acb2c5d422baf6a37a27) is that tag with the port's files copied over unchanged.

---

## 2. Review of the unofficial ChatGPT-assisted port

**Verdict: right diagnosis, unsafe implementation. Not merged.**

The port correctly found the main Blender 5 breakage. Blender 4.4 introduced *layered (slotted) Actions*, and Blender 5.0 removed the old `Action.fcurves` / `Action.groups` API. XPlane2Blender used that API everywhere, so on Blender 5 the exporter crashed as soon as a scene had any animation.

The port's implementation, however, broke other things:

| Port change | Problem found | Effect for a user if it had been included |
|---|---|---|
| `get_all_fcurves()` returns the F-curves of **every slot** in an Action | It doesn't check which slot belongs to the object being exported. | An Action shared by several objects could give one object another object's dataref animation. |
| `BONE_OT_add_xplane_dataref_keyframe` is **defined four times** in `xplane_ops.py` | Python keeps the last definition, and that one only does `return {"FINISHED"}`. | The bone **Add Keyframe** button does nothing. Bone dataref animation can't be created in the UI. Confirmed by a failing test (`bone_configurations_drag_rotate_detent_bone`). |
| `BONE_OT_remove_xplane_dataref` rewritten, with `execute` defined twice | It deletes a custom property (`xplane_dataref_N`) on the pose bone instead of removing the dataref from the bone. | The bone **Remove Dataref** button no longer removes the dataref. |
| New `pose_bone["xplane_dataref_N"]` values plus `frame_set()` per keyframe while exporting | A second, parallel place to store dataref values that the rest of the add-on doesn't know about. | Values set in the X-Plane panel and values exported could disagree, and export becomes much slower. |
| `_pre_scan_all_keyframes()` wraps `action.fcurves` in `try/except AttributeError: continue` | On Blender 5, `action.fcurves` always raises, so the pre-scan **silently skips every Action**. | Export falls back to slow per-keyframe frame changes. The upstream `frame_set_optimization` test fails on time limits. |
| Debug output | `print()` calls in the export path, and a `# ANIM_KEYS: [...]` comment written into **every exported `.obj`** | Console spam, and changed output files |
| `OBJECT_OT_add_xplane_dataref_keyframe` | Comments out `makeKeyframesLinear` | Object dataref keyframes become Bézier, so Blender's preview no longer matches X-Plane's linear interpolation. |
| `xplane_header.py` | Unchanged, so it keeps the bug fixed upstream by [#745](https://github.com/X-Plane/XPlane2Blender/pull/745) (draped normal decal) | The port lacks that upstream fix. |

**Test results on Blender 5.2.2 LTS** (upstream test suite, same machine). All three runs include the test-suite fixes for Python 3.12+ (the removed `assertEquals` and similar). Without those, most tests can't run at all.

| Code | Test files passing |
|---|---|
| Upstream `master` as-is | 35 of 160 |
| Forum port | 153 of 159 |
| 5.0.0-beta.1 (`master` of this fork) | **175 of 175** (includes 15 new tests) |

**What was taken from the port:** only its diagnosis. The same fix had been submitted upstream as [#765](https://github.com/X-Plane/XPlane2Blender/pull/765). That version is slot-aware, keeps the existing data model and adds no debug code, so it was adopted instead and extended (section 3).

---

## 3. Upstream pull requests

All 9 pull requests open on X-Plane/XPlane2Blender in October 2026 were reviewed. Adopted ones were cherry-picked, so the original author is kept as the commit author.

### Adopted

| PR | Title | Author | 5.0 commits | Effect of including it |
|---|---|---|---|---|
| [#765](https://github.com/X-Plane/XPlane2Blender/pull/765) | Fix Blender 5.x compatibility for slotted actions API | Rob P ([@lehthanis](https://github.com/lehthanis)) | [`3c8aa64`](https://github.com/LucienMP/XPlane2Blender/commit/3c8aa6417496a8f360dc1dac2cc066013f3784bb), extended in [`22f23cb`](https://github.com/LucienMP/XPlane2Blender/commit/22f23cb3e29fffbdfdee071c3bbe28c397fa6016) | **The core Blender 5 fix.** Without it, any animated scene fails to export on Blender 5 (`'Action' object has no attribute 'fcurves'`). F-curves are now read through the slot assigned to each object. The extension also reads layered Actions on Blender 4.4/4.5 through their slot, fixing bone animations that weren't exported there either; it also corrects the bone keyframe/remove operators (see [#190](https://github.com/X-Plane/XPlane2Blender/issues/190) below). |
| [#767](https://github.com/X-Plane/XPlane2Blender/pull/767) | Adds `ATTR_manip_device` (touch screen manipulator) and removes `min` for loop animation to allow for negative loops | ILIAS TSELIOS ([@airfightergr](https://github.com/airfightergr)) | [`b744cab`](https://github.com/LucienMP/XPlane2Blender/commit/b744cab5111476cc61c23c184cc0823f571856eb), [`c020d8c`](https://github.com/LucienMP/XPlane2Blender/commit/c020d8c4ccff134e0025a9eaed4aac2ba90ae6a1); test [`0ea55c6`](https://github.com/LucienMP/XPlane2Blender/commit/0ea55c686cb1fd0f8b455d2038ec8db56b14b450) | New manipulator type **Device** (X-Plane 12.1+) that makes a mesh a touch screen for a cockpit device, including plugin avionics. It writes `ATTR_manip_device` and the matching `ATTR_cockpit_device` from the chosen *Screen Material*. "Loop Animation Every" can now be negative. The author tested it in X-Plane 12.4. |
| [#753](https://github.com/X-Plane/XPlane2Blender/pull/753) | Feature: Add "Blended" Layer Group for Glass Scenery Objects (X-Plane 12.21+) | Connor Russell ([@Connor-Russell](https://github.com/Connor-Russell)) | [`9465b80`](https://github.com/LucienMP/XPlane2Blender/commit/9465b80d830a6b91609716d2137bf38d8f67adb0) (squashed from the PR), fixed in [`5e571a3`](https://github.com/LucienMP/XPlane2Blender/commit/5e571a3cc48f7c5aab69752c17eb0ea96c6736dc) and [`53ad811`](https://github.com/LucienMP/XPlane2Blender/commit/53ad811eb2faf888636849143f37e42de3b97a90) | Adds "12.2.1" to *X-Plane Version* and makes it the default for new files. With 12.2.1 selected, *Layer Group* offers **Blended** for glass scenery. **5.0 fixes:** its safeguard that resets Blended when switching to an older version never ran on Blender 5 (it used `col.get("xplane")`, which Blender 5 hides), and it ignored root objects. Dynamic enum items are now kept referenced, as Blender requires. An invalid layer group is no longer exported as an empty `ATTR_layer_group` line. |
| [#759](https://github.com/X-Plane/XPlane2Blender/pull/759) | Feature: Decal Dither Parameter | Connor Russell ([@Connor-Russell](https://github.com/Connor-Russell)) | [`f2db66a`](https://github.com/LucienMP/XPlane2Blender/commit/f2db66a0d5ee6fa1b68f260c4086b69bd95d9bbe) | Adds a *Dither Strength* to each of the four detail textures (decals), written as the dither value of `DECAL_PARAMS` / `DECAL_PARAMS_PROJ`, which was hard-coded to 0.0. The default is 0, so existing exports don't change. |
| [#760](https://github.com/X-Plane/XPlane2Blender/pull/760) | Feature: Specify Relative Directory Without Specifying Filename | Connor Russell ([@Connor-Russell](https://github.com/Connor-Russell)) | [`3a88461`](https://github.com/LucienMP/XPlane2Blender/commit/3a884610f2d94f76bc56e1fffc7f228a8ec247ed) | An OBJ name ending in `/` or `\` is treated as a folder, and the file is named after the root collection or object. For example, `../objects/` exports `../objects/<root name>.obj`. Names not ending in a separator behave as before. |
| [#761](https://github.com/X-Plane/XPlane2Blender/pull/761) | Fix: Material Incompatibility Errors and Misconfiguration when Exporting Collections with Hierarchies That Span Collections | Connor Russell ([@Connor-Russell](https://github.com/Connor-Russell)) | [`9e81e11`](https://github.com/LucienMP/XPlane2Blender/commit/9e81e115668357e381e0166d6ee82d37490e267a) | Material compatibility checks now only use objects whose geometry is exported in that OBJ. Hierarchies spanning several collections no longer cause false "incompatible material" errors, or the wrong reference material and settings. |
| [#764](https://github.com/X-Plane/XPlane2Blender/pull/764) | Add scene report CSV export for datarefs and manipulators | Rob P ([@lehthanis](https://github.com/lehthanis)) | [`9f3bcff`](https://github.com/LucienMP/XPlane2Blender/commit/9f3bcff62557a572838442117ee420a6d3971f49), [`e4067b3`](https://github.com/LucienMP/XPlane2Blender/commit/e4067b33cea352a2689ed11760c1500fc247ee95), [`d5ed305`](https://github.com/LucienMP/XPlane2Blender/commit/d5ed3054293bbaf76df0c0bcea240aac2ef91c91) | Adds **Export Scene Report (CSV)** to the X-Plane Scene panel. It writes one CSV listing every dataref (with keyframe value ranges) and every manipulator (type, datarefs, commands, values) in the scene. It doesn't affect OBJ output. This PR also contained a copy of #765; only its own three commits were taken. |

### Not adopted

| PR | Title | Author | Reason | Effect if it had been included |
|---|---|---|---|---|
| [#714](https://github.com/X-Plane/XPlane2Blender/pull/714) | Fix: vertex normals neither exported nor imported correctly | [@galvedro](https://github.com/galvedro) | It targets the experimental **importer**, which isn't in `master`. It's based on a 2022 importer branch and touches 65 files, including large test fixtures. | Nothing, because the code it fixes isn't in 5.0. It would matter if the importer is revived (issue [#610](https://github.com/X-Plane/XPlane2Blender/issues/610)). |
| [#681](https://github.com/X-Plane/XPlane2Blender/pull/681) | Update README.md 2 | [@outbaacker](https://github.com/outbaacker) | It adds a README link to the 4.2.0-alpha.1 importer build, which doesn't apply to 5.0. | It would point readers to an old 4.2 build. |

---

## 4. Upstream issues

### Fixed in 5.0

| Issue | Title | Reported by | 5.0 commits | Effect of the fix |
|---|---|---|---|---|
| [#758](https://github.com/X-Plane/XPlane2Blender/issues/758) | XP2B 4.4.0 breakage in Blender >5.0.0 | [@JT8D-17](https://github.com/JT8D-17) | [`3c8aa64`](https://github.com/LucienMP/XPlane2Blender/commit/3c8aa6417496a8f360dc1dac2cc066013f3784bb) ([#765](https://github.com/X-Plane/XPlane2Blender/pull/765)), [`22f23cb`](https://github.com/LucienMP/XPlane2Blender/commit/22f23cb3e29fffbdfdee071c3bbe28c397fa6016) | Animated scenes export on Blender 5. |
| [#754](https://github.com/X-Plane/XPlane2Blender/issues/754) | Appears bone animations are still not compatible with 4.5 | [@kkaigle](https://github.com/kkaigle) | [`22f23cb`](https://github.com/LucienMP/XPlane2Blender/commit/22f23cb3e29fffbdfdee071c3bbe28c397fa6016) | Bone dataref keyframes sit in the Armature data's slot of a layered Action. They are now found through that slot instead of the legacy `action.fcurves`, which only shows the first slot. |
| [#743](https://github.com/X-Plane/XPlane2Blender/issues/743) | Bone keyframes for datarefs | [@Im-Unknown-now](https://github.com/Im-Unknown-now) | [`22f23cb`](https://github.com/LucienMP/XPlane2Blender/commit/22f23cb3e29fffbdfdee071c3bbe28c397fa6016) | Same cause as #754. Bone dataref keyframes can be added and are exported. |
| [#762](https://github.com/X-Plane/XPlane2Blender/issues/762) | Unable to export blender files to X-plane planemaker 12.4 version. | [@iitkflightsimulator02-coder](https://github.com/iitkflightsimulator02-coder) | as #754 | Triaged as the same bug as #754. Not reproduced separately. |
| [#190](https://github.com/X-Plane/XPlane2Blender/issues/190) | Incorrect Animations in OBJ's when using an armature | [@JasonGilholme](https://github.com/JasonGilholme) | [`22f23cb`](https://github.com/LucienMP/XPlane2Blender/commit/22f23cb3e29fffbdfdee071c3bbe28c397fa6016) | **Remove Dataref** now deletes that dataref's keyframes and renumbers the later ones. Before, the later datarefs inherited the wrong keyframes. For bones it also looks on the right datablock, which was the "long standing bug" noted in `xplane_bone.py`. Bone dataref keyframes are now linear, like object ones. Covered by a new test. |
| [#763](https://github.com/X-Plane/XPlane2Blender/issues/763) | LOD light_level attr exported incorrectly | [@ddenn](https://github.com/ddenn) | [`d90ec03`](https://github.com/LucienMP/XPlane2Blender/commit/d90ec033aad5e9739a402f2c1e6179466ad353d5), [`69ba8e7`](https://github.com/LucienMP/XPlane2Blender/commit/69ba8e7f08a754b26c7f8b057cd98d63b0eaf2dc) | X-Plane resets attributes at each `ATTR_LOD`. Attributes such as `ATTR_light_level` and `ATTR_shiny_rat` are now written again in every LOD, not just the first. **This changes output** for multi-LOD files; one upstream test fixture had recorded the bug and was corrected. |
| [#751](https://github.com/X-Plane/XPlane2Blender/issues/751) | Unable to export | [@yury620](https://github.com/yury620) | [`56f95b1`](https://github.com/LucienMP/XPlane2Blender/commit/56f95b1de8a8448b10587a214c81887b9d8bbbbb) | A root with nothing in it used to cancel the whole export with no message. It's now skipped with a warning. Success or failure is shown in the status bar, and the current frame is restored on every exit path. |
| [#752](https://github.com/X-Plane/XPlane2Blender/issues/752) | Attribute Error: 'NoneType' object has no attribute 'xplane' | [@Rob-Neary](https://github.com/Rob-Neary) | [`e6a16e5`](https://github.com/LucienMP/XPlane2Blender/commit/e6a16e5aaca94a0f830576081990bb9eeb420848), [`07a290c`](https://github.com/LucienMP/XPlane2Blender/commit/07a290c2ab534d8c3d5e6fd64ba3680e0535e66a) | The Rain panel and the wiper bake operator no longer raise an error when no object is active, for example in an empty scene at startup. |
| [#704](https://github.com/X-Plane/XPlane2Blender/issues/704) | Error in "xplane_ui.py" with Blender 3.2 | [@AlteredWolf](https://github.com/AlteredWolf) | as #752 | Triaged as the same error as #752. |
| [#565](https://github.com/X-Plane/XPlane2Blender/issues/565) | 280: EEVEE vs Cycles? | [@tngreene](https://github.com/tngreene) | [`e6a16e5`](https://github.com/LucienMP/XPlane2Blender/commit/e6a16e5aaca94a0f830576081990bb9eeb420848) | `ATTR_shiny_rat` comes from the material's non-node *Specular*. Blender 5 materials always use nodes, so Blender shows that setting nowhere and the add-on's advice to "turn off Use Nodes" was impossible. It's now shown in the X-Plane material panel. |
| [#741](https://github.com/X-Plane/XPlane2Blender/issues/741) | Symlinked texture files follow the link (obj header) when exported. | [@danklaue](https://github.com/danklaue) | [`6d13bdb`](https://github.com/LucienMP/XPlane2Blender/commit/6d13bdb2f0b4656adcf342c016f325dbd03188b9) | Texture paths in the OBJ header keep the symlink's own path, not the path of its target. |
| [#473](https://github.com/X-Plane/XPlane2Blender/issues/473) | No validation for textures having a space in the file name | [@tngreene](https://github.com/tngreene) | [`6d13bdb`](https://github.com/LucienMP/XPlane2Blender/commit/6d13bdb2f0b4656adcf342c016f325dbd03188b9) | Paths with spaces now give a **warning**, because X-Plane only reads up to the first space. It's a warning rather than an error so existing exports aren't blocked. |
| [#577](https://github.com/X-Plane/XPlane2Blender/issues/577) | Validate TEXTURE field that texture does not have spaces in it | [@tngreene](https://github.com/tngreene) | as #473 | Same as #473. |
| [#725](https://github.com/X-Plane/XPlane2Blender/issues/725) | Dataref could not be parsed | [@pilotRL](https://github.com/pilotRL) | [`5688f8d`](https://github.com/LucienMP/XPlane2Blender/commit/5688f8d90722106a40a28274fa4cb97b5118f0ba) | **Partly fixed.** `DataRefs.txt` is now read as UTF-8 regardless of the Windows code page. One invalid line still makes the parser reject the whole file. |
| [#370](https://github.com/X-Plane/XPlane2Blender/issues/370) | Deprecate VLIGHT from XPlaneLights | [@tngreene](https://github.com/tngreene) | [`c84d1a8`](https://github.com/LucienMP/XPlane2Blender/commit/c84d1a887e9cfddf477f0604e58f34d5da282922) | **Default** is now labelled deprecated, like Flashing, Pulsing, Strobe and Traffic already were. Exporting any of these old VLIGHT light types gives a warning, because they are written from the light's raw location: parenting, root offsets and animation are ignored (noted by Ted Greene in the issue). Use **Automatic** instead. Exported files don't change. |
| [#738](https://github.com/X-Plane/XPlane2Blender/issues/738) | Dataref values in Bone Tab aren't colored | [@skijeffory](https://github.com/skijeffory) | [`23a4987`](https://github.com/LucienMP/XPlane2Blender/commit/23a4987a281ff79096bc5606fc4df7eb7c802e9b) | **Worked around; the cause is a long-standing Blender limitation.** Blender colours an animated field by building the field's data path from the datablock that owns it, then looking for an F-curve with that path. For add-on property groups stored on a bone, Blender can't build that path: `path_from_id()` fails with "does not support path creation". Blender is inconsistent here: the same property group on an object works (`xplane.datarefs[0].value`), a plain custom property on the same bone works (`bones["Bone"]["plain"]`), and Blender can *follow* the bone path when given it as text, which is how the keyframes are inserted, played back and exported. So keyframes always worked; only the colouring was missing. **Workaround:** the Bone panel looks up the F-curve itself and shows the state next to **Value**, like Blender's own markers: ◆ keyframe on this frame, ◇ animated, and a **red field** when the value was changed without re-keying, which would otherwise be lost on the next frame change. Add-ons can't set Blender's yellow/green/orange field colours. Blender already tracks this as an open, confirmed To Do, [Blender #48975](https://projects.blender.org/blender/blender/issues/48975) (2016). It was first reported as [Blender #25746](https://projects.blender.org/blender/blender/issues/25746) in 2011 by der_On, XPlane2Blender's original author, for this very property. The workaround can be removed once Blender can build these paths. |
| [#368](https://github.com/X-Plane/XPlane2Blender/issues/368) | Instanced Scenery Object Export Type is severly lacking in validations | [@tngreene](https://github.com/tngreene) | [`7c1be6e`](https://github.com/LucienMP/XPlane2Blender/commit/7c1be6ee8969a4cff4eb47fd4e2e7304900d6a73) | Exporting an **Instanced Scenery Object** that contains any animation now warns, naming the animated objects. X-Plane silently draws such objects one by one, which is much slower. **Checked in X-Plane 12.4.4** with [a test that places 10,000 copies](https://github.com/LucienMP/XPlane2Blender/tree/master/tools/xplane12_instancing_test) and reads how many X-Plane instanced: rotation, translation and show/hide each stop instancing. A mid-object `ATTR_shiny_rat` stops it too, but instanced exports already write that as `GLOBAL_specular`; `ATTR_hard` doesn't stop it. Warnings, not errors, so existing exports still work. |
| [#489](https://github.com/X-Plane/XPlane2Blender/issues/489) | Instanced Scenery has no validation for named and paramter lights used | [@tngreene](https://github.com/tngreene) | [`7c1be6e`](https://github.com/LucienMP/XPlane2Blender/commit/7c1be6ee8969a4cff4eb47fd4e2e7304900d6a73) | Exporting an **Instanced Scenery Object** now warns for each light that stops instancing, saying why. **Checked in X-Plane 12.4.4** with the same test: custom billboard lights are never instanced; custom spill lights are, unless they use a dataref; named and parameterized lights (and Automatic ones) are, unless X-Plane's `lights.txt` defines them with a `BILLBOARD_SW` or `SPILL_SW` version. The rules in the 2019 issue still hold, and match Laminar's 2016 guidance that "only some named lights are instancing friendly". |
| [#621](https://github.com/X-Plane/XPlane2Blender/issues/621) | Add wheel support for Drag Rotate manipulators | [@tngreene](https://github.com/tngreene) | [`f9859ce`](https://github.com/LucienMP/XPlane2Blender/commit/f9859ce41ab435227b998d13174e57f938c7913a) | Drag Rotate manipulators get the **Wheel** setting, written as `ATTR_manip_wheel` inside the manipulator. The current OBJ8 spec says the wheel works "after any manipulator that uses a single dataref"; XPlane2Blender's exported Drag Rotate + wheel OBJ loads in X-Plane 12.4.4 without errors. Scrolling the wheel in the cockpit wasn't tested (it needs a person at the controls). |
| (no issue) | Custom spill lights give no light in X-Plane 12 | Found while testing #489 | [`6109808`](https://github.com/LucienMP/XPlane2Blender/commit/610980851d931404b826bddd609bc09e89dc018f) | **Confirmed in X-Plane 12.4.4:** X-Plane 12 reads a custom spill's size as its intensity, in candela with a `cd` suffix. XPlane2Blender wrote the size in meters as a bare number (typically 15-67), which gives little or no light. Its old export left the ground dark; the fixed export lit it. For X-Plane 12+ targets, custom spills now write the light's **Intensity** (the candela setting Automatic lights already use), and the panel shows Intensity instead of Size. Older X-Plane targets are unchanged. **Changes output** for X-Plane 12 exports with custom spills. |
| [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) | OBJ conditionals is not implemented properly, or hardly at all | [@tngreene](https://github.com/tngreene) | [`ef1ba5c`](https://github.com/LucienMP/XPlane2Blender/commit/ef1ba5c907f184d86a9bc83f4af56e41cfaa0f2a) | **Done: the missing variable is added, and `ELSE` / `ELSE IF` since 13 October 2026.** X-Plane 12.4.4 knows five variables (found in its executable and each checked in the sim): `GLOBAL_LIGHTING`, `GLOBAL_SHADOWS`, `SCENERY_SHADOWS`, `VERSION10` and the undocumented `VERSION12`. Any other name, such as `VERSION11` or `SEASONAL`, logs "unknown variable for IF statement". The condition list lacked **`SCENERY_SHADOWS`**, the only variable used in a default X-Plane 12 install: Laminar's static CRJ-200 draws a fake ground shadow under `IF NOT SCENERY_SHADOWS`. It's now offered as "Scenery Shadows", and works in X-Plane 12.4.3: XPlane2Blender's `IF NOT SCENERY_SHADOWS` export was hidden with shadows on, its `IF SCENERY_SHADOWS` export was shown, and neither logged an error. The tooltips say HDR and Version 10.x are always on in X-Plane 12. `ELSE` / `ELSE IF` work in X-Plane 12.4.4 but no OBJ in a default install uses them (24,714 scanned). They're now written through an object's "Else Of" setting (see the README). |
| [#730](https://github.com/X-Plane/XPlane2Blender/issues/730) | LOD setting causes incomplete obj-file | [@fsspn](https://github.com/fsspn) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | With LODs on, objects that neither they nor a parent assigned to an LOD (*Override LODs*) were left out silently, so the reporter's OBJ had no geometry. A root's new **Objects in No LOD** setting decides, and the export warns, naming them: **All Distances** (default; every LOD, or only the farthest when LODs are additive), **First LOD**, or **Not Exported** (the old behaviour). **Checked in X-Plane 12.4.3:** the reporter's case now draws, "Not Exported" reproduces the bug, and a half-transparent box in both of two additive LODs drew about twice as opaque as one in the far LOD only, confirming the spec that additive LODs all draw. An object with *Override LODs* on but nothing ticked is still left out on purpose; upstream's `test_AllIgnored` fixture recorded the silent case, and now checks "Not Exported". **Changes output** only for files that were losing geometry. |
| [#643](https://github.com/X-Plane/XPlane2Blender/issues/643) | Should bones support Show/Hide animation? | [@todirbg](https://github.com/todirbg) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | Show/Hide set in the **Bone** tab is exported, written in the bone's `ANIM_begin`/`ANIM_end`, so it shows or hides everything under the bone (what the reporter wanted for a bone chain). The bone's custom animation attributes were ignored the same way and are exported too. The Instanced Scenery warning (#368) counts them. **Checked in X-Plane 12.4.3:** a box under a bone with `ANIM_hide` by date was hidden; the same with a range not matching the date stayed visible. |
| [#516](https://github.com/X-Plane/XPlane2Blender/issues/516) | Show/Hide only allowed on Objects, shown on Armature/Bone Panel UI | [@tngreene](https://github.com/tngreene) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | As #643. |
| [#709](https://github.com/X-Plane/XPlane2Blender/issues/709) | Vertex Optimization on Export | [@ian-m-carr](https://github.com/ian-m-carr) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | With **Optimize** on (off by default), identical vertices (position, normal, UV) are shared across the whole OBJ instead of per object, as the reporter proposed. **Checked:** of 369 test outputs, the 9 that changed (all with Optimize on) were expanded triangle by triangle and draw exactly the same geometry, with fewer vertices (e.g. 1436 → 1076 in an animated test file). Only one fixture compares vertex tables and was regenerated; the others filter them out. In X-Plane 12.4.3 two identical animated boxes (24 instead of 48 vertices) looked the same as the unoptimized export. **Changes output** of files with Optimize on. |
| [#439](https://github.com/X-Plane/XPlane2Blender/issues/439) | ATTR_shiny_rat 0 written despite being X-Plane's default | [@tngreene](https://github.com/tngreene) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | X-Plane starts with no shininess, so `ATTR_shiny_rat 0` is only written to undo an earlier value, including after the reset at each `ATTR_LOD`. **Checked:** in the test outputs only redundant `ATTR_shiny_rat 0` lines disappeared, and the shininess in effect at every `TRIS` is unchanged; in X-Plane 12.4.3 a normal-mapped panel with no `ATTR_shiny_rat` and one with an explicit `0` rendered pixel-identical (0.5 and 1 differed). **Changes output** slightly. |
| [#285](https://github.com/X-Plane/XPlane2Blender/issues/285) | No UV-Mapping needs stronger warning | [@tngreene](https://github.com/tngreene) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | A mesh with no UV map in an OBJ with a texture now gives a warning saying what happens: every vertex gets texture position 0,0, so it shows as one colour, and (as Laminar found) some GPUs draw it unpredictably. Previously there was no message at all. |
| [#515](https://github.com/X-Plane/XPlane2Blender/issues/515) | 280: Camera Collision allowed in Aircraft Export Type | [@tngreene](https://github.com/tngreene) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | Camera Collision in an **Aircraft** OBJ now warns, in `validateAircraft` as the issue suggested. The OBJ8 spec: "Only triangles in the cockpit object can be in the camera plane." Scenery and Instanced exports already refused it with an error. It's still written, so existing exports don't change. |
| [#279](https://github.com/X-Plane/XPlane2Blender/issues/279) | Validate Slope Limit | [@tngreene](https://github.com/tngreene) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | The four Slope Limit fields now keep to the spec's −90 to 90 degrees, and setting a minimum above its maximum (or the reverse) moves the other end with it. Values saved before, which the fields can't correct, are caught by an export warning: outside −90 to 90, or minimum above maximum. |
| [#766](https://github.com/X-Plane/XPlane2Blender/issues/766) | no data object properties | [@TheRealTofferAviation](https://github.com/TheRealTofferAviation) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | The X-Plane panel on the **Object Data** tab showed for every object but only has settings for lights and (X-Plane 11.30+) empties; for meshes it was empty, which looked like part of the add-on was missing. It now only appears where it has settings. A mesh's settings are on the Object and Material tabs. |
| [#710](https://github.com/X-Plane/XPlane2Blender/issues/710) | run.py and tests.py replace rather than update environment | [@ian-m-carr](https://github.com/ian-m-carr) | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | Both scripts keep the system environment, as the reporter proposed. They also work on Windows clones, where git checks out the `addons/modules` symlink as a plain text file and Blender couldn't find the add-on: they make a junction for it in the temp folder. **Checked:** `python tests.py --blender ...` runs the whole suite on Windows with Blender 5.2: 628 test cases, 0 failures. |

### Not reproducible (Blender 5.2 / X-Plane 12.4.4)

| Issue | Title | Reported by | Result |
|---|---|---|---|
| [#747](https://github.com/X-Plane/XPlane2Blender/issues/747) | Mirrored (negative-scale) linked duplicates export with inverted normals | [@NuanFeng520](https://github.com/NuanFeng520) | **Correction: reproducible, and fixed in the second pass** ([`8ca9376`](https://github.com/LucienMP/XPlane2Blender/commit/8ca93768)). The first regression test only compared each triangle's winding with its normals, which also passes when both are inverted, which is exactly what happened: a −X child exported inside out. The −X−Y case passed because its determinant is positive. The test now checks normals and winding against the cube's centre. See [section 7](#7-second-pass-code-audit). |
| [#755](https://github.com/X-Plane/XPlane2Blender/issues/755) | Automatic light with spot_params_bb_pm : wrong intensity parameter | [@cpot](https://github.com/cpot) | **Not reproducible in X-Plane 12.4.4, no change.** The issue says `500cd` isn't understood and a bare number must be used. In X-Plane 12.4.4 ([test](https://github.com/LucienMP/XPlane2Blender/tree/master/tools/xplane12_instancing_test)), `LIGHT_PARAM spot_params_bb_pm` with `50cd`/`500cd`/`5000cd` lights, brighter for higher values, and XPlane2Blender's own Automatic light export (`5000cd`) lights. Bare numbers are on a different scale: `1` and `5` light, `50` and `500` give nothing, so the suggested change would make typical lights invisible. It may have behaved differently in the X-Plane version the reporter used (October 2025). |

### Needs your decision

Checked in X-Plane 12.4.4 ([tool and results](https://github.com/LucienMP/XPlane2Blender/tree/master/tools/xplane12_instancing_test)), except #701, which was investigated in the code. Each is a choice rather than a clear bug.

| Item | What was found | Options | Recommendation |
|---|---|---|---|
| [#461](https://github.com/X-Plane/XPlane2Blender/issues/461) Always write `GLOBAL_specular 1.0` with a normal map | In X-Plane 12.4.4 a normal map makes a surface clearly more reflective; `GLOBAL_specular` 0 → 1.0 changes it only a little. XPlane2Blender writes the material's Specular (0.5 by default). The OBJ8 spec still advises 1.0 with normal maps. | (a) Force 1.0 when there's a normal map (**changes output** of every normal-mapped OBJ, slightly); (b) keep using the material's Specular, which is now visible in the X-Plane material panel | (b): the effect is small and artists can set 1.0 themselves. |
| [#576](https://github.com/X-Plane/XPlane2Blender/issues/576) `NEG_DIR_MAG` light optimisation | An optimisation for one light aimed exactly down −X: write a negative magnitude instead of an extra 180° rotation. The current output is correct, just one animation longer. The issue's author called it "a very minor case". | (a) Implement (needs changes to the lights.txt parser and its own copy of lights.txt); (b) close | (b). |
| (no issue) Custom spill without a dataref: write `none` | XPlane2Blender writes nothing in the dataref position; the OBJ8 spec says `none`. In X-Plane 12.4.4 both give identical light. | (a) Write `none` to match the spec (**changes output** of those lines only); (b) leave as is | (a) is harmless and matches the spec, but not needed. |
| [#701](https://github.com/X-Plane/XPlane2Blender/issues/701) REGRESSION: a parent's custom `ATTR_light_level` is reset for each child | XPlane2Blender 4.0 let a custom `ATTR_light_level` on a parent cover its children; 4.2 and later write `ATTR_light_level_reset` before each child mesh, so it has no effect. Cause: every material that doesn't set a light level itself asks for the reset (`xplane_material.py`), and the command writer then undoes the parent's attribute. | (a) Don't write the reset for materials that don't use light level (**changes output**; the resets at LOD boundaries from #763 must keep working); (b) leave as is, and set the light level on the materials instead | (a), with tests of both cases, if 4.0's behaviour is wanted; it's the reporter's expectation and Ben Supnik's summary in the issue. |
| [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) `ELSE` / `ELSE IF` conditions | X-Plane 12.4.4 accepts `ELSE`, `ELSE IF` and `ELSE IF NOT`; XPlane2Blender writes only `IF` / `IF NOT` ... `ENDIF`. None of 24,714 OBJs in an X-Plane 12 install with add-on scenery uses them. | (a) Add them, e.g. as an "Else" object linked to its condition (UI design work); (b) leave for the future, documented in the README | **Done (a), 13 October 2026:** an object's "Else Of" setting writes it in the `ELSE` or `ELSE IF` of that object's `IF`. |

### Still open, not started

| Issue | Title | Reported by | State | Effect of fixing it |
|---|---|---|---|---|
| [#497](https://github.com/X-Plane/XPlane2Blender/issues/497) | Bone weight appears to be unused | [@tngreene](https://github.com/tngreene) | Not started | The bone panel's weight setting would affect draw order, or be removed from the UI. |
| [#746](https://github.com/X-Plane/XPlane2Blender/issues/746) and [#338](https://github.com/X-Plane/XPlane2Blender/issues/338) | Error adding extension / plugin into Blender 4.4 / Remove relative imports and circular dependencies | [@GitDaBytes](https://github.com/GitDaBytes), [@tngreene](https://github.com/tngreene) | Not started | Packaging as a Blender *Extension* (`blender_manifest.toml`, relative imports). 5.0 installs fine as a regular add-on with *Install from Disk* on Blender 5.2; this was verified. |
---

## 5. Other changes made for 5.0

These were found by running the upstream test suite and the UI on Blender 5.2.2, or were added for testing. None has an upstream issue.

| Change | Commit | Effect |
|---|---|---|
| Legacy-file updater uses the PropertyGroup instead of `datablock["xplane"]` | [`d361138`](https://github.com/LucienMP/XPlane2Blender/commit/d36113815b9f3d249c765006cebcb7f4079e9417) | Blender 5 hides add-on properties from dictionary-style access, so opening .blend files made with XPlane2Blender 3.x crashed the updater, and Blend Glass settings were lost. |
| Wiper gradient bake rewritten for current Cycles | [`07a290c`](https://github.com/LucienMP/XPlane2Blender/commit/07a290c2ab534d8c3d5e6fd64ba3680e0535e66a) | Cycles now needs the image node to be both *active and selected*, so baking failed. The operator now sets that up, and restores bake margin, frame, render engine and selection on every exit path. A failed bake used to leave the margin at 0. Blender-Internal code paths were removed. |
| **Bundled `lights.txt` updated to X-Plane 12.4.4's** (build 124414, `Resources/bitmaps/world/lites/lights.txt`, converted to LF line endings) | [`c578fdc`](https://github.com/LucienMP/XPlane2Blender/commit/c578fdc927f1b7492bd59c9f6b3a68700bcbc1bc) | The add-on uses this copy to validate light names and fill in parameters. The previous copy was older than X-Plane 12.4: it lacked 13 lights (`garden_bollard` and the `inset_edge_lirl`/`mirl` and `inset_thresh_lirl`/`mirl` runway inset lights), so they gave "unknown light" warnings. Laminar also retuned existing lights, e.g. taillight intensities and directions. All exporter tests pass with it unchanged; only the parser test's light count changed (479 → 492). Update it again from a newer X-Plane the same way. |
| Python 3.12+ cleanups | [`5688f8d`](https://github.com/LucienMP/XPlane2Blender/commit/5688f8d90722106a40a28274fa4cb97b5118f0ba), [`6df3b20`](https://github.com/LucienMP/XPlane2Blender/commit/6df3b203c1705e526035b1095fafdb6c23b3a940) | Removes invalid-escape `SyntaxWarning`s and a `return` inside `finally`. The test suite no longer uses the removed `assertEquals` or the renamed `bpy_types` module. |
| Version 5.0.0-beta.1 | [`e48d4e2`](https://github.com/LucienMP/XPlane2Blender/commit/e48d4e296948c57ee1c3c81dcf852696f2614d26) | Requires Blender 5.0+ (`bl_info`). Data model version 124. README updated, and the bug tracker points to this fork. |
| Slotted Actions: shared Actions tested, and a warning for an Action with no slot | [`1404fae`](https://github.com/LucienMP/XPlane2Blender/commit/1404faeda03497300dd156be6999315ea7e9db62) | Since Blender 4.4 one Action can animate several datablocks, each through its own slot. A test now checks that two objects sharing one Action each export only their own slot's animation (it worked with #765; the forum port's approach would have mixed them). An Action assigned with none of its slots chosen animates nothing in Blender and used to export no animation without a word; it now gives a warning saying where to choose the slot, once per object or armature. Not supported, as before 5.0: the NLA editor (stacked or blended Actions). |
| **X-Plane 12 test tool**, `tools/xplane12_instancing_test` | [`6fc3b41`](https://github.com/LucienMP/XPlane2Blender/commit/6fc3b418eb055d319d2ab00649d5717a78926e78), [`bac34d7`](https://github.com/LucienMP/XPlane2Blender/commit/bac34d7e7158c7bf115ee4a94e66b10a7336b119), [`0267f3c`](https://github.com/LucienMP/XPlane2Blender/commit/0267f3cbeae90c19df9b84be4c30321cbfd50f62) | Runs checks in X-Plane itself: installs a test scenery pack and plugin, starts X-Plane and a flight through its Web API, records datarefs and screenshots, quits (force-closing it at a stuck quit dialog), and restores X-Plane's settings afterwards. It measured instancing with 10,000 copies, compared lights and conditions side by side, tested seasons, and loaded XPlane2Blender's own exports for the fixes above. Its README has every result. |
| **Bundled `DataRefs.txt` updated to X-Plane 12.4's** | [`f901873`](https://github.com/LucienMP/XPlane2Blender/commit/f901873d4a5f9e17fdfe3fde34200a17e4457067) | Used by the dataref search window and, since [#344](https://github.com/X-Plane/XPlane2Blender/issues/344), by the dataref checks. The old copy lacked 389 datarefs. The parser now also reads the multi-dimensional types this file uses (`float[56][10]`, `byte[]`), sized flat as X-Plane's SDK reads them. |
| **GitHub Actions workflow**, `.github/workflows/ci.yml` | [`2327afe`](https://github.com/LucienMP/XPlane2Blender/commit/2327afe2eeae57be31704ae63bdfeace2e5ce1ec), [`c4cedb7`](https://github.com/LucienMP/XPlane2Blender/commit/c4cedb7da7b749d698738878efcb822b68b6180f) | On every push: the test suite on Windows with Blender 5.2.2, the X-Plane plugin built from source with Laminar's SDK, and the add-on zip from `mkbuild.py` with that plugin inside. A tag starting with `v` publishes a GitHub release with the zip. The first run found one test that only passed with the repository on drive C: ([`f4b771c`](https://github.com/LucienMP/XPlane2Blender/commit/f4b771c0b6070deb175620c033304aa90284ccdb)). |
| Version: data model 125 | [`592d1ac`](https://github.com/LucienMP/XPlane2Blender/commit/592d1acfb66c5e05e356ca5e884c2e036e0968d8) | New properties for the light search window and "Else Of". Older files update as usual. |
| Test helper: `XP2B_TEST_OUTPUT_DIR` | [`65c6595`](https://github.com/LucienMP/XPlane2Blender/commit/65c65957841642d0663127778e538ccdbf7b063d) | When set, every test that compares against a fixture also saves its output there. Used to prove #709 and #439 changed nothing they shouldn't (every changed output was compared triangle by triangle, and shininess at every `TRIS`), and to regenerate the one fixture #709 changed. |

### New: publishing OBJs in `library.txt`

No upstream issue asks for this; it was added for X-Plane 12's seasonal objects ([`ef1ba5c`](https://github.com/LucienMP/XPlane2Blender/commit/ef1ba5c907f184d86a9bc83f4af56e41cfaa0f2a)). Each root can publish its OBJ under a library path in `library.txt`, by season if wanted. See [the README](README.md#publishing-objs-in-librarytxt) for how to use it.

- **Commands:** `EXPORT`, `EXPORT_EXTEND`, `EXPORT_EXCLUDE`, `EXPORT_RATIO`, `EXPORT_BACKUP`, and the seasonal `EXPORT_SEASON`, `EXPORT_EXTEND_SEASON` and `EXPORT_EXCLUDE_SEASON`. That's every library command in the X-Plane 12.4.4 executable; there's no seasonal Ratio or Backup.
- **Where it's written:** at the scenery pack's root when exporting into `Custom Scenery/<pack>/`, otherwise in the export folder.
- **Safe with existing files:** only a block marked with the .blend file's name is changed. Each export replaces only the lines of the OBJs it wrote, so exporting one root, or turning the option off, leaves the rest alone.
- **Checks:** a path published both by season and not is an error; a season left uncovered is a warning, since X-Plane then shows nothing (confirmed in the sim).
- **How X-Plane picks the season** turned out not to follow the calendar. At 47°N, 21 June was still spring and 15 August summer, and the tropics stayed in spring all year. The southern hemisphere gets the opposite seasons: at Hobart (42.8°S) 15 January to 15 April were summer, June and August winter, and October spring, so one seasonal set of OBJs works in both hemispheres. The season is picked when the scenery loads. Details are in the [tool's results](https://github.com/LucienMP/XPlane2Blender/tree/master/tools/xplane12_instancing_test#season-and-librarytxt-results-12-october-2026).

---

## 6. How 5.0 was tested
- **Blender:** 5.2.2 LTS on Windows 11.
- **Upstream test suite:** **189 of 189 test files pass, 704 test cases**, also in GitHub Actions on every push. 26 files are new. The first 15 cover slotted Actions shared by several objects, the operators, LOD state, the Blended layer group, `ATTR_manip_device`, mirrored objects, the VLIGHT deprecation, the instancing warnings, the Drag Rotate wheel, `SCENERY_SHADOWS` conditions, the `library.txt` export, objects in no LOD, bone Show/Hide, the new warnings and the `ATTR_shiny_rat` default. The 11 added on 13 October cover the section 8 enhancements and Check in X-Plane's parts that don't need X-Plane (the palette conversion, the classifier, the comparisons and each check's export). `tests/xplane_visual` runs Check in X-Plane's three checks in X-Plane, opt-in with `tests.py --xplane`. Upstream's own runner, `tests.py`, also passes on Windows: 628 test cases, 0 failures (8 skipped). The run uses a parallel runner, with `tests/utils/lights_parser` run on its own because it temporarily replaces `lights.txt`.
- **Installation:** the release zip installs with Blender's *Install from Disk* into a clean profile, enables, and exports a valid OBJ.
- **UI:** in a real Blender window, every X-Plane panel (Scene, Render, Object, Data, Material, Bone) was drawn for a mesh, a light and an armature. None raised an error. The bone keyframe-state markers (#738) were checked on a keyframe, between keyframes, and after an unkeyed change.
- **X-Plane 12.4.4:** the instancing rules behind the #368/#489 warnings were checked in the sim, 15 variants with 10,000 copies each ([tool and results](https://github.com/LucienMP/XPlane2Blender/tree/master/tools/xplane12_instancing_test)).
- **X-Plane 12.4.4, visual checks:** side-by-side night and day scenes for #755, #284, #461, #621 and custom spill lights, including XPlane2Blender's own exports before and after the custom spill fix ([tool and results](https://github.com/LucienMP/XPlane2Blender/tree/master/tools/xplane12_instancing_test)).
- **X-Plane 12.4.4 and 12.4.3, seasons and `library.txt`:** `EXPORT_SEASON` at 47°N and 42.8°S across the year, at 38°S, in the tropics, and with a mid-flight date change; XPlane2Blender's own seasonal exports and `library.txt` end to end, including a season left out; and its `SCENERY_SHADOWS` conditions. Southern temperate latitudes weren't tested: no base scenery for them was installed.
- **X-Plane 12.4.3, checks of the later fixes:** XPlane2Blender's exports for #730 (selective and additive LODs, and the old behaviour), bone Show/Hide (#643), shared vertices (#709, against the unoptimized export), and `ATTR_shiny_rat 0` against none (#439). Also that X-Plane draws every additive LOD in range. For #709 and #439 every changed test output was also compared line by line: the drawn triangles and the shininess at each `TRIS` are unchanged.
- **X-Plane 12.4.3, Check in X-Plane:** on its sample model, the shapes check matched to the pixel in all six views, the textures check agreed on 91 to 93% of the model, and the light was within 8 pixels and red in both. The button was also driven in a live Blender: the status bar followed the run and the comparison window opened by itself.
- **Not tested:** any Blender version other than 5.2; loading most exported OBJs in X-Plane (outputs are checked against the upstream test fixtures; the X-Plane checks above cover specific features); and `IF NOT SCENERY_SHADOWS` with scenery shadows off in the graphics settings (turning them off through an art control removed the shadows, but the condition didn't change, so the result was inconclusive).

---

## 7. Second pass: code audit

After the work above, the whole add-on was read file by file looking for bugs that nobody had reported (branch `blender5v2`, 13 October 2026). None of these has an upstream issue unless noted; most are in upstream's code too. Each one has a commit, and a test where the output changes.

### Export output

| Bug | Commit | Effect |
|---|---|---|
| **Mirrored meshes export inside out** ([#747](https://github.com/X-Plane/XPlane2Blender/issues/747), wrongly recorded above as not reproducible) | [`8ca9376`](https://github.com/LucienMP/XPlane2Blender/commit/8ca93768) | A child with a negative-determinant transform (scale -1 on a mirrored wing, gear or linked duplicate) was culled by X-Plane from the outside. The corner normals of a mirrored mesh are now taken in local space and rotated with the normal matrix, which also keeps custom normals right, and its loops are written in their already-clockwise order. |
| **`ATTR_hud_reset` was never written** | [`ca4d597`](https://github.com/LucienMP/XPlane2Blender/commit/ca4d5976) | Every mesh after a HUD glass mesh was drawn as HUD glass. The `test_hud_glass_and_reset` fixture had recorded the bug. |
| **`ATTR_poly_os 0` was never written** | same | A polygon offset stayed on for every later mesh. |
| **Attribute state after `ENDIF`** | same | Attributes set inside an `IF` block (added for #284) were treated as still in effect afterwards. X-Plane skips a false block. The next object that needs them writes them again, and the next one that doesn't resets them. |
| **Custom attribute weights were ignored** | same | `XPlaneAttributes.order()` has been a no-op since 4.1 (re-assigning an `OrderedDict` key keeps its place). |
| **Instanced scenery materials: blend mode check** | same | Compared the X-Plane 9 checkbox, not the X-Plane 10+ blend mode, so differing modes passed validation and broke instancing. |
| **Decal 2 alpha constant** | [`b0ffa20`](https://github.com/LucienMP/XPlane2Blender/commit/b0ffa209) | `DECAL_PARAMS` for the second detail texture wrote the alpha modulator twice. |
| **Resource paths with File > Export** | same | Texture, decal, particle and rain paths were relative to the .blend's folder, not to the folder the OBJ was written to. Only the "Export OBJs" button was right. |
| **`./../textures/a.png`** | same | A leading `./` replaced every `./`, resolving one folder too deep. |
| **`WIPER_param` float noise** | same | `0.6599998474121094` instead of `0.66`. |
| **Light aimed exactly opposite its lights.txt direction** | [`79121a9`](https://github.com/LucienMP/XPlane2Blender/commit/79121a99) | Wrote `ANIM_rotate 0 0 0 180 180`, which X-Plane ignores, so the light pointed the wrong way. |
| **Negative loop values** (#767) | [`fcfeac5`](https://github.com/LucienMP/XPlane2Blender/commit/fcfeac55) | Allowed by the UI since 5.0 but never written. |
| **Keyframes on fractional frames** | same | Left out of the frame scan and silently given frame 1's transform. Now read at the nearest whole frame, with a warning. |

### Crashes (tracebacks instead of an error message)

| Bug | Commit |
|---|---|
| A keyframe on a dataref's loop or show/hide value (Blender lets you key them from the panel) | [`fcfeac5`](https://github.com/LucienMP/XPlane2Blender/commit/fcfeac55) |
| A draped reference material with a bump level other than 1 | [`b0ffa20`](https://github.com/LucienMP/XPlane2Blender/commit/b0ffa209) |
| An invalid decal, thermal or wiper texture path | same |
| lights.txt's `NULL` argument (`object_v7`) with a Named or Automatic light | [`79121a9`](https://github.com/LucienMP/XPlane2Blender/commit/79121a99) |
| A Device manipulator after lowering the scene's X-Plane version | [`be9aceb`](https://github.com/LucienMP/XPlane2Blender/commit/be9acebd) |
| Saving after disabling the add-on (handlers and pointer properties left behind) | same |
| A Commands.txt in another encoding, or ending without a newline | [`6ec2b40`](https://github.com/LucienMP/XPlane2Blender/commit/6ec2b40b) |

### UI, logs and tools

| Bug | Commit |
|---|---|
| "Add Light Property" added invisible attributes to the Light datablock, which were exported | [`be9aceb`](https://github.com/LucienMP/XPlane2Blender/commit/be9acebd) |
| The material Light Level dataref search filled in the first material slot, not the active one | same |
| Bone dataref keyframe buttons hidden unless the armature object itself was animated | same |
| The Startup and Updater logs dropped every warning (`LOGGER_LEVEL_WARN` didn't match the logger) | same |
| The keyframe cache survived a failed export, so the next export used stale transforms | [`fcfeac5`](https://github.com/LucienMP/XPlane2Blender/commit/fcfeac55) |
| Decal gloss estimation leaked an image datablock into the .blend on every export | [`b0ffa20`](https://github.com/LucienMP/XPlane2Blender/commit/b0ffa209) |
| Scene report CSV (#764) reported the wrong fields for drag axis, axis knob, axis switch and detent manipulators | [`6ec2b40`](https://github.com/LucienMP/XPlane2Blender/commit/6ec2b40b) |
| DataRefs.txt failed on a blank line or a UTF-8 BOM | same |
| `tests.py --continue` exited 0 after failures; `mkbuild.py` rejected every build number and never failed on tests | [`282a3a3`](https://github.com/LucienMP/XPlane2Blender/commit/282a3a39) |

### Changes to exported OBJs

Besides the fixes above: `ATTR_hud_reset` and `ATTR_poly_os 0` now appear where they were missing, objects after an `ENDIF` may repeat or reset attributes, mirrored meshes have their normals and winding flipped back, and custom attributes with a weight are ordered by it. Two fixtures changed (`test_hud_glass_and_reset.obj`, `test_materials.obj`), both checked line by line.

### Found but left for a decision

- **Drag Rotate axis rounding** (`xplane_manipulator.py`, `fmt_value`): a precedence bug makes the pivot axis of `ATTR_manip_drag_rotate` go through `.3f` rounding although the comment says vectors must not be rounded (about 0.03 degrees for a non-axis-aligned axis). Fixing it changes many manipulator fixtures.
- **Custom billboard light alpha**: `LIGHT_CUSTOM`'s alpha is Blender's light Power in watts, 1000 for a new light, and no panel shows it.
- **#701** (parent `ATTR_light_level` reset), **#461**, **#576**, `none` for a custom spill without a dataref and `ELSE` conditions: as in section 4.

### Tests

178 test files, 640 cases, 0 failures on Blender 5.2.2 (eight skipped as before). New or rewritten test files: `negative_scale_winding`, `attribute_state_resets`, `dataref_fcurve_edge_cases`, `opposite_direction_autocorrect`.

---

## 8. Enhancements and Check in X-Plane (13 October 2026)

After the audit, 15 small feature requests from the appendix were done, [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) was completed, and a way to check exports in X-Plane itself was added. Each row links its commit. All of it is covered by the test suite; the README's "Checks and conveniences" list describes each one for users.

### New checks on export

| Issue | Commit | What changed |
|---|---|---|
| [#344](https://github.com/X-Plane/XPlane2Blender/issues/344) Validate datarefs, [#68](https://github.com/X-Plane/XPlane2Blender/issues/68) array datarefs without `[n]`, [#345](https://github.com/X-Plane/XPlane2Blender/issues/345) access to array indexes | [`f901873`](https://github.com/LucienMP/XPlane2Blender/commit/f901873d4a5f9e17fdfe3fde34200a17e4457067), [`43c3277`](https://github.com/LucienMP/XPlane2Blender/commit/43c327753ade04e74ffeae52175be62922313fd4) | Every dataref an OBJ uses (animations, show/hide on objects and bones, custom lights, light levels, manipulators, thermal sources, wipers) is checked against X-Plane 12.4's `DataRefs.txt`. The export warns once per OBJ about a `sim/` dataref that isn't in the file, an array used without an element, an element past the end, an element on a non-array, and a space in the path, and names the object. The same hint shows under the dataref field. Picking an array dataref in the search window fills in `[0]`. A plugin's own datarefs can't be in the file, so they're only checked for shape. |
| [#403](https://github.com/X-Plane/XPlane2Blender/issues/403) Textures that won't work | [`216944d`](https://github.com/LucienMP/XPlane2Blender/commit/216944d96a579bdc4305979e479cdcca51669657), [`1158cb7`](https://github.com/LucienMP/XPlane2Blender/commit/1158cb78f562bd000bd7fdfca1a133e082d350cd) | Each texture path written to the header (textures, decals, modulators, thermal and wiper textures) warns when it isn't a PNG or DDS, isn't on disk, doesn't start like a PNG or DDS, or isn't a power of two in each dimension. Only the header bytes are read. A `//` path at first warned on Windows, where `Path('//x.png')` reads as a network share. |
| [#466](https://github.com/X-Plane/XPlane2Blender/issues/466) Unit scaling | [`d29e48d`](https://github.com/LucienMP/XPlane2Blender/commit/d29e48db54e679c12cc23a6f604e0e2da62e1f17) | A scene Unit Scale other than 1 warns on export and in the Scene panel, with what a length shown as 1 m exports as. |

### Working with the exporter

| Issue | Commit | What changed |
|---|---|---|
| [#140](https://github.com/X-Plane/XPlane2Blender/issues/140) Select erroneous objects, [#239](https://github.com/X-Plane/XPlane2Blender/issues/239) button for the export log | [`cebced0`](https://github.com/LucienMP/XPlane2Blender/commit/cebced06fb6a5b085c935449923ec965790f6d8a) | A failed export selects the objects its errors name (a bone's name selects its armature). The error popup says how many errors and warnings there were, shows the first three, and has **Open Export Log** and **Select Objects In Log**, which are also in the Scene panel. |
| [#354](https://github.com/X-Plane/XPlane2Blender/issues/354) Progress indicator | [`d50195f`](https://github.com/LucienMP/XPlane2Blender/commit/d50195fb831786d1b2ee2ad59a54a7dea01f2660) | Blender's progress cursor and the status bar's text name the root being collected or written. No cancel: Blender can't redraw during an operator. |
| [#561](https://github.com/X-Plane/XPlane2Blender/issues/561) Light name search | [`d40f43a`](https://github.com/LucienMP/XPlane2Blender/commit/d40f43afff9ea17d0715f53af42a34fcc32ff59f) | A search window next to the Name field of Automatic, Named and Manual Param lights, listing every light in `lights.txt` with its parameters and whether it works as an Automatic light. |
| [#401](https://github.com/X-Plane/XPlane2Blender/issues/401) Show/Hide reorder arrows | [`d29e48d`](https://github.com/LucienMP/XPlane2Blender/commit/d29e48db54e679c12cc23a6f604e0e2da62e1f17) | Up and down arrows on every dataref, object and bone, moving it with its keyframes. Show/Hide are written, and applied by X-Plane, in this order. |

### Smaller, faster OBJs

| Issue | Commit | What changed | Output change |
|---|---|---|---|
| [#253](https://github.com/X-Plane/XPlane2Blender/issues/253) Bake static animations, [#653](https://github.com/X-Plane/XPlane2Blender/issues/653) dynamic animations that turn out static, [#562](https://github.com/X-Plane/XPlane2Blender/issues/562) no-movement rotations; [#235](https://github.com/X-Plane/XPlane2Blender/issues/235) partly | [`2c5df6c`](https://github.com/LucienMP/XPlane2Blender/commit/2c5df6c835a4a79c37800e6a882bc69521a0045f) | A dataref's translation or rotation table whose keys all give the same value is written as one static `ANIM_trans` or `ANIM_rotate` in the same place: the same transform by the OBJ spec, with no dataref to evaluate. This happens on an object with two datarefs when only one moves it, since each table samples the transform at its own keyframes. An all-zero table is dropped as before. | Only files with such tables |
| [#134](https://github.com/X-Plane/XPlane2Blender/issues/134) GPU-optimised vertex and index order | [`94fe70b`](https://github.com/LucienMP/XPlane2Blender/commit/94fe70b28f26f001313a319f2f711c361c76e36f) | With **Optimize** on, each object's triangles are reordered with Tom Forsyth's linear-speed vertex cache method. A shuffled 180,000-triangle grid went from 3.0 to 0.67 cache misses per triangle, in 3.3 s. Two fixtures were regenerated after a script confirmed they hold the same triangles. | Files with Optimize on: triangle order only |

### `ELSE` and `ELSE IF`

| Issue | Commit | What changed |
|---|---|---|
| [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) OBJ conditionals | [`592d1ac`](https://github.com/LucienMP/XPlane2Blender/commit/592d1acfb66c5e05e356ca5e884c2e036e0968d8) | An object's **Else Of** names the object whose condition it's the alternative to. It's written in that object's `ELSE`, or as `ELSE IF` when it has a condition of its own; several give a chain ending in one `ELSE`. The `IF` object needs exactly one condition (its material's count) and no animation, and both need the same parent, so the branches nest in one block; anything else is an error saying why. Attribute state restarts in each branch from the state before the `IF`, and anything a branch changed is unknown after the `ENDIF`. Nothing changes for files that don't use it. |

### Check in X-Plane

[`3c12f44`](https://github.com/LucienMP/XPlane2Blender/commit/3c12f44643fa8ff9e2a3023dd7271f94ef4af2f8), [`dfa34f1`](https://github.com/LucienMP/XPlane2Blender/commit/dfa34f1a37ce391615650cf068448103d21cff14), [`1a7116c`](https://github.com/LucienMP/XPlane2Blender/commit/1a7116c99b01c88098603e0c7db6b051ff9622ef), [`2327afe`](https://github.com/LucienMP/XPlane2Blender/commit/2327afe2eeae57be31704ae63bdfeace2e5ce1ec), [`b8aa039`](https://github.com/LucienMP/XPlane2Blender/commit/b8aa039c41e8ff4f1b7238454c0b146d8c63d170)

No upstream issue asked for this. It answers whether X-Plane draws an exported OBJ the way Blender shows the model, without the author leaving Blender: a **Check in X-Plane** button in the Scene panel exports a copy of the scene, starts X-Plane, and opens the result in an Image Editor about three minutes later. Each row of the result is one camera view: Blender, X-Plane, and the differences in red.

- **How it compares two different renderers:** nothing is lit. The model wears flat colours, used as its `TEXTURE_LIT` too, and X-Plane draws it at midnight inside a black box, so the colours come only from the texture. A small plugin places the box and the model with X-Plane's Instance API, gives the model its dataref values and takes six screenshots. Blender renders the same views with Workbench. Each pixel is matched to the nearest palette colour after removing brightness, so exposure doesn't matter.
- **Three checks:** *Shapes* replaces each material with a flat colour and compares shape, position, animation pose, show/hide and face winding exactly. *Textures* keeps the root's texture and checks UV mapping, loosely, since X-Plane shifts colours. *Lights* compares each light's billboard position and colour; spill is only reported as present or not.
- **What it took**, each found by a run: a lit green box reflected off the model and turned red faces yellow, so the box is black; other plugins' windows appeared in the screenshots, so their folders are renamed aside for the run and back afterwards; X-Plane can start the user's own saved flight after the requested one, so the runner checks the aircraft and asks again; sloping ground came up through the floor, so the box sits 1 m above the terrain.
- **It found a real mistake:** the first sample model had faces wound inside out. Blender's two-sided view drew them, X-Plane didn't, and the top view showed it.
- **Where it lives:** `io_xplane2blender/xplane_parity`, with its plugin compiled as `plugin/win.xpl` (Windows) next to its source. Its [README](https://github.com/LucienMP/XPlane2Blender/tree/master/io_xplane2blender/xplane_parity) has the details and results. Every run backs up X-Plane's preferences and Log.txt, and `parity.py cleanup` restores them and removes the plugin. It refuses to start while X-Plane is running.

---

## Appendix: triage of all open upstream issues (October 2026)

All 158 issues open on [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender/issues) on 11 October 2026, sorted by reading each issue against the upstream code.
Buckets A and B were checked against the code. The rest are classified from the issue text and were not tested.
Section 4 has more detail on the fixed and the most important open ones.

### A. Bugs still present in the code (checked against the code during triage)

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#763](https://github.com/X-Plane/XPlane2Blender/issues/763) | LOD light_level attr exported incorrectly | [@ddenn](https://github.com/ddenn) | **Fixed in 5.0** |
| [#752](https://github.com/X-Plane/XPlane2Blender/issues/752) | Attribute Error: 'NoneType' object has no attribute 'xplane' | [@Rob-Neary](https://github.com/Rob-Neary) | **Fixed in 5.0** |
| [#704](https://github.com/X-Plane/XPlane2Blender/issues/704) | Error in "xplane_ui.py" with Blender 3.2 | [@AlteredWolf](https://github.com/AlteredWolf) | **Fixed in 5.0** |
| [#751](https://github.com/X-Plane/XPlane2Blender/issues/751) | Unable to export | [@yury620](https://github.com/yury620) | **Fixed in 5.0** |
| [#747](https://github.com/X-Plane/XPlane2Blender/issues/747) | Mirrored (negative-scale) linked duplicates export with inverted normals | [@NuanFeng520](https://github.com/NuanFeng520) | **Fixed in the second pass** (section 7) |
| [#741](https://github.com/X-Plane/XPlane2Blender/issues/741) | Symlinked texture files follow the link (obj header) when exported. | [@danklaue](https://github.com/danklaue) | **Fixed in 5.0** |
| [#473](https://github.com/X-Plane/XPlane2Blender/issues/473) | No validation for textures having a space in the file name | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** |
| [#577](https://github.com/X-Plane/XPlane2Blender/issues/577) | Validate TEXTURE field that texture does not have spaces in it | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** |
| [#709](https://github.com/X-Plane/XPlane2Blender/issues/709) | Vertex Optimization on Export | [@ian-m-carr](https://github.com/ian-m-carr) | **Fixed in 5.0** (checked in X-Plane 12.4.3) |
| [#725](https://github.com/X-Plane/XPlane2Blender/issues/725) | Dataref could not be parsed | [@pilotRL](https://github.com/pilotRL) | **Fixed in 5.0** |
| [#701](https://github.com/X-Plane/XPlane2Blender/issues/701) | REGRESSION: ATTR_light_level directive in custom attributes is reset in newer exporter | [@GlidingKiwi](https://github.com/GlidingKiwi) | Left open: investigated, needs a decision (section 4) |
| [#190](https://github.com/X-Plane/XPlane2Blender/issues/190) | Incorrect Animations in OBJ's when using an armature | [@JasonGilholme](https://github.com/JasonGilholme) | **Fixed in 5.0** |
| [#643](https://github.com/X-Plane/XPlane2Blender/issues/643) | Should bones support Show/Hide animation? | [@todirbg](https://github.com/todirbg) | **Fixed in 5.0** (checked in X-Plane 12.4.3) |
| [#516](https://github.com/X-Plane/XPlane2Blender/issues/516) | Show/Hide only allowed on Objects, shown on Armature/Bone Panel UI | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** (as #643) |
| [#497](https://github.com/X-Plane/XPlane2Blender/issues/497) | Bone weight appears to be unused | [@tngreene](https://github.com/tngreene) |  |
| [#730](https://github.com/X-Plane/XPlane2Blender/issues/730) | LOD setting causes incomplete obj-file | [@fsspn](https://github.com/fsspn) | **Fixed in 5.0** (checked in X-Plane 12.4.3) |
| [#285](https://github.com/X-Plane/XPlane2Blender/issues/285) | No UV-Mapping needs stronger warning | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** (warning) |
| [#515](https://github.com/X-Plane/XPlane2Blender/issues/515) | 280: Camera Collision allowed in Aircraft Export Type | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** (warning) |
| [#279](https://github.com/X-Plane/XPlane2Blender/issues/279) | Validate Slope Limit | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** (field limits and warning) |
| [#439](https://github.com/X-Plane/XPlane2Blender/issues/439) | ATTR_shiny_rat 0 written despite being X-Plane's default | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** (checked in X-Plane 12.4.3) |
| [#710](https://github.com/X-Plane/XPlane2Blender/issues/710) | run.py and tests.py replace rather than update environment | [@ian-m-carr](https://github.com/ian-m-carr) | **Fixed in 5.0** |

### B. Blender 4.x / 5.x compatibility

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#758](https://github.com/X-Plane/XPlane2Blender/issues/758) | XP2B 4.4.0 breakage in Blender >5.0.0 | [@JT8D-17](https://github.com/JT8D-17) | **Fixed in 5.0** |
| [#754](https://github.com/X-Plane/XPlane2Blender/issues/754) | Appears bone animations are still not compatible with 4.5 | [@kkaigle](https://github.com/kkaigle) | **Fixed in 5.0** |
| [#743](https://github.com/X-Plane/XPlane2Blender/issues/743) | Bone keyframes for datarefs | [@Im-Unknown-now](https://github.com/Im-Unknown-now) | **Fixed in 5.0** |
| [#738](https://github.com/X-Plane/XPlane2Blender/issues/738) | Dataref values in Bone Tab aren't colored | [@skijeffory](https://github.com/skijeffory) | **Fixed in 5.0** (worked around) |
| [#565](https://github.com/X-Plane/XPlane2Blender/issues/565) | 280: EEVEE vs Cycles? | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** |
| [#746](https://github.com/X-Plane/XPlane2Blender/issues/746) | Error adding extension / plugin into Blender 4.4 | [@GitDaBytes](https://github.com/GitDaBytes) |  |
| [#338](https://github.com/X-Plane/XPlane2Blender/issues/338) | Remove relative imports and circular dependencies, make XP2B fully reloadable | [@tngreene](https://github.com/tngreene) |  |
| [#766](https://github.com/X-Plane/XPlane2Blender/issues/766) | no data object properties | [@TheRealTofferAviation](https://github.com/TheRealTofferAviation) | **Fixed in 5.0** |

### C. X-Plane 12 features and OBJ-spec gaps

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#755](https://github.com/X-Plane/XPlane2Blender/issues/755) | Automatic light with spot_params_bb_pm : wrong intensity parameter | [@cpot](https://github.com/cpot) | Not reproducible in X-Plane 12.4.4 |
| [#621](https://github.com/X-Plane/XPlane2Blender/issues/621) | Add wheel support for Drag Rotate manipulators | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** |
| [#370](https://github.com/X-Plane/XPlane2Blender/issues/370) | Deprecate VLIGHT from XPlaneLights | [@tngreene](https://github.com/tngreene) | **Done in 5.0** |
| [#489](https://github.com/X-Plane/XPlane2Blender/issues/489) | Instanced Scenery has no validation for named and paramter lights used | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (warnings, checked in X-Plane 12.4.4) |
| [#368](https://github.com/X-Plane/XPlane2Blender/issues/368) | Instanced Scenery Object Export Type is severly lacking in validations | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (warnings, checked in X-Plane 12.4.4) |
| [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) | OBJ conditionals is not implemented properly, or hardly at all | [@tngreene](https://github.com/tngreene) | **Done in 5.0**: `SCENERY_SHADOWS` added; `ELSE` / `ELSE IF` through "Else Of" (13 October 2026) |
| [#576](https://github.com/X-Plane/XPlane2Blender/issues/576) | 280: Add NEG_DIR_MAG to lights.txt spec, lights.txt | [@tngreene](https://github.com/tngreene) | Your decision |
| [#461](https://github.com/X-Plane/XPlane2Blender/issues/461) | Always apply GLOBAL_specular 1.0 when NORMAL texture given | [@tngreene](https://github.com/tngreene) | Your decision (checked in X-Plane 12.4.4) |

### D. Feature requests: small

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#68](https://github.com/X-Plane/XPlane2Blender/issues/68) | Datarefs that are part of an array don't automatically have numbers in [n] | [@danklaue](https://github.com/danklaue) | **Done in 5.0** (13 October 2026): the search window fills in `[0]`, and export warns about a missing element |
| [#344](https://github.com/X-Plane/XPlane2Blender/issues/344) | Validate Datarefs | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026): checked against X-Plane 12.4's `DataRefs.txt`, in the panels and on export |
| [#345](https://github.com/X-Plane/XPlane2Blender/issues/345) | Give quick preview or access to dataref array indexes | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026): array sizes shown and checked |
| [#405](https://github.com/X-Plane/XPlane2Blender/issues/405) | Block use of sim/multiplayer datarefs | [@tngreene](https://github.com/tngreene) |  |
| [#403](https://github.com/X-Plane/XPlane2Blender/issues/403) | Give errors people that their textures aren't going to work. | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026): missing, wrong type, not a power of two |
| [#520](https://github.com/X-Plane/XPlane2Blender/issues/520) | 280: LOD Additive Mode validation for no double draw | [@tngreene](https://github.com/tngreene) |  |
| [#624](https://github.com/X-Plane/XPlane2Blender/issues/624) | Custom Footer Comment | [@tngreene](https://github.com/tngreene) |  |
| [#428](https://github.com/X-Plane/XPlane2Blender/issues/428) | Empty does not allow Custom Object Properties | [@tngreene](https://github.com/tngreene) |  |
| [#140](https://github.com/X-Plane/XPlane2Blender/issues/140) | Select errornous objects after export | [@der-On](https://github.com/der-On) | **Done in 5.0** (13 October 2026) |
| [#239](https://github.com/X-Plane/XPlane2Blender/issues/239) | Create button to bring up exporter log text document instantly | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026): "Open Export Log" in the popup and Scene panel |
| [#354](https://github.com/X-Plane/XPlane2Blender/issues/354) | Progress indicator for export | [@Voidhawk9](https://github.com/Voidhawk9) | **Done in 5.0** (13 October 2026): progress cursor and status text; no cancel, Blender can't redraw during an operator |
| [#401](https://github.com/X-Plane/XPlane2Blender/issues/401) | Implement Show/Hide re-order arrows | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026) |
| [#391](https://github.com/X-Plane/XPlane2Blender/issues/391) | Create hybrid dropdown/text field for chossing Emitter Names from .pss file | [@tngreene](https://github.com/tngreene) |  |
| [#561](https://github.com/X-Plane/XPlane2Blender/issues/561) | 280: Light search field similar to datarefs and commands search field | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026) |
| [#575](https://github.com/X-Plane/XPlane2Blender/issues/575) | 280: Remove unused properties from XPlaneLayer, elsewhere | [@tngreene](https://github.com/tngreene) |  |
| [#416](https://github.com/X-Plane/XPlane2Blender/issues/416) | Irritatingly, XPlaneCockpitRegion.top is misnamed. Should be "bottom" | [@tngreene](https://github.com/tngreene) |  |
| [#375](https://github.com/X-Plane/XPlane2Blender/issues/375) | mkbuild should change bl_info['warning'] for non-RC builds | [@tngreene](https://github.com/tngreene) |  |
| [#466](https://github.com/X-Plane/XPlane2Blender/issues/466) | Unit scaling? | [@kbrandwijk](https://github.com/kbrandwijk) | **Done in 5.0** (13 October 2026): warning on export and in the Scene panel |

### D. Feature requests: medium

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#186](https://github.com/X-Plane/XPlane2Blender/issues/186) | "insert keyframe to datarefs" should be able to automatically processed | [@cpuwolf](https://github.com/cpuwolf) |  |
| [#449](https://github.com/X-Plane/XPlane2Blender/issues/449) | Implement new Autodetect Textures From Cycles workflow | [@tngreene](https://github.com/tngreene) |  |
| [#467](https://github.com/X-Plane/XPlane2Blender/issues/467) | Custom `Copy To Selected` that intelligently creates nested structures and finds destination properties | [@lehthanis](https://github.com/lehthanis) |  |
| [#558](https://github.com/X-Plane/XPlane2Blender/issues/558) | 280: Ability to toggle between world and local coordinates to make building OBJs and AGP-like scenes easier | [@muchimi](https://github.com/muchimi) |  |
| [#581](https://github.com/X-Plane/XPlane2Blender/issues/581) | Mesh as Root Bone's Blender Object does not get properly transformed | [@KarlLeclerc](https://github.com/KarlLeclerc) |  |
| [#406](https://github.com/X-Plane/XPlane2Blender/issues/406) | Allow users to name external resources for their custom plugins | [@tngreene](https://github.com/tngreene) |  |
| [#607](https://github.com/X-Plane/XPlane2Blender/issues/607) | Show only relavent UI as much as possible | [@tngreene](https://github.com/tngreene) |  |
| [#258](https://github.com/X-Plane/XPlane2Blender/issues/258) | 1-dimensionally UV-unwrapped objects cause "marching ants" problem in X-Plane. | [@danklaue](https://github.com/danklaue) |  |
| [#631](https://github.com/X-Plane/XPlane2Blender/issues/631) | Parent of newly added out-of-collection-bone does not resort its children | [@tngreene](https://github.com/tngreene) |  |
| [#329](https://github.com/X-Plane/XPlane2Blender/issues/329) | Create error codes for error messages | [@tngreene](https://github.com/tngreene) |  |
| [#369](https://github.com/X-Plane/XPlane2Blender/issues/369) | Add DEBUG level to logger (and possibly switch to python's logger) | [@tngreene](https://github.com/tngreene) |  |

### D. Export optimisations

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#562](https://github.com/X-Plane/XPlane2Blender/issues/562) | 280: No movement rotations exist in file | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026): static tables become static `ANIM_rotate` / `ANIM_trans` |
| [#235](https://github.com/X-Plane/XPlane2Blender/issues/235) | Duplicate animation transformations need optimization | [@tngreene](https://github.com/tngreene) | Partly, 13 October 2026: per-dataref static tables collapsed (#253); nested static transforms were already baked |
| [#253](https://github.com/X-Plane/XPlane2Blender/issues/253) | Optimization: Bake static animations into key frame tables | [@bsupnik](https://github.com/bsupnik) | **Done in 5.0** (13 October 2026) |
| [#331](https://github.com/X-Plane/XPlane2Blender/issues/331) | Armature-based animations create extra static transform | [@bsupnik](https://github.com/bsupnik) |  |
| [#133](https://github.com/X-Plane/XPlane2Blender/issues/133) | Optimizations to pre-post transform matrix | [@bsupnik](https://github.com/bsupnik) |  |
| [#336](https://github.com/X-Plane/XPlane2Blender/issues/336) | Optimze the XPlaneBone tree by not collecting "useless" bones | [@tngreene](https://github.com/tngreene) |  |
| [#653](https://github.com/X-Plane/XPlane2Blender/issues/653) | Imp: Turn dynamic animations that turned out to be static into static animations | [@tngreene](https://github.com/tngreene) | **Done in 5.0** (13 October 2026) |
| [#134](https://github.com/X-Plane/XPlane2Blender/issues/134) | Vertex and Index Order Should be GPU Optimized | [@bsupnik](https://github.com/bsupnik) | **Done in 5.0** (13 October 2026): triangle order for the post-transform cache, with Optimize on |

### D. Feature requests: large

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#610](https://github.com/X-Plane/XPlane2Blender/issues/610) | Imp: Importer. (yes. seriously.) | [@tngreene](https://github.com/tngreene) |  |
| [#495](https://github.com/X-Plane/XPlane2Blender/issues/495) | 280: Support instancing and proxies | [@tngreene](https://github.com/tngreene) |  |
| [#628](https://github.com/X-Plane/XPlane2Blender/issues/628) | Use constraints for animation | [@tngreene](https://github.com/tngreene) |  |
| [#501](https://github.com/X-Plane/XPlane2Blender/issues/501) | 280: Split-animations must walk up armatures bones | [@tngreene](https://github.com/tngreene) |  |

### D. Developer tooling

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#319](https://github.com/X-Plane/XPlane2Blender/issues/319) | Clean "TODO"s out of the code base! | [@tngreene](https://github.com/tngreene) |  |
| [#333](https://github.com/X-Plane/XPlane2Blender/issues/333) | XPlaneKeyframe always has location and rotation data, even when not keyframed for Location or Animation | [@tngreene](https://github.com/tngreene) |  |
| [#339](https://github.com/X-Plane/XPlane2Blender/issues/339) | Integrate mypy, pylint as part of the test suite | [@tngreene](https://github.com/tngreene) |  |
| [#341](https://github.com/X-Plane/XPlane2Blender/issues/341) | VR manip error msg "Matching Animations" missing potential case | [@tngreene](https://github.com/tngreene) |  |
| [#408](https://github.com/X-Plane/XPlane2Blender/issues/408) | Make unittest's output more reasonable | [@tngreene](https://github.com/tngreene) |  |

### E. Already fixed in upstream master

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#737](https://github.com/X-Plane/XPlane2Blender/issues/737) | Issue while exporting with xplane2blender 4.2.0 version | [@ArnavSharmaz0602](https://github.com/ArnavSharmaz0602) |  |
| [#242](https://github.com/X-Plane/XPlane2Blender/issues/242) | Parent bones overriding animation data in nested bone animations | [@jeiting](https://github.com/jeiting) |  |
| [#630](https://github.com/X-Plane/XPlane2Blender/issues/630) | XPlaneAttributes does not behave expectly when adding attributes with same name | [@tngreene](https://github.com/tngreene) |  |
| [#724](https://github.com/X-Plane/XPlane2Blender/issues/724) | Added loop feature to hide and show animations | [@Cristiano-Maggi](https://github.com/Cristiano-Maggi) |  |
| [#632](https://github.com/X-Plane/XPlane2Blender/issues/632) | GLOBAL_ blend-ing states must be mutually exclusive | [@tngreene](https://github.com/tngreene) |  |
| [#580](https://github.com/X-Plane/XPlane2Blender/issues/580) | Export Selected Root Objects Button | [@tngreene](https://github.com/tngreene) |  |
| [#722](https://github.com/X-Plane/XPlane2Blender/issues/722) | Error import ioxplane in Blender 3.4.1 thanks Ben. | [@tomstar52](https://github.com/tomstar52) |  |

### E. Same bug as another issue

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#762](https://github.com/X-Plane/XPlane2Blender/issues/762) | Unable to export blender files to X-plane planemaker 12.4 version. | [@iitkflightsimulator02-coder](https://github.com/iitkflightsimulator02-coder) | **Fixed in 5.0** |

### E. Blender 2.7x era, needs a fresh reproduction

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#127](https://github.com/X-Plane/XPlane2Blender/issues/127) | Armature with static object transform incorrectly exported | [@bsupnik](https://github.com/bsupnik) |  |
| [#193](https://github.com/X-Plane/XPlane2Blender/issues/193) | Non mesh anims being written to obj | [@JasonGilholme](https://github.com/JasonGilholme) |  |
| [#199](https://github.com/X-Plane/XPlane2Blender/issues/199) | Bone children are offset from tail instead from head | [@vilemduha](https://github.com/vilemduha) |  |

### E. Old Blender or installation problems

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#633](https://github.com/X-Plane/XPlane2Blender/issues/633) | Is it time to raise the minimum version requirements? | [@tngreene](https://github.com/tngreene) |  |
| [#673](https://github.com/X-Plane/XPlane2Blender/issues/673) | >= Blender 2.90 doesn't work for some people | [@tngreene](https://github.com/tngreene) |  |
| [#679](https://github.com/X-Plane/XPlane2Blender/issues/679) | 4.2.0 Alpha not able to install on blender? | [@tiadevs](https://github.com/tiadevs) |  |
| [#697](https://github.com/X-Plane/XPlane2Blender/issues/697) | Cannot activate XPlane2Blender add-on on Apple Silicon | [@Lonestar-one](https://github.com/Lonestar-one) |  |
| [#715](https://github.com/X-Plane/XPlane2Blender/issues/715) | 4.2.0rc to Blender 3.3.1 initialization error on Linux | [@wellthatwaseasy](https://github.com/wellthatwaseasy) |  |
| [#719](https://github.com/X-Plane/XPlane2Blender/issues/719) | Update to work with Blender 3.1 and up | [@uffdaken](https://github.com/uffdaken) |  |
| [#736](https://github.com/X-Plane/XPlane2Blender/issues/736) | Help enabling addon in osx | [@ianm111](https://github.com/ianm111) |  |
| [#750](https://github.com/X-Plane/XPlane2Blender/issues/750) | Error | [@Shaurya306](https://github.com/Shaurya306) |  |

### E. Blender 2.49 converter (not in master)

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#348](https://github.com/X-Plane/XPlane2Blender/issues/348) | 249: Create the 2.49 to 2.79 converter! | [@tngreene](https://github.com/tngreene) |  |
| [#383](https://github.com/X-Plane/XPlane2Blender/issues/383) | 249: Implement Import-Convert Dialog Box | [@tngreene](https://github.com/tngreene) |  |
| [#397](https://github.com/X-Plane/XPlane2Blender/issues/397) | 249: Obtain 2.49 projects from the commnuity! | [@tngreene](https://github.com/tngreene) |  |
| [#410](https://github.com/X-Plane/XPlane2Blender/issues/410) | 249: Convert global properties into XPlaneLayer properites | [@tngreene](https://github.com/tngreene) |  |
| [#440](https://github.com/X-Plane/XPlane2Blender/issues/440) | 249: Remove SKIP workflow code and fix unit tests, API | [@tngreene](https://github.com/tngreene) |  |
| [#441](https://github.com/X-Plane/XPlane2Blender/issues/441) | 249: Preserve 2.49 draw order With Groups and  heuristics | [@tngreene](https://github.com/tngreene) |  |
| [#444](https://github.com/X-Plane/XPlane2Blender/issues/444) | 249: Convert Scenery and Instanced Scenery properties | [@tngreene](https://github.com/tngreene) |  |
| [#469](https://github.com/X-Plane/XPlane2Blender/issues/469) | 249: Convert Panel Region Information | [@tngreene](https://github.com/tngreene) |  |
| [#476](https://github.com/X-Plane/XPlane2Blender/issues/476) | 249: Any string value from 2.49 may result in UnicodeDecodeError | [@tngreene](https://github.com/tngreene) |  |
| [#478](https://github.com/X-Plane/XPlane2Blender/issues/478) | 249: LODs not converting properly | [@tngreene](https://github.com/tngreene) |  |
| [#479](https://github.com/X-Plane/XPlane2Blender/issues/479) | 249: Magnet Conversion uses Lamp location literally | [@tngreene](https://github.com/tngreene) |  |
| [#480](https://github.com/X-Plane/XPlane2Blender/issues/480) | 249: New Unit Tests | [@tngreene](https://github.com/tngreene) |  |
| [#526](https://github.com/X-Plane/XPlane2Blender/issues/526) | 249: Warn if person is using BULK with no "OBJ" prefix found | [@tngreene](https://github.com/tngreene) |  |

### E. Experimental importer (not in master; see #610)

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#618](https://github.com/X-Plane/XPlane2Blender/issues/618) | Imp: Datablock names should be based on dataref usage, heuristics, comments, and materials | [@tngreene](https://github.com/tngreene) |  |
| [#619](https://github.com/X-Plane/XPlane2Blender/issues/619) | Imp: Absent argument cases should default to 0 | [@tngreene](https://github.com/tngreene) |  |
| [#626](https://github.com/X-Plane/XPlane2Blender/issues/626) | Imp: Mesh building error reporting | [@tngreene](https://github.com/tngreene) |  |
| [#637](https://github.com/X-Plane/XPlane2Blender/issues/637) | Imp: Multiple datarefs assaigned in animation block | [@tngreene](https://github.com/tngreene) |  |
| [#638](https://github.com/X-Plane/XPlane2Blender/issues/638) | Imp: Sequential TRIS are parented or not to each other | [@tngreene](https://github.com/tngreene) |  |
| [#640](https://github.com/X-Plane/XPlane2Blender/issues/640) | Imp: Multiple Datarefs In animation | [@tngreene](https://github.com/tngreene) |  |
| [#642](https://github.com/X-Plane/XPlane2Blender/issues/642) | Imp: _next_object_name is a real problem | [@tngreene](https://github.com/tngreene) |  |
| [#645](https://github.com/X-Plane/XPlane2Blender/issues/645) | Imp: Animation Overview | [@tngreene](https://github.com/tngreene) |  |
| [#652](https://github.com/X-Plane/XPlane2Blender/issues/652) | Imp: Bake dynamic rotations and translations after static transformations | [@tngreene](https://github.com/tngreene) |  |
| [#654](https://github.com/X-Plane/XPlane2Blender/issues/654) | Imp: Implement ANIM_trans/rotate | [@tngreene](https://github.com/tngreene) |  |
| [#665](https://github.com/X-Plane/XPlane2Blender/issues/665) | Imp: Every ANIM_rotate_begin must be its own Empty until later optimization | [@tngreene](https://github.com/tngreene) |  |
| [#668](https://github.com/X-Plane/XPlane2Blender/issues/668) | Imp: Must we keep track of dataref values with their rotation keyframes? | [@tngreene](https://github.com/tngreene) |  |
| [#677](https://github.com/X-Plane/XPlane2Blender/issues/677) | Importer:   After importing a second .obj material gets overwritten with the new imported material | [@emiliovfx](https://github.com/emiliovfx) |  |
| [#678](https://github.com/X-Plane/XPlane2Blender/issues/678) | Importer:  Ability to import several .obj at once | [@emiliovfx](https://github.com/emiliovfx) |  |
| [#680](https://github.com/X-Plane/XPlane2Blender/issues/680) | Importer: Collected v4.2.0-alpha.1 feedback | [@tngreene](https://github.com/tngreene) |  |
| [#683](https://github.com/X-Plane/XPlane2Blender/issues/683) | Invalid OBJ file header version error report should report that the obj version is incorrect. | [@wpostma](https://github.com/wpostma) |  |
| [#686](https://github.com/X-Plane/XPlane2Blender/issues/686) | Importer: Import manipulators | [@JT8D-17](https://github.com/JT8D-17) |  |
| [#687](https://github.com/X-Plane/XPlane2Blender/issues/687) | Imp: Implement ATTR_LOD, without material resetting | [@tngreene](https://github.com/tngreene) |  |
| [#688](https://github.com/X-Plane/XPlane2Blender/issues/688) | Imp: LIGHTS_NAMED and LIGHTS_PARAM | [@tngreene](https://github.com/tngreene) |  |
| [#711](https://github.com/X-Plane/XPlane2Blender/issues/711) | feat_import uses test framework set_materials to configure texture resulting in large numbers of redundant texture nodes | [@ian-m-carr](https://github.com/ian-m-carr) |  |
| [#728](https://github.com/X-Plane/XPlane2Blender/issues/728) | Import X-Plane not in Import menu | [@MickCrozier](https://github.com/MickCrozier) |  |
| [#729](https://github.com/X-Plane/XPlane2Blender/issues/729) | Import support for newer versions of Blender? | [@DWmFrancis](https://github.com/DWmFrancis) |  |
| [#749](https://github.com/X-Plane/XPlane2Blender/issues/749) | importer does not show up on multiple versions of blender | [@Nick6754](https://github.com/Nick6754) |  |
| [#757](https://github.com/X-Plane/XPlane2Blender/issues/757) | No import of X-plane obj | [@JoWa92](https://github.com/JoWa92) |  |

### E. 2.79 to 2.80 updater only

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#490](https://github.com/X-Plane/XPlane2Blender/issues/490) | 280: Set LOD for Collections 1-4 during update from Root Exports | [@tngreene](https://github.com/tngreene) |  |
| [#533](https://github.com/X-Plane/XPlane2Blender/issues/533) | 280: Updater rename feature doesn't cover if scene has no "layers" pre alpha.6 | [@tngreene](https://github.com/tngreene) |  |

### E. Questions and design discussions

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#603](https://github.com/X-Plane/XPlane2Blender/issues/603) | Does XPlaneLayer.lod and XPlaneLayer.cockpit_region need their initializer code in update? | [@tngreene](https://github.com/tngreene) |  |
| [#670](https://github.com/X-Plane/XPlane2Blender/issues/670) | Is _writeStaticRotation ever useful/is it implemented properly? | [@tngreene](https://github.com/tngreene) |  |
| [#482](https://github.com/X-Plane/XPlane2Blender/issues/482) | xplane_header.getPathRelativeToOBJ may choose the wrong path | [@tngreene](https://github.com/tngreene) |  |

### E. X-Plane side

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#293](https://github.com/X-Plane/XPlane2Blender/issues/293) | Some manipulators possibly allow scrollwheel behavior, despite no effect in X-Plane | [@danklaue](https://github.com/danklaue) |  |

### E. Documentation and community

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#230](https://github.com/X-Plane/XPlane2Blender/issues/230) | Create tutorial in gitbook explaining how to get Eclipse's debugging capabilities functional | [@tngreene](https://github.com/tngreene) |  |
| [#286](https://github.com/X-Plane/XPlane2Blender/issues/286) | Collected manual notes, requests for documentation | [@tngreene](https://github.com/tngreene) |  |
| [#453](https://github.com/X-Plane/XPlane2Blender/issues/453) | Attract contributors and Pull Requests! | [@tngreene](https://github.com/tngreene) |  |
| [#594](https://github.com/X-Plane/XPlane2Blender/issues/594) | Grow XPlane2Blender's community, with the community, take 2! | [@tngreene](https://github.com/tngreene) |  |
| [#609](https://github.com/X-Plane/XPlane2Blender/issues/609) | Move docs over to the github wiki, archive GitBooks | [@tngreene](https://github.com/tngreene) |  |
| [#726](https://github.com/X-Plane/XPlane2Blender/issues/726) | No documentation on v.4x changes | [@JT8D-17](https://github.com/JT8D-17) |  |

### E. Support requests

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#647](https://github.com/X-Plane/XPlane2Blender/issues/647) | Exporting from Blender 2.92 to X-plane11, | [@s3madar](https://github.com/s3madar) |  |
| [#651](https://github.com/X-Plane/XPlane2Blender/issues/651) | Cant Export Error | [@DemonRem](https://github.com/DemonRem) |  |
| [#703](https://github.com/X-Plane/XPlane2Blender/issues/703) | Textures not showing up in xplane 11 WED | [@DANNY757](https://github.com/DANNY757) |  |
| [#733](https://github.com/X-Plane/XPlane2Blender/issues/733) | Can't add datarefs | [@pilotRL](https://github.com/pilotRL) |  |
| [#739](https://github.com/X-Plane/XPlane2Blender/issues/739) | The model colors imported into xplane are all gray-blue | [@Haoguo-max](https://github.com/Haoguo-max) |  |
| [#740](https://github.com/X-Plane/XPlane2Blender/issues/740) | Never mind | [@primtala2](https://github.com/primtala2) |  |
| [#748](https://github.com/X-Plane/XPlane2Blender/issues/748) | No Texture on export, worked before, visible in the .obj | [@Hueyman540](https://github.com/Hueyman540) |  |
