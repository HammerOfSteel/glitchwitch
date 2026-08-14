# Villager Rig System — Design Spec

**Status:** Proposed (pending spec review + user approval)
**Author context:** Glitch Witch (Godot 4.7, GL Compatibility renderer)
**Supersedes (scope-limited):** the "villager rig/anim contract" / "part_registry
villager entries" plan noted against every villager row in
`docs/asset-inventory.md` (e.g. `sigrid-barm`, `ansel-rowe`, ...). Those rows
assumed villagers would be baked as static GLBs by extending
`tools/assetgen/part_registry.py`/`character_gen.py` (the same offline
Python→GLB pipeline used for props). This spec replaces that plan for
villagers with a runtime, DNA-driven GDScript rig system instead. It does
**not** affect Wren (the player), who keeps her Meshy-AI-sourced placeholder
body per `docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md`.

## Background

The project owner has an existing, well-proven procedural character system in
a sibling project, `HammerOfSteel/tomes_towers_and_transmutation`
(`cline_work-06_overworld_water_polish` branch,
`src/princess-creator/`). That system is a Three.js/TypeScript **runtime**
character builder: a `PrincessDNA` object drives a `BodySynthesizer` per
species archetype (human/fox/lamia/skeleton/slime), which builds a body from
primitives parented into a hierarchical joint-`Group` rig (not GPU skinning),
attaches parts via named sockets, and animates it with a small code-driven
`Animator` (idle/walk/emotes + secondary motion). DNA is fully serializable
(seeded RNG, shareable "DNA codes"), so any villager can be reproduced from a
single seed/DNA blob.

Glitch Witch's current villager placeholder (`tools/assetgen/character_gen.py`
→ `assets/generated/villager.glb`) is a single static, hand-rough v1 mesh —
explicitly called out in
`docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md` as "rough"
and not worth further procedural polish *in the old pipeline*. The project
owner wants to port the tomes_towers architecture (not its code — different
engine/language) so that every future named villager (`sigrid-barm`,
`ansel-rowe`, etc., all "Phase 8" in the asset inventory) can be generated
on-demand from DNA at runtime in Godot, rather than requiring a new baked GLB
per character.

## Decision

Build a new, self-contained GDScript system under `src/characters/villager/`
that ports the tomes_towers architecture's shape (DNA → synthesizer → rig →
sockets → animator) to Godot idioms. Scope for this phase:

- **Human archetype only.** Every currently-planned villager is human; bird
  (`clack-and-click`), quadruped (`parity-and-cache`), and small-creature
  (`the-kindlies`) archetypes are explicitly deferred to their own future
  phase and are non-goals here.
- **Villager NPCs only.** Wren is untouched.
- **One reusable system + one live proof-of-concept** placed in
  `cottage_garden`, not a fully populated village or the full 10-strong cast.

## Non-goals

- No bird/quadruped/small-creature synthesizers.
- No migration of Wren off her placeholder body.
- No authoring of the actual 10 named "Phase 8" villagers' individual DNA/
  story hookups — this phase proves the *system*, not the *cast*.
- No baked-GLB export path (unlike tomes_towers' `exporter.ts`, which exports
  PNG portraits/GLBs/JSON for its standalone creator tool) — Glitch Witch's
  villagers are built directly into the running scene tree, since there is no
  standalone "character creator" tool for this project.
- No hairstyle/clothing variety pack — v1 ships exactly one hair mesh (the
  only true socket-attached part) and one fixed clothing *shape* (the
  torso/limb primitives themselves, no separate garment mesh/silhouette).
  Clothing *color* still varies per villager via `clothing_ramp` (§1/§4) —
  that's DNA doing its job, not a "variety pack." Enough to prove the socket
  + per-part-color patterns work, not a full wardrobe.

## Architecture

### 1. Data model — `VillagerDna`

`src/characters/villager/villager_dna.gd` — a lightweight `RefCounted` (not a
`Resource`, to avoid `.tres` serialization overhead for something that's
usually generated, not hand-authored) holding:

```gdscript
class_name VillagerDna

var seed: int
var name: String
var height_scale: float       # 0.85..1.15, multiplies base rig height
var build_scale: float        # 0.85..1.15, multiplies limb/torso thickness
var skin_ramp: StringName     # existing palette ramp name, e.g. "cream"
var hair_ramp: StringName
var clothing_ramp: StringName
var hairstyle: StringName     # part id, e.g. "bob" (only one exists in v1)
```

