# Villager Rig System Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runtime GDScript system that generates villager NPC bodies
from DNA at runtime (rig + toon coloring + simple idle/walk animation), and
place one demo villager in the `cottage_garden` zone as a working proof.

**Architecture:** A small Python export (`palette_uv.json`) exposes the
existing color-palette atlas's cell coordinates to GDScript. A `VillagerRig`
builds a `Node3D` joint hierarchy from Godot's built-in primitive meshes
(`CapsuleMesh`/`SphereMesh`), stamping each primitive's UVs so it samples the
correct flat color from the existing shared toon material — no new shaders.
A tiny code-driven `VillagerAnimator` drives idle/walk via sine curves (no
baked clips). `VillagerFactory.build(dna)` is the single public entry point,
returning a `VillagerInstance` (itself the `Node3D`) that `cottage_garden.gd`
adds as a static demo NPC.

**Tech Stack:** Godot 4.7 GDScript (gdUnit4 for tests), Python 3 (pytest) for
the one small palette-export addition.

**Spec:** `docs/superpowers/specs/2026-08-10-villager-rig-system-design.md`
— read this first for the full rationale; this plan implements it exactly.

---

## Chunk 1: Palette UV export (Python) + PaletteUv loader (GDScript)

### Task 1: `palette.build_palette_uv_json()`

**Files:**
- Modify: `tools/assetgen/palette.py`
- Modify: `tools/assetgen/build.py`
- Test: `tests/python/test_palette_uv_export.py`

- [ ] **Step 1: Write the failing test**

Create `tests/python/test_palette_uv_export.py`:

```python
"""palette_uv.json export: every (ramp, shade) cell_uv, byte-deterministic."""
from __future__ import annotations

import json

from tools.assetgen import palette


def test_every_ramp_shade_pair_is_present():
    data = json.loads(palette.build_palette_uv_json())
    for name in palette.ramp_names():
        for shade in range(palette.SHADES):
            key = f"{name}/{shade}"
            assert key in data, key


def test_values_match_cell_uv_exactly():
    data = json.loads(palette.build_palette_uv_json())
    for name in palette.ramp_names():
        for shade in range(palette.SHADES):
            key = f"{name}/{shade}"
            assert data[key] == list(palette.cell_uv(name, shade))


def test_json_is_byte_deterministic():
    first = palette.build_palette_uv_json()
    second = palette.build_palette_uv_json()
    assert first == second
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_palette_uv_export.py -v`
Expected: FAIL with `AttributeError: module 'tools.assetgen.palette' has no
attribute 'build_palette_uv_json'`

- [ ] **Step 3: Implement `build_palette_uv_json()`**

In `tools/assetgen/palette.py`, add `import json` to the top imports
(alongside the existing `random`, `struct`, `zlib`), then add this function
right after `build_palette_png()` (find that function first with
`grep -n "def build_palette_png" tools/assetgen/palette.py` to place it
correctly):

```python
def build_palette_uv_json() -> bytes:
    """Flat {"ramp/shade": [u, v]} map of every cell_uv(), for runtime
    (GDScript) consumers that can't import this Python module directly —
    see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md."""
    entries = {}
    for name in ramp_names():
        for shade in range(SHADES):
            u, v = cell_uv(name, shade)
            entries[f"{name}/{shade}"] = [u, v]
    return json.dumps(entries, indent=2, sort_keys=True).encode("utf-8") + b"\n"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_palette_uv_export.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Wire it into the `make assets` build step**

In `tools/assetgen/build.py`, inside `build_all()`, right after the existing
block that writes `palette_main.png` (look for
`(OUT_DIR / "palette_main.png").write_bytes(png)` and the
`manifest["palette"]["palette_main.png"] = {...}` block that follows it),
add:

```python
    palette_uv_json = palette.build_palette_uv_json()
    (OUT_DIR / "palette_uv.json").write_bytes(palette_uv_json)
    manifest["palette"]["palette_uv.json"] = {
        "bytes": len(palette_uv_json),
        "sha256": hashlib.sha256(palette_uv_json).hexdigest(),
    }
```

- [ ] **Step 6: Rebuild assets and confirm the file is written**

Run: `python3 -m tools.assetgen.build`
Expected: exits 0; `ls assets/generated/palette_uv.json` shows the new file.

Run: `python3 -c "import json; d = json.load(open('assets/generated/palette_uv.json')); print(len(d), 'cream/3' in d, d['cream/3'])"`
Expected: prints a count (ramp count × 4) and `True` and a `[u, v]` pair like
`[0.53125, ...]`.

Run: `python3 -c "import json; m = json.load(open('assets/generated/manifest.json')); print('palette_uv.json' in m['palette'])"`
Expected: prints `True` — confirms the manifest tracks the new artifact
alongside `palette_main.png`.

- [ ] **Step 7: Run the full python suite to confirm no regressions**

Run: `python3 -m pytest tests/python -q`
Expected: same pass/fail counts as before this change (172 passed, 2 known
pre-existing Blender-baseline failures — confirm this matches, don't just
assume; if the numbers differ, stop and investigate before continuing).

- [ ] **Step 8: Commit**

```bash
git add tools/assetgen/palette.py tools/assetgen/build.py tests/python/test_palette_uv_export.py
git commit -m "feat(assetgen): export palette_uv.json for runtime GDScript consumers"
```

---

### Task 2: `PaletteUv` GDScript loader + mesh-stamping helper

**Files:**
- Create: `src/characters/villager/palette_uv.gd`
- Test: `tests/unit/test_palette_uv.gd`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_palette_uv.gd`:

```gdscript
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_palette_uv.gd --ignoreHeadlessMode`
Expected: FAIL — `PaletteUv` class not found / parse error.

- [ ] **Step 3: Ensure `palette_uv.json` exists locally**

