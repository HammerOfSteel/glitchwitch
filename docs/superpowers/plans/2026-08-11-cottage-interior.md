# Cottage Interior Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone, playable cottage interior zone (`cottage_interior.tscn`) — a hearth-lit main room plus an open bed alcove — reusing the existing `Zone`/`ZoneBuilder`/`PropPlacement` tooling and extending `tools/assetgen/props.py` with 8 new interior furniture/kit placeholder props.

**Architecture:** New deterministic `MeshBuilder`-based prop generators (`interior_wall`, `interior_floor`, `hearth`, `table`, `chair`, `shelf`, `rug`, `bed`) are added to `tools/assetgen/props.py`, following the file's existing `add_box`/`add_lathe`/`add_face` conventions (`hearth` and `bed` opt into `HERO_TRI_BUDGET` as focal pieces). `cottage_interior.tres` is a hand-authored `Zone` resource — PropPlacements only, no `ScatterRegion` (nothing is scattered indoors) — describing an L-shaped room: a 6m×4m main room plus a 2m×2m open alcove in one corner, with 12 wall segments, 7 floor tiles, and hand-placed furniture. `cottage_interior.tscn` reuses the `ZoneBuilder` pattern from `cottage_garden.tscn` but replaces the sun/sky lighting rig with a new enclosed-space rig: dim ambient `WorldEnvironment`, a warm `OmniLight3D` at the hearth, and a cooler `OmniLight3D` at a deliberate gap left in one wall (the "window"). A gdUnit budget test mirrors `test_zone_budget.gd`. No scene-transition/door logic, no gameplay systems (pantry, Leaven, tea-mending) — pure environment art, matching how `cottage_garden` shipped.

**Tech Stack:** Godot 4.7 / GDScript, gdUnit4 (GDScript tests), Python 3 + pytest (`tools/assetgen`), existing `PaletteApply` toon-material system, existing `Zone`/`ZoneBuilder` tooling.

**Spec:** `docs/superpowers/specs/2026-08-11-cottage-interior-design.md`

---

## Chunk 1: New interior props (`tools/assetgen/props.py`)

Each task follows the same red/green pattern as Tasks 8-10 of
`docs/superpowers/plans/2026-08-10-zone-tooling-environment-placeholders.md`:
add the prop name to `PROPS` (and `HERO_PROPS` where noted) pointing at a
not-yet-defined function, confirm the existing parametrized test suite in
`tests/python/test_assetgen.py` fails with `KeyError: unknown prop: <name>`,
then implement.

Reminder: `tools/assetgen/build.py` already loops over `sorted(props.PROPS)`
to build every prop's GLB — no changes to `build.py` are needed for any task
in this chunk.

### Task 1: `build_interior_wall`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Write the failing test**

Add `"interior_wall"` to the closed-volume parametrize list (a single
`add_box` call is always a closed solid, same reasoning as `crate`/`planter`).
Most tasks in this chunk append exactly one new name to this list as they
land their prop — the exception is Task 7 (`rug`), a single open quad with
no well-defined enclosed volume, which is deliberately **not** added to this
list (the same way `grass_tuft`/`flower` are excluded already). The list is
never left referencing a not-yet-implemented name, so the full suite stays
green after every task's commit, matching the 2026-08-10 plan's incremental
precedent:

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall"],
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: FAIL — `KeyError: unknown prop: interior_wall`.

- [ ] **Step 3: Write minimal implementation**

```python
def build_interior_wall(_seed: int = 0) -> MeshBuilder:
    """One 2m interior wall segment: plastered panel with a wood baseboard."""
    builder = MeshBuilder()
    add_box(builder, (0, 1.2, 0), (2.0, 2.4, 0.15), "cream", 1, top=("cream", 2))
    add_box(builder, (0, 0.08, 0), (2.0, 0.16, 0.17), "wood", 1)
    return builder
```

Add `"interior_wall": build_interior_wall,` to `PROPS` (keep the dict sorted
alphabetically, matching the existing style).

- [ ] **Step 4: Run test to verify it passes** (for this prop's `KeyError`
only — the parametrize list still has other unimplemented names until later
tasks land)

Run: `python3 -m pytest tests/python/test_assetgen.py -k interior_wall -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add interior_wall placeholder prop"
```

### Task 2: `build_interior_floor`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Add `"interior_floor"` to the closed-volume parametrize
list and verify it fails first**

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor"],
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

Run: `python3 -m pytest tests/python/test_assetgen.py -k interior_floor -q`
Expected: FAIL — `KeyError: unknown prop: interior_floor`.

- [ ] **Step 2: Write minimal implementation**

