class_name TimeOfDayRig
extends Node
## Drives a zone's Sun/Fill DirectionalLight3D pair from GameClock +
## TimeOfDayCurve, replacing what each zone's _stage() used to hard-code.
## Add as a child node in a zone's .tscn, sibling to its Sun/Fill lights.
## See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

@export var sun_path: NodePath = ^"../Sun"
@export var fill_path: NodePath = ^"../Fill"

const UPDATE_INTERVAL_SEC := 1.0

var _sun: DirectionalLight3D
var _fill: DirectionalLight3D
var _timer: Timer


func _ready() -> void:
	_sun = get_node_or_null(sun_path) as DirectionalLight3D
	_fill = get_node_or_null(fill_path) as DirectionalLight3D
	_apply_current()
	_timer = Timer.new()
	_timer.wait_time = UPDATE_INTERVAL_SEC
	_timer.timeout.connect(_apply_current)
	add_child(_timer)
	_timer.start()


func _apply_current() -> void:
	var state := TimeOfDayCurve.light_state_for_hour(GameClock.hour_of_day())
	if _sun != null:
		_sun.rotation_degrees = state.sun_rotation_degrees
		_sun.light_color = state.sun_color
		_sun.light_energy = state.sun_energy
		_sun.shadow_enabled = state.sun_shadow_enabled
	if _fill != null:
		_fill.rotation_degrees = state.fill_rotation_degrees
		_fill.light_color = state.fill_color
		_fill.light_energy = state.fill_energy
