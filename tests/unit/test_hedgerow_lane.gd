extends GdUnitTestSuite
## Hedgerow lane smoke: the zone assembles with a player and exactly the
## 16 PropPlacements described in hedgerow_lane.tres (no scatter regions).

const HEDGEROW_LANE_SCENE := "res://src/world/hedgerow_lane/hedgerow_lane.tscn"


func after_test() -> void:
	GameClock.debug_override_hour = null


func test_hedgerow_lane_assembles_with_player_and_props() -> void:
	var runner := scene_runner(HEDGEROW_LANE_SCENE)
	await runner.simulate_frames(10)
	var lane := runner.scene()

	assert_object(lane.get_node_or_null("Player")).is_not_null()

	var builder := lane.get_node("%ZoneBuilder") as ZoneBuilder
	assert_object(builder).is_not_null()

	var prop_count := 0
	for child in builder.get_children():
		if child is Node3D:
			prop_count += 1
	assert_int(prop_count).override_failure_message(
		"expected all 16 PropPlacements from hedgerow_lane.tres to be instanced under %ZoneBuilder"
	).is_equal(16)


func test_hedgerow_lane_has_time_of_day_rig_driving_sun_and_fill() -> void:
	GameClock.debug_override_hour = 12.0
	var runner := scene_runner(HEDGEROW_LANE_SCENE)
	await runner.simulate_frames(2)
	var lane := runner.scene()

	var rig := lane.get_node_or_null("TimeOfDayRig")
	assert_object(rig).override_failure_message(
		"expected a TimeOfDayRig node in hedgerow_lane.tscn"
	).is_not_null()

	var expected := TimeOfDayCurve.light_state_for_hour(12.0)
	var sun := lane.get_node("Sun") as DirectionalLight3D
	var fill := lane.get_node("Fill") as DirectionalLight3D
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
