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
