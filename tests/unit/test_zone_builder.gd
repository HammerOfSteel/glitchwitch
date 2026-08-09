extends GdUnitTestSuite
## ZoneBuilder: turns a Zone resource into real nodes from discrete prop
## placements, deterministically.

const CRATE_SCENE := "res://assets/generated/crate.glb"


func _make_zone_with_placements() -> Zone:
	var zone := Zone.new()
	zone.ground_size = Vector2(4.0, 4.0)
	var a := PropPlacement.new()
	a.scene = load(CRATE_SCENE)
	a.position = Vector3(1.0, 0.0, 1.0)
	a.rotation_degrees = Vector3(0.0, 45.0, 0.0)
	a.scale = 2.0
	var b := PropPlacement.new()
	b.scene = load(CRATE_SCENE)
	b.position = Vector3(-1.0, 0.0, -1.0)
	zone.placements = [a, b]
	return zone


func _make_zone_with_scatter() -> Zone:
	var zone := Zone.new()
	zone.ground_size = Vector2(4.0, 4.0)
	var mesh_a := BoxMesh.new()
	var mesh_b := BoxMesh.new()
	var region := ScatterRegion.new()
	region.variants = [mesh_a, mesh_b]
	region.shape = ScatterRegion.Shape.RECT
	region.size = Vector2(2.0, 2.0)  # area = 4 m^2
	region.density = 5.0  # 20 instances total, split 10/10
	region.seed = 42
	zone.scatter_regions = [region]
	return zone


func test_rebuild_instances_each_placement() -> void:
	var builder := ZoneBuilder.new()
	auto_free(builder)
	builder.zone = _make_zone_with_placements()
	builder.rebuild()

	assert_int(builder.get_child_count()).is_equal(2)
	var first := builder.get_child(0)
	assert_vector((first as Node3D).position).is_equal(Vector3(1.0, 0.0, 1.0))
	assert_vector((first as Node3D).rotation_degrees).is_equal(Vector3(0.0, 45.0, 0.0))
	assert_vector((first as Node3D).scale).is_equal(Vector3(2.0, 2.0, 2.0))


func test_rebuild_clears_previous_children() -> void:
	var builder := ZoneBuilder.new()
	auto_free(builder)
	builder.zone = _make_zone_with_placements()
	builder.rebuild()
	builder.rebuild()

	assert_int(builder.get_child_count()).is_equal(2)  # not 4


func test_ready_rebuilds_existing_zone() -> void:
	var root := Node3D.new()
	auto_free(root)
	var builder := ZoneBuilder.new()
	builder.zone = _make_zone_with_placements()
	root.add_child(builder)
	var runner := scene_runner(root)
	await runner.simulate_frames(2)

	assert_int(builder.get_child_count()).is_equal(2)


func test_setting_zone_in_tree_rebuilds_immediately() -> void:
	var root := Node3D.new()
	auto_free(root)
	var builder := ZoneBuilder.new()
	root.add_child(builder)
	var runner := scene_runner(root)
	await runner.simulate_frames(2)

	builder.zone = _make_zone_with_placements()

	assert_int(builder.get_child_count()).is_equal(2)


func test_rebuild_creates_one_multimesh_per_variant() -> void:
	var builder := ZoneBuilder.new()
	auto_free(builder)
	builder.zone = _make_zone_with_scatter()
	builder.rebuild()

	var multimeshes: Array = []
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			multimeshes.append(child)
	assert_int(multimeshes.size()).is_equal(2)

	var total_instances := 0
	for mmi in multimeshes:
		total_instances += (mmi as MultiMeshInstance3D).multimesh.instance_count
	assert_int(total_instances).is_equal(20)


