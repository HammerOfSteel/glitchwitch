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
	# Near the well, facing the cottage — a static proof-of-concept only,
	# no interaction/dialogue/AI (that's future gameplay-phase work).
	villager.position = Vector3(1.6, 0.0, 2.2)
	add_child(villager)
