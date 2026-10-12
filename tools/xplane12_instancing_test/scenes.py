"""Visual scenes for runner.py: up to 6 OBJs (from make_visual_objects.py), left to right as seen from the cockpit."""
SCENES = {
    # #755: parameterized light intensity with and without "cd"
    "spot_night": {"time": 1.0, "slots": ["v_spot_500cd", "v_spot_500", "v_spot_50cd", "v_spot_50", "v_spot_5", "v_spot_1"]},
    # Custom spill without a dataref: XPlane2Blender's output (no token) vs the spec's "none"
    "spill_night": {"time": 1.0, "slots": ["v_control", "v_spill_notoken", "v_spill_none"]},
    # #284: conditionals; red = condition true, blue = false (green in the ELSE IF chain = GLOBAL_LIGHTING)
    "conditionals_day": {"time": 13.0, "slots": ["v_if_VERSION10", "v_if_GLOBAL_LIGHTING", "v_if_GLOBAL_SHADOWS",
                                                  "v_if_SCENERY_SHADOWS", "v_elseif", "v_ifnot_GLOBAL_LIGHTING"]},
    # #461: specular with a normal map; #621 manipulator with a wheel (load check only)
    "specular_day": {"time": 13.0, "slots": ["v_nml_none", "v_nml_shiny05", "v_nml_global1", "v_nml_global0",
                                              "v_plain_global1", "v_manip_rotate_wheel"]},
}
# #461 again: panels angled to mirror the sun into the camera
SCENES["glint_day"] = {"time": 13.0, "slots": ["v_glint_nml_none", "v_glint_nml_global0", "v_glint_nml_global05",
                                               "v_glint_nml_global1", "v_glint_plain_none", "v_glint_plain_global1"]}
# Round 2: with an emissive anchor so the night stays dark
SCENES["spot_night2"] = {"time": 1.0, "slots": ["v_anchor_lit", "v_spot_500cd", "v_spot_500", "v_spot_5000cd", "v_spot_5", "v_spot_1"]}
SCENES["spill_night2"] = {"time": 1.0, "slots": ["v_spill25_notoken", None, "v_anchor_lit", None, None, "v_spill25_none"]}
# Round 3
SCENES["spill_night3a"] = {"time": 1.0, "slots": ["v_spillB_notoken_5", None, "v_spillB_none_5", None, "v_spillB_none_500cd", None]}
SCENES["spill_night3b"] = {"time": 1.0, "slots": ["v_spillB_notoken_15", None, "v_spillB_none_15", None, "v_spillB_none_5000cd", None]}
# Same spot lights as spot_night2, reversed, to confirm each glow follows its object
SCENES["spot_night3"] = {"time": 1.0, "slots": ["v_spot_1", "v_spot_5", "v_spot_5000cd", "v_spot_500", "v_spot_500cd", "v_anchor_lit"]}
SCENES["glint_day2"] = {"time": 13.0, "slots": ["v_facing_plain", "v_facing_nml_global1", "v_glint_plain_none", "v_glint_nml_global0", "v_glint_nml_global1", "x_xp2b_drag_rotate_wheel"]}
# Custom spill without a dataref: no token (XPlane2Blender) vs "none", alone and swapped
SCENES["spill_ab"] = {"time": 1.0, "slots": ["v_spillB_notoken_15", None, None, None, None, "v_spillB_none_15"]}
SCENES["spill_ba"] = {"time": 1.0, "slots": ["v_spillB_none_15", None, None, None, None, "v_spillB_notoken_15"]}
SCENES["spillcd_ab"] = {"time": 1.0, "slots": ["v_spillB_notoken_5000cd", None, None, None, None, "v_spillB_none_5000cd"]}
SCENES["spillcd_ba"] = {"time": 1.0, "slots": ["v_spillB_none_5000cd", None, None, None, None, "v_spillB_notoken_5000cd"]}
SCENES["spillunit_ab"] = {"time": 1.0, "slots": ["v_spillB_none_500", None, None, None, None, "v_spillB_none_500cd"]}
SCENES["spillunit_ba"] = {"time": 1.0, "slots": ["v_spillB_none_500cd", None, None, None, None, "v_spillB_none_500"]}
# XPlane2Blender's own custom spill export: old (meters) vs fixed (candela for X-Plane 12)
SCENES["xp2b_spill_ab"] = {"time": 1.0, "slots": ["x_xp2b_spill_xp11", None, None, None, None, "x_xp2b_spill_xp12"]}
SCENES["xp2b_spill_ba"] = {"time": 1.0, "slots": ["x_xp2b_spill_xp12", None, None, None, None, "x_xp2b_spill_xp11"]}
# #755 end to end: XPlane2Blender's own Automatic spot_params_bb_pm export (with "cd")
SCENES["xp2b_spot"] = {"time": 1.0, "slots": ["v_anchor_lit", None, "x_xp2b_spot_auto", None, None, "v_spot_500"]}
# Undocumented conditional variables: red = true, blue = false
SCENES["conditionals2_day"] = {"time": 13.0, "slots": ["v_if_VERSION11", "v_if_VERSION12", "v_if_VERSION13", "v_if_VERSION99", "v_if_SEASONAL", "v_if_NOT_A_REAL_VARIABLE"]}

