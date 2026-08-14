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