`clothing_ramp` is **not** a socket-attached part in v1 — it's simply which
ramp colors the torso/limb primitives (§4's per-part shade table already
covers this: torso/limbs sample `clothing_ramp`, head/hands sample
`skin_ramp`). Only hair is a true attached part (`head_top` socket);
"carried item" sockets (`hand_l`/`hand_r`) exist in the rig for future use
but nothing occupies them in this phase — no carried-item part is defined
yet (non-goal, see above).

`VillagerDna.random(seed: int) -> VillagerDna` — deterministic factory using
Godot's built-in `RandomNumberGenerator` seeded with `seed`, mirroring the
source's seeded-RNG-driven `randomDna()`. Colors are drawn from *existing*
`tools/assetgen/palette.py` ramp names (via a small hardcoded allow-list in
GDScript, not a live Python↔GDScript bridge) so villagers automatically match
the shared toon palette already used everywhere else — no new colors are
invented.

### 2. Rig — `VillagerRig`

`src/characters/villager/villager_rig.gd` — builds a `Node3D` hierarchy at
runtime using Godot's built-in primitive meshes (`CapsuleMesh`, `SphereMesh`,
`CylinderMesh`), which are cheap to construct but ship default UVs that do
**not** point at the correct palette atlas cell — every one needs its UVs
rewritten before use; see §4 for exactly how and where that happens. Joint
structure mirrors the source's `PrincessRig` contract 1:1 (same names,
adapted to GDScript):

```
root (Node3D, baseY)
└─ torso (MeshInstance3D, CapsuleMesh — clothing_ramp)
   ├─ neck (Node3D)
   │  └─ head (MeshInstance3D, SphereMesh — skin_ramp)
   │     └─ head_top socket (Node3D, marker — hair attaches here)
   ├─ shoulder_l / shoulder_r (Node3D)
   │  └─ elbow_l / elbow_r (MeshInstance3D, CapsuleMesh arm — clothing_ramp)
   │     └─ hand_l / hand_r (MeshInstance3D, small SphereMesh — skin_ramp;
   │        doubles as the "hand socket" — a mesh that is ALSO the
   │        attachment point, not a separate empty marker)
   └─ hip_l / hip_r (Node3D)
      └─ knee_l / knee_r (MeshInstance3D, CapsuleMesh leg — clothing_ramp)
```

Every body-mesh node listed above (torso, head, both arm segments, both
hands, both leg segments) is built AND has its UVs stamped (§4) by
`VillagerRig` itself, in the same construction pass — `VillagerRig` is the
**sole owner** of primitive creation and UV-stamping; no other module
touches mesh geometry or UVs.