```python
def build_interior_floor(_seed: int = 0) -> MeshBuilder:
    """2x2 m interior floor tile — wood plank boards."""
    builder = MeshBuilder()
    add_box(builder, (0, -0.05, 0), (2.0, 0.1, 2.0), "wood", 2, top=("wood", 3))
    return builder
```

Add `"interior_floor": build_interior_floor,` to `PROPS`.

- [ ] **Step 3: Run test to verify it passes**

Run: same command as Step 1.
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add interior_floor placeholder prop"
```

### Task 3: `build_hearth` (hero prop)

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Add `"hearth"` to the closed-volume parametrize list and
verify it fails first**

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor", "hearth"],
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

Run: `python3 -m pytest tests/python/test_assetgen.py -k hearth -q`
Expected: FAIL — `KeyError: unknown prop: hearth`.

- [ ] **Step 2: Write minimal implementation**

`add_box` is additive-only (there's no CSG subtraction in this pipeline),
so a literal carved-out "recess" isn't achievable — instead, like `jar`'s
label and `mug`'s handle, the firebox opening and ember glow are flat decal
quads placed just outside the base block's front face (`+Z` at `0.25`),
the same "surface decal" pattern `build_jar` already uses for its label:

```python
def build_hearth(_seed: int = 0) -> MeshBuilder:
    """Stone fireplace: base block with a dark firebox decal and an ember
    glow accent quad (decals, not a carved recess — add_box can't
    subtract). A hero prop — the interior's lighting focal point."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.5, 0), (0.9, 1.0, 0.5), "stone", 1, top=("stone", 2))
    builder.add_face(
        [(-0.28, 0.08, 0.251), (0.28, 0.08, 0.251),
         (0.28, 0.55, 0.251), (-0.28, 0.55, 0.251)],
        "stone", 0,
    )
    builder.add_face(
        [(-0.18, 0.1, 0.252), (0.18, 0.1, 0.252),
         (0.18, 0.4, 0.252), (-0.18, 0.4, 0.252)],
        "honey", 3,
    )
    return builder
```

(Winding check: both quads use the same corner order — bottom-left,
bottom-right, top-right, top-left — as `build_jar`'s label quad and
`add_box`'s own `+Z` face, giving an outward `+Z` normal so they render
correctly under the toon shader's `cull_back` mode. `hearth` stays a valid
member of the closed-volume test above — its dominant, fully-closed base
box gives it clearly positive net signed volume even with these two small
decal quads layered on top, the same way `jar`'s closed lathe body stays
positive volume despite its own label decal.)

Add `"hearth": build_hearth,` to `PROPS` and `"hearth"` to `HERO_PROPS`.

- [ ] **Step 3: Run test to verify it passes**

Run: same command as Step 1.
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add hearth placeholder prop"
```

### Task 4: `build_table`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Add `"table"` to the closed-volume parametrize list and
verify it fails first**

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor", "hearth", "table"],
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

Run: `python3 -m pytest tests/python/test_assetgen.py -k "table and not turntable" -q`
Expected: FAIL — `KeyError: unknown prop: table`.

- [ ] **Step 2: Write minimal implementation**

```python
def build_table(_seed: int = 0) -> MeshBuilder:
    """Simple wood table: top plus four legs."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.72, 0), (1.1, 0.06, 0.7), "wood", 2, top=("wood", 3))
    for x in (-0.48, 0.48):
        for z in (-0.28, 0.28):
            add_box(builder, (x, 0.35, z), (0.08, 0.7, 0.08), "wood", 1)
    return builder
```

Add `"table": build_table,` to `PROPS`.

- [ ] **Step 3: Run test to verify it passes**

Run: same command as Step 1.
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add table placeholder prop"
```

### Task 5: `build_chair`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Add `"chair"` to the closed-volume parametrize list and
verify it fails first**

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor", "hearth", "table", "chair"],
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

Run: `python3 -m pytest tests/python/test_assetgen.py -k chair -q`
Expected: FAIL — `KeyError: unknown prop: chair`.

- [ ] **Step 2: Write minimal implementation**

```python
def build_chair(_seed: int = 0) -> MeshBuilder:
    """Simple wood chair: seat, backrest, four legs."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.45, 0), (0.42, 0.05, 0.42), "wood", 2)
    add_box(builder, (0, 0.75, -0.19), (0.42, 0.55, 0.05), "wood", 1)
    for x in (-0.17, 0.17):
        for z in (-0.17, 0.17):
            add_box(builder, (x, 0.22, z), (0.06, 0.44, 0.06), "wood", 1)
    return builder
```

