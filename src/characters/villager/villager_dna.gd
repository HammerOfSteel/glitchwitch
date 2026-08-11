class_name VillagerDna
extends RefCounted
## A villager's generation "genome" — deterministic from a seed, drives
## HumanSynth/VillagerRig. See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §1.
##
## Ramp allow-lists are a small, deliberate v1 subset of the full palette
## (tools/assetgen/palette.py's RAMPS) chosen to look plausible for skin/
## hair/clothing — not exhaustive, easy to extend later.
const SKIN_RAMPS: Array[StringName] = [&"cream", &"honey", &"clay", &"rust"]
const HAIR_RAMPS: Array[StringName] = [&"bark", &"wood", &"void_plum", &"metal"]
const CLOTHING_RAMPS: Array[StringName] = [
	&"rust", &"honey", &"moss", &"water", &"sky", &"clay", &"metal", &"ceramic",
]
const NAME_SYLLABLES := [
	"Ash", "Bram", "Cael", "Dor", "El", "Fen", "Gil", "Hol", "Ives", "Jor",
]

var seed: int
var name: String
var height_scale: float
var build_scale: float
var skin_ramp: StringName
var hair_ramp: StringName
var clothing_ramp: StringName
var hairstyle: StringName = &"bob"  # only one exists in v1


static func random(from_seed: int) -> VillagerDna:
	var rng := RandomNumberGenerator.new()
	rng.seed = from_seed
	var dna := VillagerDna.new()
	dna.seed = from_seed
	dna.height_scale = rng.randf_range(0.85, 1.15)
	dna.build_scale = rng.randf_range(0.85, 1.15)
	dna.skin_ramp = SKIN_RAMPS[rng.randi_range(0, SKIN_RAMPS.size() - 1)]
	dna.hair_ramp = HAIR_RAMPS[rng.randi_range(0, HAIR_RAMPS.size() - 1)]
	dna.clothing_ramp = CLOTHING_RAMPS[rng.randi_range(0, CLOTHING_RAMPS.size() - 1)]
	dna.name = (
		NAME_SYLLABLES[rng.randi_range(0, NAME_SYLLABLES.size() - 1)]
		+ NAME_SYLLABLES[rng.randi_range(0, NAME_SYLLABLES.size() - 1)].to_lower()
	)
	return dna
