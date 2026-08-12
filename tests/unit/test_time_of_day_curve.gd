extends GdUnitTestSuite
## TimeOfDayCurve: pure hour -> lighting-state interpolation. No scene tree
## needed. See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

const EPS := 0.001


func test_noon_matches_todays_hardcoded_zone_values() -> void:
	var state := TimeOfDayCurve.light_state_for_hour(12.0)
	assert_vector(state.sun_rotation_degrees).is_equal_approx(Vector3(-48.0, -32.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.sun_color.is_equal_approx(Color(1.0, 0.93, 0.82))).is_true()
	assert_float(state.sun_energy).is_equal_approx(1.25, EPS)
	assert_bool(state.sun_shadow_enabled).is_true()
	assert_vector(state.fill_rotation_degrees).is_equal_approx(Vector3(-20.0, 141.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.fill_color.is_equal_approx(Color(0.68, 0.78, 0.92))).is_true()
	assert_float(state.fill_energy).is_equal_approx(0.35, EPS)


func test_midnight_matches_night_keyframe_exactly() -> void:
	var state := TimeOfDayCurve.light_state_for_hour(0.0)
	assert_vector(state.sun_rotation_degrees).is_equal_approx(Vector3(-70.0, -32.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.sun_color.is_equal_approx(Color(0.55, 0.62, 0.85))).is_true()
	assert_float(state.sun_energy).is_equal_approx(0.15, EPS)
	assert_bool(state.sun_shadow_enabled).is_false()


func test_midpoint_between_dawn_and_day_is_arithmetic_mean() -> void:
	# 9.0 is exactly halfway between the 6:00 dawn and 12:00 day keyframes.
	var state := TimeOfDayCurve.light_state_for_hour(9.0)
	# sun_energy: (0.7 + 1.25) / 2 = 0.975
	assert_float(state.sun_energy).is_equal_approx(0.975, EPS)
	# sun_color.r: (1.0 + 1.0) / 2 = 1.0, .g: (0.78 + 0.93) / 2 = 0.855
	assert_float(state.sun_color.g).is_equal_approx(0.855, EPS)


func test_midnight_wraparound_interpolates_dusk_toward_night() -> void:
	# 22.0 is between the 19:00 dusk keyframe and the 24:00-wrapped 0:00
	# night keyframe: t = (22.0 - 19.0) / (24.0 - 19.0) = 0.6.
	var state := TimeOfDayCurve.light_state_for_hour(22.0)
	assert_vector(state.sun_rotation_degrees).is_equal_approx(Vector3(-50.0, -32.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.sun_color.is_equal_approx(Color(0.73, 0.632, 0.69))).is_true()
	assert_float(state.sun_energy).is_equal_approx(0.29, EPS)
	# t = 0.6 >= 0.5, so shadow flag takes the night keyframe's false, not dusk's true.
	assert_bool(state.sun_shadow_enabled).is_false()
	assert_vector(state.fill_rotation_degrees).is_equal_approx(Vector3(-20.0, 141.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.fill_color.is_equal_approx(Color(0.46, 0.508, 0.72))).is_true()
	assert_float(state.fill_energy).is_equal_approx(0.14, EPS)


func test_shadow_flag_takes_nearer_keyframe_before_boundary() -> void:
	# 20.4 is between 19:00 dusk and 24:00-wrapped night: t = (20.4 - 19.0) / 5.0 = 0.28 < 0.5.
	var state := TimeOfDayCurve.light_state_for_hour(20.4)
	assert_bool(state.sun_shadow_enabled).is_true()
