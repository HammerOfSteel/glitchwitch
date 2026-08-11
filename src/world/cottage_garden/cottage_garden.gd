extends Node3D
## The cottage garden — Phase 4's first tooling-built zone.

# Fixed seed so the scene test's node lookup and screenshot captures are
# reproducible — see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §7.
const DEMO_VILLAGER_SEED := 20260810


func _ready() -> void:
	_stage()
	_add_demo_villager()


func _stage() -> void:
	var sun := get_node_or_null("Sun") as DirectionalLight3D
	if sun != null:
		sun.rotation_degrees = Vector3(-48.0, -32.0, 0.0)
		sun.light_color = Color(1.0, 0.93, 0.82)
		sun.light_energy = 1.25
		sun.shadow_enabled = true
	var fill := get_node_or_null("Fill") as DirectionalLight3D
	if fill != null:
		fill.rotation_degrees = Vector3(-20.0, 141.0, 0.0)
		fill.light_color = Color(0.68, 0.78, 0.92)
		fill.light_energy = 0.35


func _add_demo_villager() -> void:
	var dna := VillagerDna.random(DEMO_VILLAGER_SEED)
	var villager := VillagerFactory.build(dna)
	villager.name = "DemoVillager"
	# Near the well, facing the cottage — a static proof-of-concept only,
	# no interaction/dialogue/AI (that's future gameplay-phase work).
	villager.position = Vector3(1.6, 0.0, 2.2)
	add_child(villager)
