# Clock + Time-of-Day — Design Spec

**Status:** Approved by project owner, ready for implementation planning.
**Phase:** 4 — World & Time (`phase/04-world`), T4.5 (partial — clock + time-of-day
only; weather-lite and Patch Day/drift-quest hooks are deferred to follow-up specs).

## Goal

Give the game a real, shared notion of time-of-day that drives zone lighting,
replacing each zone's currently hard-coded static Sun/Fill light setup. Time
should sync to the real-world wall clock (simple v1: the player's local
system time, 1:1 — no solar/lat-long calculation yet), and expose weekday
math so later systems (Patch Day's weekly ritual, Phase 10; daily drift
quests, Phase 5/10) have a real clock to hook into.

## Explicitly out of scope for this spec

- Weather-lite (a separate, smaller follow-up spec once the clock exists).
- Sky/ambient (`WorldEnvironment`) color shifts across the day — only the
  `Sun`/`Fill` `DirectionalLight3D` nodes are driven by time-of-day in this
  pass.
- Real sunrise/sunset solar calculation for a configured lat/long — v1 just
  reads the OS's local time directly. A `utc_offset_hours` var is reserved
  on `GameClock` for future refinement but is inert (unused) in v1.
- In-fiction day names — weekdays are exposed as real-world Gregorian
  Monday..Sunday.
- Any change to `cottage_interior` — it has no `Sun`/`Fill` nodes (only
  `HearthLight`/`WindowLight` mood `OmniLight3D`s), so it is untouched by
  this spec.
- Patch Day and drift-quest systems themselves (Phase 5/10) — this spec only
  makes the weekday/date data available for them to consume later.

## Architecture

Two new pieces:

1. **`GameClock`** — an autoload singleton holding time data, sourced from
   Godot's `Time` singleton (which already reports local system time).
2. **`TimeOfDayRig`** — a reusable per-zone `Node` script, instanced as a
   scene-tree sibling of each zone's existing `Sun`/`Fill` lights, that
   polls `GameClock` on a slow timer and applies interpolated lighting via a
   third, pure helper:
3. **`TimeOfDayCurve`** — a pure, stateless helper (`RefCounted` with static
   methods) mapping an hour-of-day float to a lighting-state `Dictionary`.
   Being pure and scene-independent, it's directly gdUnit-testable without a
   running scene tree or real time dependency.

```
GameClock (autoload)          TimeOfDayCurve (pure helper)         TimeOfDayRig (per-zone node)
  hour_of_day() -> float  --->  light_state_for_hour(hour)   --->   applies result to
  weekday()      -> enum                                             this zone's Sun/Fill
  date_string()  -> String
  debug_override_hour (test hook)
```

## `GameClock` (`src/core/game_clock.gd`)

New autoload singleton, registered in `project.godot`'s `[autoload]` section
alongside the existing `InputBootstrap`:

```
[autoload]
InputBootstrap="*res://src/core/input_bootstrap.gd"
GameClock="*res://src/core/game_clock.gd"
```

```gdscript
class_name GameClockService
extends Node
## Real-time-synced game clock: exposes the current hour-of-day, weekday,
## and date, sourced from the OS's local system time via Godot's `Time`
## singleton. v1 is a direct 1:1 mapping (no solar/lat-long calculation) —
## see docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

enum Weekday { MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY, SATURDAY, SUNDAY }

## Placeholder for future timezone/location refinement. Inert in v1 — the
## game currently just uses whatever local time zone the OS reports.
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

**Note on the `weekday()` remap:** Godot's `Time` singleton returns
`weekday` as `0 == Sunday .. 6 == Saturday` (see `Time.Weekday` constants).
This spec's `Weekday` enum instead starts at Monday (a common
convention for "day of the week" in game/quest logic, and avoids Sunday
being day 0 which reads oddly next to "day 1 of the week"). The
`(godot_weekday + 6) % 7` conversion handles this remap; implementer should
verify this arithmetic with a concrete test case (e.g. confirm a known
Sunday date maps to `Weekday.SUNDAY == 6`).

## `TimeOfDayCurve` (`src/world/time_of_day_curve.gd`)

```gdscript
class_name TimeOfDayCurve
extends RefCounted
## Pure hour-of-day -> lighting-state mapping for Sun/Fill DirectionalLight3D
## pairs. No scene/autoload dependency — testable in isolation.
## See docs/superpowers/specs/2026-08-12-clock-time-of-day-design.md.

## Keyframe hours, in ascending order, wrapping at 24 (the last keyframe
## interpolates toward the first keyframe + 24 across midnight).
const KEYFRAME_HOURS := [0.0, 6.0, 12.0, 19.0]

# Keyframe values in the same order as KEYFRAME_HOURS. The 12:00 (noon)
# entry's sun/fill values are copied verbatim from what every zone's
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

