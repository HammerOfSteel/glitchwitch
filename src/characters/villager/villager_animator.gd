class_name VillagerAnimator
extends RefCounted
## Small code-driven animator: idle breathing/head-bob + walk hip/shoulder
## swing, sine-curve based (no baked AnimationPlayer clips) — matches the
## source's animate.ts approach. See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §5.

const BREATH_SPEED := 1.6
const BREATH_AMOUNT := 0.03
const HEAD_BOB_SPEED := 1.6
const HEAD_BOB_AMOUNT := 0.01
const WALK_SWING_SPEED := 6.0
const WALK_SWING_AMOUNT := 0.5  # radians

var _rig: VillagerRig
var _state: StringName = &"idle"
var _t := 0.0
var _head_base_y := 0.0


func _init(rig: VillagerRig) -> void:
	_rig = rig
	var head := _rig.root.find_child("head", true, false) as Node3D
	if head != null:
		_head_base_y = head.position.y


func set_motion_state(state: StringName) -> void:
	_state = state if state in [&"idle", &"walk"] else &"idle"


func current_motion_state() -> StringName:
	return _state


func update(delta: float) -> void:
	_t += delta
	var torso := _rig.root.find_child("torso", true, false) as Node3D
	if torso != null:
		torso.scale.y = 1.0 + sin(_t * BREATH_SPEED) * BREATH_AMOUNT

	var head := _rig.root.find_child("head", true, false) as Node3D
	if head != null:
		head.position.y = _head_base_y + sin(_t * HEAD_BOB_SPEED) * HEAD_BOB_AMOUNT

	if _state == &"walk":
		var swing := sin(_t * WALK_SWING_SPEED) * WALK_SWING_AMOUNT
		_rotate_pair("shoulder_l", "shoulder_r", swing)
		_rotate_pair("hip_l", "hip_r", -swing)
	else:
		_rotate_pair("shoulder_l", "shoulder_r", 0.0)
		_rotate_pair("hip_l", "hip_r", 0.0)


func _rotate_pair(left_name: String, right_name: String, angle: float) -> void:
	var left := _rig.root.find_child(left_name, true, false) as Node3D
	var right := _rig.root.find_child(right_name, true, false) as Node3D
	if left != null:
		left.rotation.x = angle
	if right != null:
		right.rotation.x = -angle
