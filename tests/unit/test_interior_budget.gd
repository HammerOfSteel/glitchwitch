extends GdUnitTestSuite
## Zone budget: cottage_interior must stay within the design bible's
## 150k tri / 120 draw call zone ceiling, same rule as test_zone_budget.gd
## applies to cottage_garden.

const COTTAGE_INTERIOR_SCENE := "res://src/world/cottage_interior/cottage_interior.tscn"
const MAX_TRIS := 150_000
const MAX_DRAW_CALLS := 120


func test_cottage_interior_within_zone_budget() -> void:
	var runner := scene_runner(COTTAGE_INTERIOR_SCENE)
	await runner.simulate_frames(3)
	var interior := runner.scene()

	var total_tris := 0
	var draw_calls := 0
	for found in interior.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.mesh != null:
			total_tris += _mesh_tri_count(mesh_instance.mesh)
			draw_calls += 1

	assert_int(total_tris).override_failure_message(
		"cottage_interior over the 150k tri zone budget"
	).is_less_equal(MAX_TRIS)
	assert_int(draw_calls).override_failure_message(
		"cottage_interior over the 120 draw call zone budget"
	).is_less_equal(MAX_DRAW_CALLS)


func _mesh_tri_count(mesh: Mesh) -> int:
	var tris := 0
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		tris += indices.size() / 3
	return tris
