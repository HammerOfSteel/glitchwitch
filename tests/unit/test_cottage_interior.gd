extends GdUnitTestSuite
## Cottage interior smoke: the zone assembles with a player and at least
## one discrete prop from the ZoneBuilder (no scatter regions indoors).

const COTTAGE_INTERIOR_SCENE := "res://src/world/cottage_interior/cottage_interior.tscn"


func test_cottage_interior_assembles_with_player_and_props() -> void:
	var runner := scene_runner(COTTAGE_INTERIOR_SCENE)
	await runner.simulate_frames(10)
	var interior := runner.scene()

	assert_object(interior.get_node_or_null("Player")).is_not_null()

	var builder := interior.get_node("%ZoneBuilder") as ZoneBuilder
	assert_object(builder).is_not_null()

	var prop_count := 0
	for child in builder.get_children():
		if child is Node3D:
			prop_count += 1
	assert_int(prop_count).override_failure_message(
		"expected all 26 PropPlacements from cottage_interior.tres to be instanced under %ZoneBuilder"
	).is_equal(26)

	assert_object(interior.get_node_or_null("HearthLight")).is_not_null()
	assert_object(interior.get_node_or_null("WindowLight")).is_not_null()
