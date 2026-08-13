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
	assert_bool(villager is StaticNpc).is_true()


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


func after_test() -> void:
	GameClock.debug_override_hour = null
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""
	DialogueRunner._voice_seed = 0


func test_demo_villager_has_talk_interactable() -> void:
	var world := preload("res://src/world/cottage_garden/cottage_garden.tscn").instantiate()
	auto_free(world)
	add_child(world)
	var villager := world.get_node("DemoVillager")
	var talk := villager.find_children("*", "Interactable", true, false)
	assert_int(talk.size()).is_equal(1)
	assert_str((talk[0] as Interactable).verb).is_equal("Talk")


func test_interacting_with_demo_villager_starts_and_can_end_dialogue() -> void:
	var world := preload("res://src/world/cottage_garden/cottage_garden.tscn").instantiate()
	auto_free(world)
	add_child(world)
	var villager := world.get_node("DemoVillager")
	var talk := villager.find_children("*", "Interactable", true, false)[0] as Interactable
	talk.interact(self)
	assert_bool(DialogueRunner.is_active()).is_true()
	# First encounter has no flags set, so greet's condition is false and it
	# routes via "else" into ask_weather's choices; pick index 1 ("Not now.",
	# next: null) to end the conversation cleanly.
	DialogueRunner.choose(1)
	assert_bool(DialogueRunner.is_active()).is_false()


## Regression test for the "single E press both ends AND restarts dialogue"
## bug: a real E keypress that resolves a line to its end (next: null) via
## DialogueRunner.advance() delivers to both DialogueBox._unhandled_input
## (which ends the conversation) and Player._unhandled_input (which
## re-triggers Interactable.interact() on the still-focused villager) within
## the SAME input dispatch, because input_enabled flips true synchronously
## off DialogueRunner.ended before the event finishes propagating.
func test_ending_dialogue_via_interact_key_does_not_immediately_restart_it() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(10)
	var garden := runner.scene()
	var player := garden.get_node("Player")
	var villager := garden.get_node("DemoVillager")

	player.global_position = villager.global_position + Vector3(0, 0, 1.0)
	player.look_at(villager.global_position + Vector3(0, player.global_position.y, 0), Vector3.UP)
	await runner.simulate_frames(5)

	# Start dialogue, then choose "Sure." (index 0) directly (not via a
	# keypress) so we land on "chat", whose next is null — the following E
	# press is the one whose own advance() call ends the conversation.
	runner.simulate_action_press("interact")
	await runner.simulate_frames(2)
	runner.simulate_action_release("interact")
	await runner.simulate_frames(2)
	DialogueRunner.choose(0)
	await runner.simulate_frames(2)
	assert_bool(DialogueRunner.is_active()).override_failure_message(
		"expected dialogue still active, showing 'chat' line"
	).is_true()

	# Player is still standing in front of (and facing) the villager, so
	# FocusResolver still has it focused. This single E press both ends the
	# conversation (chat's next is null) and, if the event isn't marked
	# handled, also reaches Player._unhandled_input in the same dispatch and
	# immediately restarts it.
	runner.simulate_action_press("interact")
	await runner.simulate_frames(2)
	runner.simulate_action_release("interact")
	await runner.simulate_frames(2)
	assert_bool(DialogueRunner.is_active()).override_failure_message(
		"a single interact keypress that ends dialogue should not also restart it"
	).is_false()
