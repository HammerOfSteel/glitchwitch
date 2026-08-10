extends GdUnitTestSuite
## Hedgerow lane smoke: the zone assembles with a player and exactly the
## 16 PropPlacements described in hedgerow_lane.tres (no scatter regions).

const HEDGEROW_LANE_SCENE := "res://src/world/hedgerow_lane/hedgerow_lane.tscn"


func test_hedgerow_lane_assembles_with_player_and_props() -> void:
	var runner := scene_runner(HEDGEROW_LANE_SCENE)
	await runner.simulate_frames(10)
	var lane := runner.scene()

	assert_object(lane.get_node_or_null("Player")).is_not_null()

	var builder := lane.get_node("%ZoneBuilder") as ZoneBuilder
	assert_object(builder).is_not_null()

	var prop_count := 0
	for child in builder.get_children():
		if child is Node3D:
			prop_count += 1
	assert_int(prop_count).override_failure_message(
		"expected all 16 PropPlacements from hedgerow_lane.tres to be instanced under %ZoneBuilder"
	).is_equal(16)
