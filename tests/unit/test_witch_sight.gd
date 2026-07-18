extends GdUnitTestSuite
## Camera modes and Witch Sight: the transition matrix, cull-mask discipline,
## overlay visibility, and avatar hiding in first person.

const PLAYER_SCENE := "res://src/player/player.tscn"


func _spawn() -> Array:
	var arena := Node3D.new()
	auto_free(arena)
	var player: Player = (load(PLAYER_SCENE) as PackedScene).instantiate()
	player.input_enabled = false
	arena.add_child(player)
	return [arena, player]


func test_defaults_hide_seam_layer_and_overlay() -> void:
	var pair := _spawn()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var rig := (pair[1] as Player).get_node("CameraRig") as CameraRig

	assert_int(int(rig.camera().cull_mask) & CameraRig.SEAM_LAYER_BIT).is_equal(0)
	assert_bool(rig.sight_enabled()).is_false()
	assert_int(rig.mode()).is_equal(CameraRig.Mode.THIRD)


func test_sight_toggle_flips_mask_overlay_and_signal() -> void:
	var pair := _spawn()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var rig := (pair[1] as Player).get_node("CameraRig") as CameraRig
	var overlay := rig.get_node("%SightOverlay") as CanvasLayer

	var events: Array = []
	rig.sight_changed.connect(func(enabled: bool) -> void: events.append(enabled))

	rig.toggle_sight()
	assert_int(int(rig.camera().cull_mask) & CameraRig.SEAM_LAYER_BIT).is_equal(
		CameraRig.SEAM_LAYER_BIT
	)
	assert_bool(overlay.visible).is_true()

	rig.toggle_sight()
	assert_int(int(rig.camera().cull_mask) & CameraRig.SEAM_LAYER_BIT).is_equal(0)
	assert_bool(overlay.visible).is_false()
	assert_array(events).is_equal([true, false])


func test_first_person_instant_switch_and_back() -> void:
	var pair := _spawn()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var rig := (pair[1] as Player).get_node("CameraRig") as CameraRig

	rig.set_mode(CameraRig.Mode.FIRST, true)
	assert_float(rig.camera().fov).is_equal_approx(CameraRig.FOV_FIRST, 0.1)
	await runner.simulate_frames(30)
	var arm := rig.get_node("%SpringArm") as SpringArm3D
	assert_float(arm.spring_length).is_less(0.15)

	rig.set_mode(CameraRig.Mode.THIRD, true)
	assert_float(rig.camera().fov).is_equal_approx(CameraRig.FOV_THIRD, 0.1)
	await runner.simulate_frames(40)
	assert_float(arm.spring_length).is_greater(1.0)


func test_tweened_transition_reaches_target_fov() -> void:
	var pair := _spawn()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var rig := (pair[1] as Player).get_node("CameraRig") as CameraRig

	rig.set_mode(CameraRig.Mode.FIRST, false)
	var reached := false
	for _i in range(40):
		await runner.simulate_frames(5)
		if absf(rig.camera().fov - CameraRig.FOV_FIRST) < 0.5:
			reached = true
			break
	assert_bool(reached).override_failure_message("fov never tweened to first person").is_true()


func test_avatar_hidden_in_first_person_only() -> void:
	var pair := _spawn()
	var runner := scene_runner(pair[0])
	var player := pair[1] as Player
	await runner.simulate_frames(3)
	var rig := player.get_node("CameraRig") as CameraRig
	var mount := player.get_node("%AvatarMount") as Node3D

	assert_bool(mount.visible).is_true()
	rig.set_mode(CameraRig.Mode.FIRST, true)
	assert_bool(mount.visible).is_false()
	rig.set_mode(CameraRig.Mode.THIRD, true)
	assert_bool(mount.visible).is_true()


func test_sight_persists_across_mode_switches() -> void:
	var pair := _spawn()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var rig := (pair[1] as Player).get_node("CameraRig") as CameraRig

	rig.set_sight(true)
	rig.set_mode(CameraRig.Mode.FIRST, true)
	assert_bool(rig.sight_enabled()).is_true()
	assert_int(int(rig.camera().cull_mask) & CameraRig.SEAM_LAYER_BIT).is_equal(
		CameraRig.SEAM_LAYER_BIT
	)
	rig.set_mode(CameraRig.Mode.THIRD, true)
	assert_bool(rig.sight_enabled()).is_true()
