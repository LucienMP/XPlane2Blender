[![Build Status](https://travis-ci.org/X-Plane/XPlane2Blender.svg?branch=master)](https://travis-ci.org/X-Plane/XPlane2Blender)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

# Introduction
This addon for Blender makes it possible to export models made in Blender to the X-Plane object format (.obj).

**This is XPlane2Blender 5.0, an unofficial port of [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender) to Blender 5.x.** Report problems with this version on [this fork's issues](https://github.com/LucienMP/XPlane2Blender/issues), not upstream.

## What's new in 5.0
Blender 5.x support:
- Animation export works with Blender 5's slotted (layered) Actions (#765), including bone dataref animations that live in the Armature's slot. On Blender 4.4/4.5 these bone animations were previously not exported either.
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

New features, from open upstream pull requests:
- Mouse wheel support for Drag Rotate manipulators (#621).
- `ATTR_manip_device` touch screen manipulator, X-Plane 12.1+ (#767). Loop values can now be negative.
- "Blended" layer group for glass scenery objects, X-Plane 12.21+ (#753).
- Dither strength for detail textures (decals) (#759).
- Export into a folder: an OBJ name ending in `/` exports to that folder using the root's name (#760).
- Scene report: a CSV of every dataref and manipulator in the scene (#764).
- Material compatibility checks no longer look at objects outside the root (#761).

Issue and pull request numbers refer to [X-Plane/XPlane2Blender](https://github.com/X-Plane/XPlane2Blender). For the authors of each change, full links, what was left out and why, and a review of the unofficial forum port, see [REVIEW-5.0.md](REVIEW-5.0.md).

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
