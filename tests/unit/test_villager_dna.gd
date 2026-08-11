extends GdUnitTestSuite
## VillagerDna: deterministic seeded random(), values in documented ranges.


func test_random_is_deterministic_for_same_seed() -> void:
	var a := VillagerDna.random(42)
	var b := VillagerDna.random(42)
	assert_float(a.height_scale).is_equal(b.height_scale)
	assert_float(a.build_scale).is_equal(b.build_scale)
	assert_str(String(a.skin_ramp)).is_equal(String(b.skin_ramp))
	assert_str(String(a.hair_ramp)).is_equal(String(b.hair_ramp))
	assert_str(String(a.clothing_ramp)).is_equal(String(b.clothing_ramp))
	assert_str(a.name).is_equal(b.name)


func test_different_seeds_can_differ() -> void:
	# Not a strict guarantee for every possible pair, but seeds 1 and 2
	# must differ in at least one field for the RNG wiring to be real
	# (a constant-DNA bug would make every seed identical).
	var a := VillagerDna.random(1)
	var b := VillagerDna.random(2)
	var identical := (
		a.height_scale == b.height_scale
		and a.build_scale == b.build_scale
		and a.skin_ramp == b.skin_ramp
		and a.hair_ramp == b.hair_ramp
		and a.clothing_ramp == b.clothing_ramp
	)
	assert_bool(identical).override_failure_message(
		"seeds 1 and 2 produced identical DNA — RNG isn't seeded correctly"
	).is_false()


func test_scales_are_within_documented_range() -> void:
	for seed in range(20):
		var dna := VillagerDna.random(seed)
		assert_float(dna.height_scale).is_greater_equal(0.85)
		assert_float(dna.height_scale).is_less_equal(1.15)
		assert_float(dna.build_scale).is_greater_equal(0.85)
		assert_float(dna.build_scale).is_less_equal(1.15)


func test_ramps_are_drawn_from_allow_lists() -> void:
	for seed in range(20):
		var dna := VillagerDna.random(seed)
		assert_bool(VillagerDna.SKIN_RAMPS.has(dna.skin_ramp)).is_true()
		assert_bool(VillagerDna.HAIR_RAMPS.has(dna.hair_ramp)).is_true()
		assert_bool(VillagerDna.CLOTHING_RAMPS.has(dna.clothing_ramp)).is_true()


func test_seed_is_retained_and_hairstyle_is_fixed_v1_value() -> void:
	var dna := VillagerDna.random(42)
	assert_int(dna.seed).is_equal(42)
	assert_str(String(dna.hairstyle)).is_equal("bob")
