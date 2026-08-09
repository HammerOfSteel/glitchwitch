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
