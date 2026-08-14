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
