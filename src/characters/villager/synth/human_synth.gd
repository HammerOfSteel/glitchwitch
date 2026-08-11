class_name HumanSynth
extends RefCounted
## The only BodySynthesizer implementation in v1 (human archetype). A thin
## pass-through to VillagerRig.build() — see
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §3. Kept
## separate from VillagerRig so a future archetype (bird/quadruped/small-
## creature — out of scope this phase) has a stable seam to implement
## alongside this one without VillagerFactory needing to change.


static func build(dna: VillagerDna) -> VillagerBuildResult:
	var rig := VillagerRig.build(dna)
	var result := VillagerBuildResult.new()
	result.root = rig.root
	result.rig = rig
	result.sockets = rig.sockets
	return result
