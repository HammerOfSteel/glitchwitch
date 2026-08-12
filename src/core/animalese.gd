class_name Animalese
extends RefCounted
## Procedural "small critter chatter" blip synthesis for dialogue voices.
## Stateless generator (same shape as TimeOfDayCurve) — no autoload needed.
## See docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §5.

const SAMPLE_RATE := 22050
const DURATION_SEC := 0.06
const MIN_FREQ_HZ := 180.0
const MAX_FREQ_HZ := 420.0

static var _cache: Dictionary = {}  # int -> AudioStreamWAV


## Returns a cached (or newly synthesized) short sine-burst blip pitched
## deterministically from `seed`. Same seed always returns the exact same
## AudioStreamWAV instance.
static func blip_for_seed(seed: int) -> AudioStreamWAV:
	if _cache.has(seed):
		return _cache[seed]
	var rng := RandomNumberGenerator.new()
	rng.seed = seed
	var freq: float = rng.randf_range(MIN_FREQ_HZ, MAX_FREQ_HZ)
	var sample_count := int(SAMPLE_RATE * DURATION_SEC)
	var data := PackedByteArray()
	data.resize(sample_count * 2)  # 16-bit mono
	for i in sample_count:
		var t := float(i) / SAMPLE_RATE
		var envelope := 1.0 - (float(i) / sample_count)  # simple linear decay
		var sample := sin(TAU * freq * t) * envelope
		var pcm := int(clamp(sample, -1.0, 1.0) * 32767.0)
		data.encode_s16(i * 2, pcm)
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = SAMPLE_RATE
	stream.stereo = false
	stream.data = data
	_cache[seed] = stream
	return stream


## Counts sign changes across the decoded 16-bit PCM samples — a simple,
## test-only proxy for "how many times the wave crossed zero", which rises
## with frequency. Used by test_animalese.gd to prove two seeds produce
## audibly different pitches, not just different-but-same-pitch data.
static func _zero_crossings(stream: AudioStreamWAV) -> int:
	var crossings := 0
	var previous := 0
	for i in stream.data.size() / 2:
		var sample := stream.data.decode_s16(i * 2)
		if previous != 0 and sign(sample) != sign(previous) and sample != 0:
			crossings += 1
		if sample != 0:
			previous = sample
	return crossings
