extends GdUnitTestSuite
## Zone budget: hedgerow_lane must stay within the design bible's
## 150k tri / 120 draw call zone ceiling, same rule as test_zone_budget.gd
## applies to cottage_garden and test_interior_budget.gd applies to
## cottage_interior.

const HEDGEROW_LANE_SCENE := "res://src/world/hedgerow_lane/hedgerow_lane.tscn"
const MAX_TRIS := 150_000
const MAX_DRAW_CALLS := 120


func test_hedgerow_lane_within_zone_budget() -> void:
	var runner := scene_runner(HEDGEROW_LANE_SCENE)
	await runner.simulate_frames(3)
	var lane := runner.scene()

	var total_tris := 0
	var draw_calls := 0
	for found in lane.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.mesh != null:
			total_tris += _mesh_tri_count(mesh_instance.mesh)
			draw_calls += 1

	assert_int(total_tris).override_failure_message(
		"hedgerow_lane over the 150k tri zone budget"
	).is_less_equal(MAX_TRIS)
	assert_int(draw_calls).override_failure_message(
		"hedgerow_lane over the 120 draw call zone budget"
	).is_less_equal(MAX_DRAW_CALLS)


func _mesh_tri_count(mesh: Mesh) -> int:
	var tris := 0
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		tris += indices.size() / 3
	return tris
