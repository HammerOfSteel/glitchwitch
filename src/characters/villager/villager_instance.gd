class_name VillagerInstance
extends Node3D
## The public face of a built villager — owns its rig/animator, exposes
## the same set_motion_state()/play_gesture() shape as WrenAvatar
## (src/player/avatar.gd) so zone/NPC code can treat both character types
## identically. See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §6.

var sockets: Dictionary = {}  # StringName -> Node3D, read-only by convention

var _animator: VillagerAnimator


func _setup(rig: VillagerRig) -> void:
	add_child(rig.root)
	sockets = rig.sockets
	_animator = VillagerAnimator.new(rig)


func _process(delta: float) -> void:
	if _animator != null:
		_animator.update(delta)


func set_motion_state(state: StringName) -> void:
	if _animator != null:
		_animator.set_motion_state(state)


func current_motion_state() -> StringName:
	if _animator == null:
		return &"idle"
	return _animator.current_motion_state()


func play_gesture(_gesture: StringName) -> void:
	pass  # v1: no gestures defined yet — matches WrenAvatar's no-op convention.
