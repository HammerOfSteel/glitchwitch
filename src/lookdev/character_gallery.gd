@tool
class_name CharacterGallery
extends Node3D
## Look-dev gallery: stages every generated character archetype side by side
## so pipeline changes (new archetypes, part swaps, rig/animation edits) can
## be eyeballed in-engine, not just verified by the Python test suite.
##
## Applies the palette toon material to every mesh (generated GLBs carry no
## materials by design) and plays each character's idle clip on loop.


func _ready() -> void:
	PaletteApply.apply(self)
	_stage()
	_play_idle()


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
		fill.shadow_enabled = false
	var camera := get_node_or_null("Camera") as Camera3D
	if camera != null:
		camera.position = Vector3(0.0, 1.6, 3.2)
		camera.rotation_degrees = Vector3(-14.0, 0.0, 0.0)
		camera.fov = 40.0
		camera.current = true


func _play_idle() -> void:
	for stand in find_children("*Stand", "Node3D", true, false):
		var players := stand.find_children("*", "AnimationPlayer", true, false)
		if players.is_empty():
			continue
		var anim := players[0] as AnimationPlayer
		if anim.has_animation("idle"):
			anim.play("idle")
