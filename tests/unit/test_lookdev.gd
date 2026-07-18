extends GdUnitTestSuite
## Look-dev smoke: shaders parse, materials resolve, the diorama assembles,
## and the palette auto-apply ritual dresses every mesh.

const PALETTE_MATERIAL_PATH := "res://src/materials/palette_main.tres"


func test_toon_shader_loads() -> void:
	var shader := load("res://src/shaders/toon.gdshader") as Shader
	assert_object(shader).is_not_null()
	assert_str(shader.code).contains("void light()")


func test_outline_shader_loads() -> void:
	var shader := load("res://src/shaders/outline.gdshader") as Shader
	assert_object(shader).is_not_null()
	assert_str(shader.code).contains("cull_front")


func test_palette_material_resolves_with_texture() -> void:
	var material := load(PALETTE_MATERIAL_PATH) as ShaderMaterial
	assert_object(material).is_not_null()
	assert_object(material.shader).is_not_null()
	var texture := material.get_shader_parameter("palette_tex") as Texture2D
	assert_object(texture).is_not_null()
	assert_object(material.next_pass).is_not_null()


func test_generated_props_import_as_scenes() -> void:
	for prop_name in ["crate", "fence", "ground_tile", "jar", "mug", "pine"]:
		var path := "res://assets/generated/%s.glb" % prop_name
		(
			assert_bool(ResourceLoader.exists(path))
			. override_failure_message("missing generated prop: %s (run make assets)" % path)
			. is_true()
		)


func test_diorama_assembles_and_applies_palette() -> void:
	var runner := scene_runner("res://src/lookdev/diorama.tscn")
	var diorama := runner.scene() as Node3D
	assert_object(diorama).is_not_null()

	var meshes := diorama.find_children("*", "MeshInstance3D", true, false)
	assert_int(meshes.size()).is_greater_equal(10)

	var palette_material: Material = load(PALETTE_MATERIAL_PATH)
	for found in meshes:
		var mesh_instance := found as MeshInstance3D
		(
			assert_object(mesh_instance.material_override)
			. override_failure_message("mesh missing palette override: %s" % mesh_instance.name)
			. is_same(palette_material)
		)


func test_diorama_has_camera_and_sun() -> void:
	var runner := scene_runner("res://src/lookdev/diorama.tscn")
	var diorama := runner.scene() as Node3D
	assert_object(diorama.get_node_or_null("Camera")).is_not_null()
	assert_object(diorama.get_node_or_null("Sun")).is_not_null()
	var sun := diorama.get_node_or_null("Sun") as DirectionalLight3D
	assert_bool(sun.shadow_enabled).is_true()
