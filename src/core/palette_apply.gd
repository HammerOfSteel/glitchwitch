class_name PaletteApply
extends RefCounted
## Dresses any subtree in the palette toon material.
##
## Generated GLBs carry no materials by design (the palette is the single
## source of color truth); every consumer applies this override on ready.

const PALETTE_MATERIAL_PATH := "res://src/materials/palette_main.tres"
## Same toon shading, no inverted-hull outline pass. The outline technique
## extrudes+cull-fronts a copy of the mesh to fake a silhouette edge, which
## only works for closed volumes — on paper-thin single-layer cards (grass,
## flower petals) it instead paints the whole card black from one side.
## Scatter foliage uses this material instead of PALETTE_MATERIAL_PATH.
const PALETTE_SCATTER_MATERIAL_PATH := "res://src/materials/palette_scatter.tres"


static func apply(root: Node) -> void:
	var material := load(PALETTE_MATERIAL_PATH) as Material
	if material == null:
		push_warning("palette material unavailable — run `make assets` first")
		return
	for found in root.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.material_override == null:
			mesh_instance.material_override = material
