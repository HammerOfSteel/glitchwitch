extends GdUnitTestSuite
## HumanSynth: thin BodySynthesizer-shaped wrapper around VillagerRig.build().


func test_build_returns_result_bundling_root_rig_and_sockets() -> void:
	var dna := VillagerDna.random(9)
	var result := HumanSynth.build(dna)
	auto_free(result.root)
	assert_object(result.root).is_not_null()
	assert_object(result.rig).is_not_null()
	assert_object(result.root).is_equal(result.rig.root)
	assert_bool(result.sockets.has(&"head_top")).is_true()
	assert_bool(result.sockets.has(&"hand_l")).is_true()
	assert_bool(result.sockets.has(&"hand_r")).is_true()
