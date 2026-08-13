extends Node3D
## The hedgerow lane — Phase 4's village dressing first pass.
## Also hosts the game's first rigged+animated background NPCs (Ansel
## Rowe the postman, Torben Ask the forester — see
## docs/character-inventory.md), alongside the cottage garden's static
## NPC type (src/characters/npc/static_npc.gd). See
## src/characters/npc/rigged_npc.gd.

# Voice seeds — arbitrary but fixed so scene tests/screenshots stay
# reproducible, matching cottage_garden.gd's DEMO_VILLAGER_VOICE_SEED
# convention.
const ANSEL_ROWE_VOICE_SEED := 20260813
const TORBEN_ASK_VOICE_SEED := 20260814

const ANSEL_ROWE_MESH_PATH := "res://assets/thirdparty/meshy-ai/NPCs/rigged/ansel_rowe/ansel_rowe.glb"
const ANSEL_ROWE_DIALOGUE_PATH := "res://data/dialogue/ansel_rowe.json"
const TORBEN_ASK_MESH_PATH := "res://assets/thirdparty/meshy-ai/NPCs/rigged/torben_ask/torben_ask.glb"
const TORBEN_ASK_DIALOGUE_PATH := "res://data/dialogue/torben_ask.json"


func _ready() -> void:
	_add_rigged_npc(
		"AnselRowe",
		ANSEL_ROWE_MESH_PATH,
		"Ansel Rowe",
		ANSEL_ROWE_DIALOGUE_PATH,
		ANSEL_ROWE_VOICE_SEED,
		Vector3(-1.2, 0.0, 1.5)
	)
	_add_rigged_npc(
		"TorbenAsk",
		TORBEN_ASK_MESH_PATH,
		"Torben Ask",
		TORBEN_ASK_DIALOGUE_PATH,
		TORBEN_ASK_VOICE_SEED,
		Vector3(1.4, 0.0, -1.8)
	)


func _add_rigged_npc(
	node_name: String,
	mesh_path: String,
	display_name: String,
	dialogue_path: String,
	voice_seed: int,
	pos: Vector3
) -> void:
	var npc := RiggedNpc.new()
	npc.name = node_name
	npc.mesh_scene_path = mesh_path
	npc.display_name = display_name
	npc.dialogue_path = dialogue_path
	npc.voice_seed = voice_seed
	npc.position = pos
	add_child(npc)
