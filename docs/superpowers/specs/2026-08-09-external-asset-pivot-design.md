# External Asset Sourcing Pivot — Design Spec

**Status:** Approved (user-directed pivot, implemented 2026-08-09)
**Supersedes (scope-limited):** the "characters are Blender-backed" and "nature
& building foundation" direction set by
`docs/superpowers/specs/2026-08-08-character-pipeline-v2-blender-design.md` and
`docs/superpowers/plans/2026-08-08-character-pipeline-v2-blender.md` (Phase 2),
and defers the scope of Phase 3 (`docs/superpowers/specs/2026-08-08-character-procedural-pipeline-design.md`
is unaffected — the v1 procedural pipeline it describes remains the live
placeholder source).
**Author context:** Glitch Witch (Godot 4.7, GL Compatibility renderer)

## Decision

Building and tuning an in-house procedural pipeline for final character art
(Blender-backed character-pipeline-v2) and for final nature/building art (the
planned Phase 3 procedural foundation) is **paused**. The project owner is
running several projects at once and has decided the more efficient path is:

- **Characters:** generate final art with Meshy AI (or a similar generative
  tool), producing rigged/animated GLBs the owner brings into the repo when
  ready — not scripted from a shared committed base mesh via `bpy`.
- **Nature & buildings:** source free/CC0 low-poly modular asset packs that fit
  the game's toy-box low-poly look, rather than building a from-scratch
  procedural nature/building generator. `tools/assetgen`'s procedural approach
  for the *existing* small prop set (mug, jar, crate, fence, pine, ground tile)
  remains valid and unchanged — this decision is about not extending that
  system to cover the full asset backlog in `docs/asset-inventory.md`.

This is **not** a judgment that the in-house work was low quality — Tasks 1–11
of character-pipeline-v2 are solid, tested groundwork (base humanoid mesh,
loader, proportions, clothing, materials, animation, export, validation). It's
a scope/effort call: maintaining a bespoke Blender toolchain for one of several
concurrent projects isn't worth it right now, when off-the-shelf generation
gets usable art faster.

## What happens to the paused work

- `tools/assetgen/blender/` (Tasks 1–11, plus the partial Task 12
  orchestrator) stays in the repo, tests and all. Nothing is deleted.
- `docs/superpowers/plans/2026-08-08-character-pipeline-v2-blender.md` and its
  design spec are marked **Paused** with a pointer to this document.
- No further tasks (12–19) are dispatched against that plan unless the project
  owner explicitly asks to resume it.
- `validate.py`'s pure-Python GLB structural/proportion gate (Task 11) is
  reusable later regardless of mesh source — noted here so it isn't
  rediscovered as "dead code" by a future pass.

## Placeholder strategy (so world/gameplay work isn't blocked)

While external art is sourced (an ongoing, as-time-allows effort by the
project owner, not a scheduled phase), every phase from Phase 4 onward keeps
moving using placeholders that already exist or are cheap to add:

### Wren (player character)

- **New placeholder:** `assets/thirdparty/wren_placeholder/wren_placeholder.glb`,
  built by `tools/assetgen/placeholders/fetch_wren_placeholder.py` from a
  rigged/animated Seren body (`seren_dress_rigged_animated_glb.zip`) the owner
  already generated via Meshy AI for a separate project
  (`HammerOfSteel/meshy`). The fetch script:
  1. Extracts the source zip's two GLBs (skinned mesh + a separate
     animations-only file — this is the shape Meshy AI's rigged+animated
     export takes).
  2. Runs `tools/assetgen/placeholders/merge_seren_placeholder.py` headless in
     Blender to merge them onto one armature, renaming clips to
     `idle` / `walk` / `run` (the source's `Armature|clip0|baselayer` rest
     pose stands in for idle; there are no wave/stir gesture clips).
  3. Writes the merged single-mesh GLB to
     `assets/thirdparty/wren_placeholder/` (gitignored, like the rest of
     `assets/thirdparty/`, and rebuilt locally by re-running the script — the
     source zip is never committed).
- `src/player/avatar.gd` (`WrenAvatar`) loads this placeholder when
  `USE_PLACEHOLDER := true` (the default now), and falls back to the
  procedural `assets/generated/wren.glb` if the placeholder hasn't been built
  locally yet. Palette dressing (`PaletteApply`) is skipped for the
  placeholder since it ships its own baked material; gesture playback
  (`play_gesture`) no-ops gracefully when the requested clip doesn't exist on
  the loaded body, instead of erroring.
- Swapping back to real Wren art later is a one-line change
  (`USE_PLACEHOLDER := false`, or repointing `PLACEHOLDER_SCENE_PATH` at the
  final GLB) plus re-verifying clip names against `MOTION_CLIPS`/
  `GESTURE_CLIPS`.

### Villagers / other NPCs

- The v1 procedural villager (`assets/generated/villager.glb`, from
  `tools/assetgen/character_gen.py`) remains the placeholder. The user has
  flagged it looks rough — that's expected of a v1 procedural placeholder and
  is exactly the kind of asset Meshy AI generation is meant to replace; no
  further procedural polish work is planned for it.
- `docs/asset-inventory.md` is annotated (see its 2026-08-09 sourcing note) so
  every remaining cast member row is understood as "needs external art,
  currently unblocked by placeholder policy" rather than "blocked."

### Environment (nature & buildings)

- `src/sandbox/glade.tscn` (and `src/lookdev/diorama.tscn`) already use the v1
  procedural prop set (`pine.glb`, `fence.glb`, `crate.glb`, `jar.glb`,
  `mug.glb`, `ground_tile.glb`) generated by `tools/assetgen/props.py`. This
  was never touched by the paused Blender character work, so it needs no
  restoration — it's the existing environment placeholder scene and stays
  exactly as-is.
- When more environment placeholders are needed for Phase 4 zone-building
  (rocks, flora variety, cottage-kit pieces), add them the same way: either
  extend `tools/assetgen/props.py` with more simple procedural props (cheap,
  in-house, no new dependency), or drop in a free/CC0 pack asset under
  `assets/thirdparty/` — whichever is faster at the time. No new tooling
  commitment is being made here; this is a "use what's fastest, per asset"
  policy, not a new pipeline.

## Verification performed

- Rebuilt and inspected the merged placeholder GLB structurally (single mesh,
  single skin, three clips named `idle`/`walk`/`run`).
- Ran the project in Godot (`src/sandbox/glade.tscn`) with the placeholder
  wired in: loads with no resource-loader errors, no fallback warning.
- Ran the full `tests/python` suite: 111/113 passing, unchanged from before
  this pivot — the 2 pre-existing failures are the known Task 12 tri-budget
  issue in the now-paused Blender orchestrator, untouched by this change.

## Non-goals

- This spec does not decide *when* the owner will produce final Meshy AI
  character art or pick specific CC0 environment packs — that's owner-driven,
  as-time-allows work outside this repo's automated pipeline.
- This spec does not remove or refactor the v1 procedural character/prop
  pipeline (`tools/assetgen/character_gen.py`, `tools/assetgen/props.py`) — it
  remains the active placeholder source and is not being retired.