Run: `make assets` (or `python3 -m tools.assetgen.build` if `make` isn't on
PATH — check `Makefile`'s `assets:` target first). This must be re-run any
time `tools/assetgen/palette.py` changes; `assets/generated/` is gitignored,
so every fresh clone/worktree needs this once before gdUnit tests touching
generated assets will pass (same requirement `test_avatar.gd` already has
for `wren.glb`).

- [ ] **Step 4: Implement `PaletteUv`**

Create `src/characters/villager/palette_uv.gd`:

```gdscript
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
	var is_valid_pair := pair is Array and pair.size() == 2 \
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_palette_uv.gd --ignoreHeadlessMode`
Expected: PASS (9 tests)

- [ ] **Step 6: Commit**

```bash
git add src/characters/villager/palette_uv.gd tests/unit/test_palette_uv.gd
git commit -m "feat(villager): add PaletteUv loader and mesh UV-stamping helper"
```

---

## Chunk 2: DNA, Rig, and Animator

### Task 3: `VillagerDna`

**Files:**
- Create: `src/characters/villager/villager_dna.gd`
- Test: `tests/unit/test_villager_dna.gd`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_villager_dna.gd`:

```gdscript
extends GdUnitTestSuite
## VillagerDna: deterministic seeded random(), values in documented ranges.


func test_random_is_deterministic_for_same_seed() -> void:
	var a := VillagerDna.random(42)
	var b := VillagerDna.random(42)
	assert_float(a.height_scale).is_equal(b.height_scale)
	assert_float(a.build_scale).is_equal(b.build_scale)
	assert_str(String(a.skin_ramp)).is_equal(String(b.skin_ramp))
	assert_str(String(a.hair_ramp)).is_equal(String(b.hair_ramp))
	assert_str(String(a.clothing_ramp)).is_equal(String(b.clothing_ramp))
	assert_str(a.name).is_equal(b.name)


func test_different_seeds_can_differ() -> void:
	# Not a strict guarantee for every possible pair, but seeds 1 and 2
	# must differ in at least one field for the RNG wiring to be real
	# (a constant-DNA bug would make every seed identical).
	var a := VillagerDna.random(1)
	var b := VillagerDna.random(2)
	var identical := (
		a.height_scale == b.height_scale
		and a.build_scale == b.build_scale
		and a.skin_ramp == b.skin_ramp
		and a.hair_ramp == b.hair_ramp
		and a.clothing_ramp == b.clothing_ramp
	)
	assert_bool(identical).override_failure_message(
		"seeds 1 and 2 produced identical DNA — RNG isn't seeded correctly"
	).is_false()


func test_scales_are_within_documented_range() -> void:
	for seed in range(20):
		var dna := VillagerDna.random(seed)
		assert_float(dna.height_scale).is_greater_equal(0.85)
		assert_float(dna.height_scale).is_less_equal(1.15)
		assert_float(dna.build_scale).is_greater_equal(0.85)
		assert_float(dna.build_scale).is_less_equal(1.15)


func test_ramps_are_drawn_from_allow_lists() -> void:
	for seed in range(20):
		var dna := VillagerDna.random(seed)
		assert_bool(VillagerDna.SKIN_RAMPS.has(dna.skin_ramp)).is_true()
		assert_bool(VillagerDna.HAIR_RAMPS.has(dna.hair_ramp)).is_true()
		assert_bool(VillagerDna.CLOTHING_RAMPS.has(dna.clothing_ramp)).is_true()


func test_seed_is_retained_and_hairstyle_is_fixed_v1_value() -> void:
	var dna := VillagerDna.random(42)
	assert_int(dna.seed).is_equal(42)
	assert_str(String(dna.hairstyle)).is_equal("bob")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_dna.gd --ignoreHeadlessMode`
Expected: FAIL — `VillagerDna` class not found.

- [ ] **Step 3: Implement `VillagerDna`**

Create `src/characters/villager/villager_dna.gd`:

```gdscript
class_name VillagerDna
extends RefCounted
## A villager's generation "genome" — deterministic from a seed, drives
## HumanSynth/VillagerRig. See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §1.
##
## Ramp allow-lists are a small, deliberate v1 subset of the full palette
## (tools/assetgen/palette.py's RAMPS) chosen to look plausible for skin/
## hair/clothing — not exhaustive, easy to extend later.
const SKIN_RAMPS: Array[StringName] = [&"cream", &"honey", &"clay", &"rust"]
const HAIR_RAMPS: Array[StringName] = [&"bark", &"wood", &"void_plum", &"metal"]
const CLOTHING_RAMPS: Array[StringName] = [
	&"rust", &"honey", &"moss", &"water", &"sky", &"clay", &"metal", &"ceramic",
]
const NAME_SYLLABLES := [
	"Ash", "Bram", "Cael", "Dor", "El", "Fen", "Gil", "Hol", "Ives", "Jor",
]

var seed: int
var name: String
var height_scale: float
var build_scale: float
var skin_ramp: StringName
var hair_ramp: StringName
var clothing_ramp: StringName
var hairstyle: StringName = &"bob"  # only one exists in v1


static func random(from_seed: int) -> VillagerDna:
	var rng := RandomNumberGenerator.new()
	rng.seed = from_seed
	var dna := VillagerDna.new()
	dna.seed = from_seed
	dna.height_scale = rng.randf_range(0.85, 1.15)
	dna.build_scale = rng.randf_range(0.85, 1.15)
	dna.skin_ramp = SKIN_RAMPS[rng.randi_range(0, SKIN_RAMPS.size() - 1)]
	dna.hair_ramp = HAIR_RAMPS[rng.randi_range(0, HAIR_RAMPS.size() - 1)]
	dna.clothing_ramp = CLOTHING_RAMPS[rng.randi_range(0, CLOTHING_RAMPS.size() - 1)]
	dna.name = (
		NAME_SYLLABLES[rng.randi_range(0, NAME_SYLLABLES.size() - 1)]
		+ NAME_SYLLABLES[rng.randi_range(0, NAME_SYLLABLES.size() - 1)].to_lower()
	)
	return dna
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_dna.gd --ignoreHeadlessMode`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/characters/villager/villager_dna.gd tests/unit/test_villager_dna.gd
git commit -m "feat(villager): add VillagerDna seeded genome model"
```

---

### Task 4: `VillagerRig`

**Files:**
- Create: `src/characters/villager/villager_rig.gd`
- Test: `tests/unit/test_villager_rig.gd`

This is the core builder: constructs the joint hierarchy from
`docs/superpowers/specs/2026-08-10-villager-rig-system-design.md` §2 using
primitive meshes stamped via `PaletteUv.stamp_mesh()`. Per-part shade table
(§4 of the spec): skin parts (head, hands) use shade 3 (lightest), clothing
parts (torso, arms, legs) use shade 2, hair uses shade 1 — matching how
`tools/assetgen/part_registry.py`'s hand-authored parts already pick shades
(e.g. `witch_head()` uses shade 3 for skin, `witch_torso()` uses shade 2).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_villager_rig.gd`:

```gdscript
extends GdUnitTestSuite
## VillagerRig: joint names present, mirrored L/R joints inverted,
## no dangling nodes after freeing.

const EXPECTED_JOINTS := [
	"torso", "neck", "head", "head_top",
	"shoulder_l", "shoulder_r", "elbow_l", "elbow_r", "hand_l", "hand_r",
	"hip_l", "hip_r", "knee_l", "knee_r",
]


func test_build_produces_all_expected_joints() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	for joint_name in EXPECTED_JOINTS:
		assert_object(rig.root.find_child(joint_name, true, false)) \
			.override_failure_message("missing joint: %s" % joint_name).is_not_null()


func test_mirrored_joints_have_inverted_scale_x() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var left := rig.root.find_child("shoulder_l", true, false) as Node3D
	var right := rig.root.find_child("shoulder_r", true, false) as Node3D
	assert_float(left.scale.x * right.scale.x).is_less(0.0)


func test_hips_are_children_of_torso() -> void:
	# Pins the spec §2 hierarchy exactly: hip_l/hip_r hang off torso (like
	# shoulder_l/shoulder_r), not directly off root — regression guard for
	# a prior bug where hips were parented to root instead.
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var torso := rig.root.find_child("torso", true, false) as Node3D
	var hip_l := rig.root.find_child("hip_l", true, false) as Node3D
	var hip_r := rig.root.find_child("hip_r", true, false) as Node3D
	assert_object(hip_l.get_parent()).is_equal(torso)
	assert_object(hip_r.get_parent()).is_equal(torso)


func test_body_meshes_are_stamped_with_expected_ramps() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var head := rig.root.find_child("head", true, false) as MeshInstance3D
	var torso := rig.root.find_child("torso", true, false) as MeshInstance3D
	var expected_skin_uv := PaletteUv.uv_for(dna.skin_ramp, 3)
	var expected_clothing_uv := PaletteUv.uv_for(dna.clothing_ramp, 2)
	var head_uvs: PackedVector2Array = head.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	var torso_uvs: PackedVector2Array = torso.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	assert_vector(head_uvs[0]).is_equal(expected_skin_uv)
	assert_vector(torso_uvs[0]).is_equal(expected_clothing_uv)


func test_hair_exists_under_head_top_and_is_stamped_with_hair_ramp() -> void:
	# v1's only socket-attached part — pins both its existence (it's easy
	# to accidentally omit) and its shade (hair always uses shade 1, per
	# the spec's fixed per-part shade table).
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var head_top := rig.root.find_child("head_top", true, false) as Node3D
	var hair := head_top.find_child("hair", true, false) as MeshInstance3D
	assert_object(hair).override_failure_message("missing hair mesh under head_top").is_not_null()
	var expected_hair_uv := PaletteUv.uv_for(dna.hair_ramp, 1)
	var hair_uvs: PackedVector2Array = hair.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
	assert_vector(hair_uvs[0]).is_equal(expected_hair_uv)


func test_sockets_dictionary_has_v1_entries() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	assert_bool(rig.sockets.has(&"head_top")).is_true()
	assert_bool(rig.sockets.has(&"hand_l")).is_true()
	assert_bool(rig.sockets.has(&"hand_r")).is_true()


func test_freeing_root_leaves_no_dangling_children() -> void:
	var dna := VillagerDna.random(7)
	var rig := VillagerRig.build(dna)
	var root := rig.root
	assert_bool(is_instance_valid(root)).is_true()
	root.queue_free()
	await get_tree().process_frame
	# queue_free() defers actual deletion by one frame; after that frame the
	# instance itself (and, transitively, every child freed alongside it)
	# must be gone — this is the reliable way to assert cleanup in Godot,
	# unlike checking get_child_count() on an object that may already be
	# invalid.
	assert_bool(is_instance_valid(root)).is_false()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_rig.gd --ignoreHeadlessMode`
Expected: FAIL — `VillagerRig` class not found.

- [ ] **Step 3: Implement `VillagerRig`**

Create `src/characters/villager/villager_rig.gd`:

```gdscript
class_name VillagerRig
extends RefCounted
## Builds the villager joint hierarchy from primitive meshes, per
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §2.
## VillagerRig is the sole owner of primitive creation and UV-stamping —
## no other module touches mesh geometry or UVs.

const SKIN_SHADE := 3
const CLOTHING_SHADE := 2
const HAIR_SHADE := 1

# Base (height_scale = 1.0, build_scale = 1.0) dimensions in meters.
const TORSO_RADIUS := 0.14
const TORSO_HEIGHT := 0.42
const HEAD_RADIUS := 0.11
const ARM_RADIUS := 0.045
const ARM_LENGTH := 0.30
const LEG_RADIUS := 0.06
const LEG_LENGTH := 0.42
const HAND_RADIUS := 0.035
const HAIR_RADIUS := 0.09

var root: Node3D
var sockets: Dictionary = {}  # StringName -> Node3D


static func build(dna: VillagerDna) -> VillagerRig:
	var rig := VillagerRig.new()
	var h := dna.height_scale
	var b := dna.build_scale
	var leg_length := LEG_LENGTH * h
	var torso_height := TORSO_HEIGHT * h

	rig.root = Node3D.new()
	rig.root.name = "VillagerRoot"

	var torso := MeshInstance3D.new()
	torso.name = "torso"
	var torso_mesh := CapsuleMesh.new()
	torso_mesh.radius = TORSO_RADIUS * b
	torso_mesh.height = torso_height
	torso.mesh = PaletteUv.stamp_mesh(torso_mesh, dna.clothing_ramp, CLOTHING_SHADE)
	torso.position = Vector3(0.0, leg_length + torso_height / 2.0, 0.0)
	rig.root.add_child(torso)

	var neck := Node3D.new()
	neck.name = "neck"
	neck.position = Vector3(0.0, torso_height / 2.0, 0.0)
	torso.add_child(neck)

	var head := MeshInstance3D.new()
	head.name = "head"
	var head_mesh := SphereMesh.new()
	head_mesh.radius = HEAD_RADIUS * b
	head_mesh.height = HEAD_RADIUS * b * 2.0
	head.mesh = PaletteUv.stamp_mesh(head_mesh, dna.skin_ramp, SKIN_SHADE)
	head.position = Vector3(0.0, HEAD_RADIUS * b, 0.0)
	neck.add_child(head)

	var head_top := Node3D.new()
	head_top.name = "head_top"
	head_top.position = Vector3(0.0, HEAD_RADIUS * b, 0.0)
	head.add_child(head_top)
	rig.sockets[&"head_top"] = head_top

	var hair := MeshInstance3D.new()
	hair.name = "hair"
	var hair_mesh := SphereMesh.new()
	hair_mesh.radius = HAIR_RADIUS * b
	hair_mesh.height = HAIR_RADIUS * b * 1.2
	hair.mesh = PaletteUv.stamp_mesh(hair_mesh, dna.hair_ramp, HAIR_SHADE)
	hair.scale = Vector3(1.0, 0.65, 1.0)
	head_top.add_child(hair)

	for side in [-1.0, 1.0]:
		var suffix := "_l" if side < 0.0 else "_r"
		var shoulder := Node3D.new()
		shoulder.name = "shoulder%s" % suffix
		shoulder.position = Vector3(side * TORSO_RADIUS * b, torso_height / 2.0, 0.0)
		shoulder.scale = Vector3(side, 1.0, 1.0)
		torso.add_child(shoulder)

		var elbow := MeshInstance3D.new()
		elbow.name = "elbow%s" % suffix
		var arm_mesh := CapsuleMesh.new()
		arm_mesh.radius = ARM_RADIUS * b
		arm_mesh.height = ARM_LENGTH * h
		elbow.mesh = PaletteUv.stamp_mesh(arm_mesh, dna.clothing_ramp, CLOTHING_SHADE)
		elbow.position = Vector3(0.0, -ARM_LENGTH * h / 2.0, 0.0)
		shoulder.add_child(elbow)

		var hand := MeshInstance3D.new()
		hand.name = "hand%s" % suffix
		var hand_mesh := SphereMesh.new()
		hand_mesh.radius = HAND_RADIUS * b
		hand_mesh.height = HAND_RADIUS * b * 2.0
		hand.mesh = PaletteUv.stamp_mesh(hand_mesh, dna.skin_ramp, SKIN_SHADE)
		hand.position = Vector3(0.0, -ARM_LENGTH * h / 2.0, 0.0)
		elbow.add_child(hand)
		rig.sockets[StringName("hand%s" % suffix)] = hand

		var hip := Node3D.new()
		hip.name = "hip%s" % suffix
		hip.position = Vector3(side * TORSO_RADIUS * b * 0.6, -torso_height / 2.0, 0.0)
		hip.scale = Vector3(side, 1.0, 1.0)
		torso.add_child(hip)

		var knee := MeshInstance3D.new()
		knee.name = "knee%s" % suffix
		var leg_mesh := CapsuleMesh.new()
		leg_mesh.radius = LEG_RADIUS * b
		leg_mesh.height = leg_length
		knee.mesh = PaletteUv.stamp_mesh(leg_mesh, dna.clothing_ramp, CLOTHING_SHADE)
		knee.position = Vector3(0.0, -leg_length / 2.0, 0.0)
		hip.add_child(knee)

	return rig
```

Note: `hip_l`/`hip_r` are children of `torso` (not `root`), matching the
spec's §2 hierarchy diagram exactly — hip joints hang off the torso the
same way shoulder joints do, so the whole upper body (torso breathing scale
+ both limb pairs) moves together. `shoulder_l`/`shoulder_r` and
`hip_l`/`hip_r` both mirror via `scale.x` for a consistent convention across
all paired joints per the spec.

- [ ] **Step 4: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_rig.gd --ignoreHeadlessMode`
Expected: PASS (7 tests)

If proportions look implausible once you screenshot the demo villager in
Task 8, come back and tune the constants at the top of this file — they're
starting values, not final art direction.

- [ ] **Step 5: Commit**

```bash
git add src/characters/villager/villager_rig.gd tests/unit/test_villager_rig.gd
git commit -m "feat(villager): add VillagerRig procedural joint/mesh builder"
```

---

### Task 5: `HumanSynth` and `VillagerBuildResult`

**Files:**
- Create: `src/characters/villager/synth/human_synth.gd`
- Create: `src/characters/villager/villager_build_result.gd`
- Test: `tests/unit/test_human_synth.gd`

Per spec §3: a thin `BodySynthesizer`-shaped wrapper around `VillagerRig` —
today it's a trivial pass-through (only one archetype exists in v1), but it
gives future archetypes (bird/quadruped/small-creature, explicitly deferred
per this feature's scope) a stable seam to plug into later without touching
`VillagerFactory`. YAGNI means no registry dict yet — `VillagerFactory` calls
`HumanSynth` directly.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_human_synth.gd`:

```gdscript
extends GdUnitTestSuite
## HumanSynth: thin BodySynthesizer-shaped wrapper around VillagerRig.build().


func test_build_returns_result_bundling_root_rig_and_sockets() -> void:
	var dna := VillagerDna.random(9)
	var result := HumanSynth.build(dna)
	auto_free(result.root)
	assert_object(result.root).is_not_null()
	assert_object(result.rig).is_not_null()
	assert_object(result.root).is_equal(result.rig.root)
	assert_bool(result.sockets.has(&"head_top")).is_true()
	assert_bool(result.sockets.has(&"hand_l")).is_true()
	assert_bool(result.sockets.has(&"hand_r")).is_true()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_human_synth.gd --ignoreHeadlessMode`
Expected: FAIL — `HumanSynth` class not found.

- [ ] **Step 3: Implement `VillagerBuildResult` and `HumanSynth`**

Create `src/characters/villager/villager_build_result.gd`:

```gdscript
class_name VillagerBuildResult
extends RefCounted
## Bundle returned by a BodySynthesizer-shaped build() function (currently
## only HumanSynth). See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §3.

var root: Node3D
var rig: VillagerRig
var sockets: Dictionary  # StringName -> Node3D
```

Create `src/characters/villager/synth/human_synth.gd`:

```gdscript
class_name HumanSynth
extends RefCounted
## The only BodySynthesizer implementation in v1 (human archetype). A thin
## pass-through to VillagerRig.build() — see
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §3. Kept
## separate from VillagerRig so a future archetype (bird/quadruped/small-
## creature — out of scope this phase) has a stable seam to implement
## alongside this one without VillagerFactory needing to change.


static func build(dna: VillagerDna) -> VillagerBuildResult:
	var rig := VillagerRig.build(dna)
	var result := VillagerBuildResult.new()
	result.root = rig.root
	result.rig = rig
	result.sockets = rig.sockets
	return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_human_synth.gd --ignoreHeadlessMode`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add src/characters/villager/villager_build_result.gd src/characters/villager/synth/human_synth.gd tests/unit/test_human_synth.gd
git commit -m "feat(villager): add HumanSynth archetype seam around VillagerRig"
```

---

### Task 6: `VillagerAnimator`

**Files:**
- Create: `src/characters/villager/villager_animator.gd`
- Test: `tests/unit/test_villager_animator.gd`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_villager_animator.gd`:

```gdscript
extends GdUnitTestSuite
## VillagerAnimator: idle/walk states drive joint rotation over time,
## unknown states fall back to idle.


func _build_animator() -> Array:
	var dna := VillagerDna.random(3)
	var rig := VillagerRig.build(dna)
	auto_free(rig.root)
	var animator := VillagerAnimator.new(rig)
	return [rig, animator]


func test_unknown_state_falls_back_to_idle() -> void:
	var pair := _build_animator()
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"somersault")
	assert_str(String(animator.current_motion_state())).is_equal("idle")


func test_walk_state_changes_shoulder_rotation_over_time() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"walk")
	var shoulder := rig.root.find_child("shoulder_l", true, false) as Node3D
	var before := shoulder.rotation.x
	for i in range(10):
		animator.update(0.1)
	var after := shoulder.rotation.x
	assert_float(before).is_not_equal(after)


