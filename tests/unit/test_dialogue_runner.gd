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
	var ended := {"value": false}
	DialogueRunner.ended.connect(func() -> void: ended["value"] = true)
	DialogueRunner.start(_fixture_graph())  # greet -> else -> ask_weather (choices_shown)
	DialogueRunner.choose(0)  # "Sure." -> sets talked_to_villager, goes to "chat"
	assert_bool(DialogueRunner.flags.get("talked_to_villager", false)).is_true()
	assert_array(lines).is_equal(["The moss has been doing well this week."])
	DialogueRunner.advance()  # chat.next == null -> ends
	assert_bool(ended["value"]).is_true()
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
	var ended := {"value": false}
	DialogueRunner.ended.connect(func() -> void: ended["value"] = true)
	DialogueRunner.start(graph)
	assert_bool(ended["value"]).is_true()
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
