extends GdUnitTestSuite
## PaletteUv: loads assets/generated/palette_uv.json and stamps flat UVs
## onto primitive meshes so they sample the correct toon palette cell.


func test_uv_for_known_ramp_shade_is_within_unit_square() -> void:
	assert_bool(FileAccess.file_exists(PaletteUv.JSON_PATH)) \
		.override_failure_message("missing palette_uv.json (run `make assets`)").is_true()
	var uv := PaletteUv.uv_for(&"cream", 3)
	assert_float(uv.x).is_greater(0.0)
	assert_float(uv.y).is_greater(0.0)
	assert_float(uv.x).is_less(1.0)
	assert_float(uv.y).is_less(1.0)


func test_uv_for_unknown_ramp_warns_and_returns_zero() -> void:
	var uv := PaletteUv.uv_for(&"not_a_real_ramp", 0)
	assert_vector(uv).is_equal(Vector2.ZERO)


func test_uv_for_malformed_cache_entry_returns_zero() -> void:
	# Directly exercises the "malformed pair" degrade path without needing a
	# real broken palette_uv.json on disk: inject a bad entry into the
	# static cache, then restore it so other tests aren't affected.
	PaletteUv._ensure_loaded()
	var saved: Dictionary = PaletteUv._cache.duplicate()
	PaletteUv._cache["broken/9"] = "not_an_array"
	var uv := PaletteUv.uv_for(&"broken", 9)
	assert_vector(uv).is_equal(Vector2.ZERO)
	PaletteUv._cache = saved


func test_uv_for_wrong_length_array_entry_returns_zero() -> void:
	# An array-shaped entry with the wrong element count (e.g. truncated or
	# extended JSON) must also degrade instead of indexing out of bounds.
	PaletteUv._ensure_loaded()
	var saved: Dictionary = PaletteUv._cache.duplicate()
	PaletteUv._cache["broken/9"] = [0.5]
	var uv := PaletteUv.uv_for(&"broken", 9)
	assert_vector(uv).is_equal(Vector2.ZERO)
	PaletteUv._cache = saved


func test_uv_for_non_numeric_pair_returns_zero() -> void:
	# A pair that is an Array of the right length but wrong element types
	# (e.g. corrupted JSON) must also degrade instead of crashing.
	PaletteUv._ensure_loaded()
	var saved: Dictionary = PaletteUv._cache.duplicate()
	PaletteUv._cache["broken/9"] = ["not", "numbers"]
	var uv := PaletteUv.uv_for(&"broken", 9)
	assert_vector(uv).is_equal(Vector2.ZERO)
	PaletteUv._cache = saved


func test_parse_json_returns_empty_dict_on_malformed_text() -> void:
	# Exercises the JSON-parse-failure fallback directly, without needing a
	# real corrupted file on disk.
	var result := PaletteUv._parse_json("{not valid json")
	assert_dict(result).is_empty()


func test_parse_json_returns_empty_dict_on_non_dict_json() -> void:
	var result := PaletteUv._parse_json("[1, 2, 3]")
	assert_dict(result).is_empty()


func test_load_from_missing_path_warns_and_yields_empty_cache() -> void:
	# Exercises the "file does not exist" fallback directly via the
	# path-parametrized loader seam, without touching the real JSON_PATH
	# or the module-level _loaded/_cache singletons.
	var result := PaletteUv._load_from_path("res://assets/generated/does_not_exist.json")
	assert_dict(result).is_empty()


func test_stamp_mesh_gives_every_vertex_the_same_uv() -> void:
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.1
	capsule.height = 0.4
	var stamped := PaletteUv.stamp_mesh(capsule, &"cream", 3)
	var expected := PaletteUv.uv_for(&"cream", 3)
	var arrays := stamped.surface_get_arrays(0)
	var uvs: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV]
	assert_int(uvs.size()).is_greater(0)
	for uv in uvs:
		assert_vector(uv).is_equal(expected)
