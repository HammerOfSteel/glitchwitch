extends Node3D
## The cottage garden — Phase 4's first tooling-built zone.

# Voice seed for the demo villager's Animalese pitch — arbitrary but fixed
# so the scene test's node lookup and screenshot captures are reproducible —
# see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §7.
const DEMO_VILLAGER_VOICE_SEED := 20260810

const DEMO_VILLAGER_MESH_PATH := "res://assets/thirdparty/meshy-ai/NPCs/villager_A_static_meshy.glb"
const DEMO_VILLAGER_DIALOGUE_PATH := "res://data/dialogue/villager_a.json"


func _ready() -> void:
	_add_demo_villager()


func _add_demo_villager() -> void:
	# Static (non-rigged) Meshy AI background villager — establishes the
	## "static NPC + dialogue" asset type (see src/characters/npc/static_npc.gd)
	# alongside the procedural VillagerFactory rig used elsewhere.
	var villager := StaticNpc.new()
	villager.name = "DemoVillager"
	villager.mesh_scene_path = DEMO_VILLAGER_MESH_PATH
	villager.display_name = "Villager"
	villager.dialogue_path = DEMO_VILLAGER_DIALOGUE_PATH
	villager.voice_seed = DEMO_VILLAGER_VOICE_SEED
	# Near the well, facing the cottage.
	villager.position = Vector3(1.6, 0.0, 2.2)
	add_child(villager)
