# Glitch Witch — Roadmap

Thirteen phases, 0 → 12. Every phase: its own branch, per-task pushes, per-subtask commits,
tests with every task, full green suite + playable artifact at the gate, then PR to `main`
and a tag. Current status lives in the table at the bottom.

**Scope target:** deep cozy RPG, 10h+ with postgame.
**Content targets:** 24 main quests · ~30 side · 10+ hidden · 20+ RNG drift templates ·
8 zones · ~16 characters + creatures · 40+ recipes · 60+ journal entries.

---

## Phase 0 — Foundation (`phase/00-foundation`)
Goal: a repo where every later phase is cheap — pipeline, tests, CI, and the look proven.

- **T0.1 Repo scaffold** — README, CONTRIBUTING (the working ritual), ROADMAP, design
  bible, story bible, licensing proposal, git/editor configs. *Tests: repo-lint suite.*
- **T0.2 Godot project bootstrap** — `project.godot` (GL Compatibility), folder
  architecture, boot scene, code-defined input map, version pins, bootstrap script for
  pinned tooling (gdUnit4). *Tests: headless import + boot smoke + input map assertions.*
- **T0.3 CI pipeline** — GitHub Actions: python/lint job, godot test job, export smoke
  (Linux + Web) with cached templates, README badge. *Test: CI green is the test.*
- **T0.4 Asset toolchain** — pure-Python `tools/assetgen`: palette PNG generator, low-poly
  mesh kit, GLB exporter, proof props (mug, jar, fence, crate, pine, ground tile).
  *Tests: byte-determinism, GLB structural validation, triangle budgets.*
- **T0.5 Look-dev diorama** — toon ramp + outline shaders, palette material, cottage-corner
  scene, lighting/post stack, screenshot runner for CI artifacts.
  *Tests: shader/scene smoke; visual artifact from CI.*

## Phase 1 — Player & Camera (`phase/01-player-camera`)
- T1.1 Character controller (cozy feel, slopes, footstep events)
- T1.2 Third-person camera (spring arm, collision, orbit, interact-framing)
- T1.3 First-person toggle + **Witch Sight** overlay (seam-revealing layer)
- T1.4 Interaction system (focus, prompts, priority)
- T1.5 Witch avatar: procedural segmented character with code-authored clips

## Phase 2 — Character Foundation (`phase/02-character-foundation`)
> **⏸️ Paused (pivot 2026-08-09):** in-house procedural/Blender character
> generation is on hold — final character art is now sourced externally
> (Meshy AI or similar), owner-driven, as time allows. Placeholders (v1
> procedural Wren/villager + a Seren-derived rigged/animated Wren stand-in)
> keep later phases unblocked in the meantime. Full rationale and placeholder
> details: [`docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md`](docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md).
> Original goal, kept for reference / possible future resumption:

Goal: turn Wren from a hard-coded one-off into a deterministic, data-driven procedural
character pipeline capable of producing the full village cast later, without ever
touching a rigged/skinned mesh. Godot-native rebuild, informed by (not ported from)
the procedural character system in `HammerOfSteel/tomes_towers_and_transmutation`
(branch `cline_work-06_overworld_water_polish`). Full design in
[`docs/superpowers/specs/2026-08-08-character-procedural-pipeline-design.md`](docs/superpowers/specs/2026-08-08-character-procedural-pipeline-design.md).

- T2.1 Character spec schema + part library registry (`character_spec.py`,
  `part_registry.py`) — archetypes, seeded part-slot resolution, compatibility rules.
  ✅ done (v1 procedural, still the live placeholder source)
- T2.2 Rig contract + animation contract (`rig_contract.py`, `animation_contract.py`) —
  canonical slot → node mapping, mandatory baseline clip set, per-archetype geometry.
  ✅ done (v1)
- T2.3 Generator/assembler + validator (`character_gen.py`, `character_validate.py`) —
  spec-to-GLB pipeline, contract-violation errors, byte-determinism guarantee.
  ✅ done (v1)
