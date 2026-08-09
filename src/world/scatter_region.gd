class_name ScatterRegion
extends Resource
## A seeded, deterministic scatter patch: a pool of mesh variants filling
## a circle or rect area at a target density (instances per m²).
##
## `variants` are plain `Mesh` resources, not PackedScenes — a MultiMesh
## renders one mesh/material per instance batch, so ZoneBuilder makes one
## MultiMeshInstance3D per variant, not per placement or per pool.

enum Shape { CIRCLE, RECT }

@export var variants: Array[Mesh] = []
@export var shape := Shape.CIRCLE
@export var center := Vector3.ZERO
## For CIRCLE: size.x is the radius (size.y unused).
## For RECT: size.x is width, size.y is depth.
@export var size := Vector2.ZERO
@export var density := 0.0  ## instances per square meter
@export var scale_min := 1.0
@export var scale_max := 1.0
@export var seed := 0
