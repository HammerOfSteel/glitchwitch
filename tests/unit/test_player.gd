extends GdUnitTestSuite
## Player controller physics: code-built arena, simulated frames.
##
## Headless physics ticks follow the wall clock, so assertions are
## time-robust: velocity/state checks after ramp-up, and
## simulate-until-condition loops with hard frame caps for distances.

const PLAYER_SCENE := "res://src/player/player.tscn"
const MAX_FRAMES := 900


func after_test() -> void:
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""
	DialogueRunner._voice_seed = 0


func _build_arena(floor_rotation_deg: float = 0.0) -> Node3D:
	var arena := Node3D.new()
	var floor_body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(40, 1, 40)
	shape.shape = box
	floor_body.add_child(shape)
	floor_body.position = Vector3(0, -0.5, 0)
	floor_body.rotation.x = deg_to_rad(floor_rotation_deg)
	arena.add_child(floor_body)
	return arena


func _spawn_player(arena: Node3D) -> Player:
	var player: Player = (load(PLAYER_SCENE) as PackedScene).instantiate()
	player.input_enabled = false
	player.position = Vector3(0, 0.1, 0)
	arena.add_child(player)
	return player


func _simulate_until(runner: GdUnitSceneRunner, predicate: Callable) -> bool:
	var frames := 0
	while frames < MAX_FRAMES:
		await runner.simulate_frames(15)
		frames += 15
		if predicate.call():
			return true
	return false


func test_player_walks_forward() -> void:
	var arena: Node3D = auto_free(_build_arena())
	var runner := scene_runner(arena)
	var player := _spawn_player(arena)
	await runner.simulate_frames(10)

	player.set_move_intent(Vector2(0, 1), false)
	var reached: bool = await _simulate_until(
		runner, func() -> bool: return player.position.z < -0.8
	)

	assert_bool(reached).override_failure_message("player never walked 0.8m").is_true()
	assert_float(absf(player.position.x)).is_less(0.15)
	var planar_speed := Vector2(player.velocity.x, player.velocity.z).length()
	assert_float(planar_speed).is_equal_approx(MovementMath.WALK_SPEED, 0.25)


func test_player_run_reaches_run_speed_and_state() -> void:
	var arena: Node3D = auto_free(_build_arena())
	var runner := scene_runner(arena)
	var player := _spawn_player(arena)
	await runner.simulate_frames(10)

	player.set_move_intent(Vector2(0, 1), true)
	var reached: bool = await _simulate_until(
		runner, func() -> bool: return Vector2(player.velocity.x, player.velocity.z).length() > 3.9
	)

	assert_bool(reached).override_failure_message("player never reached run speed").is_true()
	assert_str(player.get_motion_state()).is_equal("run")


func test_player_stops_when_intent_clears() -> void:
	var arena: Node3D = auto_free(_build_arena())
	var runner := scene_runner(arena)
	var player := _spawn_player(arena)
	await runner.simulate_frames(10)

	player.set_move_intent(Vector2(0, 1), false)
	await _simulate_until(
		runner, func() -> bool: return Vector2(player.velocity.x, player.velocity.z).length() > 2.0
	)
	player.set_move_intent(Vector2.ZERO)
	var stopped: bool = await _simulate_until(
		runner, func() -> bool: return player.get_motion_state() == &"idle"
	)

	assert_bool(stopped).override_failure_message("player never came to rest").is_true()
	var planar_speed := Vector2(player.velocity.x, player.velocity.z).length()
	assert_float(planar_speed).is_less(0.25)


func test_player_traverses_gentle_slope() -> void:
	var arena: Node3D = auto_free(_build_arena(10.0))
	var runner := scene_runner(arena)
	var player := _spawn_player(arena)
	player.position = Vector3(0, 1.0, 0)
	await runner.simulate_frames(20)

	player.set_move_intent(Vector2(0, 1), false)
	var reached: bool = await _simulate_until(
		runner, func() -> bool: return player.position.z < -0.5
	)

	assert_bool(reached).override_failure_message("player stuck on 10° slope").is_true()
	assert_bool(player.is_on_floor()).is_true()


