class_name Interactable
extends Area3D
## Something in the world that welcomes attention.
##
## Interactables register themselves in the "interactables" group; the
## FocusResolver picks one, the prompt shows its verb, and interact()
## routes the player's gesture to whatever behavior connects here.

signal interacted(by: Node)
signal focus_state_changed(focused: bool)

@export var verb := "Look"
@export var display_name := ""
@export var focus_priority := 0
@export var enabled := true

var _focused := false


func _ready() -> void:
	add_to_group(&"interactables")


func interact(by: Node) -> void:
	if enabled:
		interacted.emit(by)


func set_focused(focused: bool) -> void:
	if focused == _focused:
		return
	_focused = focused
	focus_state_changed.emit(focused)


func is_focused() -> bool:
	return _focused


func prompt_text() -> String:
	if display_name.is_empty():
		return verb
	return "%s  —  %s" % [verb, display_name]