func test_walk_state_changes_hip_rotation_over_time() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"walk")
	var hip := rig.root.find_child("hip_l", true, false) as Node3D
	var before := hip.rotation.x
	for i in range(10):
		animator.update(0.1)
	var after := hip.rotation.x
	assert_float(before).is_not_equal(after)


func test_idle_state_still_animates_subtly() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"idle")
	var torso := rig.root.find_child("torso", true, false) as Node3D
	var before := torso.scale.y
	for i in range(10):
		animator.update(0.1)
	var after := torso.scale.y
	assert_float(before).is_not_equal(after)


func test_idle_head_bob_animates_head_position() -> void:
	var pair := _build_animator()
	var rig: VillagerRig = pair[0]
	var animator: VillagerAnimator = pair[1]
	animator.set_motion_state(&"idle")
	var head := rig.root.find_child("head", true, false) as Node3D
	var before := head.position.y
	for i in range(10):
		animator.update(0.1)
	var after := head.position.y
	assert_float(before).is_not_equal(after)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_animator.gd --ignoreHeadlessMode`
Expected: FAIL — `VillagerAnimator` class not found.

- [ ] **Step 3: Implement `VillagerAnimator`**

Create `src/characters/villager/villager_animator.gd`:

```gdscript
class_name VillagerAnimator
extends RefCounted
## Small code-driven animator: idle breathing/head-bob + walk hip/shoulder
## swing, sine-curve based (no baked AnimationPlayer clips) — matches the
## source's animate.ts approach. See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §5.

