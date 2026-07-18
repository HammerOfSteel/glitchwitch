extends Node
## Boot scene — prints the banner and confirms the ritual space is intact.

@onready var _banner: Label = %Banner


func _ready() -> void:
	var version := str(ProjectSettings.get_setting("application/config/version", "0.0.0-dev"))
	_banner.text = "GLITCH WITCH\ndev build %s\n\nthe kettle is on." % version
	print("glitchwitch %s — the kettle is on." % version)
