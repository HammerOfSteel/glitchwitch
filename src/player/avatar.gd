class_name WrenAvatar
extends Node3D
## Wren's body: instances a character GLB, optionally dresses it in the
## palette, and drives its clips from the player's motion state.
##
## PIVOT NOTE (placeholder-first phase): character art generation moved
## external (Meshy AI / free packs) rather than the in-house procedural
## pipeline. Until real Wren art lands, this loads a placeholder GLB built
## from a rigged/animated Seren (Meshy AI) export via
## `tools/assetgen/placeholders/fetch_wren_placeholder.py` — see
## docs/superpowers/specs/2026-08-08-external-asset-pivot-design.md.
## That placeholder ships its own baked material and only has idle/walk/run
## clips (no wave/stir), so palette dressing and gesture playback are
## skipped gracefully when it's active. Swap PLACEHOLDER_SCENE_PATH back to
## the v1-procedural WREN_SCENE_PATH below once real art replaces it.
##
## Import note: clips are authored with "-loop" suffixes; Godot's importer
## strips the suffix and enables looping, so in-engine names are
## idle / walk / run (looping) and wave / stir (one-shot gestures).

const WREN_SCENE_PATH := "res://assets/generated/wren.glb"
const PLACEHOLDER_SCENE_PATH := "res://assets/thirdparty/wren_placeholder/wren_placeholder.glb"
const USE_PLACEHOLDER := true
const BLEND_TIME := 0.25
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
	var scene_path := PLACEHOLDER_SCENE_PATH if USE_PLACEHOLDER else WREN_SCENE_PATH
	var packed := load(scene_path) as PackedScene
	if packed == null and USE_PLACEHOLDER:
		# Fall back to the procedural body if the placeholder hasn't been
		# built locally yet (`fetch_wren_placeholder.py` not run).
		push_warning(
			"wren_placeholder.glb unavailable — run "
			+ "tools/assetgen/placeholders/fetch_wren_placeholder.py, "
			+ "falling back to procedural wren.glb"
		)
		scene_path = WREN_SCENE_PATH
		packed = load(scene_path) as PackedScene
	if packed == null:
		push_warning("wren body unavailable — run `make assets` first")
		return
	_is_placeholder = scene_path == PLACEHOLDER_SCENE_PATH
	add_child(packed.instantiate())
	if not _is_placeholder:
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
