extends GdUnitTestSuite
## Cottage garden smoke: the zone assembles with a player and at least one
## discrete prop and one scatter patch from the ZoneBuilder.

const COTTAGE_GARDEN_SCENE := "res://src/world/cottage_garden/cottage_garden.tscn"


func test_cottage_garden_assembles_with_player_and_props() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(10)
	var garden := runner.scene()

	assert_object(garden.get_node_or_null("Player")).is_not_null()

	var builder := garden.get_node("%ZoneBuilder") as ZoneBuilder
	assert_object(builder).is_not_null()

	var has_discrete_prop := false
	var has_scatter := false
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			has_scatter = true
		elif child is MeshInstance3D or child is Node3D:
			has_discrete_prop = true
	assert_bool(has_discrete_prop).override_failure_message(
		"expected at least one discrete PropPlacement instanced under %ZoneBuilder"
	).is_true()
	assert_bool(has_scatter).override_failure_message(
		"expected at least one scatter region in cottage_garden.tres"
	).is_true()
