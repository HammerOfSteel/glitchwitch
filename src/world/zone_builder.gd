@tool
class_name ZoneBuilder
extends Node3D
## Turns a Zone resource into real nodes: discrete props dressed via
## PaletteApply, same as any other prop.
##
## Live re-preview while editing an open zone is a known limitation: nested
## PropPlacement/ScatterRegion edits don't reliably bubble a `changed`
## signal up to the Zone resource. Reload the scene (or re-enter the
## editor) to see edits reflected; rebuild() always reruns on _ready().

var _zone: Zone

@export var zone: Zone:
	get:
		return _zone
	set(value):
		_zone = value
		if is_inside_tree():
			rebuild()


func _ready() -> void:
	rebuild()


func rebuild() -> void:
	for child in get_children():
		remove_child(child)
		child.queue_free()
	if _zone == null:
		return
	_build_placements()
	_build_scatter()


func _build_placements() -> void:
	for placement in _zone.placements:
		if placement.scene == null:
			continue
		var instance := placement.scene.instantiate()
		add_child(instance)
		if instance is Node3D:
			var node3d := instance as Node3D
			node3d.position = placement.position
			node3d.rotation_degrees = placement.rotation_degrees
			node3d.scale = Vector3.ONE * placement.scale
		PaletteApply.apply(instance)
		if placement.solid:
			_add_collision(instance)


func _add_collision(instance: Node) -> void:
	## Auto-derives a box collider from the placement's visual mesh AABB so
	## solid props (hedges, walls, fences...) block the player without
	## every prop needing hand-authored collision geometry.
	var aabb := _visual_aabb(instance)
	if aabb.size == Vector3.ZERO:
		return
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = aabb.size
	shape.shape = box
	shape.position = aabb.get_center()
	body.add_child(shape)
	instance.add_child(body)


func _visual_aabb(instance: Node) -> AABB:
	## Local-space AABB (relative to `instance`) covering every MeshInstance3D
	## beneath it, honoring each mesh node's transform along the way.
	var result := AABB()
	var found_any := false
	for mesh_node in instance.find_children("*", "MeshInstance3D", true, false):
		var mi := mesh_node as MeshInstance3D
		if mi.mesh == null:
			continue
		var xform := Transform3D.IDENTITY
		var node: Node3D = mi
		while node != instance:
			xform = node.transform * xform
			node = node.get_parent() as Node3D
		var mesh_aabb: AABB = xform * mi.mesh.get_aabb()
		if not found_any:
			result = mesh_aabb
			found_any = true
		else:
			result = result.merge(mesh_aabb)
	return result


func _region_area(region: ScatterRegion) -> float:
	if region.shape == ScatterRegion.Shape.CIRCLE:
		return PI * region.size.x * region.size.x
	return region.size.x * region.size.y


func _build_scatter() -> void:
	var palette_material := load(PaletteApply.PALETTE_MATERIAL_PATH) as Material
	for region in _zone.scatter_regions:
		if region.variants.is_empty():
			continue
		var total := roundi(region.density * _region_area(region))
		var counts := _split_evenly(total, region.variants.size())
		for i in range(region.variants.size()):
			var count: int = counts[i]
			if count <= 0:
				continue
			var rng := RandomNumberGenerator.new()
			rng.seed = region.seed + i
			var mmi := MultiMeshInstance3D.new()
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = region.variants[i]
			mm.instance_count = count
			for instance_index in range(count):
				mm.set_instance_transform(instance_index, _random_transform(rng, region))
			mmi.multimesh = mm
			mmi.material_override = palette_material
			add_child(mmi)


func _split_evenly(total: int, variant_count: int) -> Array:
	var counts: Array = []
	counts.resize(variant_count)
	counts.fill(0)
	for i in range(total):
		counts[i % variant_count] += 1
	return counts


func _random_transform(rng: RandomNumberGenerator, region: ScatterRegion) -> Transform3D:
	var offset: Vector3
	if region.shape == ScatterRegion.Shape.CIRCLE:
		var angle := rng.randf_range(0.0, TAU)
		var radius := region.size.x * sqrt(rng.randf())
		offset = Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
	else:
		offset = Vector3(
			rng.randf_range(-region.size.x / 2.0, region.size.x / 2.0),
			0.0,
			rng.randf_range(-region.size.y / 2.0, region.size.y / 2.0),
		)
	var scale := rng.randf_range(region.scale_min, region.scale_max)
	var basis := Basis(Vector3.UP, rng.randf_range(0.0, TAU)).scaled(Vector3.ONE * scale)
	return Transform3D(basis, region.center + offset)
