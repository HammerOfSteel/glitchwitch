class_name VillagerFactory
extends RefCounted
## The single entry point other code should use to create a villager.
## See docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §6.


static func build(dna: VillagerDna) -> VillagerInstance:
	var result := HumanSynth.build(dna)
	var instance := VillagerInstance.new()
	instance.name = dna.name
	instance._setup(result.rig)
	PaletteApply.apply(instance)
	return instance
