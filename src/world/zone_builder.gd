@tool
class_name ZoneBuilder
extends Node3D
## Turns a Zone resource into real nodes: discrete props dressed via
## PaletteApply, same as any other prop.
##
## Live re-preview while editing an open zone is a known limitation: nested
## PropPlacement/ScatterRegion edits don't reliably bubble a `changed`
## signal up to the Zone resource. Reload the scene (or re-enter the
## editor) to see edits reflected; rebuild() always reruns on _ready().

var _zone: Zone

@export var zone: Zone:
	get:
		return _zone
	set(value):
		_zone = value
		if is_inside_tree():
			rebuild()


func _ready() -> void:
	rebuild()


func rebuild() -> void:
	for child in get_children():
		remove_child(child)
		child.queue_free()
	if _zone == null:
		return
	_build_placements()


func _build_placements() -> void:
	for placement in _zone.placements:
		if placement.scene == null:
			continue
		var instance := placement.scene.instantiate()
		add_child(instance)
		if instance is Node3D:
			var node3d := instance as Node3D
			node3d.position = placement.position
			node3d.rotation_degrees = placement.rotation_degrees
			node3d.scale = Vector3.ONE * placement.scale
		PaletteApply.apply(instance)
