extends Node3D
## The sandbox glade — Phase 1's playable slice.
##
## Walk (WASD), run (Shift), orbit (mouse), zoom (wheel), toggle first person
## (V), open Witch Sight (F) to reveal the seam stone, and interact (E).

@onready var _seam_stone: MeshInstance3D = %SeamStone
@onready var _seam_interactable: Interactable = %SeamInteractable


func _ready() -> void:
	PaletteApply.apply(self)
	_stage()
	_seam_interactable.interacted.connect(_on_seam_observed)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and (event as InputEventMouseButton).pressed:
		if Input.mouse_mode != Input.MOUSE_MODE_CAPTURED and DisplayServer.window_can_draw():
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	elif event.is_action_pressed(&"pause"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _on_seam_observed(_by: Node) -> void:
	## The seam answers attention with a small, pleased spin.
	var tween := create_tween()
	(
		tween
		. tween_property(_seam_stone, "rotation:y", _seam_stone.rotation.y + TAU, 0.9)
		. set_trans(Tween.TRANS_CUBIC)
		. set_ease(Tween.EASE_OUT)
	)


func _stage() -> void:
	var sun := get_node_or_null("Sun") as DirectionalLight3D
	if sun != null:
		sun.rotation_degrees = Vector3(-48.0, -32.0, 0.0)
		sun.light_color = Color(1.0, 0.93, 0.82)
		sun.light_energy = 1.25
		sun.shadow_enabled = true
	var fill := get_node_or_null("Fill") as DirectionalLight3D
	if fill != null:
		fill.rotation_degrees = Vector3(-20.0, 141.0, 0.0)
		fill.light_color = Color(0.68, 0.78, 0.92)
		fill.light_energy = 0.35
