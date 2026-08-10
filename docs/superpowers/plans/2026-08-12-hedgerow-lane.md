# Hedgerow Lane Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, playable hedgerow-lane zone (`hedgerow_lane.tscn`) — a straight 10m×2m lane flanked by hedge rows, one stone stile crossing point, and one signpost — reusing the existing `Zone`/`ZoneBuilder`/`PropPlacement` tooling and extending `tools/assetgen/props.py` with 4 new placeholder props.

**Architecture:** New deterministic `MeshBuilder`-based prop generators (`hedge`, `stone_stile`, `lane_path`, `signpost`) are added to `tools/assetgen/props.py`, following the file's existing `add_box`/`add_lathe` conventions — none are hero props, all use the regular `TRI_BUDGET = 600`. `hedgerow_lane.tres` is a hand-authored `Zone` resource describing a straight lane along the Z axis: 5 `lane_path` tiles (10m total), a full 5-segment `hedge` row on the west edge (`+X`), a 4-segment `hedge` row plus one `stone_stile` at the middle slot on the east edge (`-X`), and one `signpost` at the north end (`+Z`) — 16 `PropPlacement`s total, no `ScatterRegion` instances. `hedgerow_lane.tscn` reuses the `ZoneBuilder`/outdoor-lighting pattern from `cottage_garden.tscn` exactly (`Sun`/`Fill` `DirectionalLight3D`s, sky `WorldEnvironment`), and `hedgerow_lane.gd` mirrors `cottage_garden.gd`'s `_stage()` staging function verbatim. A gdUnit budget test mirrors `test_zone_budget.gd`/`test_interior_budget.gd`. No scene-transition/door logic, no gameplay systems, no scatter dressing — pure environment art, matching how `cottage_garden`/`cottage_interior` shipped.

**Tech Stack:** Godot 4.7 / GDScript, gdUnit4 (GDScript tests), Python 3 + pytest (`tools/assetgen`), existing `PaletteApply` toon-material system, existing `Zone`/`ZoneBuilder` tooling.

**Spec:** `docs/superpowers/specs/2026-08-12-hedgerow-lane-design.md`

---

## Chunk 1: New lane props (`tools/assetgen/props.py`)

Each task follows the same red/green pattern as the cottage-interior plan's
Chunk 1: add the prop name to `PROPS` pointing at a not-yet-defined
function, confirm the existing parametrized test suite in
`tests/python/test_assetgen.py` fails with `KeyError: unknown prop: <name>`,
then implement. `tools/assetgen/build.py` already loops over
`sorted(props.PROPS)` — no changes to `build.py` needed.

### Task 1: `build_hedge`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Add `"hedge"` to the closed-volume parametrize list (a single `add_box`
call is always a closed solid):

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor", "hearth", "table", "chair",
              "shelf", "bed", "hedge"],
)
def test_closed_props_have_positive_volume(name):
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: hedge`.

- [ ] **Step 3: Write minimal implementation**

```python
def build_hedge(_seed: int = 0) -> MeshBuilder:
    """One 2m hedge segment: a chunky moss-green box lining the lane."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.45, 0), (2.0, 0.9, 0.5), "moss", 1, top=("moss", 2))
    return builder
```

Add `"hedge": build_hedge,` to `PROPS` (alphabetically — after
`hearth`, before `interior_floor`, since "hearth" < "hedge" at the 3rd
character: `a` < `d`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_assetgen.py -k hedge -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add hedge placeholder prop"
```

### Task 2: `build_stone_stile`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Append `"stone_stile"` to the parametrize list from Task 1.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: stone_stile`.

- [ ] **Step 3: Write minimal implementation**

Two low stone step blocks flanking a low horizontal crossbar, sized to
occupy the same ~2.0m-long slot as one `hedge` segment (so it can directly
replace one in the row):

```python
def build_stone_stile(_seed: int = 0) -> MeshBuilder:
    """A stepover crossing through a hedge row: two stone steps + a rail."""
    builder = MeshBuilder()
    for x in (-0.6, 0.6):
        add_box(builder, (x, 0.2, 0), (0.5, 0.4, 0.5), "stone", 1, top=("stone", 2))
    add_box(builder, (0, 0.55, 0), (1.3, 0.08, 0.08), "wood", 1)
    return builder
```

Add `"stone_stile": build_stone_stile,` to `PROPS` (alphabetically — after
`shelf`, before `table`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_assetgen.py -k stone_stile -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add stone_stile placeholder prop"
```

### Task 3: `build_lane_path`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Append `"lane_path"` to the parametrize list.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: lane_path`.

- [ ] **Step 3: Write minimal implementation**

Structurally like `build_ground_tile` (shallow box, flat top face) but
using the `"clay"` palette family on top instead of `"moss"`:

```python
def build_lane_path(_seed: int = 0) -> MeshBuilder:
    """2x2 m lane path tile: dirt/clay ground distinct from grass."""
    builder = MeshBuilder()
    add_box(builder, (0, -0.1, 0), (2.0, 0.2, 2.0), "clay", 1,
            top=("clay", 2), bottom=("bark", 0))
    return builder
```

Add `"lane_path": build_lane_path,` to `PROPS` (alphabetically — after
`jar`, before `mug`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_assetgen.py -k lane_path -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add lane_path placeholder prop"
```

### Task 4: `build_signpost`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Append `"signpost"` to the parametrize list.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: signpost`.

- [ ] **Step 3: Write minimal implementation**

A single wood post (proportioned like `build_fence`'s posts) with two
short angled arm-planks near the top:

```python
def build_signpost(_seed: int = 0) -> MeshBuilder:
    """A single wayfinding post with two arm-planks near the top."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.6, 0), (0.1, 1.2, 0.1), "wood", 1, top=("wood", 2))
    add_box(builder, (0.25, 1.0, 0), (0.5, 0.1, 0.06), "wood", 2)
    add_box(builder, (-0.25, 0.85, 0), (0.5, 0.1, 0.06), "wood", 2)
    return builder
