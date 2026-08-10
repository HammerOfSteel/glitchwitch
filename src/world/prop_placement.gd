class_name PropPlacement
extends Resource
## One discrete prop instance in a Zone: which scene, where, how big.

@export var scene: PackedScene
@export var position := Vector3.ZERO
@export var rotation_degrees := Vector3.ZERO
@export var scale := 1.0
## Opt-in: when true, ZoneBuilder auto-derives a box collider from this
## placement's visual mesh AABB (walls, hedges, fences...) so the player
## can't walk through it. Off by default — most props (rugs, flowers,
## interior clutter) should stay purely decorative/walk-through.
@export var solid := false
