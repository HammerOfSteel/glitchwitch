extends Node3D
## The cottage interior — Phase 4's hearth-lit interior zone (T4.3).
## Standalone scene: no scene-transition wiring to cottage_garden yet.

func _ready() -> void:
	_stage()


func _stage() -> void:
	var hearth_light := get_node_or_null("HearthLight") as OmniLight3D
	if hearth_light != null:
		hearth_light.light_color = Color(1.0, 0.62, 0.38)
		hearth_light.light_energy = 0.6
		hearth_light.omni_range = 2.2
	var window_light := get_node_or_null("WindowLight") as OmniLight3D
	if window_light != null:
		window_light.light_color = Color(0.72, 0.84, 1.0)
		window_light.light_energy = 0.5
		window_light.omni_range = 3.0
