extends GdUnitTestSuite
## Animalese: procedural per-seed blip synthesis. See
## docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §5.

const Animalese = preload("res://src/core/animalese.gd")


func test_same_seed_returns_identical_pcm_data() -> void:
	var a := Animalese.blip_for_seed(7)
	var b := Animalese.blip_for_seed(7)
	assert_array(a.data).is_equal(b.data)


func test_same_seed_returns_same_cached_instance() -> void:
	var a := Animalese.blip_for_seed(11)
	var b := Animalese.blip_for_seed(11)
	assert_object(a).is_same(b)


func test_different_seeds_produce_different_pitches() -> void:
	# Compare actual pitch (zero-crossing rate), not just raw PCM difference —
	# proves the seeds produce audibly different frequencies, not merely
	# different-but-same-pitch waveforms.
	var a := Animalese.blip_for_seed(1)
	var b := Animalese.blip_for_seed(2)
	assert_int(Animalese._zero_crossings(a)).is_not_equal(Animalese._zero_crossings(b))


func test_blip_is_short_mono_16bit() -> void:
	var blip := Animalese.blip_for_seed(3)
	assert_int(blip.stereo as int).is_equal(0)
	assert_int(blip.format).is_equal(AudioStreamWAV.FORMAT_16_BITS)
	assert_float(float(blip.mix_rate)).is_equal_approx(22050.0, 0.1)
