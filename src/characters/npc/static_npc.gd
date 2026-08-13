class_name StaticNpc
extends Node3D
## A non-rigged, static-mesh NPC — no skeleton, no AnimationPlayer/clips.
## Its "idle" motion is a plain hand-tuned Node3D transform bob + sway
## (sine-driven position/rotation), not a bone-driven animation, since the
## source mesh (a static Meshy AI export) has none. Establishes the
## "static NPC + dialogue" asset type for background/crowd villagers —
## see docs/character-inventory.md's background-villager rows and
## docs/asset-inventory.md.
##
## Mirrors the same "Interactable child + DialogueRunner.start()" wiring
## the procedural VillagerInstance-based demo villager used
## (src/world/cottage_garden/cottage_garden.gd), so static and rigged NPCs
## can sit side by side in a zone with identical dialogue plumbing.

@export var mesh_scene_path := ""
@export var display_name := ""
@export var dialogue_path := ""
@export var voice_seed := 0

## Idle bob (vertical) and sway (yaw) tuning — small enough to read as
## "breathing/shifting weight," not an obvious mechanical wobble.
@export var bob_height := 0.03
@export var bob_speed := 1.1
@export var sway_degrees := 1.5
@export var sway_speed := 0.8

var _mesh_root: Node3D
var _time := 0.0
# Per-instance phase offset so multiple static NPCs in the same scene
# don't all bob/sway in perfect unison.
var _phase := 0.0


func _ready() -> void:
	_phase = randf() * TAU
	if mesh_scene_path.is_empty():
		push_warning("StaticNpc has no mesh_scene_path set")
	else:
		var packed := load(mesh_scene_path) as PackedScene
		if packed == null:
			push_warning("StaticNpc mesh unavailable: %s" % mesh_scene_path)
		else:
			_mesh_root = packed.instantiate() as Node3D
			add_child(_mesh_root)
	var talk := Interactable.new()
	talk.verb = "Talk"
	talk.display_name = display_name
	add_child(talk)
	talk.interacted.connect(_on_interacted)


func _process(delta: float) -> void:
	if _mesh_root == null:
		return
	_time += delta
	_mesh_root.position.y = sin(_time * bob_speed + _phase) * bob_height
	_mesh_root.rotation.y = deg_to_rad(sway_degrees) * sin(_time * sway_speed + _phase)


func _on_interacted(by: Node) -> void:
	if dialogue_path.is_empty():
		return
	var graph := DialogueGraph.load_from_file(dialogue_path)
	if graph == null:
		push_error("%s failed to load/validate" % dialogue_path)
		return
	var player := by as Player
	if player != null:
		player.input_enabled = false
	DialogueRunner.start(graph, voice_seed)
