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
