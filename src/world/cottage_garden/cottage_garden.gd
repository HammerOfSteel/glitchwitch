extends Node3D
## The cottage garden — Phase 4's first tooling-built zone.

# Voice seed for the demo villager's Animalese pitch — arbitrary but fixed
# so the scene test's node lookup and screenshot captures are reproducible —
# see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §7.
const DEMO_VILLAGER_VOICE_SEED := 20260810

const DEMO_VILLAGER_MESH_PATH := "res://assets/thirdparty/meshy-ai/NPCs/villager_A_static_meshy.glb"
const DEMO_VILLAGER_DIALOGUE_PATH := "res://data/dialogue/villager_a.json"

# Same fixed-seed convention as DEMO_VILLAGER_VOICE_SEED.
const ANSEL_ROWE_VOICE_SEED := 20260813
const TORBEN_ASK_VOICE_SEED := 20260814

const ANSEL_ROWE_MESH_PATH := (
	"res://assets/thirdparty/meshy-ai/NPCs/rigged/ansel_rowe/" + "ansel_rowe.glb"
)
const ANSEL_ROWE_DIALOGUE_PATH := "res://data/dialogue/ansel_rowe.json"
const TORBEN_ASK_MESH_PATH := (
	"res://assets/thirdparty/meshy-ai/NPCs/rigged/torben_ask/" + "torben_ask.glb"
)
const TORBEN_ASK_DIALOGUE_PATH := "res://data/dialogue/torben_ask.json"

# Ansel's postal round: a loop clear of the well/crate (x=5), planters/
# fences (x=-5..-5.9), rocks, and the cottage facade (z=-4.3) — see
# hedgerow_lane.tres-style prop layout in cottage_garden.tres.
const ANSEL_ROWE_PATROL_POINTS: Array[Vector3] = [
	Vector3(2.2, 0.0, 0.5),
	Vector3(2.2, 0.0, -1.5),
	Vector3(-1.5, 0.0, -1.5),
	Vector3(-1.5, 0.0, 0.5),
]


func _ready() -> void:
	_add_demo_villager()
	_add_ansel_rowe()
	_add_torben_ask()


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


func _add_ansel_rowe() -> void:
	# Rigged+animated Meshy AI postman — walks a fixed patrol loop around
	# the garden (see src/characters/npc/rigged_npc.gd), stopping to face
	# whoever interacts with him and resuming his round once dialogue ends.
	var ansel := RiggedNpc.new()
	ansel.name = "AnselRowe"
	ansel.mesh_scene_path = ANSEL_ROWE_MESH_PATH
	ansel.display_name = "Ansel Rowe"
	ansel.dialogue_path = ANSEL_ROWE_DIALOGUE_PATH
	ansel.voice_seed = ANSEL_ROWE_VOICE_SEED
	ansel.patrol_points = ANSEL_ROWE_PATROL_POINTS
	# Start a step short of the first waypoint (not exactly on it) so he's
	# always mid-round rather than beginning each load already "arrived"
	# and paused.
	ansel.position = ANSEL_ROWE_PATROL_POINTS[0] + Vector3(0.5, 0.0, 0.0)
	add_child(ansel)


func _add_torben_ask() -> void:
	# Rigged+animated Meshy AI forester — stands still near the garden's
	# rock edge (no patrol_points), facing the garden/player.
	var torben := RiggedNpc.new()
	torben.name = "TorbenAsk"
	torben.mesh_scene_path = TORBEN_ASK_MESH_PATH
	torben.display_name = "Torben Ask"
	torben.dialogue_path = TORBEN_ASK_DIALOGUE_PATH
	torben.voice_seed = TORBEN_ASK_VOICE_SEED
	# Torben's Meshy export imports noticeably shorter than Ansel/Wren
	# (~1.46m vs. ~1.7m — see docs/character-inventory.md), which reads as
	# too small for a burly forester; scale him up to stand out.
	torben.mesh_scale = 1.5
	torben.position = Vector3(-3.5, 0.0, -3.2)
	torben.rotation.y = PI
	add_child(torben)
