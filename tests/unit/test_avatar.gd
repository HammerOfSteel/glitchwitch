extends GdUnitTestSuite
## Wren's avatar: import contract, loop modes, state driving, gestures,
## and full player integration.

const PLAYER_SCENE := "res://src/player/player.tscn"
const MAX_FRAMES := 1200


func _spawn_avatar() -> Array:
	var root := Node3D.new()
	auto_free(root)
	var avatar := WrenAvatar.new()
	root.add_child(avatar)
	return [root, avatar]


func test_wren_glb_exists_with_expected_clips() -> void:
	assert_bool(ResourceLoader.exists(WrenAvatar.WREN_SCENE_PATH)) \
		.override_failure_message("missing wren.glb (run make assets)").is_true()

	var pair := _spawn_avatar()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var avatar := pair[1] as WrenAvatar
	var anim := avatar.animation_player()
	assert_object(anim).is_not_null()

	var clips := anim.get_animation_list()
	for expected in ["idle", "walk", "run", "wave", "stir"]:
		assert_bool(expected in clips) \
			.override_failure_message("missing clip: %s in %s" % [expected, clips]).is_true()


func test_loop_modes_follow_suffix_convention() -> void:
	var pair := _spawn_avatar()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var anim := (pair[1] as WrenAvatar).animation_player()

	for looping in ["idle", "walk", "run", "stir"]:
		assert_int(anim.get_animation(looping).loop_mode) \
			.override_failure_message("%s should loop" % looping) \
			.is_equal(Animation.LOOP_LINEAR)
	assert_int(anim.get_animation("wave").loop_mode).is_equal(Animation.LOOP_NONE)


func test_motion_state_drives_clips_with_idle_fallback() -> void:
	var pair := _spawn_avatar()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var avatar := pair[1] as WrenAvatar

	assert_str(avatar.current_clip()).is_equal("idle")
	avatar.set_motion_state(&"walk")
	assert_str(avatar.current_clip()).is_equal("walk")
	avatar.set_motion_state(&"run")
	assert_str(avatar.current_clip()).is_equal("run")
	avatar.set_motion_state(&"somersault")
	assert_str(avatar.current_clip()).is_equal("idle")


func test_wave_gesture_plays_and_returns_to_motion() -> void:
	var pair := _spawn_avatar()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var avatar := pair[1] as WrenAvatar

	avatar.set_motion_state(&"walk")
	avatar.play_gesture(&"wave")
	assert_str(avatar.current_clip()).is_equal("wave")
	assert_bool(avatar.is_gesturing()).is_true()

	var returned := false
	var frames := 0
	while frames < MAX_FRAMES:
		await runner.simulate_frames(15)
		frames += 15
		if avatar.current_clip() == "walk" and not avatar.is_gesturing():
			returned = true
			break
	assert_bool(returned).override_failure_message("wave never returned to walk").is_true()


func test_stir_gesture_holds_until_stopped() -> void:
	var pair := _spawn_avatar()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)
	var avatar := pair[1] as WrenAvatar

	avatar.play_gesture(&"stir")
	await runner.simulate_frames(30)
	assert_str(avatar.current_clip()).is_equal("stir")
	assert_bool(avatar.is_gesturing()).is_true()

	avatar.stop_gesture()
	assert_str(avatar.current_clip()).is_equal("idle")


func test_avatar_meshes_wear_the_palette() -> void:
	var pair := _spawn_avatar()
	var runner := scene_runner(pair[0])
	await runner.simulate_frames(3)

	var meshes := (pair[1] as WrenAvatar).find_children("*", "MeshInstance3D", true, false)
	assert_int(meshes.size()).is_greater_equal(8)
	for found in meshes:
		var mesh_instance := found as MeshInstance3D
		assert_object(mesh_instance.material_override) \
			.override_failure_message("bare mesh: %s" % mesh_instance.name).is_not_null()


func test_player_movement_drives_avatar_clip() -> void:
	var arena := Node3D.new()
	auto_free(arena)
	var floor_body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(40, 1, 40)
	shape.shape = box
	floor_body.add_child(shape)
	floor_body.position = Vector3(0, -0.5, 0)
	arena.add_child(floor_body)

	var runner := scene_runner(arena)
	var player: Player = (load(PLAYER_SCENE) as PackedScene).instantiate()
	player.input_enabled = false
	player.position = Vector3(0, 0.1, 0)
	arena.add_child(player)
	await runner.simulate_frames(10)

	var avatar := player.get_node("%Avatar") as WrenAvatar
	assert_str(avatar.current_clip()).is_equal("idle")

	player.set_move_intent(Vector2(0, 1), true)
	var running := false
	var frames := 0
	while frames < MAX_FRAMES:
		await runner.simulate_frames(15)
		frames += 15
		if avatar.current_clip() == "run":
			running = true
			break
	assert_bool(running).override_failure_message("avatar never entered run clip").is_true()

	player.set_move_intent(Vector2.ZERO)
	var idled := false
	frames = 0
	while frames < MAX_FRAMES:
		await runner.simulate_frames(15)
		frames += 15
		if avatar.current_clip() == "idle":
			idled = true
			break
	assert_bool(idled).override_failure_message("avatar never returned to idle").is_true()
