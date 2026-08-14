# Zone Tooling + Environment Placeholders Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a data-driven `Zone` resource + `ZoneBuilder` (`@tool`) placement/scatter system in Godot, extend the Python procedural prop generator with cottage-garden placeholder props, and prove both work together in one real zone (`cottage_garden.tscn`).

**Architecture:** Three typed GDScript `Resource` classes (`PropPlacement`, `ScatterRegion`, `Zone`) hold zone layout data with no behavior. A `@tool` `ZoneBuilder.gd` node reads a `Zone` and instances discrete props (dressed via the existing `PaletteApply`) plus seeded `MultiMeshInstance3D` scatter (one per scatter variant mesh, sharing the palette material). New placeholder props (cottage kit, planter, well, grass/flower/rock) extend `tools/assetgen/props.py`, following its existing deterministic `MeshBuilder` pattern, with a new `HERO_TRI_BUDGET` exception for the cottage kit pieces. `cottage_garden.tscn` reuses `glade.tscn`'s lighting/environment/collider rig and wires a `ZoneBuilder` against a hand-authored `cottage_garden.tres` `Zone` resource.

**Tech Stack:** Godot 4.7 / GDScript, gdUnit4 (GDScript tests), Python 3 + pytest (`tools/assetgen`), existing `PaletteApply` toon-material system.

**Spec:** `docs/superpowers/specs/2026-08-10-zone-tooling-environment-placeholders-design.md`

---

## Chunk 1: Zone data model + ZoneBuilder

*Deviation from the spec's file layout:* the spec sketches the data model
as one `zone_resource.gd`; this plan splits it into `prop_placement.gd`,
`scatter_region.gd`, and `zone.gd` instead, one `Resource` subclass per
file, so each stays small and single-purpose (consistent with how the rest
of `src/` is organized — e.g. `interactable.gd` holds only `Interactable`).
The data/behavior contract from the spec is unchanged.

### Task 1: `PropPlacement` resource

**Files:**
- Create: `src/world/prop_placement.gd`
- Test: `tests/unit/test_zone_resources.gd`

- [ ] **Step 1: Write the failing test**

```gdscript
extends GdUnitTestSuite
## Zone data model: PropPlacement, ScatterRegion, Zone — pure data, no
## behavior. These tests just confirm the typed fields exist with sane
## defaults so ZoneBuilder (tested separately) can rely on them.

func test_prop_placement_defaults() -> void:
	var placement := PropPlacement.new()
	assert_object(placement.scene).is_null()
	assert_vector(placement.position).is_equal(Vector3.ZERO)
	assert_vector(placement.rotation_degrees).is_equal(Vector3.ZERO)
	assert_float(placement.scale).is_equal(1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_resources.gd --ignoreHeadlessMode`
Expected: FAIL — `Identifier "PropPlacement" not declared`.

- [ ] **Step 3: Write minimal implementation**

```gdscript
class_name PropPlacement
extends Resource
## One discrete prop instance in a Zone: which scene, where, how big.

@export var scene: PackedScene
@export var position := Vector3.ZERO
@export var rotation_degrees := Vector3.ZERO
@export var scale := 1.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS (1 test).

- [ ] **Step 5: Commit**

```bash
git add src/world/prop_placement.gd tests/unit/test_zone_resources.gd
git commit -m "Add PropPlacement zone data resource"
```

### Task 2: `ScatterRegion` resource

**Files:**
- Create: `src/world/scatter_region.gd`
- Modify: `tests/unit/test_zone_resources.gd`

- [ ] **Step 1: Write the failing test** (append to the same file)

```gdscript
func test_scatter_region_defaults() -> void:
	var region := ScatterRegion.new()
	assert_array(region.variants).is_empty()
	assert_int(region.shape).is_equal(ScatterRegion.Shape.CIRCLE)
	assert_vector(region.center).is_equal(Vector3.ZERO)
	assert_vector(region.size).is_equal(Vector2.ZERO)
	assert_float(region.density).is_equal(0.0)
	assert_float(region.scale_min).is_equal(1.0)
	assert_float(region.scale_max).is_equal(1.0)
	assert_int(region.seed).is_equal(0)
```

(Area computation from `shape`/`size` is intentionally kept out of
`ScatterRegion` — it's pure data with no methods, matching `PropPlacement`
and `Zone`. The area calculation is a `ZoneBuilder` concern and is tested
in Task 5, where it's actually used.)

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_resources.gd --ignoreHeadlessMode`
Expected: FAIL — `Identifier "ScatterRegion" not declared`.

- [ ] **Step 3: Write minimal implementation**