```

Add `"signpost": build_signpost,` to `PROPS` (alphabetically — after
`shelf`... note: after Task 2's `stone_stile` insertion, `signpost` sorts
before `stone_stile` — insert accordingly so the final alphabetical order
reads `...shelf, signpost, stone_stile, table...`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_assetgen.py -k signpost -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add signpost placeholder prop"
```

### Task 5: Build all new assets and run full python suite

**Files:** none (verification only)

- [ ] **Step 1:** Run `python3 -m tools.assetgen.build`
Expected: all 4 new `.glb` files build with no errors (alongside existing
assets). Confirm `assets/generated/` stays gitignored (`git status --short`
clean).

- [ ] **Step 2:** Run `python3 -m pytest tests/python -q`
Expected: PASS, aside from the 2 known pre-existing Blender
`test_build_character.py` baseline failures.

- [ ] **Step 3:** No commit needed (verification-only task) — but if
`build.py`'s run created any stray tracked-file diffs, investigate before
proceeding.

---

## Chunk 2: Zone assembly (`src/world/hedgerow_lane/`)

### Task 6: Author `hedgerow_lane.tres`

**Files:**
- Create: `src/world/hedgerow_lane/hedgerow_lane.tres`

- [ ] **Step 1: Write the failing test** (deferred — the smoke test in Task
7 will fail first because the scene doesn't exist yet; this task lands the
`.tres` data the scene will reference)

- [ ] **Step 2: Author the resource**

Hand-author `hedgerow_lane.tres` following the exact `.tres` syntax
conventions confirmed against `cottage_interior.tres`: `format=4`, no
`load_steps`, a real `ext_resource` backing the `ScatterRegion` script even
though `scatter_regions` stays an empty typed array.

Layout (Z axis = lane length, `+Z` = north, `-Z` = south, `+X` = west edge,
`-X` = east edge; lane tiles span `z` from `+4` down to `-4` in 2m
increments, i.e. slot centers at `z = 4, 2, 0, -2, -4`):

- 5 `lane_path` placements at `x = 0`, `z ∈ {4, 2, 0, -2, -4}` (slots 1-5,
  north to south).
- 5 `hedge` placements on the west edge at `x = 1.25`, same 5 `z` values
  (slots 1-5) — `1.25` = half lane width (1.0) + half hedge depth (0.25).
- 4 `hedge` placements on the east edge at `x = -1.25`, `z ∈ {4, 2, -2, -4}`
  (slots 1, 2, 4, 5 — slot 3 at `z = 0` deliberately skipped).
