class_name Player
extends CharacterBody3D
## The witch's body in the world.
##
## The body itself never rotates — only AvatarMount turns toward motion, so
## the camera rig stays stable. Input is translated into an *intent* which
## the physics step consumes; tests and future cutscene/AI drivers can call
## set_move_intent directly with input_enabled off.

signal stepped
signal motion_changed(state: StringName)

const STEP_DISTANCE := 1.15

@export var input_enabled := true

var _move_intent := Vector2.ZERO
var _run_intent := false
var _motion_state: StringName = &"idle"
var _step_accumulator := 0.0

@onready var _avatar_mount: Node3D = %AvatarMount


func _physics_process(delta: float) -> void:
	if input_enabled:
		_read_input()
	var target := MovementMath.target_velocity(_move_intent, _run_intent, _camera_yaw())
	velocity = MovementMath.step_velocity(velocity, target, delta)
	velocity = MovementMath.apply_gravity(velocity, delta, is_on_floor())
	move_and_slide()
	_face_motion(delta)
	_update_motion_state()
	_accumulate_steps(delta)


func set_move_intent(direction: Vector2, running: bool = false) -> void:
	_move_intent = direction
	_run_intent = running


func get_motion_state() -> StringName:
	return _motion_state


func facing_yaw() -> float:
	if _avatar_mount == null:
		return 0.0
	return _avatar_mount.rotation.y


func _read_input() -> void:
	var vec := Input.get_vector(&"move_left", &"move_right", &"move_back", &"move_forward")
	set_move_intent(vec, Input.is_action_pressed(&"run"))


func _camera_yaw() -> float:
	var rig := get_node_or_null("CameraRig")
	if rig != null and rig.has_method("yaw"):
		return rig.yaw()
	return 0.0


func _face_motion(delta: float) -> void:
	if _avatar_mount == null:
		return
	var target_yaw := MovementMath.facing_from_velocity(velocity, _avatar_mount.rotation.y)
	_avatar_mount.rotation.y = MovementMath.turn_toward(_avatar_mount.rotation.y, target_yaw, delta)


func _update_motion_state() -> void:
	var next_state := MovementMath.motion_state(velocity)
	if next_state != _motion_state:
		_motion_state = next_state
		motion_changed.emit(next_state)


func _accumulate_steps(delta: float) -> void:
	if not is_on_floor():
		return
	var planar_speed := Vector2(velocity.x, velocity.z).length()
	if planar_speed < MovementMath.IDLE_THRESHOLD:
		_step_accumulator = 0.0
		return
	_step_accumulator += planar_speed * delta
	if _step_accumulator >= STEP_DISTANCE:
		_step_accumulator = fmod(_step_accumulator, STEP_DISTANCE)
		stepped.emit()
