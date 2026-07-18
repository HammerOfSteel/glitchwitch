extends GdUnitTestSuite
## Movement math tables — the feel of the witch's walk, verified.


func test_target_speed() -> void:
	assert_float(MovementMath.target_speed(false)).is_equal_approx(2.2, 0.001)
	assert_float(MovementMath.target_speed(true)).is_equal_approx(4.2, 0.001)


func test_target_velocity_zero_input_is_zero() -> void:
	var velocity := MovementMath.target_velocity(Vector2.ZERO, false, 0.0)
	assert_vector(velocity).is_equal(Vector3.ZERO)


func test_target_velocity_forward_moves_negative_z() -> void:
	var velocity := MovementMath.target_velocity(Vector2(0, 1), false, 0.0)
	assert_float(velocity.z).is_less(0.0)
	assert_float(absf(velocity.x)).is_less(0.001)
	assert_float(velocity.length()).is_equal_approx(MovementMath.WALK_SPEED, 0.001)


func test_target_velocity_respects_camera_yaw() -> void:
	# camera turned 90° left: "forward" should move along -X
	var velocity := MovementMath.target_velocity(Vector2(0, 1), false, PI / 2.0)
	assert_float(velocity.x).is_less(-1.0)
	assert_float(absf(velocity.z)).is_less(0.001)


func test_diagonal_input_is_not_faster() -> void:
	var velocity := MovementMath.target_velocity(Vector2(1, 1), true, 0.0)
	assert_float(velocity.length()).is_less_equal(MovementMath.RUN_SPEED + 0.001)


func test_step_velocity_ramps_up_and_stops_faster() -> void:
	var target := Vector3(0, 0, -MovementMath.WALK_SPEED)
	var velocity := Vector3.ZERO
	var ramp_up_frames := 0
	while Vector2(velocity.x, velocity.z).length() < MovementMath.WALK_SPEED - 0.05:
		velocity = MovementMath.step_velocity(velocity, target, 1.0 / 60.0)
		ramp_up_frames += 1
		assert_int(ramp_up_frames).is_less(120)
	var stop_frames := 0
	while Vector2(velocity.x, velocity.z).length() > 0.05:
		velocity = MovementMath.step_velocity(velocity, Vector3.ZERO, 1.0 / 60.0)
		stop_frames += 1
		assert_int(stop_frames).is_less(120)
	assert_int(stop_frames).is_less(ramp_up_frames)


func test_apply_gravity_falls_and_sticks() -> void:
	var falling := MovementMath.apply_gravity(Vector3.ZERO, 0.5, false)
	assert_float(falling.y).is_less(-8.0)
	var grounded := MovementMath.apply_gravity(Vector3(1, -3, 0), 0.5, true)
	assert_float(grounded.y).is_equal_approx(-0.5, 0.001)
	assert_float(grounded.x).is_equal_approx(1.0, 0.001)


func test_turn_toward_converges_and_wraps() -> void:
	var yaw := 0.0
	for _i in range(120):
		yaw = MovementMath.turn_toward(yaw, PI * 0.9, 1.0 / 60.0)
	assert_float(yaw).is_equal_approx(PI * 0.9, 0.01)
	# wrap: shortest path from +170° to -170° should pass through 180°
	var wrapped := MovementMath.turn_toward(deg_to_rad(170.0), deg_to_rad(-170.0), 10.0)
	assert_float(absf(rad_to_deg(wrapped))).is_greater(165.0)


func test_facing_from_velocity_keeps_fallback_when_still() -> void:
	assert_float(MovementMath.facing_from_velocity(Vector3.ZERO, 1.23)).is_equal_approx(1.23, 0.001)


func test_motion_state_thresholds() -> void:
	assert_str(MovementMath.motion_state(Vector3.ZERO)).is_equal("idle")
	assert_str(MovementMath.motion_state(Vector3(2.0, 0, 0))).is_equal("walk")
	assert_str(MovementMath.motion_state(Vector3(0, 0, -4.0))).is_equal("run")
	# vertical speed must not affect the state
	assert_str(MovementMath.motion_state(Vector3(0, -9.0, 0))).is_equal("idle")
