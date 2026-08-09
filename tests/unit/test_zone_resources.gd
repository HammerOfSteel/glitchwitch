extends GdUnitTestSuite
## Zone data model: PropPlacement, ScatterRegion, Zone — pure data, no
## behavior. These tests just confirm the typed fields exist with sane
## defaults so ZoneBuilder (tested separately) can rely on them.

func test_prop_placement_defaults() -> void:
	var placement := PropPlacement.new()
	assert_object(placement.scene).is_null()
	assert_vector(placement.position).is_equal(Vector3.ZERO)
	assert_vector(placement.rotation_degrees).is_equal(Vector3.ZERO)
	assert_float(placement.scale).is_equal(1.0)


func test_scatter_region_defaults() -> void:
	var region := ScatterRegion.new()
	assert_array(region.variants).is_empty()
	assert_int(region.shape).is_equal(ScatterRegion.Shape.CIRCLE)
	assert_vector(region.center).is_equal(Vector3.ZERO)
	assert_vector(region.size).is_equal(Vector2.ZERO)
	assert_float(region.density).is_equal(0.0)
	assert_float(region.scale_min).is_equal(1.0)
	assert_float(region.scale_max).is_equal(1.0)
	assert_int(region.seed).is_equal(0)


func test_zone_defaults() -> void:
	var zone := Zone.new()
	assert_vector(zone.ground_size).is_equal(Vector2.ZERO)
	assert_array(zone.placements).is_empty()
	assert_array(zone.scatter_regions).is_empty()