- T2.4 Wren migration — her exact current look/rig/animations reproduced byte-identical
  through the new pipeline; `build.py` updated to call the generator. ✅ done (v1);
  Blender-backed v2 rebuild paused, see pivot note above
- T2.5 Second archetype proof (e.g. `villager`) generated end-to-end + Asset Inventory
  Matrix (`docs/asset-inventory.md`) populated with every known character/nature/
  building asset need. ✅ done (v1 proof); matrix now annotated with the sourcing
  pivot. *Tests: rig/clip/budget validation, determinism, contract version metadata
  in manifest.*

## Phase 3 — Nature & Building Foundation (`phase/03-nature-building-foundation`)
> **⏸️ Paused (pivot 2026-08-09):** deferred in favor of sourcing free/CC0
> low-poly modular packs for nature/building art, owner-driven, as time allows —
> same rationale as Phase 2's pause. The existing v1 procedural prop set
> (`tools/assetgen/props.py`: pine, fence, crate, jar, mug, ground tile) remains
> the live environment placeholder (see `src/sandbox/glade.tscn`) and needs no
> restoration. Extend it with cheap new procedural props, or drop in CC0 pack
> assets, per-asset, whichever is faster — no new pipeline commitment. See
> [`docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md`](docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md).

Original goal, kept for reference / possible future resumption: apply the same
procedural-foundation discipline to environment assets — trees, rocks, flora,
fences, and cottage/building kit pieces — informed by the referenced project's
procedural approach, adapted to Godot's mesh/scene conventions.

## Phase 4 — World & Time (`phase/04-world`)
- T4.1 Environment placeholders (extend `tools/assetgen/props.py` with new simple
  procedural props as needed, or drop in free/CC0 pack assets — per-asset choice,
  see Phase 3 pivot note) for any rocks/flora/cottage-kit/paths not already covered
  by the existing pine/fence/crate/jar/mug/ground-tile set
- T4.2 Zone tooling (placement, MultiMesh scatter, zone schema)
- T4.3 Cottage interior + garden assembled
- T4.4 Village + Hedgerow Lanes first dressing pass
- T4.5 Time-of-day + weather-lite + clock service (Patch Day weekday math, drift hooks)

## Phase 5 — Narrative Spine (`phase/05-spine`)
- T5.1 Dialogue engine (JSON graphs, conditions, portraits, animalese voices)
- T5.2 Quest engine (schema, QuestDirector, reachability lint)
- T5.3 Magpie Log journal UI
- T5.4 Versioned saves + migration framework ("meandering migrations")
- T5.5 Settings + accessibility base (rebind, text scale, reduce-glitch, palettes)
- T5.6 Pilot NPC (the baker) proving dialogue → quest → reward end-to-end

## Phase 6 — Witchcraft I (`phase/06-witchcraft-1`)
- T6.1 Pantry inventory (labeled jars, shelf UI, bloom-filter door sprite)
- T6.2 Gathering tools (broom-sweep, picker, net, flask; respawn clocks)
- T6.3 **Kettle Logic** brewing minigame + recipes + steam-rune hints
- T6.4 Blessing & naming (named objects gain traits)
- T6.5 First three potions with world effects

## Phase 7 — Witchcraft II (`phase/07-witchcraft-2`)
- T7.1 **Chalk sigils** (stroke glyphs, if/then ward rules, lintel placement)
- T7.2 Glitch anomaly framework (types, spawn director, magpie telemetry)
- T7.3 **Mending loop** (Witch Sight diagnosis → remedy → resolution)
- T7.4 **Leaven** the sourdough companion (care sim, proto-Pattern voice)
- T7.5 Breadcrumb divination (daily fortunes seed RNG drift quests)

## Phase 8 — Village & Cast (`phase/08-village-cast`)
- T8.1 NPC framework (schedules, friendship, gifts, memory of kindness)
- T8.2 Cast assets (canonical rig, 14 villagers + kids + cats + magpies + sprites)
- T8.3 Cast wave 1 (7 NPCs, schedules, intro dialogue, one side quest each)
- T8.4 Cast wave 2 (rest of cast + glitchfauna + journal entries)
- T8.5 Village life (favor-barter ledger, noticeboard, radio broadcasts)