# EXPORT_SEASON: green = spring, red = summer, blue = autumn, white = winter
_KSHN = {"latitude": 47.2310765, "longitude": -123.1565485, "heading_true": 67.87}
_NFFN = {"latitude": -17.7725672, "longitude": 177.4292681, "heading_true": 37.48}
_SEASON = {"time": 13.0, "library": "season_library.txt", "objects": ["season_spr", "season_sum", "season_fal", "season_win"]}
SCENES["season_kshn_jan"] = dict(_SEASON, day=15, start=_KSHN, tile=("dsf_season_kshn", "+40-130/+47-124.dsf"))
SCENES["season_kshn_apr"] = dict(_SEASON, day=105, start=_KSHN, tile=("dsf_season_kshn", "+40-130/+47-124.dsf"))
SCENES["season_kshn_jun"] = dict(_SEASON, day=172, start=_KSHN, tile=("dsf_season_kshn", "+40-130/+47-124.dsf"))
SCENES["season_kshn_oct"] = dict(_SEASON, day=288, start=_KSHN, tile=("dsf_season_kshn", "+40-130/+47-124.dsf"))
SCENES["season_nffn_jan"] = dict(_SEASON, day=15, start=_NFFN, tile=("dsf_season_nffn", "-20+170/-18+177.dsf"))
SCENES["season_nffn_jun"] = dict(_SEASON, day=172, start=_NFFN, tile=("dsf_season_nffn", "-20+170/-18+177.dsf"))
# Live: start in June, change to mid-January after the first screenshot
SCENES["season_kshn_live"] = dict(_SEASON, day=172, start=_KSHN, tile=("dsf_season_kshn", "+40-130/+47-124.dsf"), redate=15)

# End to end: XPlane2Blender exported the boxes and wrote library.txt (blender/export_season_library.py)
_E2E = {"time": 13.0, "start": _KSHN, "tile": ("dsf_season_kshn", "+40-130/+47-124.dsf")}
_E2E_PACK = "e2e_%s/Custom Scenery/XP2B_instancing_test"
SCENES["e2e_full_jan"] = dict(_E2E, day=15, pack=_E2E_PACK % "full")
SCENES["e2e_full_jun"] = dict(_E2E, day=172, pack=_E2E_PACK % "full")
SCENES["e2e_no_winter_jan"] = dict(_E2E, day=15, pack=_E2E_PACK % "no_winter")
SCENES["season_kshn_aug"] = dict(_SEASON, day=227, start=_KSHN, tile=("dsf_season_kshn", "+40-130/+47-124.dsf"))

# Open ocean, mirrored across the equator: does the southern hemisphere get the opposite season?
_SEAPLANE = "Aircraft/Laminar Research/Cessna 172 SP/Cessna_172SP_seaplane.acf"
_OCEAN45N = {"latitude": 45.5002698, "longitude": -150.5, "heading_true": 0.0}
_OCEAN45S = {"latitude": -45.4997302, "longitude": -150.5, "heading_true": 0.0}
for _day, _month in ((15, "jan"), (227, "aug")):
    SCENES[f"season_ocean45n_{_month}"] = dict(_SEASON, day=_day, start=_OCEAN45N, aircraft=_SEAPLANE, tile=("dsf_season_ocean45n", "+40-160/+45-151.dsf"))
    SCENES[f"season_ocean45s_{_month}"] = dict(_SEASON, day=_day, start=_OCEAN45S, aircraft=_SEAPLANE, tile=("dsf_season_ocean45s", "-50-160/-46-151.dsf"))
# Scenery shadows off (art control, reset at X-Plane's next start): the IF NOT SCENERY_SHADOWS plate shows
SCENES["e2e_full_jun_no_scenery_shadows"] = dict(_E2E, day=172, pack=_E2E_PACK % "full",
                                                 datarefs={"sim/private/controls/shadow/scenery_shadows": 0})
# The plate under IF SCENERY_SHADOWS instead: shows with scenery shadows on
SCENES["e2e_plate_if_jun"] = dict(_E2E, day=172, pack=_E2E_PACK % "plate_if")
