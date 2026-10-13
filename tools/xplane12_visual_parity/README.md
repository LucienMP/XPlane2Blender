# Visual parity test: Blender model vs X-Plane OBJ

Does X-Plane draw the exported OBJ the way Blender shows the model? This tool exports a
model with XPlane2Blender, photographs it in X-Plane from set camera positions, renders
the same views in Blender, and compares the pictures. It tests what the exporter is
responsible for: shape, position, orientation, scale, animation pose, show/hide, UV
mapping and winding.

## The idea

X-Plane and Blender will never match pixel for pixel: different renderers, lighting,
tone mapping and auto exposure. So nothing is lit:

- The model's materials use one flat **palette texture** (`palette.png`: red, blue,
  yellow, cyan, magenta, white and green for the model, black for the booth). Each
  material's UVs sit in one cell, so every pixel of a part is one known colour.
- The OBJ uses the palette as `TEXTURE_LIT` as well, and X-Plane shoots at **midnight**
  inside a **black booth** (`booth.obj`, 60 m, `ATTR_no_cull`, `GLOBAL_specular 0`).
  Sun, shadows, materials and weather play no part; the LIT texture gives the pure
  colours, and there is no light for the model's surfaces to reflect. (A self-lit green
  booth was tried first: its light came back off the model as a white specular term and
  turned red faces yellow.)
- Blender renders the same views with Workbench in flat texture mode on a black world.
- Both images are **classified** pixel by pixel: dark pixels are the background, every
  other pixel is normalised by its brightest channel, so exposure doesn't matter, and
  matched to the nearest palette colour. The label maps are compared with pixels within
  2 px of any colour change left out (anti-aliasing, bloom).

A view passes when the label maps agree on at least 97% of the compared pixels and every
colour covering at least 0.5% of the picture has an intersection-over-union of at least
0.85. `report.txt` also gives each colour's coverage and the model's pixel extent in both
pictures, which shows a field-of-view or scale mismatch directly.

## The parts

- `make_booth.py`: writes `palette.png` and `booth.obj`.
- `blender/parity_blender.py`: runs inside Blender with the add-on. `sample` makes a sample
  scene (coloured boxes, a flap animated by `sim/cockpit2/controls/flap_ratio`, a cube
  hidden when the flaps pass half way). `export` writes `model.obj` (texture paths
  renamed to `palette.png`), the booth and palette, and resolves the orbit views of
  `views.json` into camera and target offsets from the model's bounds. `render` poses the
  model at the dataref values (the frame where each dataref's keyframes give that value;
  Show/Hide applied in X-Plane's order) and renders each view. `compare` does the
  classification and writes `report.txt` and `diff_<view>.png` (disagreements in red).
- `plugin/xp2b_parity.c`: once armed and the scenery has loaded, loads the booth and the
  model with the Instance API 40 m ahead of the aircraft on the probed terrain (no DSF or
  library needed), feeds the model the dataref values in `DATAREFS`, sets the field of
  view, takes the camera with `XPLMControlCamera` through the views in `VIEWS`,
  screenshots each (20 s first for auto exposure, then 4 s each) and quits X-Plane.
- `parity.py`: the driver. Starts X-Plane, starts a midnight flight at Shelton, WA
  (KSHN) through the Web API, collects the screenshots, then renders and compares.
  During the run every other plugin folder in `Resources/plugins` is renamed into
  `Resources/plugins_aside_xp2b` (same drive, so nothing is copied) and renamed back
  afterwards (also by `install`, `cleanup` and the next run),
  because plugin windows and overlays would end up in the screenshots. X-Plane's own
  data output overlay can't be turned off from a plugin; `views.json`'s `ignore`
  rectangles (fractions of the image from the top left) leave it out of the comparison.
- `views.json`: the views as orbits (azimuth from the model's front, elevation), the field
  of view and how much of the frame the model should fill.

Camera positions are shared through OBJ coordinates (X east, Y up, Z south) relative to
the model's origin; the model is placed with heading 0, so X-Plane's local frame is the
same frame. Blender converts them back with `(x, -z, y)`.

## Running it

Needs X-Plane 12.4+ with the Web API on (Settings > Network: allow incoming traffic),
Visual Studio 2022 and Laminar's [XPSDK430](https://developer.x-plane.com/sdk/plugin-sdk-downloads/).
Close X-Plane first and don't use it during a run; each run starts and quits it.

```
plugin\build.bat C:\path\to\XPSDK430\SDK
python parity.py install
python parity.py sample
python parity.py run work\sample\sample.blend parity_sample --dataref sim/cockpit2/controls/flap_ratio=0.75
python parity.py cleanup
```

`run` takes any .blend and the name of its exportable root (object or collection).
Results go in `work/<name>/`: `model.obj`, `blender_<view>.png`, `xplane_<view>.png`,
`diff_<view>.png`, `report.txt`, the plugin's log and X-Plane's Log.txt. `--skip-xplane`
re-renders and compares with the screenshots already there, for working on the Blender
side. `--views` picks another views file. A run takes about three minutes.

## What a model must look like

- Materials with an image node showing `palette.png`, UVs inside one cell (see
  `make_booth.cell_uv`). `blender/parity_blender.py`'s `box()` shows the pattern.
- The root's Default and Night textures both `palette.png` (any path; it's renamed).
- Datarefs given with `--dataref` pose the model. Every animated object must key the
  dataref value at the same frames, since Blender has one frame to pose the whole scene.
- Small enough to be framed from inside the booth: a radius of about 6 m at the default
  60° field of view.

## Known limits

- Black is the background, so a model can't use it, and a model's parts must stay
  bright: a pixel below 8% brightness counts as background.
- Lights aren't compared; at night they'd be the only lit things, which is a possible
  extension (a `LIGHT_NAMED` with a known colour against a dark booth).
- Blender's and X-Plane's field of view conventions differ; `views.json` says which axis
  the angle applies to in X-Plane, and the extent lines in `report.txt` show any
  mismatch as a constant width or height ratio.