```gdscript
class_name ScatterRegion
extends Resource
## A seeded, deterministic scatter patch: a pool of mesh variants filling
## a circle or rect area at a target density (instances per m²).
##
## `variants` are plain `Mesh` resources, not PackedScenes — a MultiMesh
## renders one mesh/material per instance batch, so ZoneBuilder makes one
## MultiMeshInstance3D per variant, not per placement or per pool.

enum Shape { CIRCLE, RECT }

@export var variants: Array[Mesh] = []
@export var shape := Shape.CIRCLE
@export var center := Vector3.ZERO
## For CIRCLE: size.x is the radius (size.y unused).
## For RECT: size.x is width, size.y is depth.
@export var size := Vector2.ZERO
@export var density := 0.0  ## instances per square meter
@export var scale_min := 1.0
@export var scale_max := 1.0
@export var seed := 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS (2 tests total).

- [ ] **Step 5: Commit**

```bash
git add src/world/scatter_region.gd tests/unit/test_zone_resources.gd
git commit -m "Add ScatterRegion zone data resource"
```

### Task 3: `Zone` resource

**Files:**
- Create: `src/world/zone.gd`
- Modify: `tests/unit/test_zone_resources.gd`

- [ ] **Step 1: Write the failing test** (append)

```gdscript
func test_zone_defaults() -> void:
	var zone := Zone.new()
	assert_vector(zone.ground_size).is_equal(Vector2.ZERO)
	assert_array(zone.placements).is_empty()
	assert_array(zone.scatter_regions).is_empty()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_resources.gd --ignoreHeadlessMode`
Expected: FAIL — `Identifier "Zone" not declared`.

- [ ] **Step 3: Write minimal implementation**

```gdscript
class_name Zone
extends Resource
## Data-only description of a walkable zone: its footprint, discrete prop
## placements, and scatter regions. No behavior — ZoneBuilder turns this
## into actual nodes. Diffable, editable in the Inspector as a .tres file.

@export var ground_size := Vector2.ZERO
@export var placements: Array[PropPlacement] = []
@export var scatter_regions: Array[ScatterRegion] = []
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS (3 tests total).

- [ ] **Step 5: Commit**

```bash
git add src/world/zone.gd tests/unit/test_zone_resources.gd
git commit -m "Add Zone resource tying placements and scatter regions together"
```

### Task 4: `ZoneBuilder` — discrete placements

**Files:**
- Create: `src/world/zone_builder.gd`
- Create: `tests/unit/test_zone_builder.gd`

Reference: `src/core/palette_apply.gd` for how existing code walks a subtree
and applies the palette material — `ZoneBuilder` calls `PaletteApply.apply()`
per placement the same way `glade.gd` calls it once for the whole scene.

- [ ] **Step 1: Write the failing test**

```gdscript
extends GdUnitTestSuite
## ZoneBuilder: turns a Zone resource into real nodes (discrete props +
## MultiMesh scatter), deterministically.

const CRATE_SCENE := "res://assets/generated/crate.glb"


func _make_zone_with_placements() -> Zone:
	var zone := Zone.new()
	zone.ground_size = Vector2(4.0, 4.0)
	var a := PropPlacement.new()
	a.scene = load(CRATE_SCENE)
	a.position = Vector3(1.0, 0.0, 1.0)
	var b := PropPlacement.new()
	b.scene = load(CRATE_SCENE)
	b.position = Vector3(-1.0, 0.0, -1.0)
	zone.placements = [a, b]
	return zone


func test_rebuild_instances_each_placement() -> void:
	var builder := ZoneBuilder.new()
	auto_free(builder)
	builder.zone = _make_zone_with_placements()
	builder.rebuild()

	assert_int(builder.get_child_count()).is_equal(2)
	var first := builder.get_child(0)
	assert_vector((first as Node3D).position).is_equal(Vector3(1.0, 0.0, 1.0))


func test_rebuild_clears_previous_children() -> void:
	var builder := ZoneBuilder.new()
	auto_free(builder)
	builder.zone = _make_zone_with_placements()
	builder.rebuild()
	builder.rebuild()

	assert_int(builder.get_child_count()).is_equal(2)  # not 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_builder.gd --ignoreHeadlessMode`
Expected: FAIL — `Identifier "ZoneBuilder" not declared`.

- [ ] **Step 3: Write minimal implementation**

```gdscript
@tool
class_name ZoneBuilder
extends Node3D
## Turns a Zone resource into real nodes: discrete props (dressed via
## PaletteApply, same as any other prop) and seeded MultiMesh scatter.
##
## Live re-preview while editing an open zone is a known limitation: nested
## PropPlacement/ScatterRegion edits don't reliably bubble a `changed`
## signal up to the Zone resource. Reload the scene (or re-enter the
## editor) to see edits reflected; rebuild() always reruns on _ready().

@export var zone: Zone:
	set(value):
		zone = value
		if is_inside_tree():
			rebuild()


func _ready() -> void:
	rebuild()


func rebuild() -> void:
	for child in get_children():
		remove_child(child)
		child.queue_free()
	if zone == null:
		return
	_build_placements()


func _build_placements() -> void:
	for placement in zone.placements:
		if placement.scene == null:
			continue
		var instance := placement.scene.instantiate()
		add_child(instance)
		if instance is Node3D:
			var node3d := instance as Node3D
			node3d.position = placement.position
			node3d.rotation_degrees = placement.rotation_degrees
			node3d.scale = Vector3.ONE * placement.scale
		PaletteApply.apply(instance)
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add src/world/zone_builder.gd tests/unit/test_zone_builder.gd
git commit -m "Add ZoneBuilder: instance discrete Zone placements"
```

### Task 5: `ZoneBuilder` — MultiMesh scatter

**Files:**
- Modify: `src/world/zone_builder.gd`
- Modify: `tests/unit/test_zone_builder.gd`

- [ ] **Step 1: Write the failing test** (append)

