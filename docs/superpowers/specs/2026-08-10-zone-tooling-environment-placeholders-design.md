# Zone Tooling + Environment Placeholders — Design Spec

Status: approved, not yet implemented.

Scope: Phase 4, sub-tasks **T4.1 (environment placeholders)** and **T4.2 (zone
tooling)** from `ROADMAP.md`, combined into one sub-project because scattered
props and hand-placed props both need the same placement pipeline to be
useful, and neither is worth building in isolation.

## Why

Phase 4 (World & Time) has five sub-tasks (environment placeholders, zone
tooling, cottage interior + garden, village + Hedgerow Lanes dressing,
time-of-day/weather/clock). The last three all depend on being able to author
a "zone" — a dressed, walkable exterior or interior space — without hand
wiring every prop into a scene file by node path, the way `src/sandbox/glade.gd`
currently does. This sub-project delivers that authoring layer plus enough new
placeholder props to prove it on one real zone: Great-Aunt Maren Hollowmere's
cottage garden.

This follows directly from the external-asset-sourcing pivot
(`2026-08-09-external-asset-pivot-design.md`): environment placeholders
continue to be generated procedurally in Python (`tools/assetgen/props.py`),
the same way `pine`, `fence`, `crate`, `mug`, and `jar` already are. Nothing
about this design revisits that decision.

## Decision

Build zone content as **data** (a `Zone` `Resource`) consumed by a small
**GDScript `@tool` builder** that instances props and populates scatter
meshes at edit-time and at runtime — not as Python-generated `.tscn` files,
and not as fully hand-authored scenes. This keeps zone composition native to
the Godot editor (live preview, Inspector-editable) while still being
data-driven, deterministic, and testable.

## Architecture

### `Zone` resource

`res://src/world/zone_resource.gd`, a `Resource` subclass, data only:

- `ground_size: Vector2` — footprint, used by budget checks and the ground
  collider.
- `placements: Array[PropPlacement]` — each a small typed inner `Resource`
  with `scene: PackedScene`, `position: Vector3`, `rotation_degrees: Vector3`,
  `scale: float`.
- `scatter_regions: Array[ScatterRegion]` — each a typed inner `Resource`
  with `variants: Array[Mesh]` (one or more scatter mesh variants — plain
  `Mesh` resources, not `PackedScene`s; see below for why), `shape: {CIRCLE,
  RECT}`, `center: Vector3`, `size: Vector2` (radius or width/depth
  depending on shape), `density: float` (instances per m²),
  `scale_min/scale_max: float`, `seed: int`.

No behavior lives on `Zone` itself — it's serializable, diffable `.tres`
data, matching how `PropPlacement`/`ScatterRegion` should look in git diffs
when a zone is tweaked.

**Why `variants` are `Mesh`, not `PackedScene`:** a single `MultiMesh`
renders exactly one mesh with one material — it can't mix arbitrary scene
variants the way a `PropPlacement` can. `ZoneBuilder` builds **one
`MultiMeshInstance3D` per variant mesh** in a region (not one per region),
splitting the region's instance count evenly across variants (round-robin
by variant index — no per-variant weight field is needed for this slice;
all variants in a region are equally likely, and any remainder from
uneven division goes to the lowest-index variants first, deterministically).
A "grass tuft" scatter region with 2 variants therefore produces 2
`MultiMeshInstance3D` nodes, each seeded from the region seed combined with
its own variant index so the combined result is still fully deterministic.
Each generated prop used for
scatter (e.g. `grass_tuft.glb`) is a single-mesh `PackedScene`; `Zone`
authoring extracts the `Mesh` from it directly (`(load(path) as
PackedScene).instantiate().get_child(0).mesh` at authoring time, or simply
reference the `.mesh` sub-resource of the generated GLB), so `Zone` `.tres`
files store `Mesh` references, not scene instances.

### `ZoneBuilder`

`res://src/world/zone_builder.gd`, `@tool`, attached to a `Node3D` in a zone
scene, with an exported `zone: Zone` field.

