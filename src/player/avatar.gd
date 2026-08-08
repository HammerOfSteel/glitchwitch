class_name WrenAvatar
extends Node3D
## Wren's generated body: instances the wren GLB, dresses it in the palette,
## and drives its clips from the player's motion state.
##
## Import note: clips are authored with "-loop" suffixes; Godot's importer
## strips the suffix and enables looping, so in-engine names are
## idle / walk / run (looping) and wave / stir (one-shot gestures).

const WREN_SCENE_PATH := "res://assets/generated/wren.glb"
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


func _ready() -> void:
	var packed := load(WREN_SCENE_PATH) as PackedScene
	if packed == null:
		push_warning("wren.glb unavailable — run `make assets` first")
		return
	add_child(packed.instantiate())
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
	_gesturing = true
	_anim.play(GESTURE_CLIPS[gesture], BLEND_TIME)


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
