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
