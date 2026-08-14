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
		# Consume this event so it doesn't also reach Player._unhandled_input
		# in the same input dispatch — advancing to the end of a
		# conversation flips DialogueRunner.ended synchronously, which
		# re-enables Player.input_enabled before this same keypress finishes
		# propagating. Without this, the same E press that ends a
		# conversation also re-triggers FocusResolver.interact_focused() on
		# the still-focused villager, instantly restarting it.
		get_viewport().set_input_as_handled()


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
		get_viewport().set_input_as_handled()


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
