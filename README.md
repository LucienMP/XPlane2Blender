[![Build Status](https://travis-ci.org/X-Plane/XPlane2Blender.svg?branch=master)](https://travis-ci.org/X-Plane/XPlane2Blender)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

# THIS FORK'S INFORMATION

This is a fork of the original XPlane2Blender for Blender 4.x, updated to 5.x from [X-Plane to Blender 5.0 on X-Plane Forums](https://forums.x-plane.org/files/file/99499-xplane2blender-v5-unnofficial-for-blender-5/) with additional updates and PR merged into it.

1. Check README.PR.md
2. Check README-5.0.md


# Introduction
This addon for Blender makes it possible to export models made in Blender to the X-Plane object format (.obj).

**This is XPlane2Blender 5.0, an unofficial port of [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender) to Blender 5.x.** Report problems with this version on [this fork's issues](https://github.com/LucienMP/XPlane2Blender/issues), not upstream.

## What's new in 5.0
Blender 5.x support:
- Animation export works with Blender 5's slotted (layered) Actions (#765), including bone dataref animations that live in the Armature's slot. On Blender 4.4/4.5 these bone animations were previously not exported either.
- One Action can animate several objects, each through its own slot: each object exports only its own slot's animation. An Action assigned with none of its slots chosen animates nothing, so the export now warns instead of silently leaving the animation out.
- Older .blend files update correctly. Blender 5 hides add-on properties from the old dictionary-style access the updater used.
- Wiper gradient baking works with current Cycles.
- The bundled `lights.txt` is X-Plane 12.4.4's, so the 13 lights added since (such as the new runway inset lights) are recognised.
- The X-Plane material panel shows the material's Specular (exported as `ATTR_shiny_rat`). Blender materials always use nodes now, which hides that setting everywhere else.

Bug fixes:
- Removing a dataref no longer moves its keyframes onto the next dataref (#190). Bone dataref keyframes are now linear, like object ones.
- The Bone panel shows whether a dataref value is keyed (◆), animated (◇), or changed without re-keying (red field). A long-standing Blender limitation ([Blender #48975](https://projects.blender.org/blender/blender/issues/48975)) stops Blender colouring these itself (#738).
- Attributes are written again in every LOD. Previously, for example, `ATTR_light_level` only applied to the first LOD (#763).
- Export says what happened. A root with nothing in it no longer cancels the whole export silently (#751).
- Symlinked textures keep their own path (#741). Spaces in texture paths now give a warning (#473).
- Custom spill lights light up in X-Plane 12. X-Plane 12 reads their size as an intensity in candela, so XPlane2Blender now writes the light's Intensity for X-Plane 12 targets. The old size in meters gave little or no light (checked in X-Plane 12.4.4).
- Fixes the Rain panel error when nothing is selected (#752), and DataRefs.txt reading on non-UTF-8 Windows locales (#725).
- Instanced Scenery Objects warn when X-Plane won't actually instance them: any animation, custom billboard lights, custom spill lights with a dataref, and dataref-driven named or parameterized lights (#368, #489). Checked in X-Plane 12.4.4.
- The old VLIGHT light types (Default, Flashing, Pulsing, Strobe, Traffic) are all marked deprecated, and exporting them warns: their position ignores parenting and animation. Use Automatic lights instead (#370).
- With LODs on, objects nobody assigned to an LOD are no longer left out silently, which left an OBJ with no geometry (#730). A root's new **Objects in No LOD** setting (in its LOD settings) decides, and the export warns, naming them:
  - **All Distances** (default): in every LOD, or only the farthest one when the LODs are additive. X-Plane draws every additive LOD in range, so an object in all of them would be drawn several times (checked in X-Plane 12.4.3).
  - **First LOD:** only in the closest LOD.
  - **Not Exported:** left out, as before.

  An object counts as assigned when it or a parent has *Override LODs* on, even with no LOD ticked, which stays upstream's way to leave an object out on purpose.
- Show/Hide set on an armature bone (Bone tab) is now exported (#643, #516). It's written in the bone's animation block, so it shows or hides everything under the bone. The Bone tab always offered it, but it was ignored. The bone's custom animation attributes are now exported too. Checked in X-Plane 12.4.3.
- With **Optimize** on, identical vertices are shared across the whole OBJ, not just within each object (#709). OBJs with repeated parts get smaller: two identical animated boxes went from 48 to 24 vertices. Every changed test output was checked to draw exactly the same triangles, and the result was checked in X-Plane 12.4.3.
- `ATTR_shiny_rat 0` is only written to undo an earlier value. X-Plane starts at 0, and an explicit 0 looked identical to none in X-Plane 12.4.3 (#439).
- New warnings: a mesh with no UV map in a textured OBJ, which shows as one colour and can render unpredictably (#285); Camera Collision in an Aircraft OBJ, since only cockpit objects have it (#515; scenery types already refused it); Slope Limit values outside −90 to 90 degrees, or a minimum above its maximum (#279). The Slope Limit fields now also keep to that range, and moving one end past the other moves the other end too.
- The X-Plane panel on the Object Data tab only appears for lights and empties, the only types with settings there. For meshes it was an empty panel that looked like a broken install (#766).
- The upstream test runner (`tests.py`, `run.py`) works on Windows again: it keeps the system environment, and finds the add-on even when git checked out the `addons/modules` symlink as a plain file (#710).

Second pass (a read of the whole add-on, see [REVIEW-5.0.md section 7](REVIEW-5.0.md#7-second-pass-code-audit)):
- Mirrored (negative-scale) meshes no longer export inside out (#747). The earlier test for this couldn't tell.
- `ATTR_hud_reset` and `ATTR_poly_os 0` are written after HUD glass and polygon-offset meshes; they never were.
- Attributes set inside an `IF` block are written again, or reset, after the `ENDIF`, since X-Plane may have skipped the block.
- Custom attribute weights order the output again (broken since 4.1).
- Texture and decal paths are relative to the folder the OBJ is written to, also with File > Export.
- A light aimed exactly opposite its lights.txt direction is turned around instead of writing a zero rotation axis.
- Negative loop values are written; keyframes on fractional frames are read at the nearest frame with a warning.
- Fixed crashes on: keyframed loop or show/hide values, draped bump level, bad decal/thermal/wiper paths, lights.txt `NULL` arguments, a Device manipulator after lowering the X-Plane version, saving after disabling the add-on, and Commands.txt files in another encoding.
- "Add Light Property" works, the material Light Level dataref search fills in the active material, bone keyframe buttons show for bone-only animation, the Startup and Updater logs show warnings, the scene report lists the right manipulator fields, and `tests.py --continue` fails when tests fail.

New features, from open upstream pull requests:
- Mouse wheel support for Drag Rotate manipulators (#621).
- `ATTR_manip_device` touch screen manipulator, X-Plane 12.1+ (#767). Loop values can now be negative.
- "Blended" layer group for glass scenery objects, X-Plane 12.21+ (#753).
- Dither strength for detail textures (decals) (#759).
- Export into a folder: an OBJ name ending in `/` exports to that folder using the root's name (#760).
- Scene report: a CSV of every dataref and manipulator in the scene (#764).
- Material compatibility checks no longer look at objects outside the root (#761).

New features, checked in X-Plane 12.4.4:
- Publish OBJs in the scenery pack's `library.txt`, including seasonal variants (`EXPORT_SEASON`). See [Publishing OBJs in library.txt](#publishing-objs-in-librarytxt).
- The "Scenery Shadows" condition (`SCENERY_SHADOWS`), as used by Laminar's own scenery. See [Conditions](#conditions-if--endif).

Issue and pull request numbers refer to [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender). For the authors of each change, full links, what was left out and why, and a review of the unofficial forum port, see [REVIEW-5.0.md](REVIEW-5.0.md).

### Conditions (IF / ENDIF)
An object's Conditions (Object properties > Conditions) wrap its geometry in `IF <variable>` / `ENDIF`, or `IF NOT <variable>` / `ENDIF` when "Must Be On" is off. X-Plane decides each condition once, when it loads the OBJ, from its graphics settings: conditions can't use datarefs, and X-Plane reloads the OBJ when those settings change.

These are all the variables X-Plane 12.4.4 knows. They're built in, so you can't define your own:

| Variable | Shown as | True when | In X-Plane 12 |
|---|---|---|---|
| `GLOBAL_LIGHTING` | HDR | HDR rendering is on | Always true: X-Plane 12 has no non-HDR mode |
| `GLOBAL_SHADOWS` | Global Shadows | Any shadows are enabled | Follows the shadow settings |
| `SCENERY_SHADOWS` | Scenery Shadows | Scenery casts shadows | Follows the shadow settings |
| `VERSION10` | Version 10.x | X-Plane 10 or later | Always true |
| `VERSION12` | not offered | The running X-Plane is version 12 | Always true. Undocumented, found in the X-Plane executable |

- **Any other name is an error.** X-Plane logs "unknown variable for IF statement" for names such as `VERSION11`, `VERSION13` or `SEASONAL`. There's no season variable: seasonal objects go through `library.txt` instead, see below.
- **The one real-world use is a fake shadow.** In 24,714 OBJs (X-Plane 12 plus add-on scenery), the only condition that does anything is in Laminar's static CRJ-200 (and a copy of it): `IF NOT SCENERY_SHADOWS`. It draws a dark patch under the aircraft only when scenery shadows are off. To do the same, add a "Scenery Shadows" condition with "Must Be On" off. In X-Plane 12.4.3, XPlane2Blender's export of this hid the patch with shadows on, and the "Must Be On" version showed it.
- **`ELSE`, `ELSE IF` and `ELSE IF NOT` aren't supported yet.** X-Plane 12 accepts them, but XPlane2Blender only writes `IF` / `IF NOT` ... `ENDIF`. They could be added in future, for example as an "Else" object linked to its condition. Nothing in a default X-Plane 12 install uses them. Until then, use two objects with opposite conditions.

### Publishing OBJs in library.txt
Other scenery, including X-Plane's own, refers to objects by library path, such as `lib/my_library/trees/oak.obj`. A scenery pack's `library.txt` maps those paths to its OBJ files. XPlane2Blender can write those entries for you:

1. In a root's settings (Scenery Properties > Library), tick **Add to library.txt** and enter the **Library Path**.
2. Choose how the OBJ is published:
   - **Export:** replaces what lower priority packs publish under the path. Optionally set a **Ratio**, to weight how often X-Plane picks this OBJ among several.
   - **Extend:** adds to what lower priority packs publish.
   - **Exclude:** publishes the path, and stops lower priority packs from publishing it.
   - **Backup:** only used when no other pack publishes the path.
3. For seasonal variants (X-Plane 12), tick **By Season** and the seasons this OBJ is for. Publish one OBJ per season, or one per group of seasons, under the same Library Path, for example a green tree for spring and summer, a bare one for autumn, and a snowy one for winter.
4. Export. `library.txt` goes in the scenery pack's root folder when you export into `Custom Scenery/<pack>/`. Otherwise it goes in the export folder.

XPlane2Blender only changes its own block of `library.txt`, marked with the .blend file's name, so entries you wrote by hand and other .blend files' blocks are kept:

```
A
1200
LIBRARY

# BEGIN XPlane2Blender: trees.blend
EXPORT_SEASON	fal	lib/my_library/trees/oak.obj	objects/oak_bare.obj
EXPORT_SEASON	spr,sum	lib/my_library/trees/oak.obj	objects/oak_green.obj
EXPORT_SEASON	win	lib/my_library/trees/oak.obj	objects/oak_snow.obj
# END XPlane2Blender: trees.blend
```

Exporting an OBJ only replaces its own lines in the block, and turning off "Add to library.txt" removes them.

X-Plane's rules for seasons, which the export checks:
- **One or the other.** A library path is published either by season or not by season, never both. Mixing them is an export error.
- **Cover the whole year.** X-Plane needs all four seasons covered under a path, or it shows nothing in the missing ones (checked in X-Plane 12.4.3). A missing season is a warning.
- **No seasonal Ratio or Backup.** X-Plane has no seasonal version of `EXPORT_RATIO` or `EXPORT_BACKUP`.

How X-Plane 12 picks the season, as tested in X-Plane 12.4.3 and 12.4.4 ([tool and results](tools/xplane12_instancing_test)):
- **It doesn't simply follow the calendar.** At 47°N (Shelton, WA), 15 January gave winter, 15 April spring, 21 June still spring, 15 August summer, and 15 October autumn.
- **The tropics stay in one season.** At 17.8°S (Nadi, Fiji), both January and June gave spring, so give tropical scenery a spring OBJ that looks right all year.
- **The southern hemisphere has the opposite seasons.** At 42.8°S (Hobart), 15 January, 15 February and even 15 April gave summer, 21 June and 15 August winter, and 15 October spring. At 38°S (Moorabbin, Melbourne), 15 February gave summer and 15 August winter. So one seasonal set of OBJs works in both hemispheres: X-Plane picks the right one for the place.
- **The climate matters too.** 15 April was still summer at Hobart, while the mirror date at Shelton (15 October) was already autumn.
- **It's chosen when the scenery loads.** Changing the date mid-flight from June to January didn't change the OBJ within 90 seconds.

## General Requirements
- Blender 5.0 or later. Tested with Blender 5.2 LTS.
- X-Plane 12, although older X-Plane versions can still be targeted in Scene settings.

## Contact Us
For this 5.0 port, please open [an issue on this fork](https://github.com/LucienMP/XPlane2Blender/issues). The original add-on is maintained at [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender).

## Automatic Installation
**Note: This process will override an existing copy of the plugin!** To backup your current version of the plugin, see the manual instructions in the [manual](https://xp2b-docs.gitbook.io/xplane2blender-docs/index-3/34_installation). **Always make backups of your work, especially when beta testing, as newer versions may not be backwards compatibility.** Read the release notes for more details.

1. Download the addon .zip from [this fork's releases](https://github.com/LucienMP/XPlane2Blender/releases), or build it with `python mkbuild.py`. **Do not download the .zip file called "Source Code", do not unzip the io_xplane2blender .zip file**
2. In Blender, open Edit > Preferences > Add-ons, and in the drop-down menu at the top right choose "Install from Disk..."
3. Using the file picker, find the .zip file and click "Install from Disk". This will automatically unzip it to the add-ons folder
4. Ensure the checkbox next to the words "Import-Export: Export: X-Plane (.obj)" is checked
5. **Restart Blender even if you see the UI change**
6. Begin using XPlane2Blender!

For less stable betas or different versions see the [releases page](https://github.com/X-Plane/XPlane2Blender/releases). Be sure to read the notes.

## Get Started!
See the [Introduction to XPlane2Blender Video](https://developer.x-plane.com/tools/blender/) and download the example files and you'll be well on your way to exporting your first mesh and seeing it in X-Plane! Although the Blender version shown is Blender 2.79, XPlane2Blender is almost entirely the same across versions.

## Documentation Sources
- [XPlane2Blender Manual](https://xp2b-docs.gitbook.io/xplane2blender-docs)
- [The PZL-M-18, an open source aircraft](https://github.com/todirbg/PZL-M-18)
- [The BD-5J Microjet, an open source jet](https://forums.x-plane.org/index.php?/files/file/27269-bd-5j-microjet)
- [Dan Klaue's "Using Blender With PlaneMaker" Playlist](https://www.youtube.com/playlist?list=PLDB0F4B925CF9169C). While older it still explains many of the principles of XPlane2Blender
- [X-Plane Scenery File Formats](http://developer.x-plane.com/docs/specs/)
- [X-Plane.org's 3d Modeling board](https://forums.x-plane.org/index.php?/forums/forum/45-3d-modeling/)
- [X-Plane Scenery Developer Blog/Knowledge Base](http://developer.x-plane.com/)
- [X-Plane Modeling Tutorials](http://developer.x-plane.com/docs/modeling/)

## Test Suite
**The average user does not need the test suite.** Before releasing a build to the public we test the code many many many times! This is only useful for developers and power users who make changes to the source code. The tests folder must also be in the same folder as the addon folder (see manual installation).

If you have Python installed (hopefully matching Blender's internal interpreter for maximum stability) and the **full source code** downloaded, you can run the test suite. It will attempt to export sample .blend files that utilize various features of the exporter and print the results (see the contents of the ``test`` folder). All passing means XPlane2Blender is safe to use. In the XPlane2Blender folder, open up a command line and run

``python tests.py --print-fails``

This will run all tests until the end or a failure occurs. Only detailed logs will be printed for the failed test. See ``--help`` to show all flags and what they do.

Use ``--blender PATH`` when Blender isn't on your PATH, e.g. ``python tests.py --blender "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -c``. On Windows, where git usually checks out the ``addons/modules`` symlink as a plain file, the runner makes a junction for it in your temp folder.

To see what an exporter change does to every test's output, set ``XP2B_TEST_OUTPUT_DIR`` to a folder: each test that compares against a fixture also saves its output there, named after the fixture's path. Run once before and once after the change, then compare the folders. The same files can replace fixtures when a change of output is intended.