- 1 `stone_stile` placement at `x = -1.25, z = 0` (slot 3, replacing the
  skipped east-edge hedge — the lane's midpoint crossing point).
- 1 `signpost` placement at `x = -1.8, z = 4.5` (just off the east verge,
  beside lane_path slot 1 at the north end).

Total: 5 + 5 + 4 + 1 + 1 = **16** `PropPlacement`s. `ground_size =
Vector2(10, 4)` (10m lane length × ~4m footprint including both hedge
rows). Empty typed `scatter_regions` array.

- [ ] **Step 3: Commit**

```bash
git add src/world/hedgerow_lane/hedgerow_lane.tres
git commit -m "Author hedgerow_lane Zone data"
```

### Task 7: Assemble `hedgerow_lane.tscn` + `.gd` via ZoneBuilder

**Files:**
- Create: `src/world/hedgerow_lane/hedgerow_lane.tscn`
- Create: `src/world/hedgerow_lane/hedgerow_lane.gd`
- Create: `tests/unit/test_hedgerow_lane.gd`

- [ ] **Step 1: Write the failing test**

```gdscript
extends GdUnitTestSuite

const HEDGEROW_LANE_SCENE := "res://src/world/hedgerow_lane/hedgerow_lane.tscn"


func test_hedgerow_lane_has_expected_prop_count() -> void:
    var scene := load(HEDGEROW_LANE_SCENE) as PackedScene
    assert_that(scene).is_not_null()
    var instance := scene.instantiate()
    add_child(instance)
    auto_free(instance)
    var builder := instance.get_node("%ZoneBuilder")
    assert_that(builder.get_child_count()).is_equal(16)
```

(Mirror the exact assertion style — `assert_that`/`auto_free`/`%ZoneBuilder`
unique-name lookup — used in `tests/unit/test_cottage_interior.gd`.)

- [ ] **Step 2: Run test to verify it fails**

Run Godot import fresh (`/Applications/Godot.app/Contents/MacOS/Godot
--headless --path . --import`), then run the gdUnit suite filtered to this
test. Expected: FAIL — scene doesn't exist yet.

- [ ] **Step 3: Write minimal implementation**

Write `hedgerow_lane.gd` mirroring `cottage_garden.gd`'s `_stage()`
verbatim (same `Sun`/`Fill` lookup-and-configure pattern — rotation, light
color, energy, shadow flags — copied from `src/world/cottage_garden/cottage_garden.gd`).

Write `hedgerow_lane.tscn`: `WorldEnvironment` with `background_mode = 2`
(`BG_SKY`) and `ambient_light_source = 3` (`AMBIENT_SOURCE_SKY`), matching
`cottage_garden.tscn` exactly; `Sun` and `Fill` `DirectionalLight3D` nodes
in the same positions/rotations as `cottage_garden.tscn`; `GroundCollider`
sized to the lane's ~10m × 4m footprint; `ZoneBuilder` node (unique-named
`%ZoneBuilder`) referencing `hedgerow_lane.tres`; `Player` node, same as
`cottage_garden.tscn`/`cottage_interior.tscn`.

- [ ] **Step 4: Run test to verify it passes**

Re-run Godot import, then run the gdUnit suite filtered to
`test_hedgerow_lane.gd`. Expected: PASS (16-count assertion holds).
Then live-verify via the `godot-run_project` MCP tool — clean boot, only
known baseline shadowing warnings, no new errors.

- [ ] **Step 5: Commit**

```bash
git add src/world/hedgerow_lane/hedgerow_lane.tscn src/world/hedgerow_lane/hedgerow_lane.gd tests/unit/test_hedgerow_lane.gd
git commit -m "Assemble hedgerow_lane zone via ZoneBuilder"
```

(If Godot generates a `.gd.uid` sidecar for the new script or test file,
include it in this commit — matching the T4.3 precedent.)

### Task 8: Add zone budget test

**Files:**
- Create: `tests/unit/test_lane_budget.gd`

- [ ] **Step 1: Write the test**

Mirror `tests/unit/test_zone_budget.gd`/`test_interior_budget.gd` exactly:
load `hedgerow_lane.tscn`, sum triangle counts and draw calls across all
`MeshInstance3D`s under `%ZoneBuilder`, assert against the same 150k tri /
120 draw call zone ceiling.

- [ ] **Step 2: Run test to verify it passes**

Run the gdUnit suite filtered to `test_lane_budget.gd`. Expected: PASS
immediately (16 low-poly props are well under budget).

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_lane_budget.gd
git commit -m "Add hedgerow_lane zone budget test"
```

### Task 9: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1:** Run `python3 -m pytest tests/python -q`
Expected: PASS aside from the 2 known pre-existing Blender baseline
failures.

- [ ] **Step 2:** Run the full gdUnit suite (fresh `--import` first, `rm
-rf reports` after)
Expected: PASS aside from the 3 known pre-existing baseline failures
(`test_interact.gd` hysteresis + 2 in `test_avatar.gd`) — no new failures.

- [ ] **Step 3:** Live boot-check `hedgerow_lane.tscn` via
`godot-run_project` a second time for a final confirmation.

- [ ] **Step 4:** No commit needed (verification-only task).

---

## Chunk 3: Documentation

### Task 10: Update ROADMAP and asset inventory

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/asset-inventory.md`

- [ ] **Step 1:** Update `ROADMAP.md`: mark T4.4 done with a short
description matching T4.3's done-line format/style (zone path, prop count,
budget-tested-against reference), and update the Phase 4 status-table row
from "T4.1–T4.3 done, T4.4–T4.5 next" to "T4.1–T4.4 done, T4.5 next".

- [ ] **Step 2:** Update `docs/asset-inventory.md`: add 4 new rows —
`hedge` (category `nature`), `stone-stile` (category `building`),
`lane-path` (category `building`), `signpost` (category `building`) — each
`procedural placeholder`, dependencies formatted as
`tools/assetgen/props.py (\`build_x\`)` with the underscored function name,
matching the T4.3 rows' exact column conventions.

- [ ] **Step 3: Commit**

```bash
git add ROADMAP.md docs/asset-inventory.md
git commit -m "Update ROADMAP and asset inventory for hedgerow lane (T4.4)"
```