- A `rebuild()` method does the actual work: clears any previously built
  children under itself, then:
  - Instances each `PropPlacement.scene`, applies its transform, adds as a
    child, and calls `PaletteApply.apply()` on it (matching how every other
    generated prop gets dressed today).
  - For each `ScatterRegion`, computes `total := roundi(density *
    region_area)`, splits that count evenly (round-robin) across
    `region.variants`, and for each variant creates one `MultiMeshInstance3D`
    with a `MultiMesh` (`transform_format = TRANSFORM_3D`, `mesh =
    variant`), filling instance transforms using a seeded
    `RandomNumberGenerator` (`rng.seed = region.seed`, combined with the
    variant's index so each variant's sub-draw is independent but still
    reproducible) — this determinism is what makes the builder testable.
    Each `MultiMeshInstance3D`'s single `material_override` is set to the
    shared palette material (`PaletteApply.PALETTE_MATERIAL_PATH`) directly,
    since a `MultiMesh` can only carry one material — this matches the
    design-bible's "MultiMesh for scatter, one material" budget note.
- `rebuild()` runs from `_ready()` (both in-editor, when
  `Engine.is_editor_hint()`, and at runtime). Live re-preview while editing
  an open zone is a known limitation for this slice: `Resource.changed`
  does not reliably bubble up from nested `PropPlacement`/`ScatterRegion`
  subresources to the parent `Zone`, so editing a placement's transform in
  the Inspector won't auto-rebuild the scene. The practical workflow is to
  save the `Zone` `.tres` and reload the scene (or use the editor's "Reload
  Current Scene"), which re-runs `rebuild()` via `_ready()`. A dedicated
  "Rebuild Now" button (`@tool` exported `bool` toggled in the Inspector, or
  a small editor plugin) is a possible future nicety, not required now.

### First real zone: cottage garden

`res://src/world/cottage_garden/cottage_garden.tscn`:

- Reuses the `WorldEnvironment`/sun/fill-light/ground-collider setup already
  proven in `glade.tscn` (same sky material style, same lighting rig), so
  this isn't reinvented.
- A `Node3D` with `ZoneBuilder` attached and `zone` pointing at
  `cottage_garden.tres`, replacing the hand-listed `_stage()`-style prop
  wiring `glade.gd` uses today.
- Player (`player.tscn`) placed as in `glade.tscn`.

`glade.tscn` itself is untouched — it remains the Phase 1 proof-of-concept
and is not migrated to `ZoneBuilder` as part of this work (no value in
touching a scene that already passes its tests and isn't blocking anything).

## Scatter & budget mechanics

- One `MultiMeshInstance3D` per scatter variant per region (see above) —
  keeps draw calls bounded, per the design bible's zone budget
  (`docs/design-bible.md`: "Zones: ≤ 150k tris in view, ≤ 120 draw calls
  (MultiMesh for scatter, one material...)").
- Scattered instances share one `material_override` per `MultiMeshInstance3D`
  (the palette material), set directly by `ZoneBuilder` — a `MultiMesh`
  can't support per-instance material overrides, so this is the only place
  palette-dressing happens outside `PaletteApply.apply()`'s normal
  `MeshInstance3D` walk. Discrete `PropPlacement` instances continue to get
  dressed by `PaletteApply.apply()` exactly as today, since generated GLBs
  still ship with no baked materials by design (per `palette_apply.gd`'s own
  doc comment and the design bible's asset pipeline record — this spec does
  not change that).
- Per the design bible's existing split — "asserted per asset in
  `tests/python`, per zone in gdUnit scene tests" — budget checks stay in
  their existing homes rather than inventing a new Python `.tres`-parsing
  path:
  - **Per-prop** tri budgets continue to be asserted in `tests/python` for
    every `build_*` function in `props.py`, exactly as today.
  - **Per-zone** budget (total tris and draw-call count for the static
    scene, as an upper-bound approximation — this slice does not account
    for camera-frustum culling, so the check is against total authored
    tris/draw calls, a conservative stand-in for "tris in view") is
    asserted in a gdUnit test that instantiates the real zone scene, sums
    `MeshInstance3D` tri counts plus each `MultiMeshInstance3D`'s
    `mesh.get_faces().size() / 3 * multimesh.instance_count` (scatter mesh
    variants are required to be single-surface for this to be a simple
    sum — a constraint the new scatter placeholder props already satisfy),
    and counts `MeshInstance3D` + `MultiMeshInstance3D` nodes as draw calls,
    asserting against the 150k tri / 120 draw call ceiling.

### New placeholder props (extend `tools/assetgen/props.py`)

Needed to dress the cottage garden as a real zone. Per the Phase 3 pivot
note (`ROADMAP.md` T4.1), each new asset is a **per-asset choice** between
extending the existing deterministic `MeshBuilder` pipeline (seeded,
budget-asserted) or dropping in a free/CC0 low-poly pack asset that fits the
existing look — this spec doesn't mandate procedural-only. For this slice,
this list assumes the procedural route (since it's the smaller lift for
simple geometric props and keeps determinism/testing consistent), but any
entry can be swapped for a CC0 pack asset later without changing the `Zone`
schema (a `PropPlacement.scene` is just a `PackedScene` reference either
way):

- **Cottage wall/roof kit** — a small set of modular box pieces (wall
  segment, corner, roof panel) sized to combine into one small cottage
  exterior silhouette. This is a **hero prop** per the design bible's
  "hero props ≤ 1,500 tris" allowance, which is currently unimplemented in
  `props.py` (today's `TRI_BUDGET = 600` constant applies to every prop
  uniformly). This slice adds a second `HERO_TRI_BUDGET = 1500` constant to
  `props.py` plus an explicit `HERO_PROPS: set[str]` naming the hero-flagged
  `build_*` function names (initially just the cottage kit pieces), and
  extends the parametrized budget test (`test_prop_builds_within_budget`)
  to check any name in `HERO_PROPS` against `HERO_TRI_BUDGET` and everything
  else against `TRI_BUDGET`, rather than silently exceeding the existing
  single-budget test.
- **Garden planter/bed** — a simple raised box with soil-colored top face.
  Regular budget (≤ 600 tris).
- **Well or water trough** — a lathe-based cylindrical prop, reusing the
  `add_lathe` pattern already used for `mug`. Regular budget.
- **Grass tuft** and **small flower** — two low-tri variants for scatter
  (a handful of quads/cones, well under budget individually since many will
  be instanced via `MultiMesh`).
- **Rock/pebble** — simple faceted box or low-subdivision primitive, for
  scatter or occasional hero placement. Regular budget.

Each procedural entry gets its own `build_*` function in `props.py`,
following the existing pattern, with tri-budget tests alongside the
existing prop tests.

## Testing

- `tests/unit/test_zone_builder.gd` (gdUnit4): a synthetic `Zone` resource
  with 2 placements + 1 scatter region (2 variants), verifying: expected
  child count after `ZoneBuilder.rebuild()` runs; one `MultiMeshInstance3D`
  per variant with the expected combined instance count; rebuilding twice
  from the same seed produces identical transforms (determinism).
- `tests/unit/test_cottage_garden.gd` (gdUnit4): smoke test mirroring
  `test_glade.gd`'s structure — the zone assembles, the player node exists,
  and prop/scatter counts are non-zero. No interaction system is required for
  this slice (see Non-goals).
- `tests/unit/test_zone_budget.gd` (gdUnit4): instantiates
  `cottage_garden.tscn`, sums tri counts across all `MeshInstance3D`s plus
  each `MultiMeshInstance3D`'s per-instance tri count × instance count
  (single-surface scatter meshes only), and counts `MeshInstance3D` +
  `MultiMeshInstance3D` nodes as draw calls, asserting against the design
  bible's 150k tri / 120 draw call zone ceiling (a static upper-bound
  approximation, not accounting for frustum culling) — this is the "per
  zone" half of the design bible's existing "asserted per asset in
  `tests/python`, per zone in gdUnit scene tests" budget split.
- `tests/python`: new tri-budget tests for each new `build_*` function in
  `props.py` (regular props against `TRI_BUDGET`, the cottage kit against
  the new `HERO_TRI_BUDGET`).

## Non-goals (explicitly out of scope for this slice)

- Zone-to-zone transitions or streaming/loading between multiple zones.
- Time-of-day, weather, or the day/night clock (T4.5 — separate sub-project).
- Cottage **interior** (T4.3's other half — separate sub-project; this slice
  only covers the exterior garden).
- Village and Hedgerow Lanes dressing (T4.4 — separate sub-project, will
  reuse this same `Zone`/`ZoneBuilder` tooling once it exists).
- NPC placement/behavior.
- Saving/restoring player position between zones.
- A custom editor dock/plugin for authoring `Zone` resources — for this
  slice, `Zone` resources are edited via the standard Godot Inspector on a
  `.tres` file. A nicer authoring UI is a future nicety, not required now.

## Branching

Continue on the current session branch (`terrygoleman-bookish-giggle`)
rather than opening a new session/branch for Phase 4. The roadmap's
per-phase branch convention isn't a hard requirement, and Phase 2/3's pivot
work already lives on this branch.