Add `"chair": build_chair,` to `PROPS`.

- [ ] **Step 3: Run test to verify it passes**

Run: same command as Step 1.
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add chair placeholder prop"
```

### Task 6: `build_shelf`

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Add `"shelf"` to the closed-volume parametrize list and
verify it fails first**

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor", "hearth", "table", "chair",
              "shelf"],
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

Run: `python3 -m pytest tests/python/test_assetgen.py -k shelf -q`
Expected: FAIL — `KeyError: unknown prop: shelf`.

- [ ] **Step 2: Write minimal implementation**

```python
def build_shelf(_seed: int = 0) -> MeshBuilder:
    """Wall shelf: back panel plus two shelf boards, sized to host jar/mug
    props as set-dressing."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.9, -0.06), (1.0, 1.2, 0.03), "wood", 1)
    for y in (0.5, 1.3):
        add_box(builder, (0, y, 0.1), (1.0, 0.04, 0.26), "wood", 2, top=("wood", 3))
    return builder
```

Add `"shelf": build_shelf,` to `PROPS`.

- [ ] **Step 3: Run test to verify it passes**

Run: same command as Step 1.
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add shelf placeholder prop"
```

### Task 7: `build_rug`

**Files:**
- Modify: `tools/assetgen/props.py`

- [ ] **Step 1: Verify the prop doesn't exist yet**

`rug` isn't added to any existing parametrize list (see Step 2's rationale),
so `pytest -k rug` would collect zero tests rather than fail — verify
directly instead:

Run: `python3 -c "from tools.assetgen import props; props.build_prop('rug')"`
Expected: FAIL — traceback ending in `KeyError: 'unknown prop: rug'`.

- [ ] **Step 2: Write minimal implementation**

A single flat quad (like `flower`'s bloom or `jar`'s label) — deliberately
**not** added to the closed-volume parametrize list, the same
way `grass_tuft`/`flower` are excluded (an open single-sided quad has no
well-defined positive enclosed volume). The rug lies flat on the floor and
must be visible from above, so it needs an upward (`+Y`) normal: point
order goes back-left → front-left → front-right → back-right (matching
`add_box`'s own `+Y` top-face winding, `[c[4], c[7], c[6], c[5]]` in
`tools/assetgen/mesh.py`), **not** the naive back-left → back-right →
front-right → front-left order (which gives a downward `-Y` normal and
would render invisible under the toon shader's `cull_back` mode — the same
bug class that hit `flower`'s bloom quad earlier in this project):

```python
def build_rug(_seed: int = 0) -> MeshBuilder:
    """Flat woven rug — a single ground-hugging quad, facing up."""
    builder = MeshBuilder()
    builder.add_face(
        [(-0.9, 0.005, -0.6), (-0.9, 0.005, 0.6),
         (0.9, 0.005, 0.6), (0.9, 0.005, -0.6)],
        "rust", 2,
    )
    return builder
```

Add `"rug": build_rug,` to `PROPS`.

- [ ] **Step 3: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_assetgen.py -k rug -q`
Expected: PASS (now that `rug` is registered in `PROPS`, the dynamic
parametrizations over `sorted(props.PROPS)` — `test_prop_builds_within_budget`,
`test_prop_glb_is_deterministic` — pick it up automatically).

- [ ] **Step 4: Commit**

```bash
git add tools/assetgen/props.py
git commit -m "Add rug placeholder prop"
```

### Task 8: `build_bed` (hero prop)

**Files:**
- Modify: `tools/assetgen/props.py`
- Modify: `tests/python/test_assetgen.py`

- [ ] **Step 1: Add `"bed"` to the closed-volume parametrize list — this is
the final version of this list, every name in it now exists in `PROPS` by
the end of this task — and verify it fails first**

```python
@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor", "hearth", "table", "chair",
              "shelf", "bed"],
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"
```

Run: `python3 -m pytest tests/python/test_assetgen.py -k bed -q`
Expected: FAIL — `KeyError: unknown prop: bed`.

- [ ] **Step 2: Write minimal implementation**

```python
def build_bed(_seed: int = 0) -> MeshBuilder:
    """Bed frame, mattress, and pillow blockout. A hero prop — the alcove's
    focal furniture piece."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.25, 0), (1.0, 0.4, 1.9), "wood", 1)
    add_box(builder, (0, 0.9, -0.9), (1.0, 0.7, 0.1), "wood", 2)
    add_box(builder, (0, 0.5, 0.05), (0.94, 0.2, 1.7), "cream", 2, top=("cream", 3))
    add_box(builder, (0, 0.66, -0.65), (0.7, 0.14, 0.32), "cream", 3)
    return builder
