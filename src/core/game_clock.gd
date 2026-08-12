class_name GameClockService
extends Node
## Real-time-synced game clock: exposes the current hour-of-day, weekday,
## and date, sourced from Godot's own Time singleton (which already reports
## the OS's local system time — no solar/lat-long calculation in v1).
## Registered as the GameClock autoload in project.godot.
## See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

enum Weekday { MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY }

## Placeholder for future timezone/location refinement. Inert in v1 — the
## game currently just uses whatever local time zone the OS reports. Kept
## deliberately as an explicit project-owner decision (deferred lat/long
## solar-calc feature, not accidental scope creep) so the future field slot
## and its intent are documented up front rather than added as a breaking
## change later.
var utc_offset_hours: float = 0.0

## Test hook: when non-null, hour_of_day() returns this instead of reading
## the real system clock, so gdUnit tests get deterministic values.
var debug_override_hour: Variant = null


func hour_of_day() -> float:
	if debug_override_hour != null:
		return debug_override_hour
	var t := Time.get_time_dict_from_system()
	return t.hour + (t.minute / 60.0) + (t.second / 3600.0)


func weekday() -> Weekday:
	# Time.get_datetime_dict_from_system()["weekday"] is Godot's own enum
	# (Time.WEEKDAY_SUNDAY == 0 .. WEEKDAY_SATURDAY == 6); remap to ours
	# (Weekday.MONDAY == 0 .. Weekday.SUNDAY == 6) so day 0 is Monday.
	var godot_weekday: int = Time.get_datetime_dict_from_system().weekday
	return ((godot_weekday + 6) % 7) as Weekday


func date_string() -> String:
	var d := Time.get_datetime_dict_from_system()
	return "%04d-%02d-%02d" % [d.year, d.month, d.day]
