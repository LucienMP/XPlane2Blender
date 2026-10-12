# X-Plane 12 tests

Checks OBJ behaviour in X-Plane itself. It started as the instancing test: which OBJ features stop an object from being **hardware instanced**. XPlane2Blender's
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
  (`POST /api/v3/flight`, the same way FSSR's `xpweb.py` does). It then collects the results. X-Plane sometimes stops
  at a quit confirmation dialog, so the runner force-closes it 60 s after the plugin asked it to quit.
- **Visual scenes** (`scene:<name>` from `scenes.py`) place up to 6 objects side by side 30 m in front of the
  camera, so variants are compared in one screenshot under the same light. `make_visual_objects.py` writes them;
  the `x_xp2b_*` objects are XPlane2Blender's own exports, made with the scripts in `blender/` (or, for the Drag
  Rotate one, `tests/object/drag_rotate_mouse_wheel.test.py`). The plugin waits 20 s before the screenshot, for
  auto-exposure to settle.
- **Season scenes** (`season_*`, `e2e_*`) replace the pack's tile and `library.txt`, and can set the date, start
  position, aircraft, a mid-flight date change (`redate`: two more screenshots, 30 s and 90 s later) and art controls
  (`datarefs`: set once the scenery has loaded, then the scenery is reloaded; X-Plane resets them at its next start).
  `make_season_test.py` writes four coloured boxes published by season (spring green, summer red, autumn blue,
  winter white) and DSFs that place them. `blender/export_season_library.py` makes the `e2e_*` packs: XPlane2Blender
  exports the boxes into `e2e_<variant>/Custom Scenery/XP2B_instancing_test/` and writes their `library.txt`.

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
python make_visual_objects.py objects
python gen_dsf.py C:\path\to\xptools\tools\DSFTool.exe
python make_season_test.py C:\path\to\xptools\tools\DSFTool.exe
blender -b --factory-startup --addons io_xplane2blender --python blender\export_season_library.py -- "e2e_full\Custom Scenery\XP2B_instancing_test"
python runner.py install        # backs up scenery_packs.ini, preferences and Log.txt first
python runner.py run none control anim light_custom named_sw_VASI ...
python runner.py run scene:spot_night2 scene:conditionals_day ...
python runner.py run scene:season_kshn_jan scene:e2e_full_jan ...
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

## Visual results: X-Plane 12.4.4, 12 October 2026

Night scenes at 01:00, day scenes at 13:00 on 21 June. Brightness was measured from the screenshots, and each comparison
was repeated with the objects in swapped positions.