```

Add `"bed": build_bed,` to `PROPS` and `"bed"` to `HERO_PROPS`.

- [ ] **Step 3: Run test to verify it passes**

Run: same command as Step 1.
Expected: PASS.

- [ ] **Step 4: Run the full parametrized suite to confirm every name added
across Tasks 1-8 is now covered**

Run: `python3 -m pytest tests/python/test_assetgen.py -q`
Expected: PASS (all parametrized cases, including
`test_closed_props_have_positive_volume` for the 7 new closed-volume props
— every new prop except `rug`, which stays excluded per Task 7 —
`test_prop_builds_within_budget`, `test_prop_glb_is_deterministic`).

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/props.py tests/python/test_assetgen.py
git commit -m "Add bed placeholder prop"
```

### Task 9: Build the assets and confirm the manifest

**Files:** none (verification only, no code changes)

- [ ] **Step 1: Run the asset build**

Run: `python3 -m tools.assetgen.build`
Expected: output lines for all 8 new `.glb` files (`interior_wall.glb`,
`interior_floor.glb`, `hearth.glb`, `table.glb`, `chair.glb`, `shelf.glb`,
`rug.glb`, `bed.glb`) alongside the existing props, ending in `asset build OK`.

- [ ] **Step 2: Confirm `assets/generated/` stays gitignored**

Run: `git status --short`
Expected: no untracked/modified entries under `assets/generated/` (already
gitignored per the zone-tooling plan's Task 11 precedent). Nothing to
commit for this task.

- [ ] **Step 3: Run the full Python suite as a final chunk sanity check**

Run: `python3 -m pytest tests/python -q`
Expected: 2 known pre-existing, unrelated `test_build_character.py`
(Blender) failures as baseline — every other test, including all new prop
tests from Tasks 1-8, passes. No new failures beyond that baseline count.

---

## Chunk 2: `cottage_interior` zone assembly

### Task 10: `cottage_interior.tres` — author the Zone data

**Files:**
- Create: `src/world/cottage_interior/cottage_interior.tres`

This is hand-authored `.tres` text, the same way `cottage_garden.tres` was
authored in the prior plan. Unlike `cottage_garden.tres`, **no
`ScatterRegion` is needed** — every interior prop is hand-placed, so this
step has no risky "extract a Mesh sub-resource from a GLB" concern and can
be written directly as text, no editor session required.

Layout (world space, matching the design spec's "6m×4m main room + 2m×2m
open alcove" — an L-shaped room with 12 wall segments, 7 floor tiles, and
furniture):

- Main room footprint: X from -3 to 3, Z from -2 to 2 (6m × 4m).
- Alcove footprint: X from 1 to 3, Z from 2 to 4 (2m × 2m), open to the main
  room (no wall along the shared edge X 1..3, Z=2).
- Wall segments (`interior_wall`, each 2m long, placed at its center point;
  `rotation_degrees.y = 90` runs the segment along Z instead of X, same
  convention as `cottage_wall` in `cottage_garden.tres`):
  - South wall (Z=-2, full width): x = -2, 0, 2
  - West wall (X=-3, main room height): z = -1, 1
  - North wall, main-room portion only (Z=2, stops at the alcove opening):
    x = -2, 0
  - East wall, continuous across main room + alcove (X=3): z = -1, 1, 3
  - Alcove north wall (Z=4): x = 2
  - Alcove west wall (X=1, alcove height only — this is the alcove's own
    outer wall, not a partition from the main room): z = 3
  - **Deliberate window gap:** the east wall's `z = 1` segment is *omitted*
    on purpose — this is the "window" opening the design spec calls for, lit
    by the `WindowLight` added in Task 11. No window-frame prop exists in
    this pass; the gap itself is the placeholder. (This does mean that one
    square meter of the east wall is fully open — acceptable for this
    standalone, non-connected placeholder scene.)
- Floor tiles (`interior_floor`, each 2m×2m, placed at its center): main room
  needs 6 tiles (x, z) = (-2,-1), (0,-1), (2,-1), (-2,1), (0,1), (2,1); alcove
  needs 1 tile at (2, 3).
- Furniture:
  - `hearth` at (0, 0, -1.7), against the south wall.
  - `table` at (0, 0, 0.3), center of the main room.
  - `chair` at (0, 0, 1.0), facing the table.
  - `shelf` at (-2.85, 0, -1), `rotation_degrees.y = 90`, against the west
    wall.
  - `jar` at (-2.85, 1.3, -1.2) and `mug` at (-2.85, 1.3, -0.8), dressing the
    shelf's top board (reusing the existing `jar`/`mug` props, per the
    spec).
  - `rug` at (0, 0, 0.3), under the table.
  - `bed` at (2, 0, 3), in the alcove.

