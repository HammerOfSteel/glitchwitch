class_name PaletteUv
extends RefCounted
## Loads assets/generated/palette_uv.json (written by `make assets` via
## tools/assetgen/palette.py's build_palette_uv_json()) and exposes each
## ramp/shade cell's UV point, plus a helper to stamp that UV onto every
## vertex of a runtime-built primitive mesh (CapsuleMesh, SphereMesh, ...)
## so it samples the correct flat color from the shared toon palette
## material — see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §4.

const JSON_PATH := "res://assets/generated/palette_uv.json"

static var _cache: Dictionary = {}
static var _loaded := false


## Parses palette_uv.json text into a Dictionary, or returns {} (with a
## warning) if the text isn't valid JSON or isn't a JSON object. Split out
## from file I/O so it's directly unit-testable without touching disk.
static func _parse_json(text: String) -> Dictionary:
	var parsed = JSON.parse_string(text)
	if parsed == null or not (parsed is Dictionary):
		push_warning("palette_uv.json failed to parse — run `make assets` again")
		return {}
	return parsed


## Loads and parses the JSON at `path`, returning {} (with a warning) if the
## file doesn't exist or can't be opened. Split out from the module-level
## `_loaded`/`_cache` singletons so the "missing file" fallback path is
## directly unit-testable without disturbing global state.
static func _load_from_path(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		push_warning("palette_uv.json unavailable — run `make assets` first")
		return {}
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_warning("palette_uv.json could not be opened (err %d)" % FileAccess.get_open_error())
		return {}
	return _parse_json(file.get_as_text())


static func _ensure_loaded() -> void:
	if _loaded:
		return
	_loaded = true
	_cache = _load_from_path(JSON_PATH)


## UV center of a palette cell for the given ramp/shade, or Vector2.ZERO
## (with a warning) if the file is missing, malformed, or the pair isn't
## found — mirrors PaletteApply.apply()'s "degrade, don't crash" convention.
static func uv_for(ramp: StringName, shade: int) -> Vector2:
	_ensure_loaded()
	var key := "%s/%d" % [ramp, shade]
	if not _cache.has(key):
		push_warning("PaletteUv: unknown ramp/shade %s" % key)
		return Vector2.ZERO
	var pair = _cache[key]
	var is_valid_pair: bool = pair is Array and pair.size() == 2 \
		and (pair[0] is float or pair[0] is int) \
		and (pair[1] is float or pair[1] is int)
	if not is_valid_pair:
		push_warning("PaletteUv: malformed cache entry for %s" % key)
		return Vector2.ZERO
	return Vector2(pair[0], pair[1])


## Returns a new ArrayMesh identical to `primitive` except every vertex's
## UV is overwritten to a single constant point — the same "one flat color
## per mesh" technique tools/assetgen/mesh.py's add_face() uses for props,
## applied at runtime instead of at Python-build-time. NOTE: per the spec's
## ownership boundary (§4), VillagerRig is the sole caller of stamp_mesh() —
## no other code should call it directly.
static func stamp_mesh(primitive: Mesh, ramp: StringName, shade: int) -> ArrayMesh:
	var uv := uv_for(ramp, shade)
	var arrays := primitive.surface_get_arrays(0)
	var vertex_count: int = (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
	var flat_uvs := PackedVector2Array()
	flat_uvs.resize(vertex_count)
	flat_uvs.fill(uv)
	arrays[Mesh.ARRAY_TEX_UV] = flat_uvs
	var array_mesh := ArrayMesh.new()
	array_mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	return array_mesh
