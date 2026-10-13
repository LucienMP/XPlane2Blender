# Check in X-Plane: does X-Plane draw the OBJ the way Blender shows the model?

A button in the Scene panel (**Check in X-Plane**) exports the active root with
XPlane2Blender, photographs it in X-Plane from six camera positions, renders the same
views in Blender, compares the pictures and opens them side by side. It tests what the
exporter is responsible for: shape, position, orientation, scale, animation pose,
show/hide, winding, UV mapping and the lights' positions and colours.

## Using it

1. Edit > Preferences > Add-ons > XPlane2Blender: set the **X-Plane Folder**. In X-Plane,
   Settings > Network, allow incoming traffic, so that its Web API is on.
2. Close X-Plane. Select the root to check (an exportable object or collection), and pose
   the model: the datarefs' current values are what X-Plane gets.
3. Scene panel > X-Plane > **Check in X-Plane**, choose a check, OK. X-Plane starts, runs
   for about three minutes and quits; the status bar says where it is. Nothing in the
   .blend changes: the check works on a copy.
4. The comparison opens in an Image Editor: one row per view, Blender on the left,
   X-Plane in the middle, differences in red on the right. The Scene panel shows PASS or
   FAIL with the failing lines; the full report is in the `xplane_parity_report` text block.
   **Show Comparison** reopens the image.

The checks:

- **Shapes** (palette): every material is replaced by a flat colour, one per material.
  Shapes, positions, animation pose, show/hide and face winding, compared exactly: a view
  passes when the colour-classified pictures agree on at least 97% of their pixels and
  every colour's overlap (intersection over union) is at least 0.85. The report's "model
  extent" lines give the model's bounding box in both pictures, so a scale or camera
  problem shows as a ratio.
- **Textures**: the root's Default texture stays on the model, also as its lit texture.
  Checks UV mapping and texture assignment: wrong, missing, swapped or flipped textures
  show as red. X-Plane's tone mapping shifts colours, so the threshold is loose (85% of
  the model's pixels within a colour distance), and colour fidelity isn't judged.
- **Lights**: only the lights are exported. Blender renders a sphere where each light is;
  X-Plane draws its billboard. Each sphere must have an X-Plane light within 30 px, and
  the colours are compared. Spill lights' glow on the floor is reported as present or
  absent, not matched: X-Plane's halos and spill have no Blender equivalent.

During a check, the other plugins in `Resources/plugins` are renamed into
`Resources/plugins_aside_xp2b` and renamed back afterwards (their windows would be in the
screenshots); the preference turns that off. X-Plane's preferences and Log.txt are backed
up on first use and restored by `python parity.py cleanup`, which also removes the plugin.

## How it works

X-Plane and Blender never match pixel for pixel: different renderers, lighting, tone
mapping and auto exposure. So nothing is lit:

- The model wears flat colours from `palette.png` (or its own texture), used as the OBJ's
  `TEXTURE` and `TEXTURE_LIT`, and X-Plane shoots at **midnight** inside a 60 m **black
  booth** (`booth.obj`, `ATTR_no_cull`, `GLOBAL_specular 0`). The lit texture gives the
  colours and there is no light for the surfaces to reflect. (A self-lit green booth was
  tried first: its light came back off the model as a white specular term and turned red
  faces yellow.)
- The plugin (`plugin/xp2b_parity.c`, built as `plugin/win.xpl`) places the booth and the
  model with the Instance API 40 m ahead of the aircraft and 1 m above the probed terrain,
  feeds the model its dataref values, sets the field of view, takes the camera through
  the views in `VIEWS` with `XPLMControlCamera`, screenshots each and quits X-Plane.
- Blender renders the views with Workbench in flat texture mode on a black world, posed
  by the same dataref values (the frame where each dataref's keyframes give that value,
  Show/Hide applied in X-Plane's order).
- The pictures are classified pixel by pixel (dark is background; others are normalised
  by their brightest channel, so exposure doesn't matter, and matched to the nearest
  palette colour), and compared with pixels within 2 px of a colour change left out.

Camera positions are orbits from `views.json` (azimuth from the model's front, elevation),
framed from the model's bounds and shared as offsets in OBJ coordinates (X east, Y up,
Z south) from the model's origin; X-Plane's local frame at heading 0 is the same frame.
The field of view (60°) is X-Plane's horizontal angle: with it, the model's extent in
X-Plane matched Blender's to the pixel.

## From the command line, and in the test suite

```
python parity.py sample                                      # a sample scene in work/sample/
python parity.py run work\sample\sample.blend parity_sample --mode palette --dataref sim/cockpit2/controls/flap_ratio=0.75
python parity.py run MODEL.blend ROOT --mode textured
python parity.py cleanup
```

`--xplane DIR` and `--blender EXE` (or `XPLANE_DIR` and `BLENDER`) say where things are;
`--skip-xplane` re-renders and compares with the screenshots already in the work folder.
Results go in `work/<name>/`: `model.obj`, `blender_<view>.png`, `xplane_<view>.png`,
`diff_<view>.png`, `comparison.png`, `report.txt`, the plugin's log and X-Plane's Log.txt.

`tests/features/parity_tool.test.py` runs in the normal suite without X-Plane: the palette
conversion, the classifier, the comparisons and each mode's export. The X-Plane runs are
in `tests/xplane_visual/` and only run with `python tests.py --xplane` (about ten minutes
for the three modes), since they start X-Plane; CI can't run them.

## Results on the sample (X-Plane 12.4.3, 13 October 2026)

- Shapes: every view passes, every colour's overlap 1.000, the model's pixel extent the
  same in both pictures to within a few pixels. On the way there the check found a real
  defect: the first sample's top and bottom faces were wound inside out, which Blender's
  two-sided Workbench draws and X-Plane culls, so the top view showed the floor instead.
- Textures: 91 to 93% texture agreement, silhouettes overlapping 93 to 95%; the misses are
  the colour shifts at texture cell edges. Before the check rendered the root's texture on
  every material it failed honestly at 16%, since the sample's materials had no texture.
- Lights: the beacon's billboard is 2 to 8 px from Blender's sphere in every view, red in
  both (X-Plane's (1.0, 0.35, 0.1) after tone mapping).

## Building the plugin

`plugin/win.xpl` is committed, and CI rebuilds it for release packages. By hand, with
Visual Studio 2022 and Laminar's [XPSDK430](https://developer.x-plane.com/sdk/plugin-sdk-downloads/):
`plugin\build.bat C:\path\to\XPSDK430\SDK`. It is Windows only for now.

## Limits

- Black is the background, so a model's parts must stay bright: a pixel below 8%
  brightness counts as background. The shapes check uses seven colours, repeating when a
  model has more materials; parts that share a colour are told apart by position only.
- The textures check needs the root's Default texture as a file (PNG or DDS), and Blender
  shows each material's active image node, which should be that texture.
- Every animated object must key its dataref values at the same frames, since Blender
  has one frame to pose the whole scene.
- A model has to fit the booth: a radius of about 6 m at the 60° field of view.
