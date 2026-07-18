class_name InteractPrompt
extends Label
## The gentle "[E] Look — a seam in the world" whisper at the bottom of the
## screen. Purely presentational; the FocusResolver decides what it says.


func _ready() -> void:
	visible = false


func on_focus_changed(interactable: Interactable) -> void:
	if interactable == null:
		visible = false
		return
	text = "[E]  %s" % interactable.prompt_text()
	visible = true