(Exact numeric keyframe values above are a reasonable starting point for
the implementer to use verbatim; if the implementer or a screenshot review
finds night/dawn/dusk look implausible in practice, they may tune the
non-noon keyframe numbers — but the noon keyframe must stay byte-identical
to today's hard-coded values, and the overall structure/algorithm above
must not change without a design update.)

## `TimeOfDayRig` (`src/world/time_of_day_rig.gd`)

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

## Zone migration

`cottage_garden.gd` and `hedgerow_lane.gd` each have their `_stage()`
function's Sun/Fill-setting lines removed entirely (any other future
`_stage()` responsibilities, if added later, are unaffected — today neither
file's `_stage()` does anything besides this lighting setup, so `_stage()`
itself may end up empty/removable; implementer should check whether keeping
an empty `_stage()` call is worth preserving vs. deleting the function and
its `_ready()` call — prefer deleting for cleanliness since dead code is
worse than a slightly different `_ready()` shape).

Each zone's `.tscn` gets one new node added: a `Node` named `TimeOfDayRig`
with script `res://src/world/time_of_day_rig.gd`, sibling to the existing
`Sun`/`Fill` nodes, using the script's default `sun_path`/`fill_path`
(`../Sun`, `../Fill`) unchanged since both zones' lights are already named
exactly `Sun`/`Fill` at the same tree depth.

`cottage_interior.gd`/`.tscn` — **no changes**. It has no `Sun`/`Fill`
nodes (only `HearthLight`/`WindowLight` `OmniLight3D` mood lights), which
this spec deliberately does not touch.

## Testing

1. **`test_time_of_day_curve.gd`** (new, pure — no scene tree needed):
   - `light_state_for_hour(12.0)` returns exactly today's hard-coded noon
     values (regression guard against visual drift at the reference hour).
   - `light_state_for_hour(0.0)` returns the night keyframe values exactly.
   - A midpoint test (e.g. `light_state_for_hour(9.0)`, halfway between the
     6:00 dawn and 12:00 day keyframes) returns values that are the
     arithmetic mean of the two keyframes (proves linear interpolation
     actually runs, not just keyframe pass-through).
   - A midnight-wraparound test (e.g. `light_state_for_hour(22.0)`,
     between the 19:00 dusk keyframe and the 24:00-wrapped 0:00 night
     keyframe) returns a plausible interpolated value, not a crash/garbage
     value — proves the wraparound math (`next_kf_hour += 24.0`) is
     correct.
   - `sun_shadow_enabled` takes the nearer keyframe's boolean (not
     interpolated) — test both sides of the `t < 0.5` boundary.

2. **`test_game_clock.gd`** (new):
   - With `debug_override_hour` set to a specific float, `hour_of_day()`
     returns exactly that value (proves the test hook works and doesn't
     fall through to reading real system time).
   - `weekday()` returns a value in the `GameClockService.Weekday` enum's
     valid range (can't assert an exact day since it depends on real wall
     time, but confirm the type/range is sane, and confirm the
     Sunday-remap arithmetic is correct by computing it independently in
     the test and comparing — e.g. assert `weekday()` matches
     `(Time.get_datetime_dict_from_system().weekday + 6) % 7` computed
     directly in the test body).
   - `date_string()` matches Godot's own `Time.get_datetime_dict_from_system()`
     fields formatted the same way (again, computed independently in the
     test body since the exact date is real-time-dependent).

3. **Zone scene tests** (extend `test_cottage_garden.gd` and add analogous
   coverage to `hedgerow_lane`'s existing test, or add one new shared test
   if a common zone-lighting-verification helper doesn't already exist —
   implementer's judgment): with `GameClock.debug_override_hour` pinned to
   `12.0` before the scene loads, load the zone, confirm its `Sun`/`Fill`
   nodes' `rotation_degrees`/`light_color`/`light_energy` match
   `TimeOfDayCurve.light_state_for_hour(12.0)` exactly — proves the full
   wiring (`TimeOfDayRig` reading `GameClock` and applying
   `TimeOfDayCurve`'s output to the real nodes) works end-to-end, and
   that noon still looks like today's static look (no visual regression).
   Remember to reset `GameClock.debug_override_hour` back to `null` after
   each such test so it doesn't leak into unrelated tests run later in the
   same suite.

4. **Zone budget tests** (`test_zone_budget.gd`) — re-run, unaffected in
   principle since `TimeOfDayRig`/`Timer` add no `MeshInstance3D`s, but
   confirm no regression as a matter of course.

## Non-goals / explicitly deferred (for later specs, not this one)

- Weather-lite.
- Patch Day weekly ritual logic itself (Phase 10) — this spec only makes
  `weekday()`/`date_string()` available for it to consume.
- Daily drift-quest RNG seeding (Phase 5/10) — same; `date_string()` is
  intended as a future seed input, not implemented as one here.
- Real solar/lat-long sunrise-sunset calculation — `utc_offset_hours`
  exists as an inert placeholder field only.
- Sky/ambient `WorldEnvironment` color shifts.