```gdscript
func _make_zone_with_scatter() -> Zone:
	var zone := Zone.new()
	zone.ground_size = Vector2(4.0, 4.0)
	var mesh_a := BoxMesh.new()
	var mesh_b := BoxMesh.new()
	var region := ScatterRegion.new()
	region.variants = [mesh_a, mesh_b]
	region.shape = ScatterRegion.Shape.RECT
	region.size = Vector2(2.0, 2.0)  # area = 4 m^2
	region.density = 5.0             # 20 instances total, split 10/10
	region.seed = 42
	zone.scatter_regions = [region]
	return zone


func test_rebuild_creates_one_multimesh_per_variant() -> void:
	var builder := ZoneBuilder.new()
	auto_free(builder)
	builder.zone = _make_zone_with_scatter()
	builder.rebuild()

	var multimeshes: Array = []
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			multimeshes.append(child)
	assert_int(multimeshes.size()).is_equal(2)

	var total_instances := 0
	for mmi in multimeshes:
		total_instances += (mmi as MultiMeshInstance3D).multimesh.instance_count
	assert_int(total_instances).is_equal(20)


func test_rebuild_scatter_is_deterministic() -> void:
	var zone := _make_zone_with_scatter()
	var first := ZoneBuilder.new()
	auto_free(first)
	first.zone = zone
	first.rebuild()

	var second := ZoneBuilder.new()
	auto_free(second)
	second.zone = zone
	second.rebuild()

	var first_mmi := first.get_child(0) as MultiMeshInstance3D
	var second_mmi := second.get_child(0) as MultiMeshInstance3D
	assert_int(second_mmi.multimesh.instance_count) \
		.is_equal(first_mmi.multimesh.instance_count)
	for i in range(first_mmi.multimesh.instance_count):
		var expected: Transform3D = first_mmi.multimesh.get_instance_transform(i)
		var actual: Transform3D = second_mmi.multimesh.get_instance_transform(i)
		assert_bool(actual.is_equal_approx(expected)) \
			.override_failure_message("scatter instance %d transform not deterministic" % i) \
			.is_true()


func test_rebuild_dresses_placements_and_scatter_with_palette_material() -> void:
	var palette_material: Material = load(PaletteApply.PALETTE_MATERIAL_PATH)
	var builder := ZoneBuilder.new()
	auto_free(builder)
	var zone := _make_zone_with_placements()
	zone.scatter_regions = _make_zone_with_scatter().scatter_regions
	builder.zone = zone
	builder.rebuild()

	var mesh_instances: Array = []
	var multimesh_instances: Array = []
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			multimesh_instances.append(child)
		else:
			mesh_instances.append_array(
				(child as Node).find_children("*", "MeshInstance3D", true, false)
			)

	assert_int(mesh_instances.size()).is_greater(0)
	for found in mesh_instances:
		assert_object((found as MeshInstance3D).material_override) \
			.override_failure_message("a discrete placement mesh is missing the palette material") \
			.is_same(palette_material)

	assert_int(multimesh_instances.size()).is_greater(0)
	for found in multimesh_instances:
		assert_object((found as MultiMeshInstance3D).material_override) \
			.override_failure_message("a scatter MultiMeshInstance3D is missing the palette material") \
			.is_same(palette_material)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_builder.gd --ignoreHeadlessMode`
Expected: FAIL — `test_rebuild_creates_one_multimesh_per_variant` fails, no `MultiMeshInstance3D` children created.

- [ ] **Step 3: Write minimal implementation**

```gdscript
func rebuild() -> void:
	for child in get_children():
		remove_child(child)
		child.queue_free()
	if zone == null:
		return
	_build_placements()
	_build_scatter()


func _region_area(region: ScatterRegion) -> float:
	if region.shape == ScatterRegion.Shape.CIRCLE:
		return PI * region.size.x * region.size.x
	return region.size.x * region.size.y


func _build_scatter() -> void:
	var palette_material := load(PaletteApply.PALETTE_MATERIAL_PATH) as Material
	for region in zone.scatter_regions:
		if region.variants.is_empty():
			continue
		var total := roundi(region.density * _region_area(region))
		var counts := _split_evenly(total, region.variants.size())
		for i in range(region.variants.size()):
			var count: int = counts[i]
			if count <= 0:
				continue
			# Each variant gets its own RNG, seeded from the region seed
			# combined with the variant index, so adding/removing variants
			# doesn't reshuffle every other variant's placement, and the
			# same Zone always reproduces the same layout per variant.
			var rng := RandomNumberGenerator.new()
			rng.seed = region.seed + i
			var mmi := MultiMeshInstance3D.new()
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.mesh = region.variants[i]
			mm.instance_count = count
			for instance_index in range(count):
				mm.set_instance_transform(instance_index, _random_transform(rng, region))
			mmi.multimesh = mm
			mmi.material_override = palette_material
			add_child(mmi)


func _split_evenly(total: int, variant_count: int) -> Array:
	var counts: Array = []
	counts.resize(variant_count)
	counts.fill(0)
	for i in range(total):
		counts[i % variant_count] += 1
	return counts


func _random_transform(rng: RandomNumberGenerator, region: ScatterRegion) -> Transform3D:
	var offset: Vector3
	if region.shape == ScatterRegion.Shape.CIRCLE:
		var angle := rng.randf_range(0.0, TAU)
		var radius := region.size.x * sqrt(rng.randf())
		offset = Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
	else:
		offset = Vector3(
			rng.randf_range(-region.size.x / 2.0, region.size.x / 2.0),
			0.0,
			rng.randf_range(-region.size.y / 2.0, region.size.y / 2.0),
		)
	var scale := rng.randf_range(region.scale_min, region.scale_max)
	var basis := Basis(Vector3.UP, rng.randf_range(0.0, TAU)).scaled(Vector3.ONE * scale)
	return Transform3D(basis, region.center + offset)
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS (5 tests total in `test_zone_builder.gd`).

- [ ] **Step 5: Commit**

```bash
git add src/world/zone_builder.gd tests/unit/test_zone_builder.gd
git commit -m "Add MultiMesh scatter to ZoneBuilder"
```

**Chunk 1 complete when:** `test_zone_resources.gd` and `test_zone_builder.gd`
both pass via `make test-godot` (or the direct gdUnit command above), and a
full run of `make import && make test-godot` (all suites, not just the new
ones) is fully green — confirming `test_glade.gd`, `test_avatar.gd`, and
every other existing suite still pass unaffected.

---

## Chunk 2: New placeholder props (Python assetgen)

### Task 6: `HERO_TRI_BUDGET` + hero-prop exception in the budget test

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

In `tests/python/test_assetgen.py`, replace the existing
`test_prop_builds_within_budget` with a version that checks hero props
against the hero budget:

```python
@pytest.mark.parametrize("name", sorted(props.PROPS))
def test_prop_builds_within_budget(name):
    builder = props.build_prop(name, seed=0)
    assert builder.tri_count > 0
    budget = props.HERO_TRI_BUDGET if name in props.HERO_PROPS else props.TRI_BUDGET
    assert builder.tri_count <= budget, (
        f"{name}: {builder.tri_count} tris over budget {budget}"
    )
    assert len(builder.positions) == len(builder.normals) == len(builder.uvs)
    assert max(builder.indices) == builder.vertex_count - 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `AttributeError: module 'tools.assetgen.props' has no attribute 'HERO_TRI_BUDGET'`.