- [ ] **Step 1: Write the file**

```
[gd_resource type="Resource" script_class="Zone" load_steps=27 format=3]

[ext_resource type="Script" path="res://src/world/zone.gd" id="1_zone"]
[ext_resource type="Script" path="res://src/world/prop_placement.gd" id="2_placement"]
[ext_resource type="PackedScene" path="res://assets/generated/interior_wall.glb" id="3_wall"]
[ext_resource type="PackedScene" path="res://assets/generated/interior_floor.glb" id="4_floor"]
[ext_resource type="PackedScene" path="res://assets/generated/hearth.glb" id="5_hearth"]
[ext_resource type="PackedScene" path="res://assets/generated/table.glb" id="6_table"]
[ext_resource type="PackedScene" path="res://assets/generated/chair.glb" id="7_chair"]
[ext_resource type="PackedScene" path="res://assets/generated/shelf.glb" id="8_shelf"]
[ext_resource type="PackedScene" path="res://assets/generated/jar.glb" id="9_jar"]
[ext_resource type="PackedScene" path="res://assets/generated/mug.glb" id="10_mug"]
[ext_resource type="PackedScene" path="res://assets/generated/rug.glb" id="11_rug"]
[ext_resource type="PackedScene" path="res://assets/generated/bed.glb" id="12_bed"]

[sub_resource type="Resource" id="Wall_s1"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(-2, 0, -2)

[sub_resource type="Resource" id="Wall_s2"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(0, 0, -2)

[sub_resource type="Resource" id="Wall_s3"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(2, 0, -2)

[sub_resource type="Resource" id="Wall_w1"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(-3, 0, -1)
rotation_degrees = Vector3(0, 90, 0)

[sub_resource type="Resource" id="Wall_w2"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(-3, 0, 1)
rotation_degrees = Vector3(0, 90, 0)

[sub_resource type="Resource" id="Wall_n1"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(-2, 0, 2)

[sub_resource type="Resource" id="Wall_n2"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(0, 0, 2)

[sub_resource type="Resource" id="Wall_e1"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(3, 0, -1)
rotation_degrees = Vector3(0, 90, 0)

[sub_resource type="Resource" id="Wall_e3"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(3, 0, 3)
rotation_degrees = Vector3(0, 90, 0)

[sub_resource type="Resource" id="Wall_alcove_n"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(2, 0, 4)

[sub_resource type="Resource" id="Wall_alcove_w"]
script = ExtResource("2_placement")
scene = ExtResource("3_wall")
position = Vector3(1, 0, 3)
rotation_degrees = Vector3(0, 90, 0)

[sub_resource type="Resource" id="Floor_1"]
script = ExtResource("2_placement")
scene = ExtResource("4_floor")
position = Vector3(-2, 0, -1)

[sub_resource type="Resource" id="Floor_2"]
script = ExtResource("2_placement")
scene = ExtResource("4_floor")
position = Vector3(0, 0, -1)

[sub_resource type="Resource" id="Floor_3"]
script = ExtResource("2_placement")
scene = ExtResource("4_floor")
position = Vector3(2, 0, -1)

[sub_resource type="Resource" id="Floor_4"]
script = ExtResource("2_placement")
scene = ExtResource("4_floor")
position = Vector3(-2, 0, 1)

[sub_resource type="Resource" id="Floor_5"]
script = ExtResource("2_placement")
scene = ExtResource("4_floor")
position = Vector3(0, 0, 1)

[sub_resource type="Resource" id="Floor_6"]
script = ExtResource("2_placement")
scene = ExtResource("4_floor")
position = Vector3(2, 0, 1)

[sub_resource type="Resource" id="Floor_alcove"]
script = ExtResource("2_placement")
scene = ExtResource("4_floor")
position = Vector3(2, 0, 3)

[sub_resource type="Resource" id="Placement_hearth"]
script = ExtResource("2_placement")
scene = ExtResource("5_hearth")
position = Vector3(0, 0, -1.7)

[sub_resource type="Resource" id="Placement_table"]
script = ExtResource("2_placement")
scene = ExtResource("6_table")
position = Vector3(0, 0, 0.3)

[sub_resource type="Resource" id="Placement_chair"]
script = ExtResource("2_placement")
scene = ExtResource("7_chair")
position = Vector3(0, 0, 1.0)

[sub_resource type="Resource" id="Placement_shelf"]
script = ExtResource("2_placement")
scene = ExtResource("8_shelf")
position = Vector3(-2.85, 0, -1)
rotation_degrees = Vector3(0, 90, 0)

[sub_resource type="Resource" id="Placement_jar"]
script = ExtResource("2_placement")
scene = ExtResource("9_jar")
position = Vector3(-2.85, 1.3, -1.2)

[sub_resource type="Resource" id="Placement_mug"]
script = ExtResource("2_placement")
scene = ExtResource("10_mug")
position = Vector3(-2.85, 1.3, -0.8)

[sub_resource type="Resource" id="Placement_rug"]
script = ExtResource("2_placement")
scene = ExtResource("11_rug")
position = Vector3(0, 0, 0.3)

[sub_resource type="Resource" id="Placement_bed"]
script = ExtResource("2_placement")
scene = ExtResource("12_bed")
position = Vector3(2, 0, 3)

[resource]
script = ExtResource("1_zone")
ground_size = Vector2(8, 8)
placements = Array[ExtResource("2_placement")]([SubResource("Wall_s1"), SubResource("Wall_s2"), SubResource("Wall_s3"), SubResource("Wall_w1"), SubResource("Wall_w2"), SubResource("Wall_n1"), SubResource("Wall_n2"), SubResource("Wall_e1"), SubResource("Wall_e3"), SubResource("Wall_alcove_n"), SubResource("Wall_alcove_w"), SubResource("Floor_1"), SubResource("Floor_2"), SubResource("Floor_3"), SubResource("Floor_4"), SubResource("Floor_5"), SubResource("Floor_6"), SubResource("Floor_alcove"), SubResource("Placement_hearth"), SubResource("Placement_table"), SubResource("Placement_chair"), SubResource("Placement_shelf"), SubResource("Placement_jar"), SubResource("Placement_mug"), SubResource("Placement_rug"), SubResource("Placement_bed")])
scatter_regions = Array[ExtResource("2_placement")]([])
```

