class_name RiggedNpc
extends Node3D
## A rigged+animated background NPC — skeleton, skinned mesh, and idle/walk
## clips, driven by a Meshy AI export merged via
## tools/assetgen/meshy_import/import_meshy_rigged_npc.py (the same
## idle/walk/run-only clip set WrenAvatar uses — see
## src/player/avatar.gd and tools/assetgen/meshy_import/merge_meshy_rigged_npc.py).
##
## The animated counterpart to StaticNpc (src/characters/npc/static_npc.gd)
## for background NPCs whose Meshy source *does* ship bones/clips (Ansel
## Rowe, Torben Ask — see docs/character-inventory.md), rather than a plain
## static mesh. Mirrors the same "Interactable child + DialogueRunner.start()"
## wiring so rigged and static NPCs plug into a zone identically.
##
## Optionally patrols a fixed loop of waypoints (parent-local positions,
## e.g. Ansel Rowe's postal round through the cottage garden) — walking
## between them with the "walk" clip and pausing briefly at each one — and
## stops to face whoever interacts with it mid-patrol, resuming once
## dialogue ends. Leave patrol_points empty for a stationary NPC that just
## idles in place (e.g. Torben Ask).

enum State { PATROLLING, TALKING }

@export var mesh_scene_path := ""
@export var display_name := ""
@export var dialogue_path := ""
@export var voice_seed := 0
@export var idle_clip := "idle"
@export var walk_clip := "walk"

## Uniform scale applied to the instanced mesh body. Meshy AI exports vary
## in their character's real-world height (e.g. Torben Ask imports ~1.46m
## tall vs. Ansel Rowe/Wren's ~1.7m — see docs/character-inventory.md), so
## this lets a zone author size an individual NPC without touching the
## source asset.
@export var mesh_scale := 1.0

## Parent-local waypoints to loop through, in order. Empty means "stand
## still and idle" (no patrol).
@export var patrol_points: Array[Vector3] = []
@export var patrol_speed := 1.2
@export var patrol_wait_time := 1.5
@export var waypoint_arrival_threshold := 0.05

var _anim: AnimationPlayer = null
var _state: State = State.PATROLLING
var _patrol_index := 0
var _wait_timer := 0.0


func _ready() -> void:
	if mesh_scene_path.is_empty():
		push_warning("RiggedNpc has no mesh_scene_path set")
	else:
		var packed := load(mesh_scene_path) as PackedScene
		if packed == null:
			push_warning("RiggedNpc mesh unavailable: %s" % mesh_scene_path)
		else:
			var body := packed.instantiate() as Node3D
			add_child(body)
			# Meshy AI exports' rest pose faces +Z (its own "front"), same
			# convention WrenAvatar corrects for (src/player/avatar.gd) —
			# without this the NPC stands facing backward relative to how
			# a zone author would naturally place it.
			body.rotation.y = PI
			body.scale = Vector3.ONE * mesh_scale
			var players := body.find_children("*", "AnimationPlayer", true, false)
			if not players.is_empty():
				_anim = players[0] as AnimationPlayer
	var talk := Interactable.new()
	talk.verb = "Talk"
	talk.display_name = display_name
	add_child(talk)
	talk.interacted.connect(_on_interacted)
	DialogueRunner.ended.connect(_on_dialogue_ended)
	_play_clip(idle_clip)


func _process(delta: float) -> void:
	if _state != State.PATROLLING or patrol_points.is_empty():
		return
	_process_patrol(delta)


## Walks toward the current waypoint, facing the direction of travel, and
## advances to the next one (pausing briefly to idle) once close enough —
## looping back to the first waypoint after the last.
func _process_patrol(delta: float) -> void:
	if _wait_timer > 0.0:
		_wait_timer -= delta
		return
	var target: Vector3 = patrol_points[_patrol_index]
	var to_target := target - position
	to_target.y = 0.0
	var distance := to_target.length()
	if distance <= waypoint_arrival_threshold:
		_patrol_index = (_patrol_index + 1) % patrol_points.size()
		_wait_timer = patrol_wait_time
		_play_clip(idle_clip)
		return
	var direction := to_target.normalized()
	var step := patrol_speed * delta
	if step >= distance:
		position = Vector3(target.x, position.y, target.z)
	else:
		position += direction * step
	look_at(global_position + direction, Vector3.UP)
	_play_clip(walk_clip)


func _on_interacted(by: Node) -> void:
	if dialogue_path.is_empty():
		return
	var graph := DialogueGraph.load_from_file(dialogue_path)
	if graph == null:
		push_error("%s failed to load/validate" % dialogue_path)
		return
	_state = State.TALKING
	_play_clip(idle_clip)
	var actor := by as Node3D
	if actor != null:
		var look_target := actor.global_position
		look_target.y = global_position.y
		if not look_target.is_equal_approx(global_position):
			look_at(look_target, Vector3.UP)
	var player := by as Player
	if player != null:
		player.input_enabled = false
	DialogueRunner.start(graph, voice_seed)


func _on_dialogue_ended() -> void:
	if _state == State.TALKING:
		_state = State.PATROLLING


func _play_clip(clip_name: String) -> void:
	if _anim == null:
		return
	if _anim.current_animation == clip_name and _anim.is_playing():
		return
	if _anim.has_animation(clip_name):
		_anim.play(clip_name)
	else:
		push_warning("RiggedNpc: clip %s not found in %s" % [clip_name, mesh_scene_path])
