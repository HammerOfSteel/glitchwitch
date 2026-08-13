class_name RiggedNpc
extends Node3D
## A rigged+animated background NPC — skeleton, skinned mesh, and a looping
## "idle" clip, driven by a Meshy AI export merged via
## tools/assetgen/meshy_import/import_meshy_rigged_npc.py (the same
## idle/walk/run-only clip set WrenAvatar uses — see
## src/player/avatar.gd and tools/assetgen/meshy_import/merge_meshy_rigged_npc.py).
##
## The animated counterpart to StaticNpc (src/characters/npc/static_npc.gd)
## for background NPCs whose Meshy source *does* ship bones/clips (Ansel
## Rowe, Torben Ask — see docs/character-inventory.md), rather than a plain
## static mesh. Mirrors the same "Interactable child + DialogueRunner.start()"
## wiring so rigged and static NPCs plug into a zone identically.

@export var mesh_scene_path := ""
@export var display_name := ""
@export var dialogue_path := ""
@export var voice_seed := 0
@export var idle_clip := "idle"

var _anim: AnimationPlayer = null


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
			var players := body.find_children("*", "AnimationPlayer", true, false)
			if not players.is_empty():
				_anim = players[0] as AnimationPlayer
				if _anim.has_animation(idle_clip):
					_anim.play(idle_clip)
				else:
					push_warning(
						"RiggedNpc: clip %s not found in %s" % [idle_clip, mesh_scene_path]
					)
	var talk := Interactable.new()
	talk.verb = "Talk"
	talk.display_name = display_name
	add_child(talk)
	talk.interacted.connect(_on_interacted)


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
