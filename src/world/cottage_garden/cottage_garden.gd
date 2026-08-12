extends Node3D
## The cottage garden — Phase 4's first tooling-built zone.

# Fixed seed so the scene test's node lookup and screenshot captures are
# reproducible — see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §7.
const DEMO_VILLAGER_SEED := 20260810


func _ready() -> void:
	_add_demo_villager()


func _add_demo_villager() -> void:
	var dna := VillagerDna.random(DEMO_VILLAGER_SEED)
	var villager := VillagerFactory.build(dna)
	villager.name = "DemoVillager"
	# Near the well, facing the cottage.
	villager.position = Vector3(1.6, 0.0, 2.2)
	add_child(villager)
	var talk := Interactable.new()
	talk.verb = "Talk"
	talk.display_name = dna.name
	villager.add_child(talk)
	talk.interacted.connect(_on_demo_villager_interacted.bind(dna.seed))


func _on_demo_villager_interacted(by: Node, voice_seed: int) -> void:
	var graph := DialogueGraph.load_from_file("res://data/dialogue/demo_villager.json")
	if graph == null:
		push_error("demo_villager.json failed to load/validate")
		return
	var player := by as Player
	if player != null:
		player.input_enabled = false
	DialogueRunner.start(graph, voice_seed)
