# Cottage Interior Design (T4.3)

## Context

Phase 4 of the roadmap ("Cottage & environment placeholders") already delivered
`cottage_garden` — a standalone, playable exterior Zone built on the
`Zone`/`ZoneBuilder` data-driven tooling introduced in
`docs/superpowers/plans/2026-08-10-zone-tooling-environment-placeholders.md`.
The roadmap's next item, **T4.3 ("Cottage interior + garden assembled")**,
covers the remaining half: a playable cottage interior scene.

Per the story bible, the cottage is Wren's home and "control room" — hearth,
tea-mending, jar-pantry, and (later) Leaven the sourdough companion all live
here. This pass is **environment art only**: no gameplay systems (pantry
logic, Leaven, interactables) are in scope. It mirrors how `cottage_garden`
shipped as pure environment art before any interactive systems were layered
in.

No scene-transition/door system exists yet in the codebase. This spec does
**not** build one — the interior ships as a standalone playable scene (like
`cottage_garden.tscn`), the same way the garden did. Connecting garden ↔
interior is deferred to a later, separate task.

## Goals

- A new, cozy, hearth-lit cottage interior: one main room plus an open bed
  alcove, dressed with new placeholder furniture props.
- Reuse the existing `Zone`/`ZoneBuilder`/`PropPlacement` tooling for
  consistency with `cottage_garden` and all future zones.
- A new dedicated interior wall/floor kit (not a reuse of the exterior
  `cottage_wall`/`cottage_corner` pieces, which are built for outward-facing
  exterior use).
- New warm, enclosed-space lighting rig — no sun/sky.
- Budget-tested, boot-verified, standalone scene — no gameplay logic, no
  scene-transition wiring.

## Non-goals

- No door/scene-transition system between garden and interior.
- No gameplay systems: no jar-pantry inventory logic, no Leaven, no
  interactable props, no tea-mending mechanic.
- No second fully separate room — the bed area is an open alcove off the main
  room, not a separated room behind a doorway.

## New props (`tools/assetgen/props.py`)

Following the established prop-building conventions (`MeshBuilder`
`add_box`/`add_lathe`/`add_cylinder`/`add_face` helpers, toon palette-ramp
shading, `TRI_BUDGET = 600` for standard props / `HERO_TRI_BUDGET = 1500` for
hero pieces):

| Prop | Budget class | Notes |
|---|---|---|
| `interior_wall` | standard | Flat interior wall kit piece, distinct from exterior `cottage_wall` |
| `interior_floor` | standard | Flat floor tile kit piece |
| `hearth` | hero | Stone fireplace block + dark firebox recess; may include a small emissive "ember glow" quad |
| `table` | standard | Simple wood table blockout |
| `chair` | standard | Simple wood chair blockout |
| `shelf` | standard | Wall shelf, sized to host existing `jar`/`mug` props as set-dressing |
| `rug` | standard | Flat decorative floor quad |
| `bed` | hero | Frame + mattress + pillow blockout |

Existing props reused as-is: `jar`, `mug` (as shelf/table dressing).

## Zone data & scene assembly

- **`src/world/cottage_interior/cottage_interior.tres`** — a `Zone` resource
  (same class used by `cottage_garden.tres`): a list of `PropPlacement`s only
  (no `ScatterRegion` — indoor dressing is hand-placed, not scattered).
  - Main room: `interior_floor`/`interior_wall` tiles forming a rectangular
    room footprint; `hearth` against one wall; `table` + `chair` near the
    room's center; `shelf` (dressed with a `jar`/`mug`) against a wall;
    `rug` in the middle of the floor.
  - Bed alcove: an open corner of the same room (no dividing wall/doorway) —
    floor/wall tiles extend into the corner, with `bed` placed there plus a
    small accent prop (e.g. a `jar` or extra `shelf`).
- **`src/world/cottage_interior/cottage_interior.tscn`** — reuses the
  `ZoneBuilder` pattern from `cottage_garden.tscn`: a `%ZoneBuilder` node
  referencing the `.tres` above, plus `Player` and a ground/floor collider.
  The lighting/environment rig differs from `cottage_garden`'s (see below)
  rather than being copied from it.
- **`cottage_interior.gd`** — root script mirrors `cottage_garden.gd`'s role:
  it stages the scene's own lights (the hearth glow / window fill described
  below) in `_ready()`. It does not spawn the zone itself — the
  `%ZoneBuilder` node rebuilds its `PropPlacement` children on its own
  `_ready()` — and does not need to call `PaletteApply.apply(self)`, since
  `ZoneBuilder` already applies the palette to each prop instance it builds.

## Lighting rig

- `WorldEnvironment` with low, cool-neutral ambient light — dim overall, no
  sun/sky (this is an enclosed interior space, unlike the outdoor zones).
- A warm `OmniLight3D` positioned at the hearth (orange-tinted, moderate
  range/attenuation) as the scene's primary light source, creating a
  hearth-lit focal glow.
- A subtle secondary light suggesting daylight through a window (a soft,
  cooler-tinted light near a wall) for gentle fill/contrast against the warm
  hearth glow. A simple window cutout (or window-frame prop) is placed in the
  matching wall position so the light source has a visible in-world origin,
  even though no exterior view or transition exists behind it yet.

## Testing & verification

- `tests/python` — asset-generation unit tests for each new prop, following
  the existing parameterized pattern in `tests/python/test_assetgen.py`
  (`test_prop_builds_within_budget`, `test_prop_glb_is_deterministic`, etc. —
  these already iterate over all of `props.PROPS`, so new props are covered
  automatically; hero props also need adding to `HERO_PROPS` to be checked
  against `HERO_TRI_BUDGET`).
- `tests/unit/test_interior_budget.gd` (gdUnit) — mirrors
  `test_zone_budget.gd`: verifies the assembled interior Zone's total
  triangle count stays under a reasonable budget cap.
- Manual boot verification via `godot-run_project` on `cottage_interior.tscn`
  to confirm a clean load with no errors, consistent with how every prior
  zone in this track was verified.
- `ROADMAP.md` (mark T4.3 done) and `docs/asset-inventory.md` (new prop rows)
  updated at the end, matching the pattern from the zone-tooling plan's final
  documentation task.

## Out of scope / deferred

- Scene transition (garden ↔ interior) — separate future task.
- Any interactive/gameplay system tied to interior objects (pantry, Leaven,
  tea-mending, chalk sigils) — these belong to later phases per the design
  bible's systems inventory.
