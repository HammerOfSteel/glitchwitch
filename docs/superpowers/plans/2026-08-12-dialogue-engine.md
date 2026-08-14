# Dialogue Engine (T5.1) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a data-driven dialogue engine (JSON graphs, conditions, choices, procedural portraits, animalese blip audio) and prove it end-to-end by wiring a demo conversation to the existing `DemoVillager` in `cottage_garden`.

**Architecture:** A `DialogueRunner` autoload (mirrors the `GameClock` pattern) owns the pure state machine over a `DialogueGraph` data object; a decoupled `DialogueBox` UI scene (instanced under `Player`'s `HUD`) drives itself purely off `DialogueRunner`'s signals; a stateless `Animalese` helper synthesizes the blip audio. The demo villager's `Interactable` (built at runtime, like the villager itself) is the only piece of "content" wiring.

**Tech Stack:** Godot 4.7 / GDScript, gdUnit4 for tests, existing autoload/naming conventions from `GameClockService`/`GameClock`.

**Full design spec (read before starting):** `docs/superpowers/specs/2026-08-12-dialogue-engine-design.md`

**Godot binary for all commands below:** `/Applications/Godot.app/Contents/MacOS/Godot --headless --path .`
This repo's documented convention is `.tooling/godot` (see `README.md`/`Makefile`) — use that binary if it's a working native executable for your platform. In this environment specifically, `.tooling/godot` is a Linux ELF binary that cannot execute on this macOS sandbox, so the full macOS app path above is used instead. Substitute whichever binary actually runs on your machine; the `-s addons/gdUnit4/bin/GdUnitCmdTool.gd -a <path> --ignoreHeadlessMode` arguments are the same either way (mirrors the repo's own `make test-godot` target).

---

## Chunk 1: Core data & runtime (`DialogueGraph`, `DialogueRunner`)

### Task 1: `DialogueGraph` — load & validate JSON dialogue data

**Files:**
- Create: `src/core/dialogue_graph.gd`
- Create: `tests/unit/test_dialogue_graph.gd`

- [ ] **Step 1: Write the failing tests**

```gdscript
extends GdUnitTestSuite
## DialogueGraph: loads/validates data/dialogue/*.json. See
## docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §2.

const VALID_JSON := """
{
  "start": "greet",
  "nodes": {
    "greet": {
      "speaker": "Villager",
      "text": "Oh! You're the one from the cottage.",
      "condition": { "flag": "talked_to_villager", "equals": true },
      "next": "chat_repeat",
      "else": "ask_weather"
    },
    "ask_weather": {
      "speaker": "Villager",
      "text": "Fancy some small talk?",
      "choices": [
        { "text": "Sure.", "next": "chat", "set_flag": "talked_to_villager" },
        { "text": "Not now.", "next": null }
      ]
    },
    "chat": {
      "speaker": "Villager",
      "text": "The moss has been doing well this week.",
      "next": null
    },
    "chat_repeat": {
      "speaker": "Villager",
      "text": "Back again? The moss is still doing wonderfully.",
      "next": null
    }
  }
}
"""


func test_parses_valid_graph() -> void:
	var graph := DialogueGraph._parse(JSON.parse_string(VALID_JSON))
	assert_object(graph).is_not_null()
	assert_str(graph.start).is_equal("greet")
	assert_bool(graph.nodes.has("greet")).is_true()
	assert_bool(graph.nodes.has("chat_repeat")).is_true()


func test_rejects_missing_start_node() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["start"] = "nonexistent"
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_dangling_next_reference() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["chat"]["next"] = "nowhere"
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_dangling_else_reference() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["greet"]["else"] = "nowhere"
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_dangling_choice_next_reference() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["ask_weather"]["choices"][0]["next"] = "nowhere"
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_node_with_both_next_and_choices() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["chat"]["choices"] = [{ "text": "ok", "next": null }]
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_node_missing_speaker() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["chat"].erase("speaker")
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_node_with_empty_speaker() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["chat"]["speaker"] = ""
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_node_missing_text() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["chat"].erase("text")
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_rejects_node_with_empty_text() -> void:
	var data: Dictionary = JSON.parse_string(VALID_JSON)
	data["nodes"]["chat"]["text"] = ""
	var graph := DialogueGraph._parse(data)
	assert_object(graph).is_null()


func test_load_from_file_returns_null_for_missing_file() -> void:
	var graph := DialogueGraph.load_from_file("res://data/dialogue/does_not_exist.json")
	assert_object(graph).is_null()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_dialogue_graph.gd`
Expected: FAIL — `DialogueGraph` class not found / `Nonexistent function '_parse'`.

- [ ] **Step 3: Write `DialogueGraph`**

```gdscript
class_name DialogueGraph
extends RefCounted
## Loads and validates a branching dialogue JSON graph. See
## docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §2 for the
## full data format. Mirrors PaletteUv's "degrade via push_error, return
## null" convention rather than crashing on malformed content.

var start: String
var nodes: Dictionary  # String -> Dictionary (raw node data)


## Loads and parses the JSON at `path`, returning a validated DialogueGraph,
## or null (with a push_error) if the file is missing/unreadable/invalid.
static func load_from_file(path: String) -> DialogueGraph:
	if not FileAccess.file_exists(path):
		push_error("DialogueGraph: file not found: %s" % path)
		return null
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_error("DialogueGraph: could not open %s (err %d)" % [path, FileAccess.get_open_error()])
		return null
	var parsed = JSON.parse_string(file.get_as_text())
	if parsed == null or not (parsed is Dictionary):
		push_error("DialogueGraph: %s is not valid JSON" % path)
		return null
	return _parse(parsed)


## Validates a parsed JSON Dictionary into a DialogueGraph, or returns null
## (with a push_error describing the violation) if any of §2's structural
## rules are broken. Split out from load_from_file so tests can exercise
## validation directly with in-memory fixtures instead of writing files.
static func _parse(data: Dictionary) -> DialogueGraph:
	if not data.has("start") or not data.has("nodes"):
		push_error("DialogueGraph: missing 'start' or 'nodes'")
		return null
	var nodes = data["nodes"]
	if not (nodes is Dictionary):
		push_error("DialogueGraph: 'nodes' must be an object")
		return null
	var start: String = data["start"]
	if not nodes.has(start):
		push_error("DialogueGraph: start node '%s' not found" % start)
		return null
	for node_id in nodes.keys():
		var error := _validate_node(node_id, nodes[node_id], nodes)
		if not error.is_empty():
			push_error("DialogueGraph: %s" % error)
			return null
	var graph := DialogueGraph.new()
	graph.start = start
	graph.nodes = nodes
	return graph


## Returns an empty string if `node` is well-formed, otherwise a
## human-readable description of the violation.
static func _validate_node(node_id: String, node: Variant, all_nodes: Dictionary) -> String:
	if not (node is Dictionary):
		return "node '%s' must be an object" % node_id
	if not node.has("speaker") or String(node["speaker"]).is_empty():
		return "node '%s' missing non-empty 'speaker'" % node_id
	if not node.has("text") or String(node["text"]).is_empty():
		return "node '%s' missing non-empty 'text'" % node_id
	var has_next: bool = node.has("next")
	var has_choices: bool = node.has("choices")
	if has_next and has_choices:
		return "node '%s' cannot have both 'next' and 'choices'" % node_id
	if has_next and not _valid_next_ref(node["next"], all_nodes):
		return "node '%s' has dangling 'next' reference" % node_id
	if node.has("else") and not _valid_next_ref(node["else"], all_nodes):
		return "node '%s' has dangling 'else' reference" % node_id
	if has_choices:
		if not (node["choices"] is Array):
			return "node '%s' 'choices' must be an array" % node_id
		for choice in node["choices"]:
			if not (choice is Dictionary) or not choice.has("text") or not choice.has("next"):
				return "node '%s' has a malformed choice entry" % node_id
			if not _valid_next_ref(choice["next"], all_nodes):
				return "node '%s' has a choice with dangling 'next' reference" % node_id
	return ""


## A "next"/"else"/choice-next reference is valid if it's null (ends the
## conversation) or names an existing node.
static func _valid_next_ref(ref: Variant, all_nodes: Dictionary) -> bool:
	return ref == null or (ref is String and all_nodes.has(ref))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_dialogue_graph.gd`
Expected: PASS (11/11)

- [ ] **Step 5: Commit**

```bash
git add src/core/dialogue_graph.gd tests/unit/test_dialogue_graph.gd
git commit -m "feat(dialogue): add DialogueGraph JSON loader/validator"
```

### Task 2: `DialogueRunner` — state machine autoload

**Files:**
- Create: `src/core/dialogue_runner.gd`
- Modify: `project.godot` (`[autoload]` section)
- Create: `tests/unit/test_dialogue_runner.gd`

- [ ] **Step 1: Write the failing tests**

```gdscript
extends GdUnitTestSuite
## DialogueRunner: the autoload state machine over a DialogueGraph. See
## docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §3.

const FIXTURE_JSON := """
{
  "start": "greet",
  "nodes": {
    "greet": {
      "speaker": "Villager",
      "text": "Oh! You're the one from the cottage.",
      "condition": { "flag": "talked_to_villager", "equals": true },
      "next": "chat_repeat",
      "else": "ask_weather"
    },
    "ask_weather": {
      "speaker": "Villager",
      "text": "Fancy some small talk?",
      "choices": [
        { "text": "Sure.", "next": "chat", "set_flag": "talked_to_villager" },
        { "text": "Not now.", "next": null }
      ]
    },
    "chat": {
      "speaker": "Villager",
      "text": "The moss has been doing well this week.",
      "next": null
    },
    "chat_repeat": {
      "speaker": "Villager",
      "text": "Back again? The moss is still doing wonderfully.",
      "next": null
    }
  }
}
"""


func after_test() -> void:
	# DialogueRunner is a real autoload shared across the whole test run;
	# reset unconditionally so a failed assertion above can't leak stale
	# flags/state into unrelated tests run later in the same suite.
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""
	DialogueRunner._voice_seed = 0


func _fixture_graph() -> DialogueGraph:
	return DialogueGraph._parse(JSON.parse_string(FIXTURE_JSON))


func test_start_on_first_encounter_emits_choices_shown_via_else_branch() -> void:
	# greet's condition (talked_to_villager equals true) is false on a fresh
	# runner. Per §3's resolution algorithm, a false condition recurses
	# straight into "else" and returns *without* displaying the gated node
	# itself — so ask_weather's choices_shown fires immediately on start(),
	# greet's own line is never shown on this path at all.
	var lines: Array[String] = []
	var choice_events: Array[String] = []
	DialogueRunner.line_shown.connect(
		func(_speaker: String, text: String) -> void: lines.append(text)
	)
	DialogueRunner.choices_shown.connect(
		func(speaker: String, _text: String, _options: Array) -> void: choice_events.append(speaker)
	)
	DialogueRunner.start(_fixture_graph())
	assert_array(lines).is_empty()
	assert_array(choice_events).is_equal(["Villager"])
	assert_bool(DialogueRunner.is_active()).is_true()


func test_choose_sets_flag_and_follows_branch_then_advance_ends() -> void:
	var lines: Array[String] = []
	DialogueRunner.line_shown.connect(
		func(_speaker: String, text: String) -> void: lines.append(text)
	)
	var ended := false
	DialogueRunner.ended.connect(func() -> void: ended = true)
	DialogueRunner.start(_fixture_graph())  # greet -> else -> ask_weather (choices_shown)
	DialogueRunner.choose(0)  # "Sure." -> sets talked_to_villager, goes to "chat"
	assert_bool(DialogueRunner.flags.get("talked_to_villager", false)).is_true()
	assert_array(lines).is_equal(["The moss has been doing well this week."])
	DialogueRunner.advance()  # chat.next == null -> ends
	assert_bool(ended).is_true()
	assert_bool(DialogueRunner.is_active()).is_false()


func test_choose_out_of_range_index_is_noop() -> void:
	DialogueRunner.start(_fixture_graph())  # greet -> else -> ask_weather (choices_shown)
	DialogueRunner.choose(99)
	assert_bool(DialogueRunner.is_active()).is_true()


func test_advance_on_choices_node_is_noop() -> void:
	DialogueRunner.start(_fixture_graph())  # greet -> else -> ask_weather (choices_shown)
	DialogueRunner.advance()  # ask_weather has choices, not next -> no-op
	assert_bool(DialogueRunner.is_active()).is_true()


func test_condition_true_shows_greet_then_advance_follows_next_to_chat_repeat_on_retalk() -> void:
	# With the flag already set, greet's condition evaluates true, so per
	# §3 the resolver falls through and displays greet's OWN line first
	# (its "next" is only followed later via an explicit advance()) —
	# this is the asymmetric-but-correct behavior: a true condition shows
	# the gated node itself, a false one skips straight to "else".
	DialogueRunner.flags["talked_to_villager"] = true
	var lines: Array[String] = []
	DialogueRunner.line_shown.connect(
		func(_speaker: String, text: String) -> void: lines.append(text)
	)
	DialogueRunner.start(_fixture_graph())
	assert_array(lines).is_equal(["Oh! You're the one from the cottage."])
	DialogueRunner.advance()
	assert_array(lines).is_equal([
		"Oh! You're the one from the cottage.",
		"Back again? The moss is still doing wonderfully.",
	])


func test_condition_false_with_no_else_ends_immediately() -> void:
	var data: Dictionary = JSON.parse_string(FIXTURE_JSON)
	data["nodes"]["greet"].erase("else")
	var graph := DialogueGraph._parse(data)
	var ended := false
	DialogueRunner.ended.connect(func() -> void: ended = true)
	DialogueRunner.start(graph)
	assert_bool(ended).is_true()
	assert_bool(DialogueRunner.is_active()).is_false()


func test_current_voice_seed_reflects_start_argument() -> void:
	DialogueRunner.start(_fixture_graph(), 42)
	assert_int(DialogueRunner.current_voice_seed()).is_equal(42)


func test_current_voice_seed_defaults_to_zero() -> void:
	DialogueRunner.start(_fixture_graph())
	assert_int(DialogueRunner.current_voice_seed()).is_equal(0)


func test_current_voice_seed_resets_to_zero_after_conversation_ends() -> void:
	DialogueRunner.start(_fixture_graph(), 42)
	DialogueRunner.advance()  # greet -> else -> ask_weather (choices_shown)
	DialogueRunner.choose(1)  # "Not now." -> next: null -> ends
	assert_int(DialogueRunner.current_voice_seed()).is_equal(0)


func test_is_active_false_before_any_start() -> void:
	assert_bool(DialogueRunner.is_active()).is_false()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_dialogue_runner.gd`
Expected: FAIL — `Identifier "DialogueRunner" not declared` (autoload doesn't exist yet).

- [ ] **Step 3: Write `DialogueRunner` and register the autoload**

```gdscript
class_name DialogueRunnerService
extends Node
## Owns the active DialogueGraph traversal state. Registered as the
## "DialogueRunner" autoload (script class name differs to avoid Godot's
## self-collision restriction, same split as GameClockService/GameClock).
## See docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §3.

signal line_shown(speaker: String, text: String)
signal choices_shown(speaker: String, text: String, options: Array)
signal ended

var flags: Dictionary = {}  # String -> bool, in-memory only (see spec §8)

var _graph: DialogueGraph = null
var _current_node_id: String = ""
var _voice_seed: int = 0


func start(graph: DialogueGraph, voice_seed: int = 0) -> void:
	_graph = graph
	_voice_seed = voice_seed
	_resolve(graph.start)


func advance() -> void:
	if _graph == null:
		return
	var node: Dictionary = _graph.nodes[_current_node_id]
	if node.has("choices"):
		return
	_resolve(node.get("next"))


func choose(index: int) -> void:
	if _graph == null:
		return
	var node: Dictionary = _graph.nodes[_current_node_id]
	var choices = node.get("choices")
	if choices == null or index < 0 or index >= choices.size():
		return
	var choice: Dictionary = choices[index]
	if choice.has("set_flag"):
		flags[choice["set_flag"]] = true
	_resolve(choice["next"])


func is_active() -> bool:
	return _graph != null


func current_voice_seed() -> int:
	return _voice_seed


## Shared node-resolution step used by start/advance/choose. Walks
## condition/else chains until it lands on a node to display, or a null id
## to end the conversation. See spec §3 for the exact semantics.
func _resolve(node_id: Variant) -> void:
	if node_id == null or String(node_id).is_empty():
		_graph = null
		_current_node_id = ""
		_voice_seed = 0
		ended.emit()
		return
	var id: String = node_id
	var node: Dictionary = _graph.nodes[id]
	if node.has("condition"):
		var condition: Dictionary = node["condition"]
		var flag_value: bool = flags.get(condition["flag"], false)
		if flag_value != condition["equals"]:
			_resolve(node.get("else"))
			return
	_current_node_id = id
	if node.has("choices"):
		var options: Array[String] = []
		for choice in node["choices"]:
			options.append(choice["text"])
		choices_shown.emit(node["speaker"], node["text"], options)
	else:
		line_shown.emit(node["speaker"], node["text"])
```

Register the autoload in `project.godot`:

```
[autoload]

InputBootstrap="*res://src/core/input_bootstrap.gd"
GameClock="*res://src/core/game_clock.gd"
DialogueRunner="*res://src/core/dialogue_runner.gd"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_dialogue_runner.gd`
Expected: PASS (10/10)

- [ ] **Step 5: Commit**

```bash
git add src/core/dialogue_runner.gd project.godot tests/unit/test_dialogue_runner.gd
git commit -m "feat(dialogue): add DialogueRunner autoload state machine"
```

**Chunk 1 complete when:** both test files pass and `git log` shows the two commits above.

---

## Chunk 2: UI, audio, and `InteractPrompt` overlap fix

### Task 3: `Animalese` — procedural blip audio

**Files:**
- Create: `src/core/animalese.gd`
- Create: `tests/unit/test_animalese.gd`

- [ ] **Step 1: Write the failing tests**

```gdscript
extends GdUnitTestSuite
## Animalese: procedural per-seed blip synthesis. See
## docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §5.


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
	assert_float(blip.mix_rate).is_equal_approx(22050.0, 0.1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_animalese.gd`
Expected: FAIL — `Animalese` class not found.

- [ ] **Step 3: Write `Animalese`**

```gdscript
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_animalese.gd`
Expected: PASS (4/4)

- [ ] **Step 5: Commit**

```bash
git add src/core/animalese.gd tests/unit/test_animalese.gd
git commit -m "feat(dialogue): add Animalese procedural blip audio"
```

### Task 4: `InteractPrompt.force_hide()` — the overlap fix

**Files:**
- Modify: `src/interact/interact_prompt.gd`
- Create: `tests/unit/test_interact_prompt.gd`

- [ ] **Step 1: Write the failing test**

```gdscript
extends GdUnitTestSuite
## InteractPrompt: covers the dialogue-overlap fix directly (spec §4) —
## force_hide() must hide the prompt even while it's already visible, and
## on_focus_changed() must be able to re-show it afterward without waiting
## for a fresh focus_changed event.


func test_force_hide_hides_prompt_even_when_already_visible() -> void:
	var prompt := InteractPrompt.new()
	auto_free(prompt)
	var item := Interactable.new()
	auto_free(item)
	prompt.on_focus_changed(item)
	assert_bool(prompt.visible).is_true()
	prompt.force_hide()
	assert_bool(prompt.visible).is_false()


func test_on_focus_changed_reshows_prompt_after_force_hide() -> void:
	var prompt := InteractPrompt.new()
	auto_free(prompt)
	var item := Interactable.new()
	auto_free(item)
	prompt.on_focus_changed(item)
	prompt.force_hide()
	prompt.on_focus_changed(item)
	assert_bool(prompt.visible).is_true()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_interact_prompt.gd`
Expected: FAIL — `Function "force_hide" not found`.

- [ ] **Step 3: Add `force_hide()`**

```gdscript
func force_hide() -> void:
	visible = false
```

Add this method to `src/interact/interact_prompt.gd`, alongside the existing `on_focus_changed()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_interact_prompt.gd`
Expected: PASS (2/2)

- [ ] **Step 5: Commit**

```bash
git add src/interact/interact_prompt.gd tests/unit/test_interact_prompt.gd
git commit -m "feat(interact): add InteractPrompt.force_hide() for dialogue overlap fix"
```

### Task 5: `DialogueBox` UI scene

**Files:**
- Create: `src/ui/dialogue_box/dialogue_box.gd`
- Create: `src/ui/dialogue_box/dialogue_box.tscn`
- Modify: `src/player/player.tscn` (instance `DialogueBox` under `HUD`)
- Modify: `src/player/player.gd` (wire prompt-overlap signals + input pause/resume)
- Test: `tests/unit/test_dialogue_box.gd`

This task is the largest one in the plan; it has no pre-existing UI scene to copy verbatim, so build it by hand in the Godot editor via the `godot-*` MCP tools rather than hand-writing `.tscn` text (avoids fragile `ExtResource`/`SubResource` id bookkeeping).

- [ ] **Step 1: Write the failing test** (behavior-level: exercise `DialogueBox` purely through `DialogueRunner`'s signals, not by inspecting internal node structure beyond what's necessary)

```gdscript
extends GdUnitTestSuite
## DialogueBox: reacts to DialogueRunner signals only. See
## docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §4.

const DialogueBoxScene := preload("res://src/ui/dialogue_box/dialogue_box.tscn")

const FIXTURE_JSON := """
{
  "start": "greet",
  "nodes": {
    "greet": {
      "speaker": "Villager",
      "text": "Hello!",
      "choices": [
        { "text": "Hi.", "next": null }
      ]
    }
  }
}
"""


func after_test() -> void:
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""


func _fixture_graph() -> DialogueGraph:
	return DialogueGraph._parse(JSON.parse_string(FIXTURE_JSON))


func test_hidden_by_default() -> void:
	var box: DialogueBox = DialogueBoxScene.instantiate()
	auto_free(box)
	add_child(box)
	assert_bool(box.visible).is_false()


func test_shows_and_populates_choice_buttons_on_choices_shown() -> void:
	var box: DialogueBox = DialogueBoxScene.instantiate()
	auto_free(box)
	add_child(box)
	DialogueRunner.start(_fixture_graph())
	assert_bool(box.visible).is_true()
	assert_int(box.get_choice_button_count()).is_equal(1)


func test_hides_on_ended() -> void:
	var box: DialogueBox = DialogueBoxScene.instantiate()
	auto_free(box)
	add_child(box)
	DialogueRunner.start(_fixture_graph())
	DialogueRunner.choose(0)
	assert_bool(box.visible).is_false()


func test_choice_button_press_calls_dialogue_runner_choose() -> void:
	var box: DialogueBox = DialogueBoxScene.instantiate()
	auto_free(box)
	add_child(box)
	DialogueRunner.start(_fixture_graph())
	box.press_choice_button(0)
	assert_bool(DialogueRunner.is_active()).is_false()


func test_number_key_selects_choice_positionally() -> void:
	var box: DialogueBox = DialogueBoxScene.instantiate()
	auto_free(box)
	add_child(box)
	DialogueRunner.start(_fixture_graph())
	var runner := scene_runner(box)
	await runner.simulate_frames(1)
	runner.simulate_key_pressed(KEY_1)
	assert_bool(DialogueRunner.is_active()).is_false()


func test_line_shown_reveals_text_progressively_over_time() -> void:
	var box: DialogueBox = DialogueBoxScene.instantiate()
	auto_free(box)
	add_child(box)
	var single_line_json := """
	{ "start": "only", "nodes": { "only": { "speaker": "Villager", "text": "Hi there.", "next": null } } }
	"""
	DialogueRunner.start(DialogueGraph._parse(JSON.parse_string(single_line_json)))
	var text_label := box.get_node("%TextLabel") as Label
	assert_str(text_label.text).is_equal("")
	var runner := scene_runner(box)
	await runner.simulate_frames(3, 50)  # a couple reveal ticks in, not yet complete
	var partial := text_label.text
	assert_bool(partial.length() > 0 and partial.length() < "Hi there.".length()).is_true()
	assert_bool("Hi there.".begins_with(partial)).is_true()
	await runner.simulate_frames(20, 50)  # well past the remaining chars * 30ms/char
	assert_str(text_label.text).is_equal("Hi there.")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_dialogue_box.gd`
Expected: FAIL — scene/script not found.

- [ ] **Step 3: Write `dialogue_box.gd`**

```gdscript
class_name DialogueBox
extends Control
## Bottom dialogue panel. Purely reactive to DialogueRunner's signals —
## contains no dialogue-graph logic itself. See
## docs/superpowers/specs/2026-08-12-dialogue-engine-design.md §4-5.

const CHAR_REVEAL_INTERVAL := 0.03

@onready var _portrait_bg: Panel = %PortraitBg
@onready var _portrait_label: Label = %PortraitLabel
@onready var _speaker_label: Label = %SpeakerLabel
@onready var _text_label: Label = %TextLabel
@onready var _choices_box: VBoxContainer = %ChoicesBox
@onready var _reveal_timer: Timer = %RevealTimer
@onready var _blip_player: AudioStreamPlayer = %BlipPlayer

var _full_text := ""
var _reveal_index := 0
var _portrait_style: StyleBoxFlat


func _ready() -> void:
	visible = false
	# Panel (not ColorRect) so a StyleBoxFlat can round the corners into a
	# circle per spec §4 — a fresh StyleBoxFlat instance per DialogueBox so
	# recoloring it per-speaker doesn't mutate a shared/default resource.
	_portrait_style = StyleBoxFlat.new()
	_portrait_style.corner_radius_top_left = 24
	_portrait_style.corner_radius_top_right = 24
	_portrait_style.corner_radius_bottom_left = 24
	_portrait_style.corner_radius_bottom_right = 24
	_portrait_bg.add_theme_stylebox_override("panel", _portrait_style)
	DialogueRunner.line_shown.connect(_on_line_shown)
	DialogueRunner.choices_shown.connect(_on_choices_shown)
	DialogueRunner.ended.connect(_on_ended)
	_reveal_timer.timeout.connect(_on_reveal_tick)


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	if _choices_box.get_child_count() > 0:
		_handle_choice_key(event)
		return
	if event.is_action_pressed(&"interact"):
		DialogueRunner.advance()


## Number keys 1-9 select choices positionally (spec §4) — not a new
## InputMap action, deliberately deferring proper menu-navigation input.
func _handle_choice_key(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed:
		return
	var key_event := event as InputEventKey
	if key_event.keycode < KEY_1 or key_event.keycode > KEY_9:
		return
	var index := key_event.keycode - KEY_1
	if index < _choices_box.get_child_count():
		press_choice_button(index)


func get_choice_button_count() -> int:
	return _choices_box.get_child_count()


## Test/production helper: simulates pressing the Nth choice button.
func press_choice_button(index: int) -> void:
	var button := _choices_box.get_child(index) as Button
	if button != null:
		button.pressed.emit()


func _on_line_shown(speaker: String, text: String) -> void:
	_show_speaker(speaker)
	_clear_choices()
	_start_reveal(text)


func _on_choices_shown(speaker: String, text: String, options: Array) -> void:
	_show_speaker(speaker)
	_clear_choices()
	_start_reveal(text)
	for i in options.size():
		var button := Button.new()
		button.text = options[i]
		button.pressed.connect(DialogueRunner.choose.bind(i))
		_choices_box.add_child(button)


func _on_ended() -> void:
	visible = false
	_reveal_timer.stop()


func _show_speaker(speaker: String) -> void:
	visible = true
	_speaker_label.text = speaker
	_portrait_label.text = speaker.substr(0, 1).to_upper()
	_portrait_style.bg_color = Color.from_hsv(float(speaker.hash() % 360) / 360.0, 0.55, 0.85)


func _clear_choices() -> void:
	# remove_child() is immediate, so get_choice_button_count()/number-key
	# routing is correct within the same signal-handling turn — a choices->
	# choices transition must not see stale buttons from the previous node.
	# queue_free() (not free()) defers the actual object destruction, since a
	# choice button pressed by the user can still be the object emitting the
	# very signal that triggered this call — freeing it synchronously would
	# error ("Object is locked and can't be freed").
	for child in _choices_box.get_children():
		_choices_box.remove_child(child)
		child.queue_free()


func _start_reveal(text: String) -> void:
	_full_text = text
	_reveal_index = 0
	_text_label.text = ""
	_reveal_timer.wait_time = CHAR_REVEAL_INTERVAL
	_reveal_timer.start()


func _on_reveal_tick() -> void:
	if _reveal_index >= _full_text.length():
		_reveal_timer.stop()
		return
	var ch := _full_text[_reveal_index]
	_reveal_index += 1
	_text_label.text = _full_text.substr(0, _reveal_index)
	if _is_voiced_char(ch):
		_blip_player.stream = Animalese.blip_for_seed(DialogueRunner.current_voice_seed())
		_blip_player.play()


## True for characters that should trigger a blip: not whitespace, and not
## punctuation. Uses RegEx rather than a fixed list so it isn't silently
## incomplete for punctuation this codebase's dialogue content ends up
## needing later (colons, dashes, quotes, ellipses, etc.).
static var _punctuation_regex := RegEx.create_from_string("[[:punct:]]")


func _is_voiced_char(ch: String) -> bool:
	if ch.strip_edges() == "":
		return false
	return not _punctuation_regex.search(ch)
```

- [ ] **Step 4: Build `dialogue_box.tscn`**

Use the `godot-create_scene` and `godot-add_node` MCP tools to build a `Control` root named `DialogueBox` with this node tree, then attach the script and set `unique_name_in_owner = true` on each leaf referenced via `%Name` above:
- `DialogueBox` (Control, script = `dialogue_box.gd`, anchored to bottom-center like `InteractPrompt`, initially `visible = false` is set in code so leave default true in the scene)
  - `Panel` (background box)
    - `HBoxContainer`
      - `PortraitBg` (`Panel`, ~48x48, `unique_name_in_owner` — corner-radius StyleBoxFlat override applied in code, see `_ready()`)
        - `PortraitLabel` (`Label`, centered, `unique_name_in_owner`)
      - `VBoxContainer`
        - `SpeakerLabel` (`Label`, `unique_name_in_owner`)
        - `TextLabel` (`Label`, `autowrap_mode = 2`, `unique_name_in_owner`)
        - `ChoicesBox` (`VBoxContainer`, `unique_name_in_owner`)
  - `RevealTimer` (`Timer`, `one_shot = false`, `unique_name_in_owner`)
  - `BlipPlayer` (`AudioStreamPlayer`, `unique_name_in_owner`)

Save via `godot-save_scene` to `res://src/ui/dialogue_box/dialogue_box.tscn`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_dialogue_box.gd`
Expected: PASS (6/6)

- [ ] **Step 6: Write the failing Player-wiring test** (append to `tests/unit/test_player.gd`, reusing its existing `_spawn_world()`/`_make_item()`-style helpers if present, or instancing `player.tscn` directly)

```gdscript
func after_test() -> void:
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""
	DialogueRunner._voice_seed = 0


func test_dialogue_line_shown_force_hides_interact_prompt_even_if_already_visible() -> void:
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	auto_free(player)
	add_child(player)
	var prompt := player.get_node("%InteractPrompt") as InteractPrompt
	var item := Interactable.new()
	auto_free(item)
	prompt.on_focus_changed(item)  # simulate focus already held
	assert_bool(prompt.visible).is_true()
	DialogueRunner.line_shown.emit("Villager", "Hi.")
	assert_bool(prompt.visible).is_false()


func test_dialogue_choices_shown_force_hides_interact_prompt_with_real_focus() -> void:
	# Uses the real test_interact.gd-style focus-simulation pattern (not a
	# faked on_focus_changed() call) so the prompt is genuinely visible via
	# FocusResolver before we assert force_hide() reacts to choices_shown —
	# this is the actual path the first demo conversation takes on first
	# encounter (condition-false -> else -> choices_shown immediately).
	var arena := Node3D.new()
	auto_free(arena)
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	player.input_enabled = false
	arena.add_child(player)
	var item := Interactable.new()
	item.position = Vector3(0, 1, -1.5)  # in front of player, within reach
	arena.add_child(item)
	var runner := scene_runner(arena)
	await runner.simulate_frames(15)  # let FocusResolver's real evaluate() focus `item`
	var resolver := player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(item)  # sanity-check the real focus state
	var prompt := player.get_node("%InteractPrompt") as InteractPrompt
	assert_bool(prompt.visible).is_true()
	DialogueRunner.choices_shown.emit("Villager", "Nice day?", ["Sure is.", "Not really."])
	assert_bool(prompt.visible).is_false()


func test_dialogue_ended_reshows_prompt_via_current_focus() -> void:
	var arena := Node3D.new()
	auto_free(arena)
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	player.input_enabled = false
	arena.add_child(player)
	var item := Interactable.new()
	item.position = Vector3(0, 1, -1.5)  # in front of player, within reach
	arena.add_child(item)
	var runner := scene_runner(arena)
	await runner.simulate_frames(15)  # let FocusResolver's real evaluate() focus `item`
	var resolver := player.get_node("%FocusResolver") as FocusResolver
	assert_object(resolver.focused()).is_same(item)  # sanity-check the real focus state
	var prompt := player.get_node("%InteractPrompt") as InteractPrompt
	prompt.force_hide()
	DialogueRunner.ended.emit()
	assert_bool(prompt.visible).is_true()


func test_dialogue_ended_reenables_player_input() -> void:
	var player: Player = preload("res://src/player/player.tscn").instantiate()
	auto_free(player)
	add_child(player)
	player.input_enabled = false
	DialogueRunner.ended.emit()
	assert_bool(player.input_enabled).is_true()
```

- [ ] **Step 7: Run test to verify it fails**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_player.gd`
Expected: FAIL — `Player` doesn't yet react to `DialogueRunner` signals.

- [ ] **Step 8: Wire `DialogueBox` + overlap fix into `Player`**

Using `godot-add_node`, instance `res://src/ui/dialogue_box/dialogue_box.tscn` as a new child of `HUD` in `src/player/player.tscn`, as a sibling of `InteractPrompt`.

Modify `src/player/player.gd`'s `_ready()`:

```gdscript
func _ready() -> void:
	var rig := _camera_rig()
	if rig != null:
		rig.mode_changed.connect(_on_camera_mode_changed)
	var resolver := _focus_resolver()
	var prompt := get_node_or_null("%InteractPrompt") as InteractPrompt
	if resolver != null and prompt != null:
		resolver.focus_changed.connect(prompt.on_focus_changed)
	if prompt != null:
		DialogueRunner.line_shown.connect(func(_s: String, _t: String) -> void: prompt.force_hide())
		DialogueRunner.choices_shown.connect(func(_s: String, _t: String, _o: Array) -> void: prompt.force_hide())
		if resolver != null:
			DialogueRunner.ended.connect(func() -> void: prompt.on_focus_changed(resolver.focused()))
	var avatar := get_node_or_null("%Avatar") as WrenAvatar
	if avatar != null:
		motion_changed.connect(avatar.set_motion_state)
	DialogueRunner.ended.connect(func() -> void: input_enabled = true)
```

- [ ] **Step 9: Run the full existing player/interact suite to check for regressions**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_player.gd -a tests/unit/test_interact.gd -a tests/unit/test_interact_prompt.gd -a tests/unit/test_dialogue_box.gd`
Expected: PASS (all, apart from the pre-existing `test_hysteresis_keeps_focus_against_marginal_rival` flake noted in the spec's baseline).

- [ ] **Step 10: Commit**

```bash
git add src/ui/dialogue_box/ src/player/player.tscn src/player/player.gd tests/unit/test_dialogue_box.gd tests/unit/test_player.gd
git commit -m "feat(dialogue): add DialogueBox UI, wire InteractPrompt overlap fix and input pause into Player"
```

**Chunk 2 complete when:** all test files above pass, and `Player._ready()` wires `DialogueBox`/`InteractPrompt`/input pause exactly per spec §4/§6.

---

## Chunk 3: Demo integration & final verification

### Task 6: Demo dialogue data file

**Files:**
- Create: `data/dialogue/demo_villager.json`

- [ ] **Step 1: Write the file** (the exact 4-node example from spec §2/§6)

```json
{
  "start": "greet",
  "nodes": {
    "greet": {
      "speaker": "Villager",
      "text": "Oh! You're the one from the cottage.",
      "condition": { "flag": "talked_to_villager", "equals": true },
      "next": "chat_repeat",
      "else": "ask_weather"
    },
    "ask_weather": {
      "speaker": "Villager",
      "text": "Fancy some small talk?",
      "choices": [
        { "text": "Sure.", "next": "chat", "set_flag": "talked_to_villager" },
        { "text": "Not now.", "next": null }
      ]
    },
    "chat": {
      "speaker": "Villager",
      "text": "The moss has been doing well this week.",
      "next": null
    },
    "chat_repeat": {
      "speaker": "Villager",
      "text": "Back again? The moss is still doing wonderfully.",
      "next": null
    }
  }
}
```

- [ ] **Step 2: Validate it loads via a quick one-off check**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_dialogue_graph.gd` (regression check only — no test targets this file directly yet; Task 7 covers that via the integration test).

- [ ] **Step 3: Commit**

```bash
git add data/dialogue/demo_villager.json
git commit -m "feat(dialogue): add demo_villager.json dialogue content"
```

### Task 7: Wire `Interactable` into `_add_demo_villager()`

**Files:**
- Modify: `src/world/cottage_garden/cottage_garden.gd`
- Modify: `tests/unit/test_cottage_garden.gd`

- [ ] **Step 1: Write the failing test** (append to existing file; this suite already has an `after_test()` hook from the T4.5 clock work resetting `GameClock.debug_override_hour` — merge the new `DialogueRunner` reset lines into that *same* function rather than adding a second `after_test()`, since gdUnit only calls one per suite)

```gdscript
func after_test() -> void:
	GameClock.debug_override_hour = null
	DialogueRunner.flags = {}
	DialogueRunner._graph = null
	DialogueRunner._current_node_id = ""
	DialogueRunner._voice_seed = 0


func test_demo_villager_has_talk_interactable() -> void:
	var world := preload("res://src/world/cottage_garden/cottage_garden.tscn").instantiate()
	auto_free(world)
	add_child(world)
	var villager := world.get_node("DemoVillager")
	var talk := villager.find_children("*", "Interactable", true, false)
	assert_int(talk.size()).is_equal(1)
	assert_str((talk[0] as Interactable).verb).is_equal("Talk")


func test_interacting_with_demo_villager_starts_and_can_end_dialogue() -> void:
	var world := preload("res://src/world/cottage_garden/cottage_garden.tscn").instantiate()
	auto_free(world)
	add_child(world)
	var villager := world.get_node("DemoVillager")
	var talk := villager.find_children("*", "Interactable", true, false)[0] as Interactable
	talk.interact(self)
	assert_bool(DialogueRunner.is_active()).is_true()
	# First encounter has no flags set, so greet's condition is false and it
	# routes via "else" into ask_weather's choices; pick index 1 ("Not now.",
	# next: null) to end the conversation cleanly.
	DialogueRunner.choose(1)
	assert_bool(DialogueRunner.is_active()).is_false()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_cottage_garden.gd`
Expected: FAIL — no `Interactable` child found under `DemoVillager`.

- [ ] **Step 3: Wire it up in `cottage_garden.gd`**

```gdscript
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
```

(Replace the existing `_add_demo_villager()` body with the above; add the new `_on_demo_villager_interacted()` function alongside it.)

- [ ] **Step 4: Run test to verify it passes**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit/test_cottage_garden.gd`
Expected: PASS (all, including the two new tests)

- [ ] **Step 5: Commit**

```bash
git add src/world/cottage_garden/cottage_garden.gd tests/unit/test_cottage_garden.gd
git commit -m "feat(dialogue): wire demo villager Interactable to DialogueRunner"
```

### Task 8: Final full-suite verification & ROADMAP update

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Run the full gdUnit suite**

Run: `/Applications/Godot.app/Contents/MacOS/Godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd --ignoreHeadlessMode -a tests/unit`
Expected: all new dialogue-related tests pass; the 3 pre-existing baseline failures noted in the spec (`test_avatar.gd` ×2 missing clips, `test_interact.gd`'s hysteresis flake) are the only failures, unchanged from before this work. If any *other* test fails, treat it as a regression and fix before proceeding.

- [ ] **Step 2: Manual smoke test (optional but recommended given this is UI-facing)**

Use the Godot MCP `godot-run_project` tool (or, if unavailable, run `res://src/world/cottage_garden/cottage_garden.tscn` locally via the Godot editor/`--path .` in windowed mode) on `res://src/world/cottage_garden/cottage_garden.tscn`, walk to the demo villager, press `E`, confirm the dialogue box appears, choices work, animalese blips play, and `E` closes/advances correctly; confirm the `InteractPrompt` never overlaps the box.

- [ ] **Step 3: Update `ROADMAP.md`**

Mark T5.1 done in the Phase 5 task list and the Phase status table, following the exact style used for T4.5 (see the `ec949bc` commit for the pattern).

- [ ] **Step 4: Commit**

```bash
git add ROADMAP.md
git commit -m "docs: mark T5.1 dialogue engine complete in ROADMAP"
```

**Chunk 3 complete when:** full suite passes at baseline, ROADMAP reflects T5.1 done, and a manual smoke test confirms the demo conversation works end-to-end in-editor.

---

## Review guidance for execution

Per the user's standing instruction: apply the full spec-compliance + code-quality review pair only to the substantive/risky tasks — **Task 2 (`DialogueRunner` condition/branching logic)** and **Task 5 (`DialogueBox` + `InteractPrompt` overlap wiring)** — since these are exactly the places prior spec-review rounds found real bugs. Tasks 1, 3, 4, 6, and 7 are small and mechanical (a validator, a sine-wave generator, a one-line method addition, a static JSON file, and a config-shaped wiring call) — a single combined review (or none, if the task author is confident and tests pass) is sufficient for those.
