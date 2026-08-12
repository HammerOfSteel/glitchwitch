extends GdUnitTestSuite
## TimeOfDayRig: drives a zone's Sun/Fill pair from GameClock + TimeOfDayCurve.
## See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.


func after_test() -> void:
	GameClock.debug_override_hour = null


func test_applies_curve_output_to_sun_and_fill_on_ready() -> void:
	GameClock.debug_override_hour = 12.0
	var root := Node3D.new()
	auto_free(root)
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	root.add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.name = "Fill"
	root.add_child(fill)
	var rig := Node.new()
	rig.name = "TimeOfDayRig"
	rig.set_script(load("res://src/world/time_of_day_rig.gd"))
	root.add_child(rig)

	var runner := scene_runner(root)
	await runner.simulate_frames(1)

	var expected := TimeOfDayCurve.light_state_for_hour(12.0)
	assert_vector(sun.rotation_degrees).is_equal_approx(
		expected.sun_rotation_degrees,
		Vector3(0.01, 0.01, 0.01)
	)
	assert_bool(sun.light_color.is_equal_approx(expected.sun_color)).is_true()
	assert_float(sun.light_energy).is_equal_approx(expected.sun_energy, 0.001)
	assert_bool(sun.shadow_enabled).is_equal(expected.sun_shadow_enabled)
	assert_vector(fill.rotation_degrees).is_equal_approx(
		expected.fill_rotation_degrees,
		Vector3(0.01, 0.01, 0.01)
	)
	assert_bool(fill.light_color.is_equal_approx(expected.fill_color)).is_true()
	assert_float(fill.light_energy).is_equal_approx(expected.fill_energy, 0.001)
