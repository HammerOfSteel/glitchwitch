class_name CameraRig
extends Node3D
## Third-person orbit camera with cozy follow smoothing.
##
## The rig runs top-level: it trails its anchor (the player) with a soft
## exponential lag instead of being welded to it. Yaw lives on the rig,
## pitch on the PitchPivot, and a SpringArm3D keeps the camera out of walls.

signal mode_changed(mode: Mode)
signal sight_changed(enabled: bool)

enum Mode { THIRD, FIRST }

const SEAM_LAYER_BIT := 2  # render layer 2 (1 << 1): seam objects live here
const FOV_THIRD := 50.0
const FOV_FIRST := 70.0
const FIRST_PIVOT_HEIGHT := 0.25
const TRANSITION_TIME := 0.25
const MOUSE_SENSITIVITY := 0.0035
const STICK_SENSITIVITY := 2.6
const STICK_DEADZONE := 0.15
const PITCH_MIN := -1.25
const PITCH_MAX := 0.8
const ZOOM_MIN := 1.6
const ZOOM_MAX := 5.0
const ZOOM_STEP := 0.4
const ZOOM_LERP := 8.0
const FOLLOW_LERP := 12.0
const ANCHOR_HEIGHT := 1.2
const FRAME_BIAS_SPEED := 0.5
const FRAME_BIAS_IDLE_DELAY := 0.6

@export var frame_bias_enabled := false

var _yaw := 0.0
var _pitch := -0.35
var _zoom_target := 3.5
var _last_look_time := -10.0
var _bias_target: Node3D = null
var _mode := Mode.THIRD
var _sight := false
var _transition_tween: Tween = null

@onready var _pitch_pivot: Node3D = %PitchPivot
@onready var _spring_arm: SpringArm3D = %SpringArm
@onready var _camera: Camera3D = %Camera
@onready var _sight_overlay: CanvasLayer = %SightOverlay


func _ready() -> void:
	top_level = true
	_apply_rotation()
	snap_to_anchor()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var motion := event as InputEventMouseMotion
		rotate_look(-motion.relative.x * MOUSE_SENSITIVITY, -motion.relative.y * MOUSE_SENSITIVITY)
	elif event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.pressed and button.button_index == MOUSE_BUTTON_WHEEL_UP:
			zoom_by(-ZOOM_STEP)
		elif button.pressed and button.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			zoom_by(ZOOM_STEP)


func _process(delta: float) -> void:
	_poll_stick(delta)
	_follow_anchor(delta)
	_apply_frame_bias(delta)
	_spring_arm.spring_length = lerpf(
		_spring_arm.spring_length, _arm_target(), 1.0 - exp(-ZOOM_LERP * delta)
	)


func yaw() -> float:
	return _yaw


func pitch() -> float:
	return _pitch


func camera() -> Camera3D:
	return _camera


func rotate_look(yaw_delta: float, pitch_delta: float) -> void:
	_yaw = wrapf(_yaw + yaw_delta, -PI, PI)
	_pitch = clampf(_pitch + pitch_delta, PITCH_MIN, PITCH_MAX)
	_last_look_time = _now()
	_apply_rotation()


func zoom_by(step: float) -> void:
	_zoom_target = clampf(_zoom_target + step, ZOOM_MIN, ZOOM_MAX)


func zoom_target() -> float:
	return _zoom_target


func set_bias_target(target: Node3D) -> void:
	_bias_target = target


func mode() -> Mode:
	return _mode


func sight_enabled() -> bool:
	return _sight


func toggle_mode(instant: bool = false) -> void:
	set_mode(Mode.FIRST if _mode == Mode.THIRD else Mode.THIRD, instant)


func set_mode(new_mode: Mode, instant: bool = false) -> void:
	if new_mode == _mode:
		return
	_mode = new_mode
	var target_fov := FOV_FIRST if _mode == Mode.FIRST else FOV_THIRD
	var target_pivot_y := FIRST_PIVOT_HEIGHT if _mode == Mode.FIRST else 0.0
	if _transition_tween != null and _transition_tween.is_valid():
		_transition_tween.kill()
	if instant:
		_camera.fov = target_fov
		_pitch_pivot.position.y = target_pivot_y
		_spring_arm.spring_length = _arm_target()
	else:
		_transition_tween = create_tween().set_parallel(true)
		_transition_tween.tween_property(_camera, "fov", target_fov, TRANSITION_TIME)
		_transition_tween.tween_property(
			_pitch_pivot, "position:y", target_pivot_y, TRANSITION_TIME
		)
	mode_changed.emit(_mode)


func toggle_sight() -> void:
	set_sight(not _sight)


func set_sight(enabled: bool) -> void:
	if enabled == _sight:
		return
	_sight = enabled
	if enabled:
		_camera.cull_mask |= SEAM_LAYER_BIT
	else:
		_camera.cull_mask &= ~SEAM_LAYER_BIT
	if _sight_overlay != null:
		_sight_overlay.visible = enabled
	sight_changed.emit(enabled)


func _arm_target() -> float:
	return 0.0 if _mode == Mode.FIRST else _zoom_target


func snap_to_anchor() -> void:
	var anchor := _anchor_position()
	if anchor != Vector3.INF:
		global_position = anchor


func _apply_rotation() -> void:
	rotation.y = _yaw
	if _pitch_pivot != null:
		_pitch_pivot.rotation.x = _pitch


func _poll_stick(delta: float) -> void:
	var stick := Vector2(
		Input.get_joy_axis(0, JOY_AXIS_RIGHT_X), Input.get_joy_axis(0, JOY_AXIS_RIGHT_Y)
	)
	if stick.length() < STICK_DEADZONE:
		return
	rotate_look(-stick.x * STICK_SENSITIVITY * delta, -stick.y * STICK_SENSITIVITY * delta)


func _follow_anchor(delta: float) -> void:
	var anchor := _anchor_position()
	if anchor == Vector3.INF:
		return
	var weight := 1.0 - exp(-FOLLOW_LERP * delta)
	global_position = global_position.lerp(anchor, weight)


func _anchor_position() -> Vector3:
	var parent := get_parent() as Node3D
	if parent == null:
		return Vector3.INF
	return parent.global_position + Vector3(0, ANCHOR_HEIGHT, 0)


func _apply_frame_bias(delta: float) -> void:
	if not frame_bias_enabled or _bias_target == null:
		return
	if _now() - _last_look_time < FRAME_BIAS_IDLE_DELAY:
		return
	var to_target := _bias_target.global_position - global_position
	var planar := Vector2(to_target.x, to_target.z)
	if planar.length_squared() < 0.04:
		return
	var desired_yaw := atan2(-planar.x, -planar.y)
	var max_step := FRAME_BIAS_SPEED * delta
	var diff := wrapf(desired_yaw - _yaw, -PI, PI)
	_yaw = wrapf(_yaw + clampf(diff, -max_step, max_step), -PI, PI)
	_apply_rotation()


func _now() -> float:
	return float(Time.get_ticks_msec()) / 1000.0