| Question | What was compared | Result |
|---|---|---|
| [#755](https://github.com/X-Plane/XPlane2Blender/issues/755): is `500cd` ignored in `LIGHT_PARAM spot_params_bb_pm`? | `500cd`, `5000cd`, `50cd` vs bare `500`, `50`, `5`, `1`; and XPlane2Blender's own Automatic light export | **No.** `cd` values light, and brighter for higher values; XPlane2Blender's export (`5000cd`) lights. Bare numbers are on a different scale: `1` and `5` light, `50` and `500` give nothing. Writing bare numbers, as the issue suggests, would make typical lights invisible. |
| Custom spill without a dataref: no token (XPlane2Blender) vs `none` (spec) | Same light, swapped positions | **Identical.** X-Plane accepts the missing token. |
| Custom spill size: bare meters (XPlane2Blender before the fix) vs candela | Bare `5`, `15`, `25`, `500` vs `500cd`, `5000cd`; and XPlane2Blender's export before and after the fix | **Bare sizes give little or no light:** `5` faint, `15`-`25` almost none, `500` none. `500cd`/`5000cd` light strongly. XPlane2Blender's old export (`67.58`, `40`) left the ground dark; the fixed export (`5000cd`) lit it. |
| [#284](https://github.com/X-Plane/XPlane2Blender/issues/284): conditionals | `IF`/`IF NOT`/`ELSE`/`ELSE IF`/`ENDIF` with `VERSION10`, `GLOBAL_LIGHTING`, `GLOBAL_SHADOWS`, `SCENERY_SHADOWS` | **All supported.** `ELSE` and `ELSE IF` work. `VERSION10` and `GLOBAL_LIGHTING` were true (X-Plane 12 has no non-HDR mode). The two shadow variables were true with the shadow settings used; their false case wasn't tested. |
| [#461](https://github.com/X-Plane/XPlane2Blender/issues/461): `GLOBAL_specular` with a normal map | Panels angled to reflect the sky: no normal map; normal map with `GLOBAL_specular` 0, 1.0 | **Small effect.** Adding a normal map made the surface clearly more reflective (red channel 11 → 42); `GLOBAL_specular` 0 → 1.0 changed it a little (42 → 47.5). |
| [#621](https://github.com/X-Plane/XPlane2Blender/issues/621): `ATTR_manip_wheel` after `ATTR_manip_drag_rotate` | A hand-written OBJ and XPlane2Blender's export | **Loads without errors.** The wheel itself needs someone to scroll in the cockpit; that wasn't tested. |

## Season and library.txt results, 12 October 2026

The first four Shelton runs used X-Plane 12.4.4. The rest ran on 12.4.3, after the X-Plane installer replaced the
beta. All at 13:00 local time.

| Scene | Where, when | Result |
|---|---|---|
| `season_kshn_jan` / `_apr` / `_jun` / `_aug` / `_oct` | Shelton, WA (47°N): 15 Jan, 15 Apr, 21 Jun, 15 Aug, 15 Oct | Winter, spring, **spring**, summer, autumn. The season isn't the calendar season: 21 June was still spring. |
| `season_nffn_jan` / `_jun` | Nadi, Fiji (17.8°S): 15 Jan, 21 Jun | Spring both times: no seasons in the tropics. |
| `season_kshn_live` | Shelton, 21 Jun, then the date set to 15 Jan | Spring before, and still spring 30 s and 90 s after the change: the season is picked when the scenery loads. |
| `season_ocean45n_*` / `season_ocean45s_*` | Open ocean at 45°N and 45°S, seaplane | **No result:** X-Plane loads the DSF but draws no objects on open ocean. (A Vanuatu attempt also stopped at X-Plane's "Missing Scenery" dialog: its neighbouring tiles weren't installed.) The Hobart and Moorabbin runs below answered the question once Australia was installed. |
| `season_ymhb_jan` / `_feb` / `_apr` / `_jun` / `_aug` / `_oct` | Hobart, Tasmania (42.8°S): 15 Jan, 15 Feb, 15 Apr, 21 Jun, 15 Aug, 15 Oct. X-Plane 12.4.4, after Australia was installed | Summer, summer, **summer**, winter, winter, spring. **The southern hemisphere gets the opposite seasons.** 15 April was still summer, while the mirror date at Shelton (15 October) was autumn, so the local climate matters too. |
| `season_ymmb_feb` / `_aug` | Moorabbin, Melbourne (38.0°S): 15 Feb, 15 Aug | Summer, winter: the same reversal at a second site. |
| `e2e_full_jan` / `_jun` | XPlane2Blender's own seasonal export and `library.txt` | The winter OBJ in January, the spring/summer OBJ in June. No log errors. |
| `e2e_no_winter_jan` | The same, with winter left out of `library.txt` (the export warns) | Nothing is drawn in January. |
| `e2e_full_jun`, `e2e_plate_if_jun` | A plate under `IF NOT SCENERY_SHADOWS`, then under `IF SCENERY_SHADOWS`, with shadows on | Hidden, then shown: XPlane2Blender's `SCENERY_SHADOWS` conditions load and work. |
| `e2e_full_jun_no_scenery_shadows` | Art control `shadow/scenery_shadows` set to 0, scenery reloaded | Shadows went off, but the `IF NOT` plate stayed hidden. Inconclusive: the condition may follow the graphics setting rather than this control, or the reload may have kept the cached OBJ. |

## Checks of the later 5.0 fixes: X-Plane 12.4.3, 12 October 2026

`blender/export_fixes_checks.py` makes the `x_` objects with XPlane2Blender; `make_visual_objects.py` makes the
hand-written `v_` ones. Scenes `fixes_lod`, `fixes_bone_opt` and `fixes_shiny`, 13:00 on 21 June at Shelton.

| Check | What was compared | Result |
|---|---|---|
| [#730](https://github.com/X-Plane/XPlane2Blender/issues/730): objects in no LOD | XPlane2Blender exports of a box nobody assigned to an LOD: selective LODs with "All Distances" and "Not Exported", additive LODs with "All Distances" | Drawn, missing (the original bug), drawn. |
| Do additive LODs all draw? | A half-transparent box listed in both of two additive LODs (0–1000, 0–5000) vs only the far one | About 0.62 vs 0.34 opaque against the same sky, matching drawing twice (1 − 0.66² ≈ 0.56). So "All Distances" uses only the farthest additive LOD. |
| [#643](https://github.com/X-Plane/XPlane2Blender/issues/643): Show/Hide on a bone | A box under an armature bone with `ANIM_hide` by `sim/time/local_date_days` 100–200 (day 172), and 0–50 | Hidden, and shown. |
| [#709](https://github.com/X-Plane/XPlane2Blender/issues/709): shared vertices | Two identical animated boxes, Optimize on (24 vertices) vs off (72) | Both draw the two rotated boxes alike (blue area within 3%; the slots see the runway from slightly different angles). No log errors. |
| [#439](https://github.com/X-Plane/XPlane2Blender/issues/439): is `ATTR_shiny_rat 0` the default? | Normal-mapped glint panels with no `ATTR_shiny_rat`, `0`, `0.5`, `1` | No line and `0`: identical, RGB (39.8, 115.3, 233.0). `0.5`: (153.9, 171.6, 236.0); `1`: (91.2, 137.7, 234.2). |