> Note: `scatter_regions`'s typed-array `ExtResource` in the empty-array
> literal should reference `ScatterRegion`'s script, not `PropPlacement`'s —
> check `cottage_garden.tres`'s exact empty-array syntax for
> `scatter_regions` (it needs its own `[ext_resource type="Script"
> path="res://src/world/scatter_region.gd" ...]` entry even though no
> `ScatterRegion` sub-resources are created, purely so the typed empty array
> literal is well-formed). Add that `ext_resource` line and reference it in
> the empty array instead of `2_placement` in the final line.

- [ ] **Step 2: Sanity-check the resource loads**

The real verification is Task 11's smoke test (which loads this resource as
part of loading the scene) — don't write a one-off throwaway script for this.

- [ ] **Step 3: Commit**

```bash
git add src/world/cottage_interior/cottage_interior.tres
git commit -m "Author cottage_interior Zone data"
```

### Task 11: `cottage_interior.tscn` — assemble the scene

**Files:**
- Create: `src/world/cottage_interior/cottage_interior.gd`
- Create: `src/world/cottage_interior/cottage_interior.tscn`
- Create: `tests/unit/test_cottage_interior.gd`

Reference: `src/world/cottage_garden/cottage_garden.tscn` and
`cottage_garden.gd` for the `ZoneBuilder` wiring pattern this reuses (but
**not** for lighting — see below, this scene needs a new enclosed-space
rig, not glade's sun/sky rig).

- [ ] **Step 1: Write the failing test**

```gdscript
extends GdUnitTestSuite
## Cottage interior smoke: the zone assembles with a player and at least
## one discrete prop from the ZoneBuilder (no scatter regions indoors).

const COTTAGE_INTERIOR_SCENE := "res://src/world/cottage_interior/cottage_interior.tscn"


func test_cottage_interior_assembles_with_player_and_props() -> void:
	var runner := scene_runner(COTTAGE_INTERIOR_SCENE)
	await runner.simulate_frames(10)
	var interior := runner.scene()

	assert_object(interior.get_node_or_null("Player")).is_not_null()

	var builder := interior.get_node("%ZoneBuilder") as ZoneBuilder
	assert_object(builder).is_not_null()

	var prop_count := 0
	for child in builder.get_children():
		if child is Node3D:
			prop_count += 1
	assert_int(prop_count).override_failure_message(
		"expected all 26 PropPlacements from cottage_interior.tres to be instanced under %ZoneBuilder"
	).is_equal(26)

	assert_object(interior.get_node_or_null("HearthLight")).is_not_null()
	assert_object(interior.get_node_or_null("WindowLight")).is_not_null()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_cottage_interior.gd --ignoreHeadlessMode`
Expected: FAIL — scene doesn't exist yet.

- [ ] **Step 3: Write the script**

`src/world/cottage_interior/cottage_interior.gd`:

```gdscript
extends Node3D
## The cottage interior — Phase 4's hearth-lit interior zone (T4.3).
## Standalone scene: no scene-transition wiring to cottage_garden yet.

func _ready() -> void:
	_stage()


func _stage() -> void:
	var hearth_light := get_node_or_null("HearthLight") as OmniLight3D
	if hearth_light != null:
		hearth_light.light_color = Color(1.0, 0.55, 0.22)
		hearth_light.light_energy = 2.5
		hearth_light.omni_range = 4.5
	var window_light := get_node_or_null("WindowLight") as OmniLight3D
	if window_light != null:
		window_light.light_color = Color(0.72, 0.84, 1.0)
		window_light.light_energy = 0.6
		window_light.omni_range = 3.5
```

- [ ] **Step 4: Write the scene**

`src/world/cottage_interior/cottage_interior.tscn` — start from a blank
`Node3D` root (not a copy of `glade.tscn`/`cottage_garden.tscn`, since the
environment/lighting differs entirely) and add:

- Root `Node3D` named `CottageInterior`, script `cottage_interior.gd`.
- `WorldEnvironment` with a new `Environment` sub-resource: no sky —
  `background_mode = 1` (Color), `background_color` a very dark
  near-black/blue (e.g. `Color(0.03, 0.03, 0.05, 1)`), `ambient_light_source
  = 2` (Color), `ambient_light_color = Color(0.35, 0.32, 0.4, 1)`,
  `ambient_light_energy = 0.25`, `fog_enabled = false`, `tonemap_mode = 3`
  (match the existing tonemap convention from `glade.tscn`/`cottage_garden.tscn`).
- `HearthLight` (`OmniLight3D`) at `Transform3D` position `(0, 1.3, -1.7)` —
  matching the hearth's `PropPlacement` position, raised to light-source
  height.
- `WindowLight` (`OmniLight3D`) at `Transform3D` position `(3, 1.5, 1)` —
  matching the deliberate wall gap from Task 10.
- `GroundCollider` (`StaticBody3D` + `CollisionShape3D`/`BoxShape3D`),
  sized to cover the full L-shape's bounding box: `size = Vector3(6.2, 0.4,
  6.2)`, `transform` positioned so it's centered under the combined
  footprint (e.g. origin `(0, -0.2, 1)`, matching how `cottage_garden.tscn`'s
  `GroundCollider` sits just under the floor). Note in a scene comment (or
  here in the plan, no code change needed) that this is a simple bounding
  box, not an exact L-shape collider — a deliberate placeholder
  simplification, same spirit as the exterior zones' simple ground
  colliders.
- `ZoneBuilder` (`Node3D`, unique-named `%ZoneBuilder`), script
  `res://src/world/zone_builder.gd`, `zone` set to
  `res://src/world/cottage_interior/cottage_interior.tres`.