const BREATH_SPEED := 1.6
const BREATH_AMOUNT := 0.03
const HEAD_BOB_SPEED := 1.6
const HEAD_BOB_AMOUNT := 0.01
const WALK_SWING_SPEED := 6.0
const WALK_SWING_AMOUNT := 0.5  # radians

var _rig: VillagerRig
var _state: StringName = &"idle"
var _t := 0.0
var _head_base_y := 0.0


func _init(rig: VillagerRig) -> void:
	_rig = rig
	var head := _rig.root.find_child("head", true, false) as Node3D
	if head != null:
		_head_base_y = head.position.y


func set_motion_state(state: StringName) -> void:
	_state = state if state in [&"idle", &"walk"] else &"idle"


func current_motion_state() -> StringName:
	return _state


func update(delta: float) -> void:
	_t += delta
	var torso := _rig.root.find_child("torso", true, false) as Node3D
	if torso != null:
		torso.scale.y = 1.0 + sin(_t * BREATH_SPEED) * BREATH_AMOUNT

	var head := _rig.root.find_child("head", true, false) as Node3D
	if head != null:
		head.position.y = _head_base_y + sin(_t * HEAD_BOB_SPEED) * HEAD_BOB_AMOUNT

	if _state == &"walk":
		var swing := sin(_t * WALK_SWING_SPEED) * WALK_SWING_AMOUNT
		_rotate_pair("shoulder_l", "shoulder_r", swing)
		_rotate_pair("hip_l", "hip_r", -swing)
	else:
		_rotate_pair("shoulder_l", "shoulder_r", 0.0)
		_rotate_pair("hip_l", "hip_r", 0.0)


