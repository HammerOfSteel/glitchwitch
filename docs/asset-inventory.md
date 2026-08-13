# Asset Inventory Matrix

Tracks every known-needed character/nature/building asset so future asset phases
have a backlog instead of guesswork. Populated per
`docs/superpowers/specs/2026-08-08-character-procedural-pipeline-design.md`.

**Sourcing pivot (2026-08-09):** see
`docs/superpowers/specs/2026-08-09-external-asset-pivot-design.md`. Rather than an
in-house procedural pipeline generating every row below, the project owner will
source final character art via Meshy AI (or similar) and final nature/building art
via free/CC0 low-poly modular packs, as time allows per asset. Every "planned"
character/nature/building row in this table is unblocked from that sourcing
work by a placeholder for now — either the existing v1 procedural output
(`tools/assetgen/character_gen.py`, `tools/assetgen/props.py`) or, for Wren, a
rigged/animated Seren (Meshy AI) placeholder body. "Procedural" in the
Rig/Anim/Dependencies columns below still describes the *placeholder's* origin,
not a commitment to keep building it procedurally in-house.

| Asset ID | Category | Subtype | Procedural/Handcrafted | Rig/Anim | Dependencies | Priority | Gameplay dependency | Status |
|---|---|---|---|---|---|---|---|---|
| wren | character | witch (player) | sourced: Meshy AI dressed/rigged/animated body | idle/walk/run clips (no wave/stir yet — not in Meshy's stock anim library) | `tools/assetgen/meshy_import/import_wren_meshy.py` | P0 | Phase 1 player avatar | sourced (Meshy AI) |
| sigrid-barm | character | villager (baker) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P1 | Phase 8 cast wave 1 | planned |
| ansel-rowe | character | villager (postman) | sourced: Meshy AI rigged/animated body | idle/walk/run clips | `tools/assetgen/meshy_import/import_meshy_rigged_npc.py --name ansel_rowe`; `src/characters/npc/rigged_npc.gd` | P1 | Phase 8 cast wave 1; The Last Route; cottage garden background NPC (Ansel patrols a fixed loop) | sourced (Meshy AI) |
| maud-tressel | character | villager (elder) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P1 | Phase 8; Echoes in the Wallpaper | planned |
| juniper-vale | character | villager (teen) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P1 | Phase 8; A Small Prayer | planned |
| torben-ask | character | villager (forester) | sourced: Meshy AI rigged/animated body | idle/walk/run clips | `tools/assetgen/meshy_import/import_meshy_rigged_npc.py --name torben_ask`; `src/characters/npc/rigged_npc.gd` | P1 | Phase 8; No Fast-Forward; cottage garden background NPC (stationary) | sourced (Meshy AI) |
| greta-furrow | character | villager (farmer) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P1 | Phase 8; Meandering Migration | planned |
| ines-jarvi | character | villager (shopkeep) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P1 | Phase 8 cast wave 2 | planned |
| fenn-solder | character | villager (tinkerer) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P1 | Phase 8 cast wave 2 | planned |
| hollis-bram | character | villager (warden) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P1 | Phase 8; Act II debate arc | planned |
| odell-rime | character | villager (teacher) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P2 | Phase 8 cast wave 2 | planned |
| eamon-brook | character | villager (fisher) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P2 | Phase 8 cast wave 2 | planned |
| tansy-mothwood | character | villager (hedge-witch) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P2 | Phase 8 cast wave 2 | planned |
| pip-and-nettle | character | kids (2) | procedural | child archetype (new) | new child rig pose + part entries | P2 | Phase 8; hidden quest finders | planned |
| sal-a-manda | character | villager (traveling DJ) | procedural | villager rig/anim contract | src/characters/villager/ (VillagerFactory) | P2 | Phase 8; news drip cameo | planned |
| parity-and-cache | character | cats (2) | procedural | quadruped archetype (new) | new quadruped rig/anim contract | P2 | Phase 8; cat system | planned |
| clack-and-click | character | magpies (2) | procedural | bird archetype (new) | new bird rig/anim contract | P1 | journal/quest log presence from Phase 5 | planned |
| the-kindlies | character | pantry sprites (small creature) | procedural | sprite archetype (new) | new small-creature rig/anim contract | P2 | Phase 8+ pantry audit quests | planned |
| villager-rig-system | character | procedural rig system (not a specific villager) | procedural (runtime GDScript, not baked GLB) | VillagerRig joint hierarchy + VillagerAnimator sine-driven idle/walk | src/characters/villager/ (HumanSynth, VillagerRig, VillagerAnimator, VillagerFactory) | P0 | Phase 5 villager rig system; demo villager in cottage_garden | done |
| pine-tree | nature | tree | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 environment v1 | planned |
| ground-tile | nature | terrain tile | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 environment v1 | planned |
| fence | building | fence kit piece | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 environment v1 | planned |
| cottage-kit | building | cottage wall/roof/door kit | procedural placeholder — see cottage_wall/cottage_corner/cottage_roof rows | n/a | tools/assetgen/props.py | P0 | Phase 4 cottage interior/garden | done (v1 placeholder, proven in `cottage_garden` zone) |
| rocks-flora | nature | rocks + flora variety pack | procedural placeholder — see rock/grass-tuft/flower rows | n/a | tools/assetgen/props.py | P1 | Phase 4 environment v1 | done (v1 placeholder, proven in `cottage_garden` zone) |
| village-hall-signal-house | building | Signal House interior/exterior | procedural or handcrafted (TBD Phase 3) | n/a | Phase 3 nature/building foundation | P2 | Phase 10 Act II debate arc | planned |
| cottage-wall | building | cottage wall kit piece (hero prop) | procedural placeholder | n/a | tools/assetgen/props.py (`build_cottage_wall`) | P0 | Phase 4 cottage interior/garden | done |
| cottage-corner | building | cottage corner post kit piece (hero prop) | procedural placeholder | n/a | tools/assetgen/props.py (`build_cottage_corner`) | P0 | Phase 4 cottage interior/garden | done |
| cottage-roof | building | cottage flat roof kit piece (hero prop) | procedural placeholder | n/a | tools/assetgen/props.py (`build_cottage_roof`) | P0 | Phase 4 cottage interior/garden | done |
| cottage-facade | building | two-story stone cottage exterior (hero prop): coursed-stone walls with a baked procedural masonry texture, quoins, string course, pitched slate roof, chimney+pot, 4 sash windows, cottage-green door | procedural placeholder — supersedes the cottage-wall/cottage-corner/cottage-roof kit assembly as the `cottage_garden` zone's exterior building | n/a | tools/assetgen/props.py (`build_cottage_facade`), palette.py (`stone_wall` baked texture) | P0 | Phase 4 cottage interior/garden | done |
| planter | nature | garden planter box | procedural placeholder | n/a | tools/assetgen/props.py (`build_planter`) | P1 | Phase 4 environment v1 | done |
| well | building | small stone well | procedural placeholder | n/a | tools/assetgen/props.py (`build_well`) | P1 | Phase 4 environment v1 | done |
| rock | nature | scatter/discrete rock | procedural placeholder | n/a | tools/assetgen/props.py (`build_rock`) | P1 | Phase 4 environment v1 | done |
| grass-tuft | nature | scatter grass patch prop | procedural placeholder | n/a | tools/assetgen/props.py (`build_grass_tuft`) | P1 | Phase 4 environment v1 | done |
| flower | nature | scatter flower prop | procedural placeholder | n/a | tools/assetgen/props.py (`build_flower`) | P1 | Phase 4 environment v1 | done |
| interior-wall | building | interior wall kit piece | procedural placeholder | n/a | tools/assetgen/props.py (`build_interior_wall`) | P0 | Phase 4 cottage interior | done |
| interior-floor | building | interior floor tile kit piece | procedural placeholder | n/a | tools/assetgen/props.py (`build_interior_floor`) | P0 | Phase 4 cottage interior | done |
| hearth | building | stone hearth (hero prop) | procedural placeholder | n/a | tools/assetgen/props.py (`build_hearth`) | P0 | Phase 4 cottage interior | done |
| table | building | wood dining table | procedural placeholder | n/a | tools/assetgen/props.py (`build_table`) | P0 | Phase 4 cottage interior | done |
| chair | building | wood chair | procedural placeholder | n/a | tools/assetgen/props.py (`build_chair`) | P0 | Phase 4 cottage interior | done |
| shelf | building | wall shelf with boards | procedural placeholder | n/a | tools/assetgen/props.py (`build_shelf`) | P0 | Phase 4 cottage interior | done |
| rug | building | floor rug decal quad | procedural placeholder | n/a | tools/assetgen/props.py (`build_rug`) | P0 | Phase 4 cottage interior | done |
| bed | building | alcove bed (hero prop) | procedural placeholder | n/a | tools/assetgen/props.py (`build_bed`) | P0 | Phase 4 cottage interior | done |
| hedge | nature | moss hedge lane segment | procedural placeholder | n/a | tools/assetgen/props.py (`build_hedge`) | P0 | Phase 4 hedgerow lane | done |
| stone-stile | building | stone stepover crossing | procedural placeholder | n/a | tools/assetgen/props.py (`build_stone_stile`) | P0 | Phase 4 hedgerow lane | done |
| lane-path | building | clay/dirt lane path tile | procedural placeholder | n/a | tools/assetgen/props.py (`build_lane_path`) | P0 | Phase 4 hedgerow lane | done |
| signpost | building | wood wayfinding signpost | procedural placeholder | n/a | tools/assetgen/props.py (`build_signpost`) | P0 | Phase 4 hedgerow lane | done |