- `Player` (instance of `res://src/player/player.tscn`), positioned inside
  the main room, e.g. `(0, 0.2, 1.8)`, facing the hearth/table.

- [ ] **Step 5: Run test to verify it passes**

Run: same command as Step 2.
Expected: PASS.

- [ ] **Step 6: Manually verify in Godot** (use the Godot MCP tools)

Run the scene and confirm no errors in the debug output; confirm the walls,
floor tiles, hearth, table, chair, shelf (with jar/mug on top), rug, and bed
are all visible and dressed with the palette material; confirm the room
reads as warm/hearth-lit rather than flat-lit, and that the window gap in
the east wall is visible with the cooler `WindowLight` glow coming through
it.

- [ ] **Step 7: Commit**

```bash
git add src/world/cottage_interior/cottage_interior.gd src/world/cottage_interior/cottage_interior.tscn tests/unit/test_cottage_interior.gd
git commit -m "Assemble cottage_interior zone via ZoneBuilder"
```

(Remember to check `git status` after Godot has touched these files for any
`.uid` sidecar files it generated, and add them in a follow-up commit if
so — this has happened for every new `.tscn`/`.gd` pair in this project so
far.)

### Task 12: Zone budget test

**Files:**
- Create: `tests/unit/test_interior_budget.gd`

- [ ] **Step 1: Write the test**