func _rotate_pair(left_name: String, right_name: String, angle: float) -> void:
	var left := _rig.root.find_child(left_name, true, false) as Node3D
	var right := _rig.root.find_child(right_name, true, false) as Node3D
	if left != null:
		left.rotation.x = angle
	if right != null:
		right.rotation.x = -angle
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_animator.gd --ignoreHeadlessMode`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/characters/villager/villager_animator.gd tests/unit/test_villager_animator.gd
git commit -m "feat(villager): add VillagerAnimator sine-driven idle/walk motion"
```

---

## Chunk 3: Façade, zone integration, docs

### Task 7: `VillagerInstance` and `VillagerFactory`

**Files:**
- Create: `src/characters/villager/villager_instance.gd`
- Create: `src/characters/villager/villager_factory.gd`
- Test: `tests/unit/test_villager_factory.gd`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_villager_factory.gd`:

```gdscript
extends GdUnitTestSuite
## VillagerFactory/VillagerInstance: the public entry point other code uses.

const MAX_TRIS := 4000  # docs/design-bible.md per-character budget


func test_build_returns_instance_with_v1_sockets() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	assert_object(instance).is_not_null()
	assert_bool(instance.sockets.has(&"head_top")).is_true()
	assert_bool(instance.sockets.has(&"hand_l")).is_true()
	assert_bool(instance.sockets.has(&"hand_r")).is_true()


