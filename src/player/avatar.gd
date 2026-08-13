class_name WrenAvatar
extends Node3D
## Wren's body: instances a character GLB, optionally dresses it in the
## palette, and drives its clips from the player's motion state.
##
## SOURCING NOTE: character art generation moved external (Meshy AI) rather
## than the in-house procedural pipeline - see
## docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md.
## Wren's real body now loads from a Meshy AI dressed/rigged/animated export,
## merged into a single GLB (idle/walk/run clips only - Meshy's stock combat/
## swim/sleep library clips are dropped since this is a no-combat game) via
## `tools/assetgen/meshy_import/import_wren_meshy.py`. If that hasn't been
## built locally yet, this falls back to the earlier Seren-based placeholder
## GLB, then to the v1-procedural WREN_SCENE_PATH.
##
## Import note: clips are authored with "-loop" suffixes; Godot's importer
## strips the suffix and enables looping, so in-engine names are
## idle / walk / run (looping) and wave / stir (one-shot gestures).

const WREN_SCENE_PATH := "res://assets/generated/wren.glb"
const PLACEHOLDER_SCENE_PATH := "res://assets/thirdparty/wren_placeholder/wren_placeholder.glb"
const MESHY_WREN_SCENE_PATH := "res://assets/thirdparty/meshy-ai/wren/wren.glb"
const USE_PLACEHOLDER := true
const BLEND_TIME := 0.25
# Player's CharacterBody3D rests with its origin ~0.15m below the floor
# (capsule bottom = capsule offset 0.7 - height/2 0.55 = 0.15), so its feet
# touch the ground. The procedural wren.glb bakes that offset into its own
# root; the externally-sourced Meshy exports don't, so their feet render
# sunk into the ground without this compensating lift.
const PLACEHOLDER_GROUND_OFFSET := 0.15
const MOTION_CLIPS: Dictionary = {
	&"idle": &"idle",
	&"walk": &"walk",
	&"run": &"run",
}
const GESTURE_CLIPS: Dictionary = {
	&"wave": &"wave",
	&"stir": &"stir",
}

var _anim: AnimationPlayer = null
var _motion: StringName = &"idle"
var _gesturing := false
var _is_placeholder := false


func _ready() -> void:
	var scene_path := MESHY_WREN_SCENE_PATH
	var packed := load(scene_path) as PackedScene
	if packed == null and USE_PLACEHOLDER:
		# Fall back to the earlier Seren-based placeholder if the real Wren
		# GLB hasn't been built locally yet
		# (`tools/assetgen/meshy_import/import_wren_meshy.py` not run).
		push_warning(
			(
				"meshy-ai/wren/wren.glb unavailable — run "
				+ "tools/assetgen/meshy_import/import_wren_meshy.py, "
				+ "falling back to wren_placeholder.glb"
			)
		)
		scene_path = PLACEHOLDER_SCENE_PATH
		packed = load(scene_path) as PackedScene
	if packed == null:
		# Fall back further to the procedural body if neither Meshy export
		# has been built locally yet.
		push_warning("wren_placeholder.glb unavailable — falling back to procedural " + "wren.glb")
		scene_path = WREN_SCENE_PATH
		packed = load(scene_path) as PackedScene
	if packed == null:
		push_warning("wren body unavailable — run `make assets` first")
		return
	_is_placeholder = scene_path == PLACEHOLDER_SCENE_PATH or scene_path == MESHY_WREN_SCENE_PATH
	var body := packed.instantiate() as Node3D
	add_child(body)
	if _is_placeholder:
		# Meshy AI exports' rest pose faces +Z (its own "front"), opposite
		# AvatarMount's -Z-forward convention that MovementMath's facing
		# calculations assume — without this the avatar walks
		# backward-facing relative to its direction of travel.
		body.rotation.y = PI
		body.position.y = PLACEHOLDER_GROUND_OFFSET
	else:
		PaletteApply.apply(self)
	var players := find_children("*", "AnimationPlayer", true, false)
	if not players.is_empty():
		_anim = players[0] as AnimationPlayer
		_anim.animation_finished.connect(_on_animation_finished)
	_play_motion()


func set_motion_state(state: StringName) -> void:
	_motion = state if MOTION_CLIPS.has(state) else &"idle"
	if not _gesturing:
		_play_motion()


func play_gesture(gesture: StringName) -> void:
	if _anim == null or not GESTURE_CLIPS.has(gesture):
		return
	var clip := String(GESTURE_CLIPS[gesture] as StringName)
	if not _anim.has_animation(clip):
		# Placeholder body has no gesture clips yet — no-op rather than error.
		return
	_gesturing = true
	_anim.play(clip, BLEND_TIME)


func stop_gesture() -> void:
	if not _gesturing:
		return
	_gesturing = false
	_play_motion()


func is_gesturing() -> bool:
	return _gesturing


func current_clip() -> String:
	if _anim == null:
		return ""
	return _anim.current_animation


func animation_player() -> AnimationPlayer:
	return _anim


func _play_motion() -> void:
	if _anim == null:
		return
	var clip := String(MOTION_CLIPS[_motion] as StringName)
	if _anim.current_animation != clip:
		_anim.play(clip, BLEND_TIME)


func _on_animation_finished(_clip: StringName) -> void:
	_gesturing = false
	_play_motion()
