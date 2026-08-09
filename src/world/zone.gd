class_name Zone
extends Resource
## Data-only description of a walkable zone: its footprint, discrete prop
## placements, and scatter regions. No behavior — ZoneBuilder turns this
## into actual nodes. Diffable, editable in the Inspector as a .tres file.

@export var ground_size := Vector2.ZERO
@export var placements: Array[PropPlacement] = []
@export var scatter_regions: Array[ScatterRegion] = []