func test_step_signal_fires_while_walking() -> void:
	var arena: Node3D = auto_free(_build_arena())
	var runner := scene_runner(arena)
	var player := _spawn_player(arena)
	await runner.simulate_frames(10)

	var steps: Array = []
	player.stepped.connect(func() -> void: steps.append(true))
	player.set_move_intent(Vector2(0, 1), false)
	var enough: bool = await _simulate_until(runner, func() -> bool: return steps.size() >= 2)

	assert_bool(enough).override_failure_message("fewer than 2 steps emitted").is_true()


func test_motion_changed_signal_sequence() -> void:
	var arena: Node3D = auto_free(_build_arena())
	var runner := scene_runner(arena)
	var player := _spawn_player(arena)
	await runner.simulate_frames(10)

	var states: Array = []
	player.motion_changed.connect(func(state: StringName) -> void: states.append(state))
	player.set_move_intent(Vector2(0, 1), true)
	await _simulate_until(runner, func() -> bool: return states.has(&"run"))
	player.set_move_intent(Vector2.ZERO)
	var settled: bool = await _simulate_until(
		runner, func() -> bool: return not states.is_empty() and states.back() == &"idle"
	)

	assert_array(states).contains([&"run"])
	assert_bool(settled).override_failure_message("never settled back to idle").is_true()


func test_avatar_mount_faces_motion() -> void:
	var arena: Node3D = auto_free(_build_arena())
	var runner := scene_runner(arena)
	var player := _spawn_player(arena)
	await runner.simulate_frames(10)

	player.set_move_intent(Vector2(1, 0), false)  # strafe right -> +X
	var faced: bool = await _simulate_until(
		runner, func() -> bool: return absf(rad_to_deg(player.facing_yaw()) + 90.0) < 8.0
	)

	(
		assert_bool(faced)
		. override_failure_message(
			"avatar yaw %.1f° never faced -90°" % rad_to_deg(player.facing_yaw())
		)
		. is_true()
	)


func test_dialogue_line_shown_force_hides_interact_prompt_even_if_already_visible() -> void:
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	auto_free(player)
	add_child(player)
	var prompt := player.get_node("%InteractPrompt") as InteractPrompt
	var item := Interactable.new()
	auto_free(item)
	prompt.on_focus_changed(item)  # simulate focus already held
	assert_bool(prompt.visible).is_true()
	DialogueRunner.line_shown.emit("Villager", "Hi.")
	assert_bool(prompt.visible).is_false()


func test_dialogue_choices_shown_force_hides_interact_prompt_with_real_focus() -> void:
	# Uses the real test_interact.gd-style focus-simulation pattern (not a
	# faked on_focus_changed() call) so the prompt is genuinely visible via
	# FocusResolver before we assert force_hide() reacts to choices_shown —
	# this is the actual path the first demo conversation takes on first
	# encounter (condition-false -> else -> choices_shown immediately).
	var arena := Node3D.new()
	auto_free(arena)
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	player.input_enabled = false
	arena.add_child(player)
	var item := Interactable.new()
	item.position = Vector3(0, 1, -1.5)  # in front of player, within reach
	arena.add_child(item)
	var runner := scene_runner(arena)
	await runner.simulate_frames(15)  # let FocusResolver's real evaluate() focus `item`
	var resolver := player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(item)  # sanity-check the real focus state
	var prompt := player.get_node("%InteractPrompt") as InteractPrompt
	assert_bool(prompt.visible).is_true()
	DialogueRunner.choices_shown.emit("Villager", "Nice day?", ["Sure is.", "Not really."])
	assert_bool(prompt.visible).is_false()


func test_dialogue_ended_reshows_prompt_via_current_focus() -> void:
	var arena := Node3D.new()
	auto_free(arena)
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	player.input_enabled = false
	arena.add_child(player)
	var item := Interactable.new()
	item.position = Vector3(0, 1, -1.5)  # in front of player, within reach
	arena.add_child(item)
	var runner := scene_runner(arena)
	await runner.simulate_frames(15)  # let FocusResolver's real evaluate() focus `item`
	var resolver := player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(item)  # sanity-check the real focus state
	var prompt := player.get_node("%InteractPrompt") as InteractPrompt
	prompt.force_hide()
	DialogueRunner.ended.emit()
	assert_bool(prompt.visible).is_true()


func test_dialogue_ended_reenables_player_input() -> void:
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	auto_free(player)
	add_child(player)
	player.input_enabled = false
	DialogueRunner.ended.emit()
	assert_bool(player.input_enabled).is_true()