func test_build_applies_shared_palette_material() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	var root := Node3D.new()
	auto_free(root)
	root.add_child(instance)
	var runner := scene_runner(root)
	await runner.simulate_frames(1)
	var meshes := instance.find_children("*", "MeshInstance3D", true, false)
	assert_int(meshes.size()).is_greater(0)
	for found in meshes:
		var mesh_instance := found as MeshInstance3D
		assert_object(mesh_instance.material_override) \
			.override_failure_message("bare mesh: %s" % mesh_instance.name).is_not_null()


func test_build_stays_within_character_tri_budget() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	var total_tris := 0
	for found in instance.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.mesh != null:
			for surface in range(mesh_instance.mesh.get_surface_count()):
				var arrays := mesh_instance.mesh.surface_get_arrays(surface)
				var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
				total_tris += indices.size() / 3
	assert_int(total_tris).override_failure_message(
		"villager over the %d tri character budget" % MAX_TRIS
	).is_less_equal(MAX_TRIS)


func test_build_stamps_every_body_part_with_its_assigned_uv() -> void:
	# Proves the UV-stamp step actually ran end-to-end through the full
	# façade (VillagerFactory -> HumanSynth -> VillagerRig), not just that
	# no errors were logged — matches this spec's testing requirement that
	# UV arrays are checked against palette_uv.gd's uv_for(ramp, shade) for
	# each part's assigned ramp/shade.
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	var expected_by_name := {
		"head": PaletteUv.uv_for(dna.skin_ramp, 3),
		"hand_l": PaletteUv.uv_for(dna.skin_ramp, 3),
		"hand_r": PaletteUv.uv_for(dna.skin_ramp, 3),
		"torso": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"elbow_l": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"elbow_r": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"knee_l": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"knee_r": PaletteUv.uv_for(dna.clothing_ramp, 2),
		"hair": PaletteUv.uv_for(dna.hair_ramp, 1),
	}
	for part_name: String in expected_by_name:
		var node := instance.find_child(part_name, true, false) as MeshInstance3D
		assert_object(node).override_failure_message(
			"missing expected mesh part: %s" % part_name
		).is_not_null()
		var uvs: PackedVector2Array = node.mesh.surface_get_arrays(0)[Mesh.ARRAY_TEX_UV]
		var expected_uv: Vector2 = expected_by_name[part_name]
		for uv in uvs:
			assert_vector(uv).override_failure_message(
				"wrong UV stamp on %s" % part_name
			).is_equal(expected_uv)


func test_set_motion_state_switches_animator_state() -> void:
	var dna := VillagerDna.random(11)
	var instance := VillagerFactory.build(dna)
	auto_free(instance)
	instance.set_motion_state(&"walk")
	assert_str(String(instance.current_motion_state())).is_equal("walk")
	instance.set_motion_state(&"somersault")
	assert_str(String(instance.current_motion_state())).is_equal("idle")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_factory.gd --ignoreHeadlessMode`
Expected: FAIL — `VillagerFactory` class not found.

- [ ] **Step 3: Implement `VillagerInstance`**

Create `src/characters/villager/villager_instance.gd`:

```gdscript
class_name VillagerInstance
extends Node3D
## The public face of a built villager — owns its rig/animator, exposes
## the same set_motion_state()/play_gesture() shape as WrenAvatar
## (src/player/avatar.gd) so zone/NPC code can treat both character types
## identically. See
## docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §6.

