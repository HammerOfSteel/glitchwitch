# Glitch Witch — Roadmap

Twelve phases, 0 → 11. Every phase: its own branch, per-task pushes, per-subtask commits,
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
- T1.5 Witch avatar: CC0 rigged base restyled, animation tree

## Phase 2 — World & Time (`phase/02-world`)
- T2.1 Environment generators v1 (trees, rocks, flora, fences, cottage kit, paths)
- T2.2 Zone tooling (placement, MultiMesh scatter, zone schema)
- T2.3 Cottage interior + garden assembled
- T2.4 Village + Hedgerow Lanes first dressing pass
- T2.5 Time-of-day + weather-lite + clock service (Patch Day weekday math, drift hooks)

## Phase 3 — Narrative Spine (`phase/03-spine`)
- T3.1 Dialogue engine (JSON graphs, conditions, portraits, animalese voices)
- T3.2 Quest engine (schema, QuestDirector, reachability lint)
- T3.3 Magpie Log journal UI
- T3.4 Versioned saves + migration framework ("meandering migrations")
- T3.5 Settings + accessibility base (rebind, text scale, reduce-glitch, palettes)
- T3.6 Pilot NPC (the baker) proving dialogue → quest → reward end-to-end

## Phase 4 — Witchcraft I (`phase/04-witchcraft-1`)
- T4.1 Pantry inventory (labeled jars, shelf UI, bloom-filter door sprite)
- T4.2 Gathering tools (broom-sweep, picker, net, flask; respawn clocks)
- T4.3 **Kettle Logic** brewing minigame + recipes + steam-rune hints
- T4.4 Blessing & naming (named objects gain traits)
- T4.5 First three potions with world effects

## Phase 5 — Witchcraft II (`phase/05-witchcraft-2`)
- T5.1 **Chalk sigils** (stroke glyphs, if/then ward rules, lintel placement)
- T5.2 Glitch anomaly framework (types, spawn director, magpie telemetry)
- T5.3 **Mending loop** (Witch Sight diagnosis → remedy → resolution)
- T5.4 **Leaven** the sourdough companion (care sim, proto-Pattern voice)
- T5.5 Breadcrumb divination (daily fortunes seed RNG drift quests)

## Phase 6 — Village & Cast (`phase/06-village-cast`)
- T6.1 NPC framework (schedules, friendship, gifts, memory of kindness)
- T6.2 Cast assets (canonical rig, 14 villagers + kids + cats + magpies + sprites)
- T6.3 Cast wave 1 (7 NPCs, schedules, intro dialogue, one side quest each)
- T6.4 Cast wave 2 (rest of cast + glitchfauna + journal entries)
- T6.5 Village life (favor-barter ledger, noticeboard, radio broadcasts)

## Phase 7 — Act I Complete + Polish Gate 1 (`phase/07-act1`)
- T7.1 Act I main chain (8 quests: arrival → the hearth speaks)
- T7.2 Act I side content (10 side + 3 hidden)
- T7.3 Tutorialization (The Runbook as diegetic help)
- T7.4 Audio pass 1 (bus tree, stem-ready AudioDirector manifest, SFX, animalese tuning)
- T7.5 Polish gate: perf, feel, VFX v2, dev builds all platforms → **Act I playable**

## Phase 8 — Act II: Seams & Glitches (`phase/08-act2`)
- T8.1 Escalation systems (anomaly director, The Seams pocket zones, echo playback)
- T8.2 Moss Forest + Fen zones (slow-time fields)
- T8.3 Stark chains A: The Last Route · Echoes in the Wallpaper
- T8.4 Stark chains B: A Small Prayer · No Fast-Forward · Meandering Migration
- T8.5 Act II main chain (10 quests) → **Act II playable**

## Phase 9 — Act III: Consent to the Pattern (`phase/09-act3`)
- T9.1 Kindness ledger surfacing (checksum categories, Runbook ledger page)
- T9.2 Act III main chain (6 quests → the Night of Static)
- T9.3 **Checksum of the Heart** finale ceremony + ending variants
- T9.4 Credits, outro slot, epilogue world states → **story complete**

## Phase 10 — Postgame & Depth (`phase/10-postgame`)
- T10.1 Patch Day weekly ritual (changelog on the pantry door)
- T10.2 Drift quests at scale (20+ templates, rarity, pity timers)
- T10.3 Full seasons (visuals, tables, 4 festivals)
- T10.4 NG+ echoes + hidden meta-quests (the magpies' true cache)
- T10.5 Collections & completion rewards

## Phase 11 — Release (`phase/11-release`)
- T11.1 Performance & memory (pooling, LOD, web tuning)
- T11.2 Accessibility & UX audit (photosensitivity, captions, assists)
- T11.3 Localization scaffold + English proofread
- T11.4 Stability (soak runs, save fuzzing, bug bash)
- T11.5 Release v1.0.0 + post-1.0 Patch Day roadmap

---

## Status

| Phase | Branch | State |
|---|---|---|
| 0 — Foundation | `phase/00-foundation` | 🔨 in progress |
| 1–11 | — | 📋 planned |

## Deferred / floating

- **Music integration:** the album's adapted stems are produced by the project owner and
  drop into `content/music/manifest.json` any time after Phase 7 — the AudioDirector is
  built stem-ready with generated ambience beds as placeholders.
- **License decision** (owner): see [LICENSES.md](LICENSES.md).
- **Name vetoes** (owner): village, cast, and entity names proposed in the story bible.
