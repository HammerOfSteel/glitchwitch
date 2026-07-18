extends Node
## CLI look-dev screenshot runner.
##
## Usage (needs a GL context — CI uses xvfb + llvmpipe):
##   godot --path . res://src/lookdev/screenshot.tscn
## Captures every scene in CAPTURES into artifacts/ and quits 0 on success.

const CAPTURES := {
	"lookdev_diorama": "res://src/lookdev/diorama.tscn",
	"sandbox_glade": "res://src/sandbox/glade.tscn",
}
const SETTLE_FRAMES := 10


func _ready() -> void:
	_run()


func _run() -> void:
	var failures := 0
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path("res://artifacts"))
	for capture_name: String in CAPTURES:
		var packed := load(CAPTURES[capture_name]) as PackedScene
		if packed == null:
			push_error("cannot load scene for capture: %s" % capture_name)
			failures += 1
			continue
		var scene := packed.instantiate()
		add_child(scene)
		for _i in range(SETTLE_FRAMES):
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var image := get_viewport().get_texture().get_image()
		if image == null or image.is_empty():
			push_error("viewport capture failed (headless renderer?)")
			failures += 1
		else:
			var path := "res://artifacts/%s.png" % capture_name
			var error := image.save_png(ProjectSettings.globalize_path(path))
			print("screenshot -> %s (err=%d)" % [path, error])
			if error != OK:
				failures += 1
		remove_child(scene)
		scene.queue_free()
		await get_tree().process_frame
	get_tree().quit(0 if failures == 0 else 1)
