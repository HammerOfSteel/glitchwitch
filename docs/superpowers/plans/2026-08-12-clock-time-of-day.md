# Clock + Time-of-Day Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the game a real, shared clock (synced to wall-clock time) that
drives each zone's Sun/Fill lighting through the day, replacing the
currently hard-coded static lighting in `cottage_garden.gd` and
`hedgerow_lane.gd`.

**Architecture:** Three new GDScript units — `GameClock` (autoload
singleton wrapping Godot's `Time` singleton), `TimeOfDayCurve` (a pure,
stateless helper mapping an hour-of-day float to a lighting-state
`Dictionary` via keyframe interpolation), and `TimeOfDayRig` (a reusable
per-zone `Node` that polls `GameClock` on a 1s `Timer` and applies
`TimeOfDayCurve`'s output to a zone's `Sun`/`Fill` `DirectionalLight3D`
pair). `cottage_interior` is untouched (no Sun/Fill nodes).

**Tech Stack:** Godot 4.7 GDScript (gdUnit4 for tests).

**Spec:** `docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md` —
read this first for full rationale; this plan implements it task-by-task.

---

## Chunk 1: Core clock + curve + rig

### Task 1: `TimeOfDayCurve` pure helper

**Files:**
- Create: `src/world/time_of_day_curve.gd`
- Test: `tests/unit/test_time_of_day_curve.gd`

- [ ] **Step 1: Write the failing tests**

```gdscript
extends GdUnitTestSuite
## TimeOfDayCurve: pure hour -> lighting-state interpolation. No scene tree
## needed. See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

const EPS := 0.001


func test_noon_matches_todays_hardcoded_zone_values() -> void:
	var state := TimeOfDayCurve.light_state_for_hour(12.0)
	assert_vector(state.sun_rotation_degrees).is_equal_approx(Vector3(-48.0, -32.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.sun_color.is_equal_approx(Color(1.0, 0.93, 0.82))).is_true()
	assert_float(state.sun_energy).is_equal_approx(1.25, EPS)
	assert_bool(state.sun_shadow_enabled).is_true()
	assert_vector(state.fill_rotation_degrees).is_equal_approx(Vector3(-20.0, 141.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.fill_color.is_equal_approx(Color(0.68, 0.78, 0.92))).is_true()
	assert_float(state.fill_energy).is_equal_approx(0.35, EPS)


func test_midnight_matches_night_keyframe_exactly() -> void:
	var state := TimeOfDayCurve.light_state_for_hour(0.0)
	assert_vector(state.sun_rotation_degrees).is_equal_approx(Vector3(-70.0, -32.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.sun_color.is_equal_approx(Color(0.55, 0.62, 0.85))).is_true()
	assert_float(state.sun_energy).is_equal_approx(0.15, EPS)
	assert_bool(state.sun_shadow_enabled).is_false()


func test_midpoint_between_dawn_and_day_is_arithmetic_mean() -> void:
	# 9.0 is exactly halfway between the 6:00 dawn and 12:00 day keyframes.
	var state := TimeOfDayCurve.light_state_for_hour(9.0)
	# sun_energy: (0.7 + 1.25) / 2 = 0.975
	assert_float(state.sun_energy).is_equal_approx(0.975, EPS)
	# sun_color.r: (1.0 + 1.0) / 2 = 1.0, .g: (0.78 + 0.93) / 2 = 0.855
	assert_float(state.sun_color.g).is_equal_approx(0.855, EPS)


func test_midnight_wraparound_interpolates_dusk_toward_night() -> void:
	# 22.0 is between the 19:00 dusk keyframe and the 24:00-wrapped 0:00
	# night keyframe: t = (22.0 - 19.0) / (24.0 - 19.0) = 0.6.
	var state := TimeOfDayCurve.light_state_for_hour(22.0)
	assert_vector(state.sun_rotation_degrees).is_equal_approx(Vector3(-50.0, -32.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.sun_color.is_equal_approx(Color(0.73, 0.632, 0.69))).is_true()
	assert_float(state.sun_energy).is_equal_approx(0.29, EPS)
	# t = 0.6 >= 0.5, so shadow flag takes the night keyframe's false, not dusk's true.
	assert_bool(state.sun_shadow_enabled).is_false()
	assert_vector(state.fill_rotation_degrees).is_equal_approx(Vector3(-20.0, 141.0, 0.0), Vector3(EPS, EPS, EPS))
	assert_bool(state.fill_color.is_equal_approx(Color(0.46, 0.508, 0.72))).is_true()
	assert_float(state.fill_energy).is_equal_approx(0.14, EPS)


func test_shadow_flag_takes_nearer_keyframe_before_boundary() -> void:
	# 20.4 is between 19:00 dusk and 24:00-wrapped night: t = (20.4 - 19.0) / 5.0 = 0.28 < 0.5.
	var state := TimeOfDayCurve.light_state_for_hour(20.4)
	assert_bool(state.sun_shadow_enabled).is_true()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_time_of_day_curve.gd --ignoreHeadlessMode`
