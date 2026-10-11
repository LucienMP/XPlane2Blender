# XPlane2Blender 5.0: review of the unofficial Blender 5 port and of upstream contributions

This document records where the 5.0 code came from: who wrote each part, what was adopted, what was left out and why, and what each change does for users.

The unofficial forum port reviewed in section 2 is kept unchanged on the branch [`reference/chatgpt-port-as-received`](https://github.com/LucienMP/XPlane2Blender/tree/reference/chatgpt-port-as-received) for comparison.

**About the `#numbers`:** every `#123` here refers to the **original repository, [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender)**, not to this fork. Each one is linked. Commit messages on this fork also mention these numbers, but there GitHub links them to this fork, which has no issues of its own.

**Commit links** point to commits on this fork's `master`.

## Contents
1. [Where the code came from](#1-where-the-code-came-from)
2. [Review of the unofficial ChatGPT-assisted port](#2-review-of-the-unofficial-chatgpt-assisted-port)
3. [Upstream pull requests](#3-upstream-pull-requests)
4. [Upstream issues](#4-upstream-issues)
5. [Other changes made for 5.0](#5-other-changes-made-for-50)
6. [How 5.0 was tested](#6-how-50-was-tested)
7. [Appendix: triage of all open upstream issues](#appendix-triage-of-all-open-upstream-issues-october-2026)

---

## 1. Where the code came from

| Source | Authors | Link | Used in 5.0? |
|---|---|---|---|
| **XPlane2Blender**, the original add-on (GPL-3.0) | Ted Greene, Ben Supnik, Amy Parent, Maya F. Eroğlu, and contributors (Laminar Research / X-Plane) | <https://github.com/X-Plane/XPlane2Blender> | **Yes, as the base.** 5.0 starts from upstream `master` at commit [`ee03ed6`](https://github.com/X-Plane/XPlane2Blender/commit/ee03ed6a96601199d7bccf3d65fb1378664e828e) ("Start 4.5.0 development"). |
| **"xplane2blender v5 unnofficial for Blender 5+"**, an unofficial port by xjs36uk, made with ChatGPT's help, posted in the *Utilities* file section of the X-Plane.Org forums in April 2026 | **xjs36uk** (X-Plane.Org forum user). The port's own `bl_info` still credits the original authors. | <https://forums.x-plane.org/files/file/99499-xplane2blender-v5-unnofficial-for-blender-5> | **No, not merged.** It was reviewed in full (section 2). Its central idea was right, but a cleaner implementation of the same fix (#765) was used instead. |
| **Open pull requests** on X-Plane/XPlane2Blender | Rob P, ILIAS TSELIOS, Connor Russell, galvedro, outbaacker | [open pull requests](https://github.com/X-Plane/XPlane2Blender/pulls) | 7 of 9 adopted (section 3) |
| **Open issues** on X-Plane/XPlane2Blender | Various reporters, listed per issue | [open issues](https://github.com/X-Plane/XPlane2Blender/issues) | 15 fixed, 1 not reproducible, the rest triaged (section 4 and the appendix) |
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
| 5.0.0-beta.1 (`master` of this fork) | **166 of 166** (includes 8 new tests) |

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

### Not reproducible on Blender 5.2

| Issue | Title | Reported by | Result |
|---|---|---|---|
| [#747](https://github.com/X-Plane/XPlane2Blender/issues/747) | Mirrored (negative-scale) linked duplicates export with inverted normals | [@NuanFeng520](https://github.com/NuanFeng520) | Mirrored children (−X, and −X−Y, with and without custom normals) export with triangles facing their normals on Blender 5.2. No code change; a regression test was added in [`0447259`](https://github.com/LucienMP/XPlane2Blender/commit/04472594d2fadbe6cbb0cda2eea246a65bb76d41). |

### Still open, and worth doing next

| Issue | Title | Reported by | State | Effect of fixing it |
|---|---|---|---|---|
| [#738](https://github.com/X-Plane/XPlane2Blender/issues/738) | Dataref values in Bone Tab aren't colored | [@skijeffory](https://github.com/skijeffory) | **Confirmed still present** in Blender 5.2 | Cosmetic. Keyframed bone dataref values would show as animated in the panel. Bone keyframes do export correctly. |
| [#755](https://github.com/X-Plane/XPlane2Blender/issues/755) | Automatic light with spot_params_bb_pm : wrong intensity parameter | [@cpot](https://github.com/cpot) | Needs Laminar to confirm the X-Plane 12 rule | Correct intensity for this light. Currently `cd` is added to every automatic light's intensity. |
| [#621](https://github.com/X-Plane/XPlane2Blender/issues/621) | Add wheel support for Drag Rotate manipulators | [@tngreene](https://github.com/tngreene) | Needs spec confirmation | Mouse-wheel support for Drag Rotate manipulators |
| [#709](https://github.com/X-Plane/XPlane2Blender/issues/709) | Vertex Optimization on Export | [@ian-m-carr](https://github.com/ian-m-carr) | Not started; it **changes output** | Shares identical vertices between objects. The reporter saw about a third as many VT lines on a cockpit. |
| [#701](https://github.com/X-Plane/XPlane2Blender/issues/701) | REGRESSION: ATTR_light_level directive in custom attributes is reset in newer exporter | [@GlidingKiwi](https://github.com/GlidingKiwi) | Not started; it **changes output** | A custom `ATTR_light_level` on a parent would no longer be reset by each child's material. |
| [#643](https://github.com/X-Plane/XPlane2Blender/issues/643) and [#516](https://github.com/X-Plane/XPlane2Blender/issues/516) | Should bones support Show/Hide animation? / Show/Hide only allowed on Objects, shown on Armature/Bone Panel UI | [@todirbg](https://github.com/todirbg), [@tngreene](https://github.com/tngreene) | Not started | The bone panel offers Show/Hide, but it's never exported. Either export it or remove it from the bone UI. |
| [#497](https://github.com/X-Plane/XPlane2Blender/issues/497) | Bone weight appears to be unused | [@tngreene](https://github.com/tngreene) | Not started | The bone panel's weight setting would affect draw order, or be removed from the UI. |
| [#746](https://github.com/X-Plane/XPlane2Blender/issues/746) and [#338](https://github.com/X-Plane/XPlane2Blender/issues/338) | Error adding extension / plugin into Blender 4.4 / Remove relative imports and circular dependencies | [@GitDaBytes](https://github.com/GitDaBytes), [@tngreene](https://github.com/tngreene) | Not started | Packaging as a Blender *Extension* (`blender_manifest.toml`, relative imports). 5.0 installs fine as a regular add-on with *Install from Disk* on Blender 5.2; this was verified. |

---

## 5. Other changes made for 5.0

These were found by running the upstream test suite and the UI on Blender 5.2.2. None has an upstream issue.

| Change | Commit | Effect |
|---|---|---|
| Legacy-file updater uses the PropertyGroup instead of `datablock["xplane"]` | [`d361138`](https://github.com/LucienMP/XPlane2Blender/commit/d36113815b9f3d249c765006cebcb7f4079e9417) | Blender 5 hides add-on properties from dictionary-style access, so opening .blend files made with XPlane2Blender 3.x crashed the updater, and Blend Glass settings were lost. |
| Wiper gradient bake rewritten for current Cycles | [`07a290c`](https://github.com/LucienMP/XPlane2Blender/commit/07a290c2ab534d8c3d5e6fd64ba3680e0535e66a) | Cycles now needs the image node to be both *active and selected*, so baking failed. The operator now sets that up, and restores bake margin, frame, render engine and selection on every exit path. A failed bake used to leave the margin at 0. Blender-Internal code paths were removed. |
| Python 3.12+ cleanups | [`5688f8d`](https://github.com/LucienMP/XPlane2Blender/commit/5688f8d90722106a40a28274fa4cb97b5118f0ba), [`6df3b20`](https://github.com/LucienMP/XPlane2Blender/commit/6df3b203c1705e526035b1095fafdb6c23b3a940) | Removes invalid-escape `SyntaxWarning`s and a `return` inside `finally`. The test suite no longer uses the removed `assertEquals` or the renamed `bpy_types` module. |
| Version 5.0.0-beta.1 | [`e48d4e2`](https://github.com/LucienMP/XPlane2Blender/commit/e48d4e296948c57ee1c3c81dcf852696f2614d26) | Requires Blender 5.0+ (`bl_info`). Data model version 124. README updated, and the bug tracker points to this fork. |

---

## 6. How 5.0 was tested
- **Blender:** 5.2.2 LTS on Windows 11.
- **Upstream test suite:** **166 of 166 test files pass**, including 8 new ones covering the operators, LOD state, the Blended layer group, `ATTR_manip_device`, mirrored objects and the VLIGHT deprecation. The run uses a parallel runner, with `tests/utils/lights_parser` run on its own because it temporarily replaces `lights.txt`.
- **Installation:** the release zip installs with Blender's *Install from Disk* into a clean profile, enables, and exports a valid OBJ.
- **UI:** in a real Blender window, every X-Plane panel (Scene, Render, Object, Data, Material, Bone) was drawn for a mesh, a light and an armature. None raised an error.
- **Not tested:** loading the exported OBJs in X-Plane itself (outputs are checked against the upstream test fixtures), and any Blender version other than 5.2.

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
| [#747](https://github.com/X-Plane/XPlane2Blender/issues/747) | Mirrored (negative-scale) linked duplicates export with inverted normals | [@NuanFeng520](https://github.com/NuanFeng520) | Not reproducible on 5.2 |
| [#741](https://github.com/X-Plane/XPlane2Blender/issues/741) | Symlinked texture files follow the link (obj header) when exported. | [@danklaue](https://github.com/danklaue) | **Fixed in 5.0** |
| [#473](https://github.com/X-Plane/XPlane2Blender/issues/473) | No validation for textures having a space in the file name | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** |
| [#577](https://github.com/X-Plane/XPlane2Blender/issues/577) | Validate TEXTURE field that texture does not have spaces in it | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** |
| [#709](https://github.com/X-Plane/XPlane2Blender/issues/709) | Vertex Optimization on Export | [@ian-m-carr](https://github.com/ian-m-carr) |  |
| [#725](https://github.com/X-Plane/XPlane2Blender/issues/725) | Dataref could not be parsed | [@pilotRL](https://github.com/pilotRL) | **Fixed in 5.0** |
| [#701](https://github.com/X-Plane/XPlane2Blender/issues/701) | REGRESSION: ATTR_light_level directive in custom attributes is reset in newer exporter | [@GlidingKiwi](https://github.com/GlidingKiwi) |  |
| [#190](https://github.com/X-Plane/XPlane2Blender/issues/190) | Incorrect Animations in OBJ's when using an armature | [@JasonGilholme](https://github.com/JasonGilholme) | **Fixed in 5.0** |
| [#643](https://github.com/X-Plane/XPlane2Blender/issues/643) | Should bones support Show/Hide animation? | [@todirbg](https://github.com/todirbg) |  |
| [#516](https://github.com/X-Plane/XPlane2Blender/issues/516) | Show/Hide only allowed on Objects, shown on Armature/Bone Panel UI | [@tngreene](https://github.com/tngreene) |  |
| [#497](https://github.com/X-Plane/XPlane2Blender/issues/497) | Bone weight appears to be unused | [@tngreene](https://github.com/tngreene) |  |
| [#730](https://github.com/X-Plane/XPlane2Blender/issues/730) | LOD setting causes incomplete obj-file | [@fsspn](https://github.com/fsspn) |  |
| [#285](https://github.com/X-Plane/XPlane2Blender/issues/285) | No UV-Mapping needs stronger warning | [@tngreene](https://github.com/tngreene) |  |
| [#515](https://github.com/X-Plane/XPlane2Blender/issues/515) | 280: Camera Collision allowed in Aircraft Export Type | [@tngreene](https://github.com/tngreene) |  |
| [#279](https://github.com/X-Plane/XPlane2Blender/issues/279) | Validate Slope Limit | [@tngreene](https://github.com/tngreene) |  |
| [#439](https://github.com/X-Plane/XPlane2Blender/issues/439) | ATTR_shiny_rat 0 written despite being X-Plane's default | [@tngreene](https://github.com/tngreene) |  |
| [#710](https://github.com/X-Plane/XPlane2Blender/issues/710) | run.py and tests.py replace rather than update environment | [@ian-m-carr](https://github.com/ian-m-carr) |  |

### B. Blender 4.x / 5.x compatibility

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#758](https://github.com/X-Plane/XPlane2Blender/issues/758) | XP2B 4.4.0 breakage in Blender >5.0.0 | [@JT8D-17](https://github.com/JT8D-17) | **Fixed in 5.0** |
| [#754](https://github.com/X-Plane/XPlane2Blender/issues/754) | Appears bone animations are still not compatible with 4.5 | [@kkaigle](https://github.com/kkaigle) | **Fixed in 5.0** |
| [#743](https://github.com/X-Plane/XPlane2Blender/issues/743) | Bone keyframes for datarefs | [@Im-Unknown-now](https://github.com/Im-Unknown-now) | **Fixed in 5.0** |
| [#738](https://github.com/X-Plane/XPlane2Blender/issues/738) | Dataref values in Bone Tab aren't colored | [@skijeffory](https://github.com/skijeffory) |  |
| [#565](https://github.com/X-Plane/XPlane2Blender/issues/565) | 280: EEVEE vs Cycles? | [@tngreene](https://github.com/tngreene) | **Fixed in 5.0** |
| [#746](https://github.com/X-Plane/XPlane2Blender/issues/746) | Error adding extension / plugin into Blender 4.4 | [@GitDaBytes](https://github.com/GitDaBytes) |  |
| [#338](https://github.com/X-Plane/XPlane2Blender/issues/338) | Remove relative imports and circular dependencies, make XP2B fully reloadable | [@tngreene](https://github.com/tngreene) |  |
| [#766](https://github.com/X-Plane/XPlane2Blender/issues/766) | no data object properties | [@TheRealTofferAviation](https://github.com/TheRealTofferAviation) |  |

### C. X-Plane 12 features and OBJ-spec gaps

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#755](https://github.com/X-Plane/XPlane2Blender/issues/755) | Automatic light with spot_params_bb_pm : wrong intensity parameter | [@cpot](https://github.com/cpot) |  |
| [#621](https://github.com/X-Plane/XPlane2Blender/issues/621) | Add wheel support for Drag Rotate manipulators | [@tngreene](https://github.com/tngreene) |  |
| [#370](https://github.com/X-Plane/XPlane2Blender/issues/370) | Deprecate VLIGHT from XPlaneLights | [@tngreene](https://github.com/tngreene) | **Done in 5.0** |
| [#489](https://github.com/X-Plane/XPlane2Blender/issues/489) | Instanced Scenery has no validation for named and paramter lights used | [@tngreene](https://github.com/tngreene) |  |
| [#368](https://github.com/X-Plane/XPlane2Blender/issues/368) | Instanced Scenery Object Export Type is severly lacking in validations | [@tngreene](https://github.com/tngreene) |  |
| [#284](https://github.com/X-Plane/XPlane2Blender/issues/284) | OBJ conditionals is not implemented properly, or hardly at all | [@tngreene](https://github.com/tngreene) |  |
| [#576](https://github.com/X-Plane/XPlane2Blender/issues/576) | 280: Add NEG_DIR_MAG to lights.txt spec, lights.txt | [@tngreene](https://github.com/tngreene) |  |
| [#461](https://github.com/X-Plane/XPlane2Blender/issues/461) | Always apply GLOBAL_specular 1.0 when NORMAL texture given | [@tngreene](https://github.com/tngreene) |  |

### D. Feature requests: small

| Issue | Title | Reported by | 5.0 status |
|---|---|---|---|
| [#68](https://github.com/X-Plane/XPlane2Blender/issues/68) | Datarefs that are part of an array don't automatically have numbers in [n] | [@danklaue](https://github.com/danklaue) |  |
| [#344](https://github.com/X-Plane/XPlane2Blender/issues/344) | Validate Datarefs | [@tngreene](https://github.com/tngreene) |  |
| [#345](https://github.com/X-Plane/XPlane2Blender/issues/345) | Give quick preview or access to dataref array indexes | [@tngreene](https://github.com/tngreene) |  |
| [#405](https://github.com/X-Plane/XPlane2Blender/issues/405) | Block use of sim/multiplayer datarefs | [@tngreene](https://github.com/tngreene) |  |
| [#403](https://github.com/X-Plane/XPlane2Blender/issues/403) | Give errors people that their textures aren't going to work. | [@tngreene](https://github.com/tngreene) |  |
| [#520](https://github.com/X-Plane/XPlane2Blender/issues/520) | 280: LOD Additive Mode validation for no double draw | [@tngreene](https://github.com/tngreene) |  |
| [#624](https://github.com/X-Plane/XPlane2Blender/issues/624) | Custom Footer Comment | [@tngreene](https://github.com/tngreene) |  |
| [#428](https://github.com/X-Plane/XPlane2Blender/issues/428) | Empty does not allow Custom Object Properties | [@tngreene](https://github.com/tngreene) |  |
| [#140](https://github.com/X-Plane/XPlane2Blender/issues/140) | Select errornous objects after export | [@der-On](https://github.com/der-On) |  |
| [#239](https://github.com/X-Plane/XPlane2Blender/issues/239) | Create button to bring up exporter log text document instantly | [@tngreene](https://github.com/tngreene) |  |
| [#354](https://github.com/X-Plane/XPlane2Blender/issues/354) | Progress indicator for export | [@Voidhawk9](https://github.com/Voidhawk9) |  |
| [#401](https://github.com/X-Plane/XPlane2Blender/issues/401) | Implement Show/Hide re-order arrows | [@tngreene](https://github.com/tngreene) |  |
| [#391](https://github.com/X-Plane/XPlane2Blender/issues/391) | Create hybrid dropdown/text field for chossing Emitter Names from .pss file | [@tngreene](https://github.com/tngreene) |  |
| [#561](https://github.com/X-Plane/XPlane2Blender/issues/561) | 280: Light search field similar to datarefs and commands search field | [@tngreene](https://github.com/tngreene) |  |
| [#575](https://github.com/X-Plane/XPlane2Blender/issues/575) | 280: Remove unused properties from XPlaneLayer, elsewhere | [@tngreene](https://github.com/tngreene) |  |
| [#416](https://github.com/X-Plane/XPlane2Blender/issues/416) | Irritatingly, XPlaneCockpitRegion.top is misnamed. Should be "bottom" | [@tngreene](https://github.com/tngreene) |  |
| [#375](https://github.com/X-Plane/XPlane2Blender/issues/375) | mkbuild should change bl_info['warning'] for non-RC builds | [@tngreene](https://github.com/tngreene) |  |
| [#466](https://github.com/X-Plane/XPlane2Blender/issues/466) | Unit scaling? | [@kbrandwijk](https://github.com/kbrandwijk) |  |

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
| [#562](https://github.com/X-Plane/XPlane2Blender/issues/562) | 280: No movement rotations exist in file | [@tngreene](https://github.com/tngreene) |  |
| [#235](https://github.com/X-Plane/XPlane2Blender/issues/235) | Duplicate animation transformations need optimization | [@tngreene](https://github.com/tngreene) |  |
| [#253](https://github.com/X-Plane/XPlane2Blender/issues/253) | Optimization: Bake static animations into key frame tables | [@bsupnik](https://github.com/bsupnik) |  |
| [#331](https://github.com/X-Plane/XPlane2Blender/issues/331) | Armature-based animations create extra static transform | [@bsupnik](https://github.com/bsupnik) |  |
| [#133](https://github.com/X-Plane/XPlane2Blender/issues/133) | Optimizations to pre-post transform matrix | [@bsupnik](https://github.com/bsupnik) |  |
| [#336](https://github.com/X-Plane/XPlane2Blender/issues/336) | Optimze the XPlaneBone tree by not collecting "useless" bones | [@tngreene](https://github.com/tngreene) |  |
| [#653](https://github.com/X-Plane/XPlane2Blender/issues/653) | Imp: Turn dynamic animations that turned out to be static into static animations | [@tngreene](https://github.com/tngreene) |  |
| [#134](https://github.com/X-Plane/XPlane2Blender/issues/134) | Vertex and Index Order Should be GPU Optimized | [@bsupnik](https://github.com/bsupnik) |  |

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
