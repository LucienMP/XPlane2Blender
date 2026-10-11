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
