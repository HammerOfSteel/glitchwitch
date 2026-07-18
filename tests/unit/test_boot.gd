extends GdUnitTestSuite
## Boot smoke suite — the project opens, the main scene lives,
## and the default input ritual is registered.

const EXPECTED_ACTIONS: Array[StringName] = [
	&"move_forward",
	&"move_back",
	&"move_left",
	&"move_right",
	&"run",
	&"interact",
	&"camera_toggle",
	&"witch_sight",
	&"journal",
	&"pause",
]


func test_project_identity() -> void:
	var name := str(ProjectSettings.get_setting("application/config/name", ""))
	assert_str(name).is_equal("Glitch Witch")


func test_main_scene_is_configured_and_exists() -> void:
	var main_scene := str(ProjectSettings.get_setting("application/run/main_scene", ""))
	assert_str(main_scene).is_equal("res://src/sandbox/glade.tscn")
	assert_bool(ResourceLoader.exists(main_scene)).is_true()


func test_banner_scene_boots() -> void:
	var runner := scene_runner("res://src/main/main.tscn")
	assert_object(runner.scene()).is_not_null()
	var banner: Label = runner.scene().get_node("%Banner")
	assert_object(banner).is_not_null()
	assert_str(banner.text).contains("GLITCH WITCH")


func test_default_input_actions_registered() -> void:
	InputBootstrap.register_default_actions()
	for action in EXPECTED_ACTIONS:
		(
			assert_bool(InputMap.has_action(action))
			. override_failure_message("missing input action: %s" % action)
			. is_true()
		)


func test_movement_actions_have_key_and_joypad_events() -> void:
	InputBootstrap.register_default_actions()
	for action in [&"move_forward", &"move_back", &"move_left", &"move_right"]:
		var events := InputMap.action_get_events(action)
		var has_key := false
		var has_joy := false
		for event in events:
			if event is InputEventKey:
				has_key = true
			elif event is InputEventJoypadMotion:
				has_joy = true
		(
			assert_bool(has_key and has_joy)
			. override_failure_message("action %s missing key or joypad binding" % action)
			. is_true()
		)