- [ ] **Step 3: Write minimal implementation**

In `tools/assetgen/props.py`, right after `TRI_BUDGET = 600`:

```python
HERO_TRI_BUDGET = 1500

# Props allowed to spend the hero budget instead of the regular one — kept
# to a short, explicit list so budget creep needs a deliberate edit here.
HERO_PROPS: set[str] = set()
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS — `HERO_PROPS` is empty so behavior is unchanged from before.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add HERO_TRI_BUDGET exception model to prop budget test"
```

### Task 7: `build_planter` and `build_rock` (regular-budget props)

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Add `"planter"` and `"rock"` to the closed-volume parametrize list (they're
simple boxes, so they belong alongside `crate`/`ground_tile`):

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock"]
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

No new test file is needed for the budget/determinism checks — they already
run over `sorted(props.PROPS)`, so registering the new builders in `PROPS`
(Step 3) is what makes them exercised.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: planter` (and `rock`).

- [ ] **Step 3: Write minimal implementation**

In `tools/assetgen/props.py`, add before the `PROPS` dict:

```python
def build_planter(_seed: int = 0) -> MeshBuilder:
    """Raised garden bed — a soil-topped box for the cottage garden."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.2, 0), (0.9, 0.4, 0.5), "wood", 1, top=("clay", 0))
    return builder


def build_rock(seed: int = 0) -> MeshBuilder:
    """A low, faceted rock — scatterable or occasional hero placement."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    width = rng.uniform(0.35, 0.5)
    depth = rng.uniform(0.3, 0.45)
    height = rng.uniform(0.2, 0.32)
    add_box(builder, (0, height / 2.0, 0), (width, height, depth), "stone", 1,
            top=("stone", 2))
    return builder
```

Then update `PROPS`:

```python
PROPS = {
    "crate": build_crate,
    "fence": build_fence,
    "ground_tile": build_ground_tile,
    "jar": build_jar,
    "mug": build_mug,
    "pine": build_pine,
    "planter": build_planter,
    "rock": build_rock,
}
```

(`"clay"`, `"wood"`, and `"stone"` are existing ramps in
`tools/assetgen/palette.py`'s `RAMPS` list — already verified, no
substitution needed for this task.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: PASS (all tests, including the new closed-volume and budget
checks for `planter` and `rock`).

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add planter and rock placeholder props"
```