```gdscript
extends GdUnitTestSuite
## Zone budget: cottage_interior must stay within the design bible's
## 150k tri / 120 draw call zone ceiling, same rule as test_zone_budget.gd
## applies to cottage_garden.

const COTTAGE_INTERIOR_SCENE := "res://src/world/cottage_interior/cottage_interior.tscn"
const MAX_TRIS := 150_000
const MAX_DRAW_CALLS := 120


func test_cottage_interior_within_zone_budget() -> void:
	var runner := scene_runner(COTTAGE_INTERIOR_SCENE)
	await runner.simulate_frames(3)
	var interior := runner.scene()

	var total_tris := 0
	var draw_calls := 0
	for found in interior.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := found as MeshInstance3D
		if mesh_instance.mesh != null:
			total_tris += _mesh_tri_count(mesh_instance.mesh)
			draw_calls += 1

	assert_int(total_tris).override_failure_message(
		"cottage_interior over the 150k tri zone budget"
	).is_less_equal(MAX_TRIS)
	assert_int(draw_calls).override_failure_message(
		"cottage_interior over the 120 draw call zone budget"
	).is_less_equal(MAX_DRAW_CALLS)


func _mesh_tri_count(mesh: Mesh) -> int:
	var tris := 0
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
		tris += indices.size() / 3
	return tris
```

(No `MultiMeshInstance3D` loop — this scene has no `ScatterRegion`s, unlike
`test_zone_budget.gd`'s `cottage_garden` case.)

- [ ] **Step 2: Run test to verify it passes**

Run: `.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit/test_interior_budget.gd --ignoreHeadlessMode`
Expected: PASS immediately — 26 small placeholder props are nowhere near
150k tris or 120 draw calls. If it unexpectedly fails, re-check Task 10's
placement count didn't balloon.

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_interior_budget.gd
git commit -m "Add cottage_interior zone budget test"
```

### Task 13: Full verification pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full Python suite**

Run: `python3 -m pytest tests/python -q`
Expected: 2 known pre-existing, unrelated Blender failures as baseline; no
new failures.

- [ ] **Step 2: Run the full gdUnit suite**

Run (after a fresh `--headless --path . --import` if this is a new shell):
`.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit --ignoreHeadlessMode`
Expected: 3 known pre-existing failures as baseline
(`test_interact.gd::test_hysteresis_keeps_focus_against_marginal_rival`, 2 in
`test_avatar.gd`); no new failures. Clean up: `rm -rf reports`.

- [ ] **Step 3: Live Godot boot check**

Use the Godot MCP `godot-run_project` tool (or equivalent) to run
`cottage_interior.tscn` directly and confirm clean boot with no new errors
(pre-existing shadowing warnings are expected baseline noise, same as every
prior zone).

---

## Chunk 3: Documentation

### Task 14: Update `ROADMAP.md` and `docs/asset-inventory.md`

**Files:**
- Modify: `ROADMAP.md`
- Modify: `docs/asset-inventory.md`

- [ ] **Step 1: Update `ROADMAP.md`**

In the Phase 4 section, mark T4.3 done, following the exact style of the
T4.1/T4.2 entries above it:

```
- T4.3 Cottage interior + garden assembled ✅ done — `cottage_interior`
  zone (`src/world/cottage_interior/`): hearth-lit main room + open bed
  alcove, 8 new placeholder props (interior wall/floor kit, hearth, table,
  chair, shelf, rug, bed), budget-tested against the same 150k tri / 120
  draw call ceiling as `cottage_garden`
  (see `docs/superpowers/plans/2026-08-11-cottage-interior.md`)
```

Update the Status table's Phase 4 row/notes if it currently lists T4.3 as
outstanding, consistent with how the T4.1/T4.2 completion was reflected
there in the prior plan's Task 15.

- [ ] **Step 2: Update `docs/asset-inventory.md`**

Add 8 new rows (one per new prop), following the existing table's exact
column format (`Asset ID | Category | Subtype | Procedural/Handcrafted |
Rig/Anim | Dependencies | Priority | Gameplay dependency | Status`), e.g.:

```
| interior-wall | nature | building kit (interior) | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
| interior-floor | nature | building kit (interior) | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
| hearth | nature | furniture (hero) | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
| table | nature | furniture | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
| chair | nature | furniture | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
| shelf | nature | furniture | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
| rug | nature | furniture | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
| bed | nature | furniture (hero) | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior | done |
```

(Match the exact category/style conventions already used for the
`cottage-kit`/`well`/`grass-tuft` rows added in the prior plan's Task 15 —
check that section of the table directly before writing these, and adjust
category/subtype wording to match established precedent rather than
inventing new ones.)

- [ ] **Step 3: Commit**

```bash
git add ROADMAP.md docs/asset-inventory.md
git commit -m "Update ROADMAP and asset inventory for cottage interior (T4.3)"
```