var sockets: Dictionary = {}  # StringName -> Node3D, read-only by convention

var _animator: VillagerAnimator


func _setup(rig: VillagerRig) -> void:
	add_child(rig.root)
	sockets = rig.sockets
	_animator = VillagerAnimator.new(rig)


func _process(delta: float) -> void:
	if _animator != null:
		_animator.update(delta)


func set_motion_state(state: StringName) -> void:
	if _animator != null:
		_animator.set_motion_state(state)


func current_motion_state() -> StringName:
	if _animator == null:
		return &"idle"
	return _animator.current_motion_state()


func play_gesture(_gesture: StringName) -> void:
	pass  # v1: no gestures defined yet — matches WrenAvatar's no-op convention.
```

- [ ] **Step 4: Implement `VillagerFactory`**

Create `src/characters/villager/villager_factory.gd`:

```gdscript
class_name VillagerFactory
extends RefCounted
## The single entry point other code should use to create a villager.
## See docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §6.


static func build(dna: VillagerDna) -> VillagerInstance:
	var result := HumanSynth.build(dna)
	var instance := VillagerInstance.new()
	instance.name = dna.name
	instance._setup(result.rig)
	PaletteApply.apply(instance)
	return instance
```

- [ ] **Step 5: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_villager_factory.gd --ignoreHeadlessMode`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add src/characters/villager/villager_instance.gd src/characters/villager/villager_factory.gd tests/unit/test_villager_factory.gd
git commit -m "feat(villager): add VillagerInstance/VillagerFactory public facade"
```

---

### Task 8: Demo villager in `cottage_garden`

**Files:**
- Modify: `src/world/cottage_garden/cottage_garden.gd`
- Modify: `tests/unit/test_cottage_garden.gd`
- Verify (no code change expected): `tests/unit/test_zone_budget.gd`

- [ ] **Step 1: Write the failing test (scene smoke check)**

In `tests/unit/test_cottage_garden.gd`, add this test function (append it
after the existing `test_cottage_garden_assembles_with_player_and_props`):

```gdscript
func test_cottage_garden_has_demo_villager() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(10)
	var garden := runner.scene()
	var villager := garden.get_node_or_null("DemoVillager")
	assert_object(villager).override_failure_message(
		"expected a DemoVillager node in cottage_garden.tscn"
	).is_not_null()
	assert_bool(villager is VillagerInstance).is_true()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_cottage_garden.gd --ignoreHeadlessMode`
Expected: FAIL — `DemoVillager` node not found (new test fails; the
pre-existing test in this file should still pass).

- [ ] **Step 3: Add the demo villager to `cottage_garden.gd`**

View the current file first — `src/world/cottage_garden/cottage_garden.gd`
(shown in full in this plan's research; it currently only has `_ready()`
calling `_stage()`, and `_stage()` adjusts the `Sun`/`Fill` lights). Add a
new `_add_demo_villager()` call and function:

```gdscript
extends Node3D
## The cottage garden — Phase 4's first tooling-built zone.

# Fixed seed so the scene test's node lookup and screenshot captures are
# reproducible — see docs/superpowers/specs/2026-08-10-villager-rig-system-design.md §7.
const DEMO_VILLAGER_SEED := 20260810


func _ready() -> void:
	_stage()
	_add_demo_villager()


func _stage() -> void:
	var sun := get_node_or_null("Sun") as DirectionalLight3D
	if sun != null:
		sun.rotation_degrees = Vector3(-48.0, -32.0, 0.0)
		sun.light_color = Color(1.0, 0.93, 0.82)
		sun.light_energy = 1.25
		sun.shadow_enabled = true
	var fill := get_node_or_null("Fill") as DirectionalLight3D
	if fill != null:
		fill.rotation_degrees = Vector3(-20.0, 141.0, 0.0)
		fill.light_color = Color(0.68, 0.78, 0.92)
		fill.light_energy = 0.35


func _add_demo_villager() -> void:
	var dna := VillagerDna.random(DEMO_VILLAGER_SEED)
	var villager := VillagerFactory.build(dna)
	villager.name = "DemoVillager"
	# Near the well, facing the cottage — a static proof-of-concept only,
	# no interaction/dialogue/AI (that's future gameplay-phase work).
	villager.position = Vector3(1.6, 0.0, 2.2)
	add_child(villager)
```

(Keep the rest of the file's existing content/comments as-is — only add the
constant and the new function/call; don't reformat unrelated lines.)

- [ ] **Step 4: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_cottage_garden.gd --ignoreHeadlessMode`
Expected: PASS (both tests in this file)

- [ ] **Step 5: Extend the zone budget test**

Open `tests/unit/test_zone_budget.gd`. It already sums tris/draw-calls
across every `MeshInstance3D`/`MultiMeshInstance3D` under the loaded
`cottage_garden` scene root (see its `test_cottage_garden_within_zone_budget`
function) — the demo villager you just added is a child of the scene root
found by `garden.find_children("*", "MeshInstance3D", true, false)`, so it's
**already included automatically**. This satisfies the spec's "test_zone_budget.gd,
extended" requirement in effect (the villager is now covered by the existing
assertion) even though no source line in this file needs to change — the
"extension" is the villager's tris now flowing into an already-generic sum,
not a new line of test code. Just re-run it to confirm the budget still
holds with the villager added:

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_budget.gd --ignoreHeadlessMode`
Expected: PASS. If it now FAILS (over budget), the villager's primitive
count is too high for this zone's remaining tri headroom — reduce
`VillagerRig`'s primitive complexity (e.g. don't use `CylinderMesh`'s
default high radial-segment count; construct `CapsuleMesh`/`SphereMesh`
with explicit lower `radial_segments`/`rings` properties) rather than
raising the zone budget itself.

- [ ] **Step 6: Rebuild assets, reimport, and take a verification screenshot**

Run: `python3 -m tools.assetgen.build` (ensures `palette_uv.json` is current)
Run: `.tooling/godot --headless --path . --import` (forces Godot to pick up
any changed generated assets — see this session's established gotcha:
import-cache staleness after asset rebuilds)

`cottage_garden` is already registered in `src/lookdev/screenshot.gd`'s
`CAPTURES` dict, so no new capture wiring is needed. Run the screenshot
runner exactly as `tools/ci/run.sh`'s `job_screenshot()` does — it needs a
real GL context, so do **not** pass `--headless` (unlike the gdUnit test
runs above):

Run: `LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a --server-args="-screen 0 1280x720x24" .tooling/godot --path . res://src/lookdev/screenshot.tscn`
(if `xvfb-run` isn't available in your environment, run
`.tooling/godot --path . res://src/lookdev/screenshot.tscn` directly on a
machine with a real/virtual GL context instead)
Expected: exits 0; writes `artifacts/cottage_garden.png` (and every other
scene in `CAPTURES`).

