class_name MovementMath
extends RefCounted
## Pure movement math for the witch's cozy locomotion.
##
## Everything here is static and deterministic so the feel of the game
## can be tuned and tested without touching physics.

const WALK_SPEED := 2.2
const RUN_SPEED := 4.2
const ACCELERATION := 10.0
const DECELERATION := 14.0
const TURN_LERP := 10.0
const GRAVITY := 18.0
const IDLE_THRESHOLD := 0.2
const RUN_THRESHOLD := 3.2


static func target_speed(running: bool) -> float:
	return RUN_SPEED if running else WALK_SPEED


static func target_velocity(input_vec: Vector2, running: bool, camera_yaw: float) -> Vector3:
	## Camera-relative planar velocity target. input_vec: x = strafe, y = forward.
	if input_vec.length_squared() < 0.0001:
		return Vector3.ZERO
	var clamped := input_vec.limit_length(1.0)
	var direction := Vector3(clamped.x, 0.0, -clamped.y).rotated(Vector3.UP, camera_yaw)
	return direction * target_speed(running)


static func step_velocity(current: Vector3, target: Vector3, delta: float) -> Vector3:
	## Accelerate toward the target, decelerate faster than we speed up —
	## responsive stops feel kind; slow starts feel cozy.
	var planar_current := Vector3(current.x, 0.0, current.z)
	var rate := (
		ACCELERATION if target.length_squared() > planar_current.length_squared() else DECELERATION
	)
	var stepped := planar_current.move_toward(target, rate * delta)
	return Vector3(stepped.x, current.y, stepped.z)


static func apply_gravity(velocity: Vector3, delta: float, on_floor: bool) -> Vector3:
	if on_floor and velocity.y <= 0.0:
		return Vector3(velocity.x, -0.5, velocity.z)  # gentle floor stick
	return Vector3(velocity.x, velocity.y - GRAVITY * delta, velocity.z)


static func turn_toward(current_yaw: float, target_yaw: float, delta: float) -> float:
	## Exponential-smoothed angular approach; frame-rate independent.
	var weight := 1.0 - exp(-TURN_LERP * delta)
	return lerp_angle(current_yaw, target_yaw, weight)


static func facing_from_velocity(velocity: Vector3, fallback_yaw: float) -> float:
	var planar := Vector2(velocity.x, velocity.z)
	if planar.length_squared() < 0.01:
		return fallback_yaw
	return atan2(-planar.x, -planar.y)


static func motion_state(velocity: Vector3) -> StringName:
	var planar_speed := Vector2(velocity.x, velocity.z).length()
	if planar_speed < IDLE_THRESHOLD:
		return &"idle"
	if planar_speed < RUN_THRESHOLD:
		return &"walk"
	return &"run"
