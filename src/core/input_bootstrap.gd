extends Node
## Registers the game's default input actions at boot.
##
## Bindings live in code rather than project.godot on purpose: player
## rebinding (Phase 3) mutates the runtime InputMap anyway, so code is
## the single source of truth for defaults. Registration is idempotent.

const DEADZONE := 0.2

const KEY_BINDINGS: Dictionary = {
	&"move_forward": [KEY_W, KEY_UP],
	&"move_back": [KEY_S, KEY_DOWN],
	&"move_left": [KEY_A, KEY_LEFT],
	&"move_right": [KEY_D, KEY_RIGHT],
	&"run": [KEY_SHIFT],
	&"interact": [KEY_E],
	&"camera_toggle": [KEY_V],
	&"witch_sight": [KEY_F],
	&"journal": [KEY_J],
	&"pause": [KEY_ESCAPE],
}

const JOY_BINDINGS: Dictionary = {
	&"run": JOY_BUTTON_B,
	&"interact": JOY_BUTTON_A,
	&"camera_toggle": JOY_BUTTON_RIGHT_STICK,
	&"witch_sight": JOY_BUTTON_Y,
	&"journal": JOY_BUTTON_BACK,
	&"pause": JOY_BUTTON_START,
}

const JOY_AXES: Dictionary = {
	&"move_forward": [JOY_AXIS_LEFT_Y, -1.0],
	&"move_back": [JOY_AXIS_LEFT_Y, 1.0],
	&"move_left": [JOY_AXIS_LEFT_X, -1.0],
	&"move_right": [JOY_AXIS_LEFT_X, 1.0],
}


func _ready() -> void:
	register_default_actions()


static func register_default_actions() -> void:
	if InputMap.has_action(&"move_forward"):
		return
	for action in KEY_BINDINGS:
		_ensure_action(action)
		for keycode in KEY_BINDINGS[action]:
			var key_event := InputEventKey.new()
			key_event.physical_keycode = keycode as Key
			InputMap.action_add_event(action, key_event)
	for action in JOY_BINDINGS:
		_ensure_action(action)
		var button_event := InputEventJoypadButton.new()
		button_event.button_index = JOY_BINDINGS[action] as JoyButton
		InputMap.action_add_event(action, button_event)
	for action in JOY_AXES:
		_ensure_action(action)
		var motion_event := InputEventJoypadMotion.new()
		motion_event.axis = JOY_AXES[action][0] as JoyAxis
		motion_event.axis_value = JOY_AXES[action][1]
		InputMap.action_add_event(action, motion_event)


static func _ensure_action(action: StringName) -> void:
	if not InputMap.has_action(action):
		InputMap.add_action(action, DEADZONE)
