extends GdUnitTestSuite
## Zone budget: cottage_garden must stay within the design bible's
## 150k tri / 120 draw call zone ceiling. This is a static upper-bound
## check (no frustum culling accounted for), matching the design bible's
## "asserted per asset in tests/python, per zone in gdUnit scene tests"
## split.

const COTTAGE_GARDEN_SCENE := "res://src/world/cottage_garden/cottage_garden.tscn"
const MAX_TRIS := 150_000
const MAX_DRAW_CALLS := 120


func test_cottage_garden_within_zone_budget() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(3)
	var garden := runner.scene()

	var total_tris := 0
	var draw_calls := 0
	for found in garden.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.mesh != null:
			total_tris += _mesh_tri_count(mesh_instance.mesh)
			draw_calls += 1
	for found in garden.find_children("*", "MultiMeshInstance3D", true, false):
		var mmi := found as MultiMeshInstance3D
		if mmi.multimesh != null and mmi.multimesh.mesh != null:
			var per_instance := _mesh_tri_count(mmi.multimesh.mesh)
			total_tris += per_instance * mmi.multimesh.instance_count
			draw_calls += 1

	assert_int(total_tris).override_failure_message(
		"cottage_garden over the 150k tri zone budget"
	).is_less_equal(MAX_TRIS)
	assert_int(draw_calls).override_failure_message(
		"cottage_garden over the 120 draw call zone budget"
	).is_less_equal(MAX_DRAW_CALLS)


func _mesh_tri_count(mesh: Mesh) -> int:
	# Scatter/generated props are single-primitive (asserted in
	# tests/python/test_assetgen.py::test_scatter_props_export_as_single_primitive),
	# so summing surface_get_array_len over ARRAY_INDEX is exact here.
	var tris := 0
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		tris += indices.size() / 3
	return tris
