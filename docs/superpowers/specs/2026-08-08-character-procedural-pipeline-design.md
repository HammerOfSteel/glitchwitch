# Character Procedural Pipeline — Design Spec

**Status:** Approved for planning
**Owner phase:** New Phase — "Character Foundation" (inserted before current Phase 2 — World & Time)
**Author context:** Glitch Witch (Godot 4, GL Compatibility renderer)

## Why this exists

Phase 1 built one procedural character (Wren) as a bespoke, hand-authored module:
`tools/assetgen/character.py` hard-codes her rig, her meshes, and her five clips.
That was correct for proving the toy-render art direction end-to-end. It is not a
system yet — there is no way to generate a second character (an NPC, a villager, a
princess-type archetype) without copy-pasting the whole file and hand-editing every
constant.

Phase 6 (Village & Cast) needs 14+ villagers + kids + cats + magpies. Without a real
pipeline, that phase either explodes in bespoke files or gets rushed. This spec defines
the **foundation phase** that turns "one hard-coded witch" into "a deterministic,
data-driven character generator" — before we owe the project a village of NPCs.

## Reference project (logic source, not code source)

`HammerOfSteel/tomes_towers_and_transmutation` (branch
`cline_work-06_overworld_water_polish`) has a mature procedural character system
(princesses/NPCs) covering part composition, bones/rigging, and animation. We are
**not** porting its code — different engine, different mesh/animation format, different
constraints (segmented rigid-part rig with no skinning vs. that project's approach).
We are borrowing its *shape*: archetype-driven specs, a part registry with
compatibility rules, a rig/animation contract that every generated character must
satisfy, and validation tooling that catches broken combinations before they ship.
Where our existing `tools/assetgen` conventions (pure Python, deterministic, byte-hash
tested, GLB output) differ from that project's approach, our conventions win — this is
a Godot-native rebuild, informed by proven logic, not a transplant.

## Scope

**In scope:** the character generation pipeline itself — spec schema, part registry,
rig contract, animation contract, generator/assembler, validator, and refactoring Wren
to be the first character produced *by* the pipeline instead of a one-off script.
Also in scope: the **Asset Inventory Matrix**, a tracked artifact enumerating every
character/nature/building asset the game will eventually need, so the next phase
(broader asset production) has a backlog instead of guesswork.

**Out of scope:** actually authoring the full village cast (Phase 6's job), nature/
building generators themselves (next phase's job — this phase only produces their
inventory entries), skinned/bone-deformed meshes (segmented rigid-part rigs remain the
art direction per the design bible; skinning stays a documented fallback, not this
phase's concern).

## Architecture

The pipeline has four layers, each a distinct Python module under `tools/assetgen/`:

1. **Spec input** (`character_spec.py`) — a plain-data `CharacterSpec`: archetype id
   (e.g. `witch`, `villager`, `princess`, `child`), a `seed` (int, drives all
   randomized choices), a dict of part-slot choices (explicit or `None` = "let the
   generator pick deterministically from the seed"), a palette/material profile name,
   and an animation profile name (which named clip set this character needs — not
   every NPC needs `stir-loop`, but every character needs `idle-loop`/`walk-loop`).
2. **Part Library Registry** (`part_registry.py`) — a catalog of available part
   builders (head shapes, hats, hair, torsos, arms, boots, accessories) indexed by
   **slot** (`hips`, `head`, `torso`, `arm`, `boot`, `hair`, `headwear`, `accessory`). Each
   entry declares: which rig slot it fills, which archetypes it's compatible with,
   and any mesh-builder function reference (reusing `mesh.py`'s `add_box`/
   `add_cylinder`/`add_lathe` primitives — no new mesh primitives needed for this
   phase).
3. **Rig Contract** (`rig_contract.py`) — declares required node names per slot
   (mirroring Wren's existing node tree: `hips`, `torso`, `arm_l`, `arm_r`, `head`,
   `hat`, `braid`, `boot_l`, `boot_r` — all always present, see "Optional rig slots"
   below for why `hat`/`braid` are structurally mandatory nodes despite being
   visually optional per archetype), required parent/child
   relationships, and the attachment point each slot expects (translation anchor).
   This generalizes the constants currently hard-coded in `character.py` (`HIPS_POS`,
   `TORSO_POS`, etc.) into per-archetype configurable rig geometry, while keeping the
   same node-naming scheme so existing animation code keeps working unchanged.

   **Slot → node name mapping (canonical, fixed for this phase):**

   | Slot (registry key) | Rig node name(s) |
   |---|---|
   | `hips` | `hips` |
   | `torso` | `torso` |
   | `arm` | `arm_l`, `arm_r` (one registry entry, mirrored L/R by the rig builder) |
   | `head` | `head` |
   | `headwear` | `hat` (the rig node is always named `hat`, regardless of archetype — see "Optional rig slots" below) |
   | `hair` | `braid` (the rig node is always named `braid` for this phase — future archetypes needing non-braid hairstyles reuse the same node name, since it's a node identity, not a literal braid) |
   | `boot` | `boot_l`, `boot_r` (one registry entry, mirrored L/R) |
   | `accessory` | archetype-defined extra node(s), attached under `torso`, no baseline animation targets it |

   The registry slot names (`headwear`, `hair`) are the *catalog/compatibility* keys
   used in `part_registry.py` and `CharacterSpec.parts`; the rig *node* names (`hat`,
   `braid`) are what animation channels and the validator's node-existence checks
   target. Both are fixed vocab for this phase — no per-archetype renaming of nodes.
4. **Animation Contract** (`animation_contract.py`) — declares the mandatory baseline
   clip set every character must have (`idle-loop`, `walk-loop`, `run-loop`) and
   optional clips per animation profile (`wave`, `stir-loop`, future emotes). Reuses
   the existing `_gait`/`_idle`/`_wave`-style clip generators from `character.py`,
   parameterized instead of hard-coded, so a generated character with different limb
   lengths still gets correctly-scaled gait clips.

**Generator/Assembler** (`character_gen.py`) ties these together: given a
`CharacterSpec`, it resolves part choices (explicit or seeded-random from the
registry), builds the rig via `rig_contract`, attaches part meshes, generates
animation clips via `animation_contract`, and returns the same `(SceneNode, list[
AnimationClip])` shape that `gltf.build_scene_glb` already consumes.

**`build.py` integration (explicit, not implicit):** `build.py` currently calls
`character.build_rig()` / `character.build_animations()` / `character.flattened_builder()`
directly. This phase updates `build.py`'s character section to instead call
`character_gen.generate(spec)` for each character in a small `CHARACTERS` list (starting
with just Wren's spec), and extends the `manifest["characters"][name]` dict with the new
per-character metadata: `archetype`, `seed`, `resolved_parts` (dict of slot -> part id),
`spec_schema_version`, `rig_contract_version`, `animation_contract_version`, alongside the existing `tris`,
`bytes`, `sha256`, `clips` keys. `character.py` itself is kept as a thin module that
defines Wren's canonical `CharacterSpec` (archetype `witch`, fixed seed, explicit part
choices matching her current look) and re-exports it for `build.py` and tests to import
— this avoids a large diff in `build.py` while making the new pipeline the actual code
path for every character, including Wren.

### Determinism rules (explicit)

Byte-identical GLB output requires more than "same seed": seeded part selection must be
fully specified, not left to incidental dict/set iteration order. This phase's generator
must:

- Draw part choices using a single seeded `random.Random(seed)` instance per character,
  consumed in a fixed slot order — alphabetical by slot name: `accessory, arm, boot,
  hair, head, headwear, hips, torso` — defined once in `rig_contract.py`.
- When a slot has multiple compatible candidates in the registry, sort candidate part
  IDs lexicographically before indexing into them with the RNG — never rely on dict
  insertion order or set iteration.
- Build child node lists in the same fixed slot order every time (matches the existing
  pattern in `character.py`'s `build_rig`, which already lists children in a fixed
  order).
- Record the fully-resolved part choices (explicit or seed-derived) in the manifest
  (`resolved_parts`), so a byte-diff investigation can always answer "what did the seed
  pick" without re-running the RNG.

**Validator** (`character_validate.py`) runs after generation: confirms every rig
contract node exists, every mandatory clip exists and closes its loop (reusing the
loop-closure check pattern already in `test_character.py`), confirms triangle budget
(`TRI_BUDGET`, same 1500 ceiling used for Wren, revisited per-archetype if needed), and
raises descriptive `ValueError`s naming the exact missing/broken piece — no silent
fallbacks.

Same `CharacterSpec` (same archetype, seed, explicit part choices) → byte-identical
GLB output (see Determinism rules above), extending the existing
`test_wren_glb_is_deterministic` guarantee to every generated character. This is what
makes the pipeline testable and safe to regenerate after contract changes.

### Migration of Wren

Wren becomes `CharacterSpec(archetype="witch", seed=<fixed>, parts={...explicit...})`
run through the new generator. Her exact current mesh/rig/animation output must be
byte-identical after migration (regression-tested), proving the refactor preserved
behavior while the interface underneath changed completely.

**Canonical part builders must be reused verbatim, not reimplemented.** Wren's current
private helpers in `character.py` — `_skirt()`, `_torso()`, `_arm()`, `_head()`,
`_hat()`, `_braid()`, `_boot()` — become the first entries in `part_registry.py`,
moved (not rewritten) into registry-backed builder functions tagged for the `witch`
archetype's slots: `_skirt()` fills the `hips` slot, `_torso()` the `torso` slot,
`_arm()` the `arm` slot, `_head()` the `head` slot, `_hat()` the `headwear` slot,
`_braid()` the `hair` slot, `_boot()` the `boot` slot (see the slot → node table
above). This is a mechanical move: same mesh geometry, same profile tuples, same
palette ramp names, just relocated and registered instead of called directly from
`build_rig()`. Byte-identical output depends on this being a pure move, not a
rewrite.

### Visually-optional slots (hat, hair) are structurally mandatory nodes

`character.py`'s existing animation clips (`_idle`, `_gait`, `_wave`) target `hat` and
`braid` nodes unconditionally. These slots are "optional" only in the sense that an
archetype may choose an invisible placeholder mesh for them — the rig node itself is
never optional (see Rig Contract above). To keep the animation contract simple and avoid
per-profile clip branching, every rig built by `rig_contract.build(archetype)` **always
includes a node for every slot the animation contract's baseline clips target** —
`headwear` and `hair` slots are structurally required nodes, even when a given
archetype's registry entry for that slot is an empty/invisible placeholder mesh (zero
faces, a `MeshBuilder()` with no geometry added). This means:

- The animation contract's clip generators never need to special-case "this character
  has no hat" — the node exists, it's just invisible.
- The part registry's compatibility rules pick *which* mesh (real hat, real hair, or
  the empty placeholder) fills the slot per archetype — a `villager` archetype might
  default to the empty headwear placeholder, a `princess` archetype to an actual tiara
  mesh.
- The validator's "required rig node" check is simple and uniform across archetypes:
  every character has every baseline slot's node, always.

## Data flow

```
CharacterSpec (archetype, seed, part choices, animation profile)
   -> resolve part choices (explicit wins; else seeded pick from part_registry,
      filtered by archetype compatibility)
   -> rig_contract.build(archetype) -> SceneNode tree with slots populated by
      resolved part meshes
   -> animation_contract.build(rig, animation profile) -> list[AnimationClip]
   -> character_validate.check(rig, clips) -> raises on any contract violation
   -> gltf.build_scene_glb(rig, clips, name) -> GLB bytes (existing, unchanged)
   -> manifest entry: seed, archetype, part choices, spec schema version,
      rig contract version, animation contract version, tri count, sha256 (extends
      build.py's existing
      manifest.json pattern)
```

## Error handling & quality gates

- Invalid/unknown archetype id → `ValueError` naming the id and listing valid ones.
- Part choice incompatible with archetype (e.g. a `princess`-only hat slot chosen for
  a `child` archetype) → `ValueError` naming the slot and the incompatibility.
- Missing mandatory rig node or clip after generation → `ValueError` naming exactly
  which contract requirement failed (never a downstream KeyError/IndexError).
- Triangle budget exceeded → `ValueError` with actual vs. budget tri count.
- All contract versions (spec schema, rig contract, animation contract) are simple
  integers bumped on breaking changes, recorded in the manifest per character, so a
  future regeneration pass can detect which characters need re-authoring.

**Phase "done" gate:**
1. Wren regenerated through the new pipeline, byte-identical to her Phase 1 output
   (or a documented, deliberate, tested change if not).
2. At least one additional archetype (e.g. `villager`) generated end-to-end with a
   distinct seed, proving the pipeline isn't Wren-shaped underneath.
3. Validator catches at least one deliberately-broken fixture per failure category
   (missing node, missing clip, bad triangle budget, incompatible part) in tests.
4. Full pytest suite green; existing `test_character.py` assertions still pass
   (adapted to call through the new generator where appropriate).
5. Tooling doc (`tools/assetgen/README.md` or a docstring-level guide) explains: how
   to add a new part, how to add a new archetype, how to run the validator.

## Asset Inventory Matrix

A tracked artifact (`docs/asset-inventory.md`, a Markdown table — no new tooling
needed) listing every known-needed asset across the next phases, so asset production
isn't blind. Columns:

| Column | Meaning |
|---|---|
| Asset ID | short stable slug |
| Category | `character` / `nature` / `building` |
| Subtype | e.g. `villager`, `pine tree`, `cottage wall kit` |
| Procedural vs handcrafted | which pipeline (if any) produces it |
| Required rig/animation | for characters: which contract; for others: n/a |
| Dependencies | e.g. "needs part_registry hair slot", "needs palette ramp X" |
| Priority tier | tied to which future phase needs it first |
| Gameplay dependency | which quest/system blocks on this asset existing |
| Status | `planned` / `in progress` / `done` |

This phase populates it with every character the design/story bible already commits
to: Wren (design bible), the 15-row cast table in `story-bible.md` (Sigrid Barm,
Ansel Rowe, Maud Tressel, Juniper Vale, Torben Ask, Greta Furrow, Ines Jarvi, Fenn
Solder, Hollis Bram, Odell Rime, Eamon Brook, Tansy Mothwood, Pip & Nettle (kids, one
row), Sal A. Manda, Parity & Cache (cats, one row)), plus **Clack & Click** (the
magpie pair) and **the Kindlies** (pantry sprites), both named in `story-bible.md`'s
"The Pattern" section but not in the cast table — added here as their own rows since
they are confirmed characters needing generation. Nature/building categories get
placeholder rows only (populated in detail during the following asset-production
phase, but stubbed here so the backlog exists).

## Roadmap placement

Insert as a new phase between current Phase 1 (Player & Camera, complete) and current
Phase 2 (World & Time). All following phase numbers shift down by one. See
`ROADMAP.md` for the renumbered table.
