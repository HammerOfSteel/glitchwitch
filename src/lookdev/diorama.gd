@tool
class_name Diorama
extends Node3D
## Look-dev diorama: a cottage corner proving the toy-render style.
##
## Applies the palette toon material to every mesh (generated GLBs carry no
## materials by design) and stages the sun, fill, and camera.

const PALETTE_MATERIAL_PATH := "res://src/materials/palette_main.tres"


func _ready() -> void:
	apply_palette(self)
	_stage()


static func apply_palette(root: Node) -> void:
	var material := load(PALETTE_MATERIAL_PATH) as Material
	if material == null:
		push_warning("palette material unavailable — run `make assets` first")
		return
	for found in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		mesh_instance.material_override = material


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
		camera.position = Vector3(3.1, 2.6, 3.4)
		camera.rotation_degrees = Vector3(-28.0, 41.0, 0.0)
		camera.fov = 45.0
		camera.current = true
