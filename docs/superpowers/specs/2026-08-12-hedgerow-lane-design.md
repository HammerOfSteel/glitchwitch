# Hedgerow Lane Design (T4.4)

## Context

Phase 4's roadmap item **T4.4 ("Village + Hedgerow Lanes first dressing
pass")** is next after T4.1–T4.3 delivered `cottage_garden` (exterior) and
`cottage_interior` (interior), both built on the `Zone`/`PropPlacement`/
`ScatterRegion`/`ZoneBuilder` tooling introduced in T4.2.

Per the story bible, Mosslane Hollow is "a hedge-country village... Stone
stiles, wet hedgerows, one shop, one bakery, one chapel-sized Signal House."
The T4.1/T4.2 spec explicitly deferred all of this as "a separate
sub-project, will reuse this same `Zone`/`ZoneBuilder` tooling once it
exists" — this spec is that sub-project's first slice.

This pass is scoped narrowly to the **hedgerow lane itself**: the
connective-tissue path with its hedges, a stone stile, and a signpost. The
village's three named buildings (shop, bakery, Signal House) are explicitly
out of scope here and become their own follow-up task. This mirrors how
`cottage_garden` and `cottage_interior` each shipped as focused, single-zone
environment-art passes before any gameplay or NPC systems were layered in.

No scene-transition/door system exists yet in the codebase (still deferred,
same as T4.3). `hedgerow_lane` ships as a standalone playable scene, just
like `cottage_garden.tscn` and `cottage_interior.tscn` — no wiring between
zones.

## Goals

- A new, straight hedgerow lane: a walkable stone/dirt path flanked by rows
  of hedges on both sides, with one stone stile roughly midway (a crossing
  point through one hedge line) and one signpost near an end.
- Four new placeholder props: `hedge`, `stone_stile`, `lane_path`,
  `signpost`.
- Reuse the existing `Zone`/`ZoneBuilder`/`PropPlacement` tooling for
  consistency with `cottage_garden` and `cottage_interior`. No
  `ScatterRegion` usage in this pass (no scatter dressing — kept for a later
  stretch task if wanted).
- Outdoor lighting/environment matching `cottage_garden`'s exterior setup
  (sky background, not the interior's dark/no-sky rig).
- Budget-tested, boot-verified, standalone scene — no gameplay logic, no
  scene-transition wiring.

## Non-goals

- No shop, bakery, or Signal House exteriors — a separate follow-up task.
- No scatter dressing (grass tufts/flowers along the verges) — a possible
  stretch task later, not this pass.
- No door/scene-transition system between `cottage_garden`/`cottage_interior`
  and `hedgerow_lane`.
- No gameplay systems: no NPCs, no favor-barter ledger, no noticeboard/radio
  content (that's Phase 8's "Village & Cast").
- No bend/fork/junction in the lane — a single straight corridor only.

## New props (`tools/assetgen/props.py`)

Following the established prop-building conventions (`MeshBuilder`
`add_box`/`add_face` helpers, toon palette-ramp shading, regular
`TRI_BUDGET = 600`; none of these are hero props):

- **`hedge`** — a chunky moss-green box, roughly 1.2m (long) × 0.9m (tall) ×
  0.5m (deep), reusing the `"moss"` palette cell already used by
  `build_ground_tile`'s top face. One segment per placement, laid end-to-end
  along the lane like `fence` segments.
- **`stone_stile`** — two low stone step blocks (one on each side of a hedge
  line) with a low horizontal crossbar between them, using the `"stone"`
  palette family already established by `build_well`. Represents a
  step-over crossing point through a hedge row.
- **`lane_path`** — a 2×2m ground tile, structurally like
  `build_ground_tile` (a shallow box with a flat top face) but with a
  dirt/stone top color instead of moss, so the lane path reads visually
  distinct from grass. Placed end-to-end like `ground_tile`/
  `interior_floor` to form the walkable lane surface.
- **`signpost`** — a single wood post with one or two small plank "arms"
  near the top, proportioned like `build_fence`'s posts (post ~0.1×0.9×0.1m)
  with the crossbars replaced by shorter angled arm-planks near the post
  top.

All four are closed volumes suitable for the existing
`test_closed_props_have_positive_volume` parametrize list (added to the
hardcoded name list, matching T4.3's incremental-TDD convention), except
none need special-casing beyond that — no new `HERO_PROPS` entries, no new
`TRI_BUDGET` tier.

## Zone layout (`src/world/hedgerow_lane/`)

Mirrors `cottage_interior`'s file structure:

- **`hedgerow_lane.tres`** — a straight lane along the Z axis, five
  `lane_path` tiles placed end-to-end (2m each, ~10m total length × 2m
  wide), flanked by rows of `hedge` segments along both long edges (roughly
  five segments per side, matching the lane's length). One `stone_stile`
  placed at the lane's midpoint on one hedge row (marking a crossing point).
  One `signpost` placed near one end of the lane, just off the path.
  `ground_size` sized to the lane's footprint (~10m × 2m plus hedge margins).
  No `scatter_regions` (empty typed array, same `.tres` syntax convention as
  `cottage_interior.tres` — `format=4`, no `load_steps`, real `ext_resource`
  backing any typed-empty-array script reference).
- **`hedgerow_lane.tscn`** — WorldEnvironment configured for outdoor use
  (sky background/ambient source, matching `cottage_garden.tscn`'s values —
  not the interior's dark/no-sky rig), a directional light (sun) if
  `cottage_garden` uses one, `ZoneBuilder`, `Player`, `GroundCollider` sized
  to the lane's footprint.
- **`hedgerow_lane.gd`** — no staging script planned; `cottage_garden` has
  none and this zone has no special lighting rig to stage (unlike the
  interior's hearth/window lights). Add one only if a concrete need emerges
  during implementation.

## Testing & docs

- Extend `tests/python/test_assetgen.py`'s hardcoded
  `test_closed_props_have_positive_volume` parametrize list with `hedge`,
  `stone_stile`, `lane_path`, `signpost` (all four are closed volumes).
- New `tests/unit/test_hedgerow_lane.gd` — smoke test asserting the exact
  total `PropPlacement` count under `%ZoneBuilder`, mirroring
  `test_cottage_interior.gd`.
- New `tests/unit/test_lane_budget.gd` — tri-count/draw-call budget test
  against the same 150k tri / 120 draw call ceiling, mirroring
  `test_zone_budget.gd`/`test_interior_budget.gd`.
- Update `ROADMAP.md`: mark T4.4 done with a short description, matching
  T4.3's done-line format.
- Update `docs/asset-inventory.md`: 4 new rows for `hedge` (category
  `nature`), `stone_stile` (category `building`), `lane_path` (category
  `building`), `signpost` (category `building`), all `procedural
  placeholder`, dependencies formatted as
  `tools/assetgen/props.py (\`build_x\`)`, matching the T4.3 rows exactly.

## Success criteria

- `python3 -m tools.assetgen.build` builds all 4 new `.glb` assets with no
  errors; full python test suite passes (aside from the 2 known
  pre-existing Blender `test_build_character.py` baseline failures).
- `hedgerow_lane.tscn` boots cleanly in Godot (verified via the MCP
  `godot-run_project` tool) with no new errors/warnings beyond known
  baseline shadowing warnings.
- Full gdUnit suite passes aside from the 3 known pre-existing baseline
  failures (`test_interact.gd` hysteresis + 2 in `test_avatar.gd`).
- `ROADMAP.md` and `docs/asset-inventory.md` updated to reflect the new
  zone and props.
