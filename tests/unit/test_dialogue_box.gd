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
