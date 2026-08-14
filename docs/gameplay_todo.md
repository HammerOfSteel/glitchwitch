# Gameplay Todo — Cottage → Mosslane Meadow Expansion

> Working name: **Mosslane Meadow**. A single, seamless expansion of the existing
> `cottage_garden` zone outward into meadow and forest-edge, so we finally have one
> good-sized, *actually-in-the-game* space to build and playtest movement, NPCs,
> interaction, and (later) quest content in — instead of a 12m×12m test pad. Think
> *Little Witch in the Woods* / Stardew's "outside the farmhouse" — the cottage stays
> the anchor, the world opens up around it.

Do this before returning to the normal ROADMAP.md track. It isn't disconnected from
that plan — it's Phase 4 (World & Time, currently 🚧 in progress) done properly, and it
plants the seed for Phase 10's Moss Forest and Torben's **No Fast-Forward** chain early,
so that ground already exists (literally) when we get there.

## Why this shape, specifically

- **Mosslane Hollow** (story-bible.md) is a hedge-country village; Torben Ask, the
  forester (already in-scene, patrolling the garden — see checkpoint 032), is tied to
  **No Fast-Forward**, which centers on a **moss stone** in the **Moss Forest**
  (Phase 10, T10.2). Extending the cottage garden into a forest edge with a moss-stone
  landmark isn't scope creep — it's the same location the roadmap already calls for,
  built early enough to live in during every phase between now and then.
- The design bible's zone budget (≤150k tris / ≤120 draw calls, MultiMesh for scatter)
  already assumes exactly this kind of space — `ZoneBuilder`/`ScatterRegion`/
  `PropPlacement` (`src/world/`) were built generic, proven on `cottage_garden`,
  `cottage_interior`, `hedgerow_lane`. This expansion is the tooling's first real stress
  test at scale, not a new system.
- There is currently **no zone-streaming/portal system** in the project — every zone is
  its own scene with no loading boundary between them. "Seamless" therefore means: grow
  the *existing* `cottage_garden.tscn` outward in place (more ground tiles, more
  `PropPlacement`/`ScatterRegion` entries), not bolt on a second zone behind a loading
  seam. That's the one architectural decision this doc is committing to up front.

## Scope

**In scope:**
- Extend `cottage_garden`'s ground plane outward (today: 12.2×12.2, tiled from
  `ground_tile.glb`) into a meadow band, then a forest edge, then a small clearing.
- New procedural props (same `tools/assetgen/props.py` pipeline as everything else —
  no new asset pipeline): a mossy ground/forest-floor variant, a **moss stone** landmark
  (foreshadowing only — no dialogue/quest logic yet), denser pine variety, a fallen log
  or two, maybe a footbridge/stepping-stones if a stream reads well.
- Density-graded scatter: sparse near the tended garden, denser toward the clearing —
  reusing `ScatterRegion`/`ZoneBuilder`, the same mechanism as the garden's existing
  grass/flower scatter.
- A budget pass: re-validate the (probably raised) zone ceiling once real content is in,
  the same way every existing zone is budget-tested.
- One small "make it feel alive" touch — a bench/sit-log, a lookout point, or a hidden
  note prop — nothing quest-shaped, just presence.

**Out of scope (explicitly, for now):**
- Any zone streaming/portal/loading-seam system. Revisit only if a single-scene budget
  genuinely can't hold the space we want.
- Actual Moss Forest slow-time mechanics or **No Fast-Forward** quest content (Phase 10 /
  Phase 5's quest engine, T5.2, isn't built yet). The moss stone here is scenery, not a
  quest trigger.
- Terrain elevation/heightmap system. Stays flat like every existing zone unless prop-based
  mounds (stacked rock dressing) turn out to be enough — a real heightmap tool is a
  bigger, separate decision.

## Zone layout (grounded in the current `cottage_garden.tres` coordinates)

Existing, unchanged: cottage facade `z=-4.3`, well `(5,0,3)`, crate `(5,0,1)`, planters
`(-5,0,3)`/`(-5,0,1)`, rocks `(4,0,-3)`/`(-4,0,-4)`, fences `x=-5.9`, `DemoVillager`
`(1.6,0,2.2)`, Ansel's patrol loop, Torben at `(-3.5,0,-3.2)`, player spawn `(0,0.2,3)`.

Growth direction: **+Z**, away from the cottage facade, past the existing garden
dressing — the one side of the current 12.2×12.2 pad with open room to extend.

1. **Garden core** (existing) — untouched.
2. **Meadow band** — wider open grass past the current fence line, a fence *gap* acting
   as a visual threshold out of the "tended" garden, scattered flowers thinning out.
3. **Forest edge** — pine density ramps up, rocks and fallen logs appear, ground
   texture shifts toward the new mossy/forest-floor variant.
4. **Small clearing** — the destination: denser ambient dressing, the moss stone
   landmark, a sit-log/bench. This is the "somewhere to be," not just a way-point.

## Task breakdown

- [ ] **T1 — New procedural props** (`tools/assetgen/props.py`): forest-floor ground
  tile variant, moss stone, fallen log (or a rock variant reused at larger scale +
  moss coloring). Same tests-per-asset pattern as existing props (byte-determinism,
  GLB structural validation, triangle budget).
- [ ] **T2 — Extend the zone**: grow `cottage_garden.tscn`'s ground tiling and
  `PropPlacement`/`ScatterRegion` list to cover meadow → forest edge → clearing.
  Existing NPCs/props/patrol points stay exactly where they are.
- [ ] **T3 — Populate scatter with a density gradient**: sparse near the garden fence,
  denser toward the clearing, using `ScatterRegion` the same way the garden's grass/
  flowers already work.
- [ ] **T4 — Budget pass**: re-run `test_zone_budget.gd`; if real content pushes past
  150k tris / 120 draw calls, decide per-instance-count trims vs. a deliberate,
  documented ceiling raise for this one larger zone (owner call, not assumed).
- [ ] **T5 — Playtest pass**: confirm player movement/collision and `CameraRig`'s
  follow/spring-arm still feel good at this larger scale (no code changes expected,
  but worth confirming — especially once the camera-glitch investigation above has a
  root cause, since a bigger space is exactly where "specific spots" get easier to find).
- [ ] **T6 (stretch)** — one small presence touch: a sit-able bench/log, a lookout view,
  or a hidden note prop tucked in the clearing. Not a quest, just something to notice.

## Open questions (owner call before/while executing)

- Target footprint: the meadow+forest-edge+clearing should probably land somewhere
  around 3–4× the current garden's area — good enough to actually walk around in
  without needing a sprint mechanic yet. Shout if you want it bigger or smaller.
- Zone budget: keep everything inside the existing 150k tri / 120 draw call ceiling
  (leans harder on MultiMesh scatter), or would you rather raise the ceiling
  specifically for this "big test/home" zone and document why?
- Moss stone: pure foreshadowing prop for now, or worth a line or two of flavor text
  (e.g. a `Talk`-style inspect prompt with no dialogue graph) so it's already
  noticeable before Torben's chain exists?