func test_rebuild_scatter_is_deterministic() -> void:
	var zone := _make_zone_with_scatter()
	var first := ZoneBuilder.new()
	auto_free(first)
	first.zone = zone
	first.rebuild()

	var second := ZoneBuilder.new()
	auto_free(second)
	second.zone = zone
	second.rebuild()

	var first_mmi := first.get_child(0) as MultiMeshInstance3D
	var second_mmi := second.get_child(0) as MultiMeshInstance3D
	assert_int(second_mmi.multimesh.instance_count) \
		.is_equal(first_mmi.multimesh.instance_count)
	for i in range(first_mmi.multimesh.instance_count):
		var expected: Transform3D = first_mmi.multimesh.get_instance_transform(i)
		var actual: Transform3D = second_mmi.multimesh.get_instance_transform(i)
		assert_bool(actual.is_equal_approx(expected)) \
			.override_failure_message("scatter instance %d transform not deterministic" % i) \
			.is_true()


func test_rebuild_ignores_null_scatter_variants_without_losing_density() -> void:
	var zone := _make_zone_with_scatter()
	zone.scatter_regions[0].variants = [BoxMesh.new(), null, BoxMesh.new()]
	var builder := ZoneBuilder.new()
	auto_free(builder)
	builder.zone = zone
	builder.rebuild()

	var multimeshes: Array = []
	var total_instances := 0
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			multimeshes.append(child)
			total_instances += (child as MultiMeshInstance3D).multimesh.instance_count

	assert_int(multimeshes.size()).is_equal(2)
	assert_int(total_instances).is_equal(20)
	for found in multimeshes:
		assert_object((found as MultiMeshInstance3D).multimesh.mesh).is_not_null()


func test_rebuild_keeps_variant_layout_stable_when_null_slot_exists() -> void:
	var base_zone := _make_zone_with_scatter()
	var with_null_zone := _make_zone_with_scatter()
	with_null_zone.scatter_regions[0].variants = [
		with_null_zone.scatter_regions[0].variants[0],
		null,
		with_null_zone.scatter_regions[0].variants[1],
	]

	var base_builder := ZoneBuilder.new()
	auto_free(base_builder)
	base_builder.zone = base_zone
	base_builder.rebuild()

	var with_null_builder := ZoneBuilder.new()
	auto_free(with_null_builder)
	with_null_builder.zone = with_null_zone
	with_null_builder.rebuild()

	var base_mmi := base_builder.get_child(1) as MultiMeshInstance3D
	var with_null_mmi := with_null_builder.get_child(1) as MultiMeshInstance3D
	assert_int(with_null_mmi.multimesh.instance_count).is_equal(base_mmi.multimesh.instance_count)
	for i in range(base_mmi.multimesh.instance_count):
		var expected: Transform3D = base_mmi.multimesh.get_instance_transform(i)
		var actual: Transform3D = with_null_mmi.multimesh.get_instance_transform(i)
		assert_bool(actual.is_equal_approx(expected)) \
			.override_failure_message("variant layout changed when null slot was inserted at index %d" % i) \
			.is_true()


func test_rebuild_dresses_placements_and_scatter_with_palette_material() -> void:
	var palette_material: Material = load(PaletteApply.PALETTE_MATERIAL_PATH)
	var builder := ZoneBuilder.new()
	auto_free(builder)
	var zone := _make_zone_with_placements()
	zone.scatter_regions = _make_zone_with_scatter().scatter_regions
	builder.zone = zone
	builder.rebuild()

	var mesh_instances: Array = []
	var multimesh_instances: Array = []
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			multimesh_instances.append(child)
		else:
			mesh_instances.append_array(
				(child as Node).find_children("*", "MeshInstance3D", true, false)
			)

	assert_int(mesh_instances.size()).is_greater(0)
	for found in mesh_instances:
		assert_object((found as MeshInstance3D).material_override) \
			.override_failure_message("a discrete placement mesh is missing the palette material") \
			.is_same(palette_material)

	assert_int(multimesh_instances.size()).is_greater(0)
	for found in multimesh_instances:
		assert_object((found as MultiMeshInstance3D).material_override) \
			.override_failure_message("a scatter MultiMeshInstance3D is missing the palette material") \
			.is_same(palette_material)
