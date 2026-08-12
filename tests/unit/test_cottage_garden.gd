extends GdUnitTestSuite
## Cottage garden smoke: the zone assembles with a player and at least one
## discrete prop and one scatter patch from the ZoneBuilder.

const COTTAGE_GARDEN_SCENE := "res://src/world/cottage_garden/cottage_garden.tscn"


func test_cottage_garden_assembles_with_player_and_props() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(10)
	var garden := runner.scene()

	assert_object(garden.get_node_or_null("Player")).is_not_null()

	var builder := garden.get_node("%ZoneBuilder") as ZoneBuilder
	assert_object(builder).is_not_null()

	var has_discrete_prop := false
	var has_scatter := false
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			has_scatter = true
		elif child is MeshInstance3D or child is Node3D:
			has_discrete_prop = true
	assert_bool(has_discrete_prop).override_failure_message(
		"expected at least one discrete PropPlacement instanced under %ZoneBuilder"
	).is_true()
	assert_bool(has_scatter).override_failure_message(
		"expected at least one scatter region in cottage_garden.tres"
	).is_true()


func test_cottage_garden_has_demo_villager() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(10)
	var garden := runner.scene()
	var villager := garden.get_node_or_null("DemoVillager")
	assert_object(villager).override_failure_message(
		"expected a DemoVillager node in cottage_garden.tscn"
	).is_not_null()
	assert_bool(villager is VillagerInstance).is_true()


func test_cottage_garden_has_time_of_day_rig_driving_sun_and_fill() -> void:
	GameClock.debug_override_hour = 12.0
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(2)
	var garden := runner.scene()

	var rig := garden.get_node_or_null("TimeOfDayRig")
	assert_object(rig).override_failure_message(
		"expected a TimeOfDayRig node in cottage_garden.tscn"
	).is_not_null()

	var expected := TimeOfDayCurve.light_state_for_hour(12.0)
	var sun := garden.get_node("Sun") as DirectionalLight3D
	var fill := garden.get_node("Fill") as DirectionalLight3D
	assert_vector(sun.rotation_degrees).is_equal_approx(expected.sun_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(sun.light_color.is_equal_approx(expected.sun_color)).is_true()
	assert_float(sun.light_energy).is_equal_approx(expected.sun_energy, 0.001)
	assert_bool(sun.shadow_enabled).is_equal(expected.sun_shadow_enabled)
	assert_vector(fill.rotation_degrees).is_equal_approx(expected.fill_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(fill.light_color.is_equal_approx(expected.fill_color)).is_true()
	assert_float(fill.light_energy).is_equal_approx(expected.fill_energy, 0.001)

	GameClock.debug_override_hour = null
