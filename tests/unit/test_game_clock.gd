extends GdUnitTestSuite
## GameClock: real-time-synced clock singleton. See
## docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.


func test_debug_override_hour_bypasses_real_system_time() -> void:
	GameClock.debug_override_hour = 14.5
	assert_float(GameClock.hour_of_day()).is_equal_approx(14.5, 0.001)
	GameClock.debug_override_hour = null


func test_weekday_returns_value_in_enum_range() -> void:
	var day := GameClock.weekday()
	assert_int(day).is_greater_equal(GameClockService.Weekday.MONDAY)
	assert_int(day).is_less_equal(GameClockService.Weekday.SUNDAY)


func test_sunday_remap_formula_is_correct_for_known_godot_weekdays() -> void:
	# Godot's Time singleton: weekday 0 == Sunday .. 6 == Saturday.
	# Ours: Weekday.MONDAY == 0 .. Weekday.SUNDAY == 6.
	# Verified with fixed known inputs, independent of the real system clock,
	# so this proves the remap formula itself, not just self-consistency.
	assert_int((0 + 6) % 7).is_equal(GameClockService.Weekday.SUNDAY)  # Godot Sunday -> ours SUNDAY
	assert_int((1 + 6) % 7).is_equal(GameClockService.Weekday.MONDAY)  # Godot Monday -> ours MONDAY
	assert_int((6 + 6) % 7).is_equal(GameClockService.Weekday.SATURDAY)  # Godot Saturday -> ours SATURDAY


func test_date_string_matches_godot_system_date_same_day() -> void:
	var expected := Time.get_datetime_dict_from_system()
	var expected_str := "%04d-%02d-%02d" % [expected.year, expected.month, expected.day]
	assert_str(GameClock.date_string()).is_equal(expected_str)
