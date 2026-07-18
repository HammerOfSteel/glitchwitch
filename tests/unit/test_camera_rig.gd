extends GdUnitTestSuite
## Camera rig: clamps, wrapping, zoom, follow smoothing, wall collision.

const RIG_SCENE := "res://src/camera/camera_rig.tscn"
const PLAYER_SCENE := "res://src/player/player.tscn"


func _rig_under_parent() -> Array:
	var parent := Node3D.new()
	auto_free(parent)
	var rig: CameraRig = (load(RIG_SCENE) as PackedScene).instantiate()
	parent.add_child(rig)
	return [parent, rig]


func test_pitch_clamps_at_both_ends() -> void:
	var pair := _rig_under_parent()
	var runner := scene_runner(pair[0])
	var rig: CameraRig = pair[1]
	await runner.simulate_frames(2)

	rig.rotate_look(0.0, -10.0)
	assert_float(rig.pitch()).is_equal_approx(CameraRig.PITCH_MIN, 0.001)
	rig.rotate_look(0.0, 10.0)
	assert_float(rig.pitch()).is_equal_approx(CameraRig.PITCH_MAX, 0.001)


func test_yaw_wraps_to_pi_range() -> void:
	var pair := _rig_under_parent()
	var runner := scene_runner(pair[0])
	var rig: CameraRig = pair[1]
	await runner.simulate_frames(2)

	rig.rotate_look(10.0 * PI + 0.5, 0.0)
	assert_float(rig.yaw()).is_between(-PI, PI)


func test_zoom_clamps() -> void:
	var pair := _rig_under_parent()
	var runner := scene_runner(pair[0])
	var rig: CameraRig = pair[1]
	await runner.simulate_frames(2)

	for _i in range(30):
		rig.zoom_by(-CameraRig.ZOOM_STEP)
	assert_float(rig.zoom_target()).is_equal_approx(CameraRig.ZOOM_MIN, 0.001)
	for _i in range(30):
		rig.zoom_by(CameraRig.ZOOM_STEP)
	assert_float(rig.zoom_target()).is_equal_approx(CameraRig.ZOOM_MAX, 0.001)


func test_rig_follows_moved_parent() -> void:
	var pair := _rig_under_parent()
	var runner := scene_runner(pair[0])
	var parent: Node3D = pair[0]
	var rig: CameraRig = pair[1]
	await runner.simulate_frames(2)

	parent.global_position = Vector3(6, 0, -4)
	var caught_up := false
	for _i in range(60):
		await runner.simulate_frames(10)
		var anchor := parent.global_position + Vector3(0, CameraRig.ANCHOR_HEIGHT, 0)
		if rig.global_position.distance_to(anchor) < 0.2:
			caught_up = true
			break
	assert_bool(caught_up).override_failure_message("rig never caught up to anchor").is_true()


func test_spring_arm_keeps_camera_out_of_wall() -> void:
	var arena := Node3D.new()
	auto_free(arena)
	# floor
	var floor_body := StaticBody3D.new()
	var floor_shape := CollisionShape3D.new()
	var floor_box := BoxShape3D.new()
	floor_box.size = Vector3(20, 1, 20)
	floor_shape.shape = floor_box
	floor_body.add_child(floor_shape)
	floor_body.position = Vector3(0, -0.5, 0)
	arena.add_child(floor_body)
	# wall close behind the player (+Z, where the camera wants to be)
	var wall := StaticBody3D.new()
	var wall_shape := CollisionShape3D.new()
	var wall_box := BoxShape3D.new()
	wall_box.size = Vector3(10, 6, 0.4)
	wall_shape.shape = wall_box
	wall.add_child(wall_shape)
	wall.position = Vector3(0, 2, 1.5)
	arena.add_child(wall)

	var runner := scene_runner(arena)
	var player: Player = (load(PLAYER_SCENE) as PackedScene).instantiate()
	player.input_enabled = false
	player.position = Vector3(0, 0.1, 0)
	arena.add_child(player)
	await runner.simulate_frames(40)

	var rig := player.get_node("CameraRig") as CameraRig
	var camera := rig.camera()
	# wall front face is at z = 1.3; camera must stay on the player's side
	assert_float(camera.global_position.z).is_less(1.35)


func test_frame_bias_drifts_yaw_toward_target_when_idle() -> void:
	var pair := _rig_under_parent()
	var runner := scene_runner(pair[0])
	var parent: Node3D = pair[0]
	var rig: CameraRig = pair[1]
	rig.frame_bias_enabled = true
	await runner.simulate_frames(2)

	# target sits along -X from the rig -> desired yaw ≈ +90°
	var target := Node3D.new()
	target.position = Vector3(-5, 0, 0)
	parent.add_child(target)
	rig.set_bias_target(target)

	var start_error := absf(wrapf(deg_to_rad(90.0) - rig.yaw(), -PI, PI))
	# wait out the idle delay, then let bias act
	await runner.simulate_frames(90)
	var end_error := absf(wrapf(deg_to_rad(90.0) - rig.yaw(), -PI, PI))
	assert_float(end_error).is_less(start_error)