Inspect `artifacts/cottage_garden.png`. Confirm:
- The villager is visible, upright, feet on the ground (not sunk in/
  floating — the known `avatar.gd` ground-offset pitfall from this
  session applies here too if proportions are off).
- Body/head/hair/limb colors are plausible flat toon shades, not black/
  magenta (a black or hot-magenta part means `PaletteUv.uv_for()` fell back
  to `Vector2.ZERO` — check `assets/generated/palette_uv.json` exists and
  is fresh).
- No visible seams (this session's outline-shader seam pitfall applies to
  any adjacent-primitive boundary too, though single closed primitives
  shouldn't trigger it the way subdivided quads did).

If proportions look wrong (too tall/short/blocky), go back to Task 4 and
adjust `VillagerRig`'s constants, then repeat this step.

- [ ] **Step 7: Run the full verification suite**

Before this plan, this repo had a Python test baseline (from Task 1 Step 7)
and a gdUnit baseline you should capture now for comparison — run
`grep -rn "^func test_" tests/unit | wc -l` to see the current gdUnit test
count before your changes (this plan adds exactly 33 new `func test_` cases
across `test_palette_uv.gd` (9), `test_villager_dna.gd` (5),
`test_villager_rig.gd` (7), `test_human_synth.gd` (1),
`test_villager_animator.gd` (5), `test_villager_factory.gd` (5), and one
appended to `test_cottage_garden.gd`).

Run: `python3 -m pytest tests/python -q`
Expected: same as Task 1 Step 7's baseline, plus this plan's 3 new
`test_palette_uv_export.py` tests (no new failures beyond whatever
pre-existing failures Task 1 Step 7 already established).

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit --ignoreHeadlessMode`
Expected: pass count = (your pre-plan gdUnit baseline count) + 33; fail
count identical to your pre-plan baseline (i.e. this plan introduces zero
new failures) — confirm by parsing `reports/report_1/results.xml` if the
summary line is ambiguous, don't just trust a hardcoded number here since
the exact pre-existing baseline can drift as the codebase evolves.

- [ ] **Step 8: Commit**

```bash
git add src/world/cottage_garden/cottage_garden.gd tests/unit/test_cottage_garden.gd
git commit -m "feat(villager): place a demo VillagerInstance in cottage_garden"
```

---

### Task 9: Documentation updates

**Files:**
- Modify: `docs/asset-inventory.md`

- [ ] **Step 1: Update every villager row**

Open `docs/asset-inventory.md`. For each of the 13 "Phase 8" villager rows
(`sigrid-barm`, `ansel-rowe`, `maud-tressel`, `juniper-vale`, `torben-ask`,
`greta-furrow`, `ines-jarvi`, `fenn-solder`, `hollis-bram`, `odell-rime`,
`eamon-brook`, `tansy-mothwood`, `sal-a-manda`) — find them with
`grep -n "villager (" docs/asset-inventory.md` — change the "Dependencies"
column from `part_registry villager entries` to
`src/characters/villager/ (VillagerFactory)`, leaving every other column
(name, priority, phase note, status "planned") unchanged. These rows stay
"planned" — this task only updates *how* they'll eventually be built, not
their status; authoring each named villager's actual DNA/story hookup is
still future Phase 8 work.

- [ ] **Step 2: Add a new `villager-rig-system` row**

Add a new row (following the existing table's column order and style —
check the header row and a neighboring row like `cottage-facade` for exact
column names/order first) documenting the system itself:

```
| villager-rig-system | character | procedural rig system (not a specific villager) | procedural (runtime GDScript, not baked GLB) | VillagerRig joint hierarchy + VillagerAnimator sine-driven idle/walk | src/characters/villager/ (HumanSynth, VillagerRig, VillagerAnimator, VillagerFactory) | P0 | Phase 5 villager rig system; demo villager in cottage_garden | done |
```

Adjust exact wording/column count to match whatever the real header row
requires — the table's actual columns take precedence over this example.

- [ ] **Step 3: Commit**

```bash
git add docs/asset-inventory.md
git commit -m "docs: point villager rows at the new VillagerFactory system"
```

---

## Final verification (whole plan)

- [ ] Run `python3 -m pytest tests/python -q` — confirm no new failures
  vs. the pre-plan baseline (Task 1 Step 7).
- [ ] Run `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit --ignoreHeadlessMode` — confirm the pass count is your pre-plan
  gdUnit baseline + 33, and the fail count is unchanged from your pre-plan
  baseline (this plan should introduce zero new failures; see Task 8 Step 7
  for how to capture the pre-plan baseline).
- [ ] Confirm the `cottage_garden` screenshot shows a plausible, upright,
  correctly-colored demo villager with no ground-clipping or seam
  artifacts.
- [ ] Confirm `git log` shows one new commit per task introduced by this
  plan (9 commits: Tasks 1-9), and `git status` is clean (no uncommitted
  changes remain).