Expected: FAIL — `TimeOfDayCurve` identifier not found (class doesn't exist yet).

- [ ] **Step 3: Write the implementation**

```gdscript
class_name TimeOfDayCurve
extends RefCounted
## Pure, stateless hour-of-day -> lighting-state mapping. No scene tree or
## real-time dependency — directly gdUnit-testable.
## See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

# Hours at which each keyframe below applies. Must stay sorted ascending;
# light_state_for_hour() linearly interpolates between the two nearest
# entries here, wrapping past the last one back to the first (+24, so it
# interpolates toward the first keyframe + 24 across midnight).
const KEYFRAME_HOURS := [0.0, 6.0, 12.0, 19.0]

# Keyframe values in the same order as KEYFRAME_HOURS. The 12:00 (noon)
# entry's sun_/fill_ values are byte-identical to what every zone's
# _stage() previously hard-coded, so noon looks pixel-identical to today's
# static look (no visual regression at the exact hour existing screenshots
# were taken at).
const KEYFRAMES := [
	# 00:00 — night: dim, cool moonlight-only, no shadows.
	{
		"sun_rotation_degrees": Vector3(-70.0, -32.0, 0.0),
		"sun_color": Color(0.55, 0.62, 0.85),
		"sun_energy": 0.15,
		"sun_shadow_enabled": false,
		"fill_rotation_degrees": Vector3(-20.0, 141.0, 0.0),
		"fill_color": Color(0.4, 0.48, 0.7),
		"fill_energy": 0.1,
	},
	# 06:00 — dawn: soft warm low-angle light, shadows on (low contrast).
	{
		"sun_rotation_degrees": Vector3(-15.0, -32.0, 0.0),
		"sun_color": Color(1.0, 0.78, 0.6),
		"sun_energy": 0.7,
		"sun_shadow_enabled": true,
		"fill_rotation_degrees": Vector3(-20.0, 141.0, 0.0),
		"fill_color": Color(0.6, 0.68, 0.85),
		"fill_energy": 0.25,
	},
	# 12:00 — day: exact values every zone's _stage() already hard-codes today.
	{
		"sun_rotation_degrees": Vector3(-48.0, -32.0, 0.0),
		"sun_color": Color(1.0, 0.93, 0.82),
		"sun_energy": 1.25,
		"sun_shadow_enabled": true,
		"fill_rotation_degrees": Vector3(-20.0, 141.0, 0.0),
		"fill_color": Color(0.68, 0.78, 0.92),
		"fill_energy": 0.35,
	},
	# 19:00 — dusk: warm low-angle light fading toward night.
	{
		"sun_rotation_degrees": Vector3(-20.0, -32.0, 0.0),
		"sun_color": Color(1.0, 0.65, 0.45),
		"sun_energy": 0.5,
		"sun_shadow_enabled": true,
		"fill_rotation_degrees": Vector3(-20.0, 141.0, 0.0),
		"fill_color": Color(0.55, 0.55, 0.75),
		"fill_energy": 0.2,
	},
]


## Returns a Dictionary: sun_rotation_degrees (Vector3), sun_color (Color),
## sun_energy (float), sun_shadow_enabled (bool), fill_rotation_degrees
## (Vector3), fill_color (Color), fill_energy (float) — linearly
## interpolated between the two nearest keyframes in KEYFRAMES, wrapping
## across midnight. sun_shadow_enabled is not interpolated (bool) — it
## takes the value of whichever keyframe `hour` is closer to.
static func light_state_for_hour(hour: float) -> Dictionary:
	var h: float = fmod(hour, 24.0)
	if h < 0.0:
		h += 24.0

	var count := KEYFRAME_HOURS.size()
	var idx := 0
	for i in range(count):
		if KEYFRAME_HOURS[i] <= h:
			idx = i
	var next_idx := (idx + 1) % count

	var kf_hour: float = KEYFRAME_HOURS[idx]
	var next_kf_hour: float = KEYFRAME_HOURS[next_idx]
	if next_idx == 0:
		next_kf_hour += 24.0

	var span: float = next_kf_hour - kf_hour
	var t: float = 0.0 if span <= 0.0 else (h - kf_hour) / span

	var a: Dictionary = KEYFRAMES[idx]
	var b: Dictionary = KEYFRAMES[next_idx]

	return {
		"sun_rotation_degrees": (a.sun_rotation_degrees as Vector3).lerp(b.sun_rotation_degrees, t),
		"sun_color": (a.sun_color as Color).lerp(b.sun_color, t),
		"sun_energy": lerpf(a.sun_energy, b.sun_energy, t),
		"sun_shadow_enabled": a.sun_shadow_enabled if t < 0.5 else b.sun_shadow_enabled,
		"fill_rotation_degrees": (a.fill_rotation_degrees as Vector3).lerp(b.fill_rotation_degrees, t),
		"fill_color": (a.fill_color as Color).lerp(b.fill_color, t),
		"fill_energy": lerpf(a.fill_energy, b.fill_energy, t),
	}
```

- [ ] **Step 4: Re-import so Godot picks up the new `class_name`**

Run: `.tooling/godot --headless --path . --import`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_time_of_day_curve.gd --ignoreHeadlessMode`
Expected: PASS (5/5)

- [ ] **Step 6: Commit**

```bash
git add src/world/time_of_day_curve.gd tests/unit/test_time_of_day_curve.gd
git commit -m "feat(world): add TimeOfDayCurve pure lighting-interpolation helper"
```

---

### Task 2: `GameClock` autoload

**Files:**
- Create: `src/core/game_clock.gd`
- Test: `tests/unit/test_game_clock.gd`
- Modify: `project.godot` (register the autoload)

- [ ] **Step 1: Write the failing tests**

```gdscript
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_game_clock.gd --ignoreHeadlessMode`
Expected: FAIL — `GameClock`/`GameClockService` not found (autoload not registered, class doesn't exist yet).

- [ ] **Step 3: Write the implementation**

```gdscript
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
```

- [ ] **Step 4: Register the autoload in `project.godot`**

Open `project.godot` and find the `[autoload]` section:

```
[autoload]

InputBootstrap="*res://src/core/input_bootstrap.gd"
```

Add the new line so it reads:

```
[autoload]

InputBootstrap="*res://src/core/input_bootstrap.gd"
GameClock="*res://src/core/game_clock.gd"
```

- [ ] **Step 5: Re-import so Godot picks up the new autoload + `class_name`**

Run: `.tooling/godot --headless --path . --import`

- [ ] **Step 6: Run tests to verify they pass**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_game_clock.gd --ignoreHeadlessMode`
Expected: PASS (4/4)

- [ ] **Step 7: Commit**

```bash
git add src/core/game_clock.gd tests/unit/test_game_clock.gd project.godot
git commit -m "feat(core): add GameClock autoload for real-time-synced hour/weekday/date"
```

---

### Task 3: `TimeOfDayRig` per-zone node

**Files:**
- Create: `src/world/time_of_day_rig.gd`
- Test: `tests/unit/test_time_of_day_rig.gd`

- [ ] **Step 1: Write the failing test**

This builds a minimal scene by hand (a `Node3D` root with `Sun`/`Fill`
`DirectionalLight3D` children and a `TimeOfDayRig` sibling), pins
`GameClock.debug_override_hour` before the rig's `_ready()` runs, then
asserts the lights were driven to match `TimeOfDayCurve`'s output. Note
`TimeOfDayRig._apply_current()` runs once synchronously inside `_ready()`,
so a single simulated frame is enough — no need to wait on the 1s `Timer`.

```gdscript
extends GdUnitTestSuite
## TimeOfDayRig: drives a zone's Sun/Fill pair from GameClock + TimeOfDayCurve.
## See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.


func test_applies_curve_output_to_sun_and_fill_on_ready() -> void:
	GameClock.debug_override_hour = 12.0
	var root := Node3D.new()
	auto_free(root)
	var sun := DirectionalLight3D.new()
	sun.name = "Sun"
	root.add_child(sun)
	var fill := DirectionalLight3D.new()
	fill.name = "Fill"
	root.add_child(fill)
	var rig := Node.new()
	rig.name = "TimeOfDayRig"
	rig.set_script(load("res://src/world/time_of_day_rig.gd"))
	root.add_child(rig)

	var runner := scene_runner(root)
	await runner.simulate_frames(1)

	var expected := TimeOfDayCurve.light_state_for_hour(12.0)
	assert_vector(sun.rotation_degrees).is_equal_approx(expected.sun_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(sun.light_color.is_equal_approx(expected.sun_color)).is_true()
	assert_float(sun.light_energy).is_equal_approx(expected.sun_energy, 0.001)
	assert_bool(sun.shadow_enabled).is_equal(expected.sun_shadow_enabled)
	assert_vector(fill.rotation_degrees).is_equal_approx(expected.fill_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(fill.light_color.is_equal_approx(expected.fill_color)).is_true()
	assert_float(fill.light_energy).is_equal_approx(expected.fill_energy, 0.001)

	GameClock.debug_override_hour = null
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_time_of_day_rig.gd --ignoreHeadlessMode`
Expected: FAIL — `res://src/world/time_of_day_rig.gd` doesn't exist yet.

- [ ] **Step 3: Write the implementation**

```gdscript
class_name TimeOfDayRig
extends Node
## Drives a zone's Sun/Fill DirectionalLight3D pair from GameClock +
## TimeOfDayCurve, replacing what each zone's _stage() used to hard-code.
## Add as a child node in a zone's .tscn, sibling to its Sun/Fill lights.
## See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

@export var sun_path: NodePath = ^"../Sun"
@export var fill_path: NodePath = ^"../Fill"

const UPDATE_INTERVAL_SEC := 1.0

var _sun: DirectionalLight3D
var _fill: DirectionalLight3D
var _timer: Timer


func _ready() -> void:
	_sun = get_node_or_null(sun_path) as DirectionalLight3D
	_fill = get_node_or_null(fill_path) as DirectionalLight3D
	_apply_current()
	_timer = Timer.new()
	_timer.wait_time = UPDATE_INTERVAL_SEC
	_timer.timeout.connect(_apply_current)
	add_child(_timer)
	_timer.start()


func _apply_current() -> void:
	var state := TimeOfDayCurve.light_state_for_hour(GameClock.hour_of_day())
	if _sun != null:
		_sun.rotation_degrees = state.sun_rotation_degrees
		_sun.light_color = state.sun_color
		_sun.light_energy = state.sun_energy
		_sun.shadow_enabled = state.sun_shadow_enabled
	if _fill != null:
		_fill.rotation_degrees = state.fill_rotation_degrees
		_fill.light_color = state.fill_color
		_fill.light_energy = state.fill_energy
```

- [ ] **Step 4: Re-import so Godot picks up the new `class_name`**

Run: `.tooling/godot --headless --path . --import`

- [ ] **Step 5: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_time_of_day_rig.gd --ignoreHeadlessMode`
Expected: PASS (1/1)

- [ ] **Step 6: Commit**

```bash
git add src/world/time_of_day_rig.gd tests/unit/test_time_of_day_rig.gd
git commit -m "feat(world): add TimeOfDayRig to drive zone Sun/Fill from GameClock"
```

---

## Chunk 2: Zone migration + verification

### Task 4: Migrate `cottage_garden` to `TimeOfDayRig`

**Files:**
- Modify: `src/world/cottage_garden/cottage_garden.gd`
- Modify: `src/world/cottage_garden/cottage_garden.tscn`
- Modify: `tests/unit/test_cottage_garden.gd`

- [ ] **Step 1: Add a failing scene test for the new `TimeOfDayRig` node**

Append to `tests/unit/test_cottage_garden.gd`:

```gdscript
func test_cottage_garden_has_time_of_day_rig_driving_sun_and_fill() -> void:
	GameClock.debug_override_hour = 12.0
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(2)
	var garden := runner.scene()

	var rig := garden.get_node_or_null("TimeOfDayRig")
	assert_object(rig).override_failure_message(
		"expected a TimeOfDayRig node in cottage_garden.tscn"
	).is_not_null()

	var expected := TimeOfDayCurve.light_state_for_hour(12.0)
	var sun := garden.get_node("Sun") as DirectionalLight3D
	var fill := garden.get_node("Fill") as DirectionalLight3D
	assert_vector(sun.rotation_degrees).is_equal_approx(expected.sun_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(sun.light_color.is_equal_approx(expected.sun_color)).is_true()
	assert_float(sun.light_energy).is_equal_approx(expected.sun_energy, 0.001)
	assert_bool(sun.shadow_enabled).is_equal(expected.sun_shadow_enabled)
	assert_vector(fill.rotation_degrees).is_equal_approx(expected.fill_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(fill.light_color.is_equal_approx(expected.fill_color)).is_true()
	assert_float(fill.light_energy).is_equal_approx(expected.fill_energy, 0.001)

	GameClock.debug_override_hour = null
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_cottage_garden.gd --ignoreHeadlessMode`
Expected: FAIL — no `TimeOfDayRig` node in the scene yet (`garden.get_node_or_null("TimeOfDayRig")` is null).

- [ ] **Step 3: Remove the hard-coded `_stage()` lighting and add the node**

In `src/world/cottage_garden/cottage_garden.gd`, delete `_stage()` entirely
(today it does nothing besides Sun/Fill setup) and its call from `_ready()`:

```gdscript
extends Node3D
## The cottage garden — Phase 4's first tooling-built zone.

# Fixed seed so the scene test's node lookup and screenshot captures are
# reproducible — see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §7.
const DEMO_VILLAGER_SEED := 20260810


func _ready() -> void:
	_add_demo_villager()


func _add_demo_villager() -> void:
	var dna := VillagerDna.random(DEMO_VILLAGER_SEED)
	var villager := VillagerFactory.build(dna)
	villager.name = "DemoVillager"
	# Near the well, facing the cottage — a static proof-of-concept only,
	# no interaction/dialogue/AI (that's future gameplay-phase work).
	villager.position = Vector3(1.6, 0.0, 2.2)
	add_child(villager)
```

In `src/world/cottage_garden/cottage_garden.tscn`, add a new `ext_resource` for the script near the top (alongside the other
`ext_resource` lines) and the new node after `Fill`. This scene's current
header is `[gd_scene load_steps=7 format=3]` — bump `load_steps` to `8`
since a new `ext_resource` is being added:

```
[gd_scene load_steps=8 format=3]
```

```
[ext_resource type="Script" path="res://src/world/time_of_day_rig.gd" id="5_time_of_day"]
```

```
[node name="TimeOfDayRig" type="Node" parent="."]
script = ExtResource("5_time_of_day")
```

- [ ] **Step 4: Re-import**

Run: `.tooling/godot --headless --path . --import`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_cottage_garden.gd --ignoreHeadlessMode`
Expected: PASS (3/3 — the two existing tests plus the new one)

- [ ] **Step 6: Commit**

```bash
git add src/world/cottage_garden/cottage_garden.gd src/world/cottage_garden/cottage_garden.tscn tests/unit/test_cottage_garden.gd
git commit -m "refactor(cottage_garden): replace static lighting with TimeOfDayRig"
```

---

### Task 5: Migrate `hedgerow_lane` to `TimeOfDayRig`

**Files:**
- Modify: `src/world/hedgerow_lane/hedgerow_lane.gd`
- Modify: `src/world/hedgerow_lane/hedgerow_lane.tscn`
- Modify: `tests/unit/test_hedgerow_lane.gd`

- [ ] **Step 1: Add a failing scene test for the new `TimeOfDayRig` node**

Append to `tests/unit/test_hedgerow_lane.gd`:

```gdscript
func test_hedgerow_lane_has_time_of_day_rig_driving_sun_and_fill() -> void:
	GameClock.debug_override_hour = 12.0
	var runner := scene_runner(HEDGEROW_LANE_SCENE)
	await runner.simulate_frames(2)
	var lane := runner.scene()

	var rig := lane.get_node_or_null("TimeOfDayRig")
	assert_object(rig).override_failure_message(
		"expected a TimeOfDayRig node in hedgerow_lane.tscn"
	).is_not_null()

	var expected := TimeOfDayCurve.light_state_for_hour(12.0)
	var sun := lane.get_node("Sun") as DirectionalLight3D
	var fill := lane.get_node("Fill") as DirectionalLight3D
	assert_vector(sun.rotation_degrees).is_equal_approx(expected.sun_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(sun.light_color.is_equal_approx(expected.sun_color)).is_true()
	assert_float(sun.light_energy).is_equal_approx(expected.sun_energy, 0.001)
	assert_bool(sun.shadow_enabled).is_equal(expected.sun_shadow_enabled)
	assert_vector(fill.rotation_degrees).is_equal_approx(expected.fill_rotation_degrees, Vector3(0.01, 0.01, 0.01))
	assert_bool(fill.light_color.is_equal_approx(expected.fill_color)).is_true()
	assert_float(fill.light_energy).is_equal_approx(expected.fill_energy, 0.001)

	GameClock.debug_override_hour = null
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_hedgerow_lane.gd --ignoreHeadlessMode`
Expected: FAIL — no `TimeOfDayRig` node in the scene yet.

- [ ] **Step 3: Remove the hard-coded `_stage()` lighting and add the node**

`src/world/hedgerow_lane/hedgerow_lane.gd`'s `_ready()` only ever called
`_stage()`, and `_stage()` only ever did Sun/Fill setup — delete both:

```gdscript
extends Node3D
## The hedgerow lane — Phase 4's village dressing first pass.
```

In `src/world/hedgerow_lane/hedgerow_lane.tscn`, add the same
`ext_resource` + `TimeOfDayRig` node as Task 4, sibling to `Sun`/`Fill`.
This scene's current header is also `[gd_scene load_steps=7 format=3]` —
bump `load_steps` to `8`:

```
[gd_scene load_steps=8 format=3]
```

```
[ext_resource type="Script" path="res://src/world/time_of_day_rig.gd" id="5_time_of_day"]
```

```
[node name="TimeOfDayRig" type="Node" parent="."]
script = ExtResource("5_time_of_day")
```

(Confirmed: neither `cottage_garden.tscn` nor `hedgerow_lane.tscn` uses
`id="5_..."` for any existing `ext_resource`, so `id="5_time_of_day"` is
free to use in both without collision.)

- [ ] **Step 4: Re-import**

Run: `.tooling/godot --headless --path . --import`

- [ ] **Step 5: Run tests to verify they pass**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_hedgerow_lane.gd --ignoreHeadlessMode`
Expected: PASS (2/2 — the existing test plus the new one)

- [ ] **Step 6: Commit**

```bash
git add src/world/hedgerow_lane/hedgerow_lane.gd src/world/hedgerow_lane/hedgerow_lane.tscn tests/unit/test_hedgerow_lane.gd
git commit -m "refactor(hedgerow_lane): replace static lighting with TimeOfDayRig"
```

---

### Task 6: Full verification + docs

**Files:**
- Modify: `ROADMAP.md`

- [ ] **Step 1: Run the full gdUnit suite**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit --ignoreHeadlessMode`
Expected: current confirmed baseline (re-verified at plan-writing time) is
**99 test cases, 3 failures**, all pre-existing and unrelated to this plan:
`test_interact.gd`'s `test_score_prefers_near_centered_important`, and two
failing assertions within `test_avatar.gd:30` (missing `wave` and `stir`
animation clips). This plan adds 12 new test cases across Tasks 1–5 (5 in
`test_time_of_day_curve.gd`, 4 in `test_game_clock.gd`, 1 in
`test_time_of_day_rig.gd`, 1 in `test_cottage_garden.gd`, 1 in
`test_hedgerow_lane.gd`), so the expected new total is **111 test cases,
still exactly 3 failures** (the same pre-existing ones, unchanged) — if the
failure count is anything other than 3, or if the failing test names don't
match the three above, stop and investigate before proceeding (do not
assume it's unrelated).

Also re-run the zone budget tests explicitly to confirm no tri/node-count
regression (the spec calls this out since `TimeOfDayRig`/`Timer` are new
nodes, even though they add no `MeshInstance3D`s):

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_budget.gd --ignoreHeadlessMode`
Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_lane_budget.gd --ignoreHeadlessMode`
Expected: both PASS, unchanged from before this plan.

- [ ] **Step 2: Manually verify a visual sanity check (optional but recommended)**

Since `--headless` can't render, if a real GL context is available, launch
`cottage_garden.tscn` briefly (non-headless) with
`GameClock.debug_override_hour` unset (real time) and confirm the lighting
looks sane for the actual time of day — this is a spot-check, not a gated
step, since the noon keyframe regression is already covered by Task 4's
automated test.

- [ ] **Step 3: Update `ROADMAP.md`**

Find the Phase 4 (World & Time) section's T4.5 line and mark the
clock/time-of-day portion done, noting weather-lite and Patch Day/drift
hooks remain as separate deferred follow-up work (per
`docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md`'s explicit
scope split). Read the current T4.5 line's exact wording in `ROADMAP.md`
first and edit it in place rather than guessing its format — do not
reformat unrelated roadmap lines.

- [ ] **Step 4: Commit**

```bash
git add ROADMAP.md
git commit -m "docs: mark T4.5 clock + time-of-day complete in ROADMAP"
```
