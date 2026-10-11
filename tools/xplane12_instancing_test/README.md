# X-Plane 12 instancing test

Checks, in X-Plane itself, which OBJ features stop an object from being **hardware instanced**. XPlane2Blender's
Instanced Scenery Object warnings ([#368](https://github.com/X-Plane/XPlane2Blender/issues/368),
[#489](https://github.com/X-Plane/XPlane2Blender/issues/489)) are based on these results. Rerun it when a new
X-Plane version might have changed the rules.

## How it works

- `make_objects.py` writes a textured 3 m box, plus variants that each add one feature: an animation, an attribute,
  or a light.
- `gen_dsf.py` builds an overlay DSF that places **10,000 copies** of `objects/test.obj` on the grass beside runway 05
  at Shelton, WA (KSHN). It also builds an empty DSF, used as the baseline.
- `plugin/` is a small X-Plane plugin. Once the runner has armed it, it waits for the scenery to load, records every
  numeric dataref five times, takes a screenshot and quits X-Plane.
- `runner.py` swaps in one variant, starts X-Plane, and starts the flight through X-Plane's Web API
  (`POST /api/v3/flight`, the same way FSSR's `xpweb.py` does). It then collects the results.

**The measure:** `sim/private/stats/instance/num_cluster_objs`, the number of objects X-Plane has put into instancing
clusters. With 10,000 copies an instanced variant raises it by about 10,000. A non-instanced one doesn't change it.
Between repeated runs it varies by a few hundred, because slightly different surrounding scenery loads each time.
The old way of checking, the `terrain/kill_clusters` art control from Laminar's 2016 blog post, no longer exists in
X-Plane 12.

## Running it

Needs: X-Plane 12.4+, the Web API on (Settings > Network: incoming traffic allowed), Visual Studio 2022, Laminar's
[XPSDK430](https://developer.x-plane.com/sdk/plugin-sdk-downloads/) and
[XPTools](https://developer.x-plane.com/tools/xptools/) (for `DSFTool.exe`). **Close X-Plane first, and don't use it
while the runs go: each run starts and quits X-Plane.**

```
plugin\build.bat C:\path\to\XPSDK430\SDK
python make_objects.py objects
python gen_dsf.py C:\path\to\xptools\tools\DSFTool.exe
python runner.py install        # backs up scenery_packs.ini, preferences and Log.txt first
python runner.py run none control anim light_custom named_sw_VASI ...
python runner.py cleanup        # removes the plugin and scenery, restores the backups
```

Each run takes about 2 minutes. The results go in `results/<variant>/`: `datarefs.tsv`, the plugin's `log.txt`,
X-Plane's `Log.txt` and a screenshot. `XPLANE_DIR` sets the X-Plane folder (default `E:\X-Plane 12`).

## Results: X-Plane 12.4.4 (build 124414), 11–12 October 2026

The baseline (no objects) was 637,898 and 637,805 in two runs; differences are from their average.

| Variant | What it adds | `num_cluster_objs` change | Instanced? |
|---|---|---|---|
| `control` | Nothing (plain box) | +9,565 / +9,877 | **Yes** |
| `anim` | `ANIM_rotate` | −545 | No |
| `anim_trans` | `ANIM_trans` | −69 | No |
| `anim_hide` | `ANIM_hide` (never actually hidden) | +89 | No |
| `attr_shiny_rat` | `ATTR_shiny_rat` before the triangles | +27 | No |
| `attr_hard` | `ATTR_hard` before the triangles | +9,563 | **Yes** |
| `light_custom` | `LIGHT_CUSTOM` (dataref `NULL`) | −111 | No |
| `spill_custom_none` | `LIGHT_SPILL_CUSTOM`, dataref `none` | +9,648 | **Yes** |
| `spill_custom_dref` | `LIGHT_SPILL_CUSTOM`, dataref `sim/graphics/animation/lights/strobe` | +213 | No |
| `named_hw_headlight` | `LIGHT_NAMED headlight` (hardware only in lights.txt) | +9,179 | **Yes** |
| `named_hw_obs_red_night` | `LIGHT_NAMED obs_red_night` (hardware only) | +9,601 | **Yes** |
| `named_sw_VASI` | `LIGHT_NAMED VASI` (`BILLBOARD_SW`) | −785 | No |
| `named_sw_airplane_beacon` | `LIGHT_NAMED airplane_beacon` (`BILLBOARD_SW`) | +32 | No |
| `param_hw_full_custom_halo` | `LIGHT_PARAM full_custom_halo` (hardware only) | +9,738 | **Yes** |
| `param_sw_airplane_beacon_rotate` | `LIGHT_PARAM airplane_beacon_rotate` (`BILLBOARD_SW`) | −507 | No |

The non-instanced variants did load and draw. Their screenshots show the wall of boxes, and X-Plane logged no
scenery errors.

**So, in X-Plane 12.4.4, an object isn't instanced when it has:**
- any animation: rotation, translation or show/hide;
- a mid-object `ATTR_shiny_rat`. Not every attribute breaks it: `ATTR_hard` doesn't;
- a custom billboard light;
- a custom spill light with a dataref;
- a named or parameterized light that X-Plane's `lights.txt` defines with a software (`BILLBOARD_SW` or `SPILL_SW`)
  version.

This matches Laminar's guidance in [Third Party Cars Should Really Be Instanced](https://developer.x-plane.com/2016/02/third-party-cars-should-really-be-instanced/)
(2016) and [Making 3-d Modeling Less Weird](https://developer.x-plane.com/2015/12/making-3d-modeling-less-weird/)
(2015), and the `lights.txt` header in X-Plane 12.4.4 ("BILLBOARD_SW - dataref-driven billboard", "SPILL_SW -
dataref driven spill").