### Task 8: `build_well` (lathe-based prop)

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Add `"well"` to the closed-volume parametrize list started in Task 7 (with
capped ends, it's a fully closed solid, same as `crate`/`planter`/`rock`):

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well"]
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: well`.

- [ ] **Step 3: Write minimal implementation**

```python
def build_well(_seed: int = 0) -> MeshBuilder:
    """Small stone well — the cottage garden's water source."""
    builder = MeshBuilder()
    profile = [
        (0.0, 0.0),
        (0.35, 0.0),
        (0.37, 0.5),
        (0.35, 0.55),  # lip
    ]
    add_lathe(builder, profile, 12, "stone", 1, cap_start=True, cap_end=True)
    return builder
```

(`cap_start=True`/`cap_end=True` close the bottom and lip so the well is a
watertight solid — needed for `test_closed_props_have_positive_volume` to
give a meaningful positive-volume result; without caps this is an open
tube like `mug`'s body, which is why `mug`/`jar` aren't in that
parametrize list.)

Add `"well": build_well,` to `PROPS`.

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add well placeholder prop"
```

### Task 9: `build_grass_tuft` and `build_flower` (scatter props)

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Add a check that scatter props export as exactly one glTF primitive — this
is the real constraint the zone budget test in Chunk 3 depends on (a
`MultiMesh` can only render one mesh, so `ZoneBuilder` needs each scatter
variant's GLB to be a single mesh/primitive, and the Chunk 3 budget test
sums each surface's index count as a simple `tris * instance_count`, which
is only exact if there's exactly one surface):

```python
@pytest.mark.parametrize("name", ["grass_tuft", "flower"])
def test_scatter_props_export_as_single_primitive(name):
    doc = gltf.parse_glb(gltf.build_glb(props.build_prop(name, seed=0), name))["json"]
    assert len(doc["meshes"][0]["primitives"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: grass_tuft`.

- [ ] **Step 3: Write minimal implementation**

```python
def build_grass_tuft(seed: int = 0) -> MeshBuilder:
    """A few crossed blade quads — cheap enough to scatter densely."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    for i in range(3):
        angle = (math.pi / 3.0) * i
        height = rng.uniform(0.18, 0.28)
        half_width = 0.05
        dx = math.cos(angle) * half_width
        dz = math.sin(angle) * half_width
        builder.add_face(
            [
                (-dx, 0.0, -dz), (dx, 0.0, dz),
                (dx, height, dz), (-dx, height, -dz),
            ],
            "moss", 2,
        )
    return builder


def build_flower(seed: int = 0) -> MeshBuilder:
    """A single small flower — stem plus a flat bloom quad."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    add_cylinder(builder, (0, 0.09, 0), 0.01, 0.18, 5, "moss", 1, cap_top=False)
    bloom_shade = rng.choice([0, 1, 2])
    builder.add_face(
        [
            (-0.05, 0.18, 0.0), (0.05, 0.18, 0.0),
            (0.05, 0.18, 0.1), (-0.05, 0.18, 0.1),
        ],
        "honey", bloom_shade,
    )
    return builder
```

Add both to `PROPS`. (`"moss"` and `"honey"` are existing ramps in
`palette.py` — `"honey"`'s warm gold tone stands in for the flower bloom
placeholder; already verified, no substitution needed.)

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add grass tuft and flower scatter placeholder props"
```

### Task 10: Cottage wall/roof kit (hero props)

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("name", ["cottage_wall", "cottage_corner", "cottage_roof"])
def test_cottage_kit_pieces_are_hero_props(name):
    # These pieces opt into the higher HERO_TRI_BUDGET allowance (see
    # HERO_PROPS in props.py) since a modular building kit has more surface
    # detail than a single small prop. They don't need to actually exceed
    # the regular TRI_BUDGET to justify the exception — the exception exists
    # so kit pieces have headroom to gain detail later without a fresh budget
    # negotiation, not because these specific placeholders demand it.
    assert name in props.HERO_PROPS
    builder = props.build_prop(name, seed=0)
    assert 0 < builder.tri_count <= props.HERO_TRI_BUDGET
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: cottage_wall`.

- [ ] **Step 3: Write minimal implementation**

```python
def build_cottage_wall(_seed: int = 0) -> MeshBuilder:
    """One 2m wall segment: timber frame plus a whitewashed infill panel."""
    builder = MeshBuilder()
    add_box(builder, (0, 1.0, 0), (2.0, 2.0, 0.2), "cream", 2)
    for x in (-0.95, 0.95):
        add_box(builder, (x, 1.0, 0), (0.1, 2.0, 0.22), "bark", 1)
    add_box(builder, (0, 1.95, 0), (2.0, 0.1, 0.22), "bark", 1)
    add_box(builder, (0, 0.05, 0), (2.0, 0.1, 0.22), "bark", 1)
    return builder


def build_cottage_corner(_seed: int = 0) -> MeshBuilder:
    """An L-shaped corner post joining two wall segments."""
    builder = MeshBuilder()
    add_box(builder, (0, 1.0, 0), (0.2, 2.0, 0.2), "bark", 1)
    add_box(builder, (0, 1.95, 0), (0.24, 0.1, 0.24), "bark", 2)
    return builder


def build_cottage_roof(_seed: int = 0) -> MeshBuilder:
    """A flat two-panel roof placeholder (not actually pitched — both
    panels sit at the same height side by side). Good enough to read as
    "roof-shaped" from a distance; a true pitched/mitred ridge is left for
    a later, non-placeholder pass."""
    builder = MeshBuilder()
    add_box(builder, (-0.55, 0.15, 0), (1.3, 0.1, 2.2), "honey", 2)
    add_box(builder, (0.55, 0.15, 0), (1.3, 0.1, 2.2), "honey", 2)
    return builder
```

(`"cream"` and `"honey"` are existing ramps in `palette.py`, standing in
for whitewash/plaster and thatch respectively — already verified, no
substitution needed. The roof is deliberately a flat two-panel placeholder,
not a mitred ridge; `build_cottage_roof` doesn't attempt any rotation —
both panels sit flat side by side, which is a fine "roof-shaped enough"
placeholder per the pivot's placeholder policy.)

Add all three to `PROPS`, and to `HERO_PROPS`:

```python
HERO_PROPS: set[str] = {"cottage_wall", "cottage_corner", "cottage_roof"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS. Also re-run the full suite to confirm nothing regressed:
`python3 -m pytest tests/python -q`.
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add cottage wall/corner/roof hero placeholder props"
```

### Task 11: Wire new props into the asset build + regenerate

**Files:**
- Modify: none (verifies `tools/assetgen/build.py` already picks up new `PROPS` entries automatically via `sorted(props.PROPS)`)

- [ ] **Step 1: Run the asset build**

Run: `python3 -m tools.assetgen.build`
Expected: succeeds; `assets/generated/` now contains
`planter.glb`, `rock.glb`, `well.glb`, `grass_tuft.glb`, `flower.glb`,
`cottage_wall.glb`, `cottage_corner.glb`, `cottage_roof.glb`, plus
`manifest.json` listing them under `"props"`.

- [ ] **Step 2: Verify manifest entries**

Run: `python3 -c "import json; m = json.load(open('assets/generated/manifest.json')); print(sorted(m['props']))"`
Expected: includes all 8 new names alongside the existing ones.

- [ ] **Step 3: Re-import in Godot so the new GLBs are usable**

Run: `.tooling/godot --headless --path . --import`
Expected: completes without errors; `.import` files exist for each new GLB
under `assets/generated/`.

- [ ] **Step 4: Commit** (only if `assets/generated/` is tracked in git —
check with `git status assets/generated/` first; per the pivot spec this
directory is expected to be gitignored/rebuildable, so this step likely
produces nothing to commit)

```bash
git status assets/generated/
# If tracked and changed:
git add assets/generated/
git commit -m "Regenerate assets/generated with new placeholder props"
```

**Chunk 2 complete when:** `python3 -m pytest tests/python -q` is fully
green, and `assets/generated/` contains all 8 new placeholder prop GLBs.

---

## Chunk 3: Cottage garden zone + budget/smoke tests

### Task 12: `cottage_garden.tres` — author the Zone data

**Files:**
- Create: `src/world/cottage_garden/cottage_garden.tres`

This is hand-authored `.tres` text (Godot's resource text format), the same
way `src/materials/palette_main.tres` is hand-authored today — no Godot
editor GUI session is required.

- [ ] **Step 1: Get each new prop's UID** (Godot 4.4+ resources are
addressed by UID as well as path; using `path=` `ext_resource` entries is
still valid and simpler for hand-authoring, so this plan uses `path=`
consistently, matching how `glade.tscn`'s `ext_resource` entries are
written — no separate UID lookup needed.)

- [ ] **Step 2: Write the file**

```
[gd_resource type="Resource" script_class="Zone" load_steps=18 format=3]

[ext_resource type="Script" path="res://src/world/zone.gd" id="1_zone"]
[ext_resource type="Script" path="res://src/world/prop_placement.gd" id="2_placement"]
[ext_resource type="Script" path="res://src/world/scatter_region.gd" id="3_scatter"]
[ext_resource type="PackedScene" path="res://assets/generated/cottage_wall.glb" id="4_wall"]
[ext_resource type="PackedScene" path="res://assets/generated/cottage_corner.glb" id="5_corner"]
[ext_resource type="PackedScene" path="res://assets/generated/cottage_roof.glb" id="6_roof"]
[ext_resource type="PackedScene" path="res://assets/generated/planter.glb" id="7_planter"]
[ext_resource type="PackedScene" path="res://assets/generated/well.glb" id="8_well"]
[ext_resource type="PackedScene" path="res://assets/generated/fence.glb" id="9_fence"]

[sub_resource type="Resource" id="Placement_wall_n"]
script = ExtResource("2_placement")
scene = ExtResource("4_wall")
position = Vector3(0, 0, -2)
rotation_degrees = Vector3(0, 0, 0)
scale = 1.0

[sub_resource type="Resource" id="Placement_wall_e"]
script = ExtResource("2_placement")
scene = ExtResource("4_wall")
position = Vector3(2, 0, 0)
rotation_degrees = Vector3(0, 90, 0)
scale = 1.0

[sub_resource type="Resource" id="Placement_corner_ne"]
script = ExtResource("2_placement")
scene = ExtResource("5_corner")
position = Vector3(2, 0, -2)
rotation_degrees = Vector3(0, 0, 0)
scale = 1.0

[sub_resource type="Resource" id="Placement_roof"]
script = ExtResource("2_placement")
scene = ExtResource("6_roof")
position = Vector3(1, 2, -1)
rotation_degrees = Vector3(0, 0, 0)
scale = 1.0

[sub_resource type="Resource" id="Placement_planter"]
script = ExtResource("2_placement")
scene = ExtResource("7_planter")
position = Vector3(-2, 0, 1.5)
rotation_degrees = Vector3(0, 0, 0)
scale = 1.0

[sub_resource type="Resource" id="Placement_well"]
script = ExtResource("2_placement")
scene = ExtResource("8_well")
position = Vector3(2.5, 0, 2.5)
rotation_degrees = Vector3(0, 0, 0)
scale = 1.0

[sub_resource type="Resource" id="Placement_fence_1"]
script = ExtResource("2_placement")
scene = ExtResource("9_fence")
position = Vector3(-3, 0, -1)
rotation_degrees = Vector3(0, 90, 0)
scale = 1.0

[sub_resource type="Resource" id="Placement_fence_2"]
script = ExtResource("2_placement")
scene = ExtResource("9_fence")
position = Vector3(-3, 0, 0)
rotation_degrees = Vector3(0, 90, 0)
scale = 1.0

[resource]
script = ExtResource("1_zone")
ground_size = Vector2(8, 8)
placements = Array[ExtResource("2_placement")]([SubResource("Placement_wall_n"), SubResource("Placement_wall_e"), SubResource("Placement_corner_ne"), SubResource("Placement_roof"), SubResource("Placement_planter"), SubResource("Placement_well"), SubResource("Placement_fence_1"), SubResource("Placement_fence_2")])
scatter_regions = Array[ExtResource("3_scatter")]([])
```

> Note for the implementer: the `scatter_regions` array is left empty here
> deliberately — `ScatterRegion.variants` needs `Mesh` resources (not
> `PackedScene`s), which means extracting the `.mesh` sub-resource from
> each generated GLB. That's fiddly to hand-write correctly in `.tres` text
> without risking a malformed reference. **Do this step interactively in
> the Godot editor instead**: open `cottage_garden.tres` in the Inspector
> (create it via this task's text first, then open the project in the
> editor), add 1–2 `ScatterRegion` entries (e.g. a grass-tuft/flower patch
> covering most of the 8×8 ground), assign `grass_tuft.glb`'s and
> `flower.glb`'s mesh sub-resources as `variants`, set a modest `density`
> (e.g. `2.0`–`4.0` instances/m² — check against the zone budget test in
> Task 14 once it exists), and save. This keeps the risky "reference a
> nested mesh sub-resource of an imported GLB from hand-written text" step
> out of manually authored text, matching the design spec's stated
> authoring workflow ("edited via the standard Godot Inspector").

- [ ] **Step 3: Author the scatter regions (interactive, in the Godot editor)**

Open the project in the Godot editor, open `cottage_garden.tres` in the
Inspector, and add exactly the 1-2 `ScatterRegion` entries described in
Step 2's note above (grass-tuft/flower patch covering most of the 8×8
ground, `grass_tuft.glb`/`flower.glb` mesh sub-resources as `variants`,
density 2.0-4.0/m²). Save the resource. **This step is required, not
optional** — Task 13's smoke test and Task 14's budget test both assert a
scatter region exists, so they will fail (correctly) until this step is
done. Do not mark this task complete without having actually added and
saved at least one `ScatterRegion`.

- [ ] **Step 4: Sanity-load the resource**

Run: `.tooling/godot --headless --path . --script res://tools/dev/print_zone.gd`
— if no such dev script exists yet, skip this step and instead verify via
the gdUnit smoke test in Task 13, which loads the resource as part of
loading the scene. (Do not create a one-off throwaway script just for this
manual check — the smoke test is the real verification.)

- [ ] **Step 5: Commit**

```bash
git add src/world/cottage_garden/cottage_garden.tres
git commit -m "Author cottage_garden Zone data"
```

### Task 13: `cottage_garden.tscn` — assemble the scene

**Files:**
- Create: `src/world/cottage_garden/cottage_garden.gd`
- Create: `src/world/cottage_garden/cottage_garden.tscn`
- Create: `tests/unit/test_cottage_garden.gd`

Reference: `src/sandbox/glade.tscn` and `src/sandbox/glade.gd` for the
lighting/environment/collider rig this reuses, and `tests/unit/test_glade.gd`
for the smoke-test pattern this follows.

- [ ] **Step 1: Write the failing test**

```gdscript
extends GdUnitTestSuite
## Cottage garden smoke: the zone assembles with a player and at least one
## discrete prop and one scatter patch from the ZoneBuilder.

const COTTAGE_GARDEN_SCENE := "res://src/world/cottage_garden/cottage_garden.tscn"


func test_cottage_garden_assembles_with_player_and_props() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(10)
	var garden := runner.scene()

	assert_object(garden.get_node_or_null("Player")).is_not_null()

	var builder := garden.get_node("%ZoneBuilder") as ZoneBuilder
	assert_object(builder).is_not_null()

	var has_discrete_prop := false
	var has_scatter := false
	for child in builder.get_children():
		if child is MultiMeshInstance3D:
			has_scatter = true
		elif child is MeshInstance3D or child is Node3D:
			has_discrete_prop = true
	assert_bool(has_discrete_prop).override_failure_message(
		"expected at least one discrete PropPlacement instanced under %ZoneBuilder"
	).is_true()
	assert_bool(has_scatter).override_failure_message(
		"expected at least one scatter region in cottage_garden.tres"
	).is_true()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_cottage_garden.gd --ignoreHeadlessMode`
Expected: FAIL — scene doesn't exist yet.

- [ ] **Step 3: Write the scene + script**

`src/world/cottage_garden/cottage_garden.gd` (mirrors `glade.gd`'s
`_stage()` lighting setup, minus the seam-stone interaction which isn't
part of this zone):

```gdscript
extends Node3D
## The cottage garden — Phase 4's first tooling-built zone.

func _ready() -> void:
	_stage()


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
```

`src/world/cottage_garden/cottage_garden.tscn` — copy `src/sandbox/glade.tscn`
as a starting point (`WorldEnvironment`, `Sun`, `Fill`, `GroundCollider`,
`Player`), then:
- Point the root script at `cottage_garden.gd` instead of `glade.gd`.
- Remove the `SeamStone`/`SeamInteractable` nodes (not part of this zone).
- Add a `Node3D` named `ZoneBuilder` (unique-named `%ZoneBuilder`) with
  script `res://src/world/zone_builder.gd`, `zone` set to
  `res://src/world/cottage_garden/cottage_garden.tres`.
- Keep the `Player` node and its transform from `glade.tscn`, repositioned
  if needed so it spawns inside the 8×8 garden footprint (e.g. `(0, 0, 3)`).

- [ ] **Step 4: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS.

- [ ] **Step 5: Manually verify in Godot** (use the Godot MCP tools if
available in this environment, mirroring how `glade.tscn` was verified
during the pivot work)

Run the scene and confirm no errors in the debug output; confirm the
cottage kit pieces, planter, well, fence, and grass/flower scatter are all
visible and dressed with the palette material.

- [ ] **Step 6: Commit**

```bash
git add src/world/cottage_garden/cottage_garden.gd src/world/cottage_garden/cottage_garden.tscn tests/unit/test_cottage_garden.gd
git commit -m "Assemble cottage_garden zone via ZoneBuilder"
```

### Task 14: Zone budget test

**Files:**
- Create: `tests/unit/test_zone_budget.gd`

- [ ] **Step 1: Write the failing test**

```gdscript
extends GdUnitTestSuite
## Zone budget: cottage_garden must stay within the design bible's
## 150k tri / 120 draw call zone ceiling. This is a static upper-bound
## check (no frustum culling accounted for), matching the design bible's
## "asserted per asset in tests/python, per zone in gdUnit scene tests"
## split.

const COTTAGE_GARDEN_SCENE := "res://src/world/cottage_garden/cottage_garden.tscn"
const MAX_TRIS := 150_000
const MAX_DRAW_CALLS := 120


func test_cottage_garden_within_zone_budget() -> void:
	var runner := scene_runner(COTTAGE_GARDEN_SCENE)
	await runner.simulate_frames(3)
	var garden := runner.scene()

	var total_tris := 0
	var draw_calls := 0
	for found in garden.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.mesh != null:
			total_tris += _mesh_tri_count(mesh_instance.mesh)
			draw_calls += 1
	for found in garden.find_children("*", "MultiMeshInstance3D", true, false):
		var mmi := found as MultiMeshInstance3D
		if mmi.multimesh != null and mmi.multimesh.mesh != null:
			var per_instance := _mesh_tri_count(mmi.multimesh.mesh)
			total_tris += per_instance * mmi.multimesh.instance_count
			draw_calls += 1

	assert_int(total_tris).override_failure_message(
		"cottage_garden over the 150k tri zone budget"
	).is_less_equal(MAX_TRIS)
	assert_int(draw_calls).override_failure_message(
		"cottage_garden over the 120 draw call zone budget"
	).is_less_equal(MAX_DRAW_CALLS)


func _mesh_tri_count(mesh: Mesh) -> int:
	# Scatter/generated props are single-primitive (asserted in
	# tests/python/test_assetgen.py::test_scatter_props_export_as_single_primitive),
	# so summing surface_get_array_len over ARRAY_INDEX is exact here.
	var tris := 0
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		tris += indices.size() / 3
	return tris
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_zone_budget.gd --ignoreHeadlessMode`
Expected: this test should PASS immediately if Task 13 assembled a small
scene, since 8 hero/regular props plus a modest grass/flower scatter patch
is nowhere near 150k tris. If it unexpectedly FAILS, the scatter `density`
set in Task 12 is too high — lower it in `cottage_garden.tres` and rerun.

- [ ] **Step 3: N/A** (test passing on first run is fine here — this task
is a budget *guard*, not new production code with a red/green cycle)

- [ ] **Step 4: Commit**

```bash
git add tests/unit/test_zone_budget.gd
git commit -m "Add cottage_garden zone budget test"
```

### Task 15: Update `ROADMAP.md` and `docs/asset-inventory.md`

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/asset-inventory.md`

- [ ] **Step 1: Update ROADMAP.md**

In the Phase 4 section, mark T4.1 and T4.2 done and note where the spec/plan
live:

```markdown
- T4.1 Environment placeholders ✅ done — cottage kit, planter, well,
  grass/flower/rock added to `tools/assetgen/props.py`
  (see `docs/superpowers/plans/2026-08-10-zone-tooling-environment-placeholders.md`)
- T4.2 Zone tooling (placement, MultiMesh scatter, zone schema) ✅ done —
  `Zone`/`ZoneBuilder` in `src/world/`, proven via `cottage_garden` zone
```

Update the Status table's Phase 4 row from "⏭️ next up" to reflect T4.1/T4.2
done, T4.3–T4.5 still pending.

- [ ] **Step 2: Update docs/asset-inventory.md**

Add rows for the 8 new placeholder props (name, source = "procedural
placeholder", status = done), matching the existing table format.

- [ ] **Step 3: Commit**

```bash
git add ROADMAP.md docs/asset-inventory.md
git commit -m "Mark T4.1/T4.2 done in ROADMAP and asset inventory"
```

**Chunk 3 complete when:** `make test` (both `test-python` and
`test-godot`) is fully green, `cottage_garden.tscn` loads cleanly with zero
errors when run directly in Godot, and `ROADMAP.md`/`docs/asset-inventory.md`
reflect T4.1/T4.2 as done.

---

## Final verification (whole plan)

- [ ] Run `python3 -m pytest tests/python -q` — expect all green (no
  regressions vs. the 111/113-passing baseline noted in the pivot spec; the
  2 pre-existing Task-12 Blender failures are unrelated and expected to
  remain failing).
- [ ] Run `make import && make test-godot` — expect all gdUnit suites green,
  including the new `test_zone_resources.gd`, `test_zone_builder.gd`,
  `test_cottage_garden.gd`, and `test_zone_budget.gd`.
- [ ] Run `cottage_garden.tscn` directly in Godot (via the Godot MCP tools
  or `make run` pointed at the scene) and visually confirm the cottage
  kit, planter, well, fence, and grass/flower scatter render correctly with
  palette materials and no console errors.
