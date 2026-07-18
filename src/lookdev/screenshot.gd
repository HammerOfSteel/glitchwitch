extends Node
## CLI look-dev screenshot runner.
##
## Usage (needs a GL context — CI uses xvfb + llvmpipe):
##   godot --path . res://src/lookdev/screenshot.tscn
## Writes artifacts/lookdev_diorama.png and quits with 0 on success.

const DIORAMA_PATH := "res://src/lookdev/diorama.tscn"
const OUTPUT_PATH := "res://artifacts/lookdev_diorama.png"
const SETTLE_FRAMES := 8


func _ready() -> void:
	var packed := load(DIORAMA_PATH) as PackedScene
	if packed == null:
		push_error("cannot load diorama scene")
		get_tree().quit(1)
		return
	add_child(packed.instantiate())
	_capture()


func _capture() -> void:
	for _i in range(SETTLE_FRAMES):
		await get_tree().process_frame
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	if image == null or image.is_empty():
		push_error("viewport capture failed (headless renderer?)")
		get_tree().quit(1)
		return
	var dir_path := ProjectSettings.globalize_path("res://artifacts")
	DirAccess.make_dir_recursive_absolute(dir_path)
	var error := image.save_png(ProjectSettings.globalize_path(OUTPUT_PATH))
	print("lookdev screenshot -> %s (err=%d)" % [OUTPUT_PATH, error])
	get_tree().quit(0 if error == OK else 1)