## Phase 9 — Act I Complete + Polish Gate 1 (`phase/09-act1`)
- T9.1 Act I main chain (8 quests: arrival → the hearth speaks)
- T9.2 Act I side content (10 side + 3 hidden)
- T9.3 Tutorialization (The Runbook as diegetic help)
- T9.4 Audio pass 1 (bus tree, stem-ready AudioDirector manifest, SFX, animalese tuning)
- T9.5 Polish gate: perf, feel, VFX v2, dev builds all platforms → **Act I playable**

## Phase 10 — Act II: Seams & Glitches (`phase/10-act2`)
- T10.1 Escalation systems (anomaly director, The Seams pocket zones, echo playback)
- T10.2 Moss Forest + Fen zones (slow-time fields)
- T10.3 Stark chains A: The Last Route · Echoes in the Wallpaper
- T10.4 Stark chains B: A Small Prayer · No Fast-Forward · Meandering Migration
- T10.5 Act II main chain (10 quests) → **Act II playable**

## Phase 11 — Act III: Consent to the Pattern (`phase/11-act3`)
- T11.1 Kindness ledger surfacing (checksum categories, Runbook ledger page)
- T11.2 Act III main chain (6 quests → the Night of Static)
- T11.3 **Checksum of the Heart** finale ceremony + ending variants
- T11.4 Credits, outro slot, epilogue world states → **story complete**

## Phase 12 — Postgame, Depth & Release (`phase/12-postgame-release`)
- T12.1 Patch Day weekly ritual (changelog on the pantry door)
- T12.2 Drift quests at scale (20+ templates, rarity, pity timers)
- T12.3 Full seasons (visuals, tables, 4 festivals)
- T12.4 NG+ echoes + hidden meta-quests (the magpies' true cache)
- T12.5 Collections & completion rewards
- T12.6 Performance & memory (pooling, LOD, web tuning)
- T12.7 Accessibility & UX audit (photosensitivity, captions, assists)
- T12.8 Localization scaffold + English proofread
- T12.9 Stability (soak runs, save fuzzing, bug bash)
- T12.10 Release v1.0.0 + post-1.0 Patch Day roadmap

---

## Status

| Phase | Branch | State |
|---|---|---|
| 0 — Foundation | `phase/00-foundation` | ✅ complete |
| 1 — Player & Camera | `phase/01-player-camera` | ✅ complete |
| 2 — Character Foundation | `phase/02-character-foundation` | ⏸️ paused (external art pivot 2026-08-09) — v1 placeholders live |
| 3 — Nature & Building Foundation | `phase/03-nature-building-foundation` | ⏸️ paused (external art pivot 2026-08-09) — v1 placeholders live |
| 4 — World & Time | `phase/04-world` | ⏭️ next up (proceeds now on placeholders, see pivot spec) |
| 5–12 | — | 📋 planned |

At each gate: suites fully green, playable artifact, docs updated.
Gate records — Phase 0: 36 pytest + 11 gdUnit. Phase 1: 44 pytest + 57 gdUnit,
Linux export boots into the sandbox glade.

## Housekeeping (small chores, none blocking)

- [ ] **One-time CI activation:** add `.github/workflows/ci.yml` on the default branch
  (copy from [`tools/ci/workflow.stub.yml`](tools/ci/workflow.stub.yml) — automation
  tokens cannot write that path). Every push then runs style + pytest + gdUnit +
  Linux/Web export builds + look-dev screenshots as downloadable artifacts.
- [ ] **Tag `v0.2.0`** after the phase merges (covers phases 0–1; per-phase tags resume
  at each future gate).
- [ ] Owner: license decision — see [LICENSES.md](LICENSES.md).
- [ ] Owner: story-bible name vetoes (village, cast, entities).
- [ ] Owner: adapted album stems, any time — the manifest slot opens in Phase 9.

## Deferred / floating

- **Music integration:** the album's adapted stems are produced by the project owner and
  drop into `content/music/manifest.json` any time after Phase 9 — the AudioDirector is
  built stem-ready with generated ambience beds as placeholders.
