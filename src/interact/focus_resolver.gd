class_name FocusResolver
extends Node3D
## Chooses which interactable holds the witch's attention.
##
## Scans the "interactables" group each physics frame, scores candidates in
## the facing cone by distance, angle, and priority, and applies hysteresis
## so focus never flickers between near-equal candidates.

signal focus_changed(interactable: Interactable)

const REACH := 2.5
const CONE_DOT := 0.42  # ≈ 65° half-angle
const HYSTERESIS := 0.85  # focused item keeps a 15% score advantage
const PRIORITY_WEIGHT := 0.5

var _focused: Interactable = null


func _physics_process(_delta: float) -> void:
	evaluate()


func focused() -> Interactable:
	return _focused


func interact_focused(by: Node) -> void:
	if _focused != null:
		_focused.interact(by)


static func score(distance: float, facing_dot: float, priority: int) -> float:
	## Lower is better: near, centered, and important things win.
	return distance * (2.0 - facing_dot) - float(priority) * PRIORITY_WEIGHT


func evaluate() -> void:
	var facing := _facing()
	var best: Interactable = null
	var best_score := INF
	for node in get_tree().get_nodes_in_group(&"interactables"):
		var item := node as Interactable
		if item == null or not item.enabled or not item.is_inside_tree():
			continue
		var offset := item.global_position - global_position
		var distance := offset.length()
		if distance > REACH:
			continue
		var facing_dot := facing.dot(offset.normalized()) if distance > 0.01 else 1.0
		if facing_dot < CONE_DOT:
			continue
		var candidate_score := score(distance, facing_dot, item.focus_priority)
		if item == _focused:
			candidate_score *= HYSTERESIS
		if candidate_score < best_score:
			best_score = candidate_score
			best = item
	_set_focus(best)


func _set_focus(item: Interactable) -> void:
	if item == _focused:
		return
	if _focused != null:
		_focused.set_focused(false)
	_focused = item
	if _focused != null:
		_focused.set_focused(true)
	focus_changed.emit(_focused)


func _facing() -> Vector3:
	var player := get_parent() as Player
	if player != null:
		var yaw := player.facing_yaw()
		return Vector3(-sin(yaw), 0.0, -cos(yaw))
	return -global_transform.basis.z
