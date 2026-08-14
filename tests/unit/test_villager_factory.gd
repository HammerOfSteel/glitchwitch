extends GdUnitTestSuite
## VillagerFactory/VillagerInstance: the public entry point other code uses.

const MAX_TRIS := 4000  # docs/design-bible.md per-character budget


func test_build_returns_instance_with_v1_sockets() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	assert_object(instance).is_not_null()
	assert_bool(instance.sockets.has(&"head_top")).is_true()
	assert_bool(instance.sockets.has(&"hand_l")).is_true()
	assert_bool(instance.sockets.has(&"hand_r")).is_true()


func test_build_applies_shared_palette_material() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	var root := Node3D.new()
	auto_free(root)
	root.add_child(instance)
	var runner := scene_runner(root)
	await runner.simulate_frames(1)
	var meshes := instance.find_children("*", "MeshInstance3D", true, false)
	assert_int(meshes.size()).is_greater(0)
	for found in meshes:
		var mesh_instance := found as MeshInstance3D
		assert_object(mesh_instance.material_override) \
			.override_failure_message("bare mesh: %s" % mesh_instance.name).is_not_null()


func test_build_stays_within_character_tri_budget() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	var total_tris := 0
	for found in instance.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.mesh != null:
			for surface in range(mesh_instance.mesh.get_surface_count()):
				var arrays := mesh_instance.mesh.surface_get_arrays(surface)
				var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
				total_tris += indices.size() / 3
	assert_int(total_tris).override_failure_message(
		"villager over the %d tri character budget" % MAX_TRIS
	).is_less_equal(MAX_TRIS)


func test_build_stamps_every_body_part_with_its_assigned_uv() -> void:
	# Proves the UV-stamp step actually ran end-to-end through the full
	# façade (VillagerFactory -> HumanSynth -> VillagerRig), not just that
	# no errors were logged — matches this spec's testing requirement that
	# UV arrays are checked against palette_uv.gd's uv_for(ramp, shade) for
	# each part's assigned ramp/shade.
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	var expected_by_name := {
		"head": PaletteUv.uv_for(dna.skin_ramp, 3),
		"hand_l": PaletteUv.uv_for(dna.skin_ramp, 3),
		"hand_r": PaletteUv.uv_for(dna.skin_ramp, 3),
		"torso": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"elbow_l": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"elbow_r": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"knee_l": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"knee_r": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"hair": PaletteUv.uv_for(dna.hair_ramp, 1),
	}
	for part_name: String in expected_by_name:
		var node := instance.find_child(part_name, true, false) as MeshInstance3D
		assert_object(node).override_failure_message(
			"missing expected mesh part: %s" % part_name
		).is_not_null()
		var uvs: PackedVector2Array = node.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
		var expected_uv: Vector2 = expected_by_name[part_name]
		for uv in uvs:
			assert_vector(uv).override_failure_message(
				"wrong UV stamp on %s" % part_name
			).is_equal(expected_uv)


func test_set_motion_state_switches_animator_state() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	instance.set_motion_state(&"walk")
	assert_str(String(instance.current_motion_state())).is_equal("walk")
	instance.set_motion_state(&"somersault")
	assert_str(String(instance.current_motion_state())).is_equal("idle")