**Hair (v1's one attached part):** since there is exactly one hairstyle in
v1, it is a single hardcoded builder function,
`VillagerRig._build_hair(dna) -> MeshInstance3D` (a small squashed
`SphereMesh`, no separate part-registry/lookup needed — YAGNI until a second
hairstyle exists), UV-stamped to `hair_ramp` the same way as body meshes, and
parented directly under the `head_top` socket by `VillagerRig` itself as
part of the same construction pass (not a later "attach" step done by the
factory).

### 3. Synthesizer — `HumanSynth`

`src/characters/villager/synth/human_synth.gd` — the (only, for now)
implementation of a small `BodySynthesizer`-shaped contract:

```gdscript
# static func build(dna: VillagerDna) -> VillagerBuildResult
```

`VillagerBuildResult` bundles `root: Node3D`, `rig: VillagerRig`, and
`sockets: Dictionary[StringName, Node3D]` (`head_top`, `hand_l`, `hand_r` in
v1 — a deliberately small subset of the source's 9 sockets, since hair and
carried items are the only part categories this phase needs). No `dispose()`
method — see §4's note on why Godot doesn't need one.

This mirrors the source's `synth/index.ts` registry pattern in spirit, but
since there's only one archetype in v1, `HumanSynth` is called directly by
the factory rather than through a registry indirection — YAGNI: a registry
dict is trivial to add later when a second archetype exists.

### 4. Materials

No new shader. Villagers still use the exact same `palette_main.tres`
`ShaderMaterial` (+ `outline_main.tres` next-pass), applied once to the whole
villager subtree via the existing `PaletteApply.apply()` — unchanged, since
`PaletteApply` only ever assigns one shared `material_override` per
`MeshInstance3D` and has no notion of "which ramp." **Coloring still comes
entirely from mesh UVs**, exactly like every other prop, because the shared
shader samples the palette atlas texture at whatever UV each vertex carries
(`filter_nearest`, one flat color per sampled cell) — Godot's built-in
primitives (`CapsuleMesh` etc.) ship their own default UVs, which point at
the *wrong* place in the atlas, so they cannot be used as-is.

**Fix — a small build-time export + a runtime UV stamp:**

`tools/assetgen/palette.py`'s `cell_uv(ramp, shade)` takes **both** a ramp
name and a shade index (0..`SHADES`-1, darkest to lightest) — a single ramp
name alone (e.g. `"cream"`) is not enough to pick one atlas cell. This spec's
`VillagerDna` ramp fields (`skin_ramp`, `hair_ramp`, `clothing_ramp`) name the
ramp only; **shade is fixed per body part, not per DNA**, matching how
existing hand-authored parts do it (e.g. `part_registry.py`'s `witch_head()`
uses shade `3` for skin, `witch_torso()` uses shade `2`) — e.g. head/hands
always sample shade 3 (lightest) of `skin_ramp`, torso/limbs always sample
shade 2, hair always samples shade 1. This is a small hardcoded table in
`VillagerRig`, not part of the DNA schema — varying shade-per-part is a v2
concern (YAGNI for a single demo villager).

- `tools/assetgen/palette.py`'s existing build step (`make assets`) gains one
  new output: `assets/generated/palette_uv.json`, a flat
  `{"ramp/shade": [u, v]}` map (e.g. `"cream/3": [0.53, 0.19]`) covering every
  `(ramp, shade)` pair `cell_uv()` can produce — the *single source of
  truth* stays Python (no duplicated ramp math in GDScript), it's just
  re-exported in a runtime-readable form. This is additive to
  `build_palette_png()`'s existing output, not a new pipeline.
- `src/characters/villager/palette_uv.gd` — loads `palette_uv.json` once
  (static cache, no autoload needed) and exposes
  `static func uv_for(ramp: StringName, shade: int) -> Vector2`. If the file
  is missing, fails to parse (malformed JSON), or the `(ramp, shade)` key
  isn't found — all three treated identically — it `push_warning()`s
  (matching `PaletteApply.apply()`'s existing "run `make assets` first"
  warning convention) and returns `Vector2.ZERO` — the villager still
  renders (as one wrong-but-valid flat color), it just looks wrong instead of
  crashing, exactly like the rest of the asset pipeline degrades today.
- `VillagerRig`'s primitive-building step, for each generated
  `MeshInstance3D`, uses `SurfaceTool` to rewrite that surface's UV array so
  **every vertex maps to one constant point** (`palette_uv.gd`'s point for
  that part's fixed ramp+shade pair) — i.e. the same "one flat color per
  mesh" technique `MeshBuilder.add_face()` already uses for props, just
  applied at runtime instead of at Python-build-time. `PaletteApply.apply()`
  is then called once on the whole villager root exactly as it is for every
  other scene subtree today — no changes to `PaletteApply` itself.

This keeps the "one shared material, all color from UVs" architecture fully
intact and sidesteps the outline-seam pitfall discovered this session (each
primitive is one closed Godot mesh resource, not subdivided quads, so no new
seam risk).

**No manual `dispose()` is needed** (unlike the source's Three.js synths,
which must manually free `BufferGeometry`s). Godot's `PrimitiveMesh`
resources and nodes are reference-counted/freed automatically when their
owning node is `queue_free()`'d — this is a deliberate simplification from
the source architecture, not an oversight.

### 5. Animation — `VillagerAnimator`

`src/characters/villager/villager_animator.gd` — a small per-frame driver,
called from `_process(delta)`, that rotates rig joints via sine-based curves
(idle: torso breathing scale + head bob; walk: hip/shoulder swing) — no
baked `AnimationPlayer` clips in v1, matching the source's code-driven
`animate.ts` approach rather than `avatar.gd`'s clip-based
`AnimationPlayer`/`AnimationTree` approach (those are for the externally
authored Wren mesh; villagers have no external clips to play). Exposes
`set_motion_state(state: StringName)` (`&"idle"` / `&"walk"`) matching
`avatar.gd`'s exact method name (`WrenAvatar.set_motion_state()`), so future
zone/NPC-controller code reads consistently across both character types.

### 6. Façade — `VillagerFactory` and `VillagerInstance`

`src/characters/villager/villager_factory.gd`:

```gdscript
static func build(dna: VillagerDna) -> VillagerInstance
```

`VillagerInstance` (`src/characters/villager/villager_instance.gd`) **is**
the returned root — it `extends Node3D`, owns the rig/sockets/animator
internally, and is the one public surface other code touches:

```gdscript
class_name VillagerInstance
extends Node3D

var sockets: Dictionary  # StringName -> Node3D, read-only by convention

func set_motion_state(state: StringName) -> void   # &"idle" / &"walk"
func play_gesture(gesture: StringName) -> void  # no-op if unsupported (v1: none)
```

Internally, `VillagerInstance._process(delta)` drives its own
`VillagerAnimator` — matching how `avatar.gd`'s `WrenAvatar` is itself the
`Node3D` with `set_motion_state`/`play_gesture` methods, so zone/NPC code can
treat both character types identically. Cleanup is plain `queue_free()` (no
custom `dispose()` — see §4's note on why this differs from the source).

`VillagerFactory.build()` internally: `HumanSynth.build(dna)` (which fully
builds `VillagerRig` — meshes, UV-stamping, and hair all done, per §2/§3) →
construct the `VillagerInstance`, parent the rig under it, and return it. No
separate "attach parts" or "stamp UVs" step happens in the factory — that
work is entirely `VillagerRig`'s responsibility (§2).

### 7. Zone integration (proof-of-concept)

`cottage_garden.tscn`/`.gd` gains one demo villager, added as a direct child
of the `CottageGarden` root node (same level as its other manually-placed
nodes like `Sun`/`Fill`), named `DemoVillager`, built via
`VillagerFactory.build(VillagerDna.random(20260810))` (fixed seed for
deterministic scene tests) in `_stage()`, standing near the well — a static
(non-interactive, no dialogue/AI yet — that's future gameplay-phase work)
figure proving the system renders correctly in a real, already-shipped zone
alongside the stone cottage. No new interaction/quest logic — this is purely
an art/tech integration proof.

## Testing

`tools/assetgen/palette.py` gains its own Python test:

- `tests/python/test_palette_uv_export.py` — `palette_uv.json` is written by
  the `make assets` build step, contains an entry for every `(ramp, shade)`
  pair the villager system's fixed shade table (§4) actually uses, and each
  entry's `[u, v]` matches `cell_uv(ramp, shade)` exactly (regression-proofs
  the export against the existing pinned-hash-style tests already in
  `tests/python/`).

The GDScript-side system otherwise has no Python component (it's pure
runtime GDScript once the JSON export exists) and is covered by gdUnit tests
under `tests/unit/` (matching existing files like `tests/unit/test_avatar.gd`,
`tests/unit/test_cottage_garden.gd`):

- `tests/unit/test_villager_dna.gd` — `VillagerDna.random(seed)` is
  deterministic (same seed → identical DNA fields) and produces values
  within documented ranges.
- `tests/unit/test_villager_rig.gd` — `HumanSynth.build()` produces a rig
  with all expected joint names present, mirrored L/R joints have inverted
  `scale.x`, and freeing the returned root (`queue_free()` + a frame) leaves
  no dangling children/resources.
- `tests/unit/test_villager_factory.gd` — `VillagerFactory.build()` returns a
  `VillagerInstance` with the 3 v1 sockets populated, every body/hair mesh's
  `material_override` set to the shared palette material (proving
  `PaletteApply.apply()` ran) and UV arrays matching `palette_uv.gd`'s
  `uv_for(ramp, shade)` for their assigned part (proving the UV-stamp step
  ran correctly, not just "no errors logged"), and its own tri count is
  within the ≤4,000-tris/character budget (`docs/design-bible.md`) — this is
  the *only* place the per-character budget is asserted.
- `tests/unit/test_zone_budget.gd` (existing zone-budget test, extended) —
  currently asserts `cottage_garden`'s total tris/draw-calls against the
  design bible's zone ceiling (≤150k tris, ≤120 draw calls); extended to
  include the demo villager in that same total, so the zone-level check
  stays where the repo already puts it, separate from the
  character-level budget assert in `test_villager_factory.gd` above.
- `tests/unit/test_cottage_garden.gd` (existing scene smoke test) —
  extended with one assertion that the `DemoVillager` node exists in the
  built scene, matching this file's existing role as a structural/content
  smoke test (not a budget test).

## Documentation updates

- `docs/asset-inventory.md`: every villager row's "Est. approach" /
  "Dependencies" columns updated from "part_registry villager entries" to
  reference this system; a new `villager-rig-system` row added (P0, "Phase 5
  villager rig system", status "planned" until built).
- This spec's header already marks the old plan as superseded (scope-limited
  to villagers only).

## Open questions for the user before implementation

None outstanding — all scope decisions (archetype, target, zone
proof-of-concept) were confirmed during brainstorming. Naming of the actual
demo villager (e.g. reuse one of the "Phase 8" names like `sigrid-barm`, or a
throwaway placeholder name) is left to the implementation plan to propose,
since it's a small, reversible detail.
