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
| wren | character | witch (player) | placeholder: Seren (Meshy AI) rigged/animated body | idle/walk/run clips (no wave/stir) | `tools/assetgen/placeholders/fetch_wren_placeholder.py` | P0 | Phase 1 player avatar | placeholder (external art pending) |
| sigrid-barm | character | villager (baker) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8 cast wave 1 | planned |
| ansel-rowe | character | villager (postman) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8 cast wave 1; The Last Route | planned |
| maud-tressel | character | villager (elder) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8; Echoes in the Wallpaper | planned |
| juniper-vale | character | villager (teen) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8; A Small Prayer | planned |
| torben-ask | character | villager (forester) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8; No Fast-Forward | planned |
| greta-furrow | character | villager (farmer) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8; Meandering Migration | planned |
| ines-jarvi | character | villager (shopkeep) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8 cast wave 2 | planned |
| fenn-solder | character | villager (tinkerer) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8 cast wave 2 | planned |
| hollis-bram | character | villager (warden) | procedural | villager rig/anim contract | part_registry villager entries | P1 | Phase 8; Act II debate arc | planned |
| odell-rime | character | villager (teacher) | procedural | villager rig/anim contract | part_registry villager entries | P2 | Phase 8 cast wave 2 | planned |
| eamon-brook | character | villager (fisher) | procedural | villager rig/anim contract | part_registry villager entries | P2 | Phase 8 cast wave 2 | planned |
| tansy-mothwood | character | villager (hedge-witch) | procedural | villager rig/anim contract | part_registry villager entries | P2 | Phase 8 cast wave 2 | planned |
| pip-and-nettle | character | kids (2) | procedural | child archetype (new) | new child rig pose + part entries | P2 | Phase 8; hidden quest finders | planned |
| sal-a-manda | character | villager (traveling DJ) | procedural | villager rig/anim contract | part_registry villager entries | P2 | Phase 8; news drip cameo | planned |
| parity-and-cache | character | cats (2) | procedural | quadruped archetype (new) | new quadruped rig/anim contract | P2 | Phase 8; cat system | planned |
| clack-and-click | character | magpies (2) | procedural | bird archetype (new) | new bird rig/anim contract | P1 | journal/quest log presence from Phase 5 | planned |
| the-kindlies | character | pantry sprites (small creature) | procedural | sprite archetype (new) | new small-creature rig/anim contract | P2 | Phase 8+ pantry audit quests | planned |
| pine-tree | nature | tree | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 environment v1 | planned |
| ground-tile | nature | terrain tile | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 environment v1 | planned |
| fence | building | fence kit piece | procedural (existing assetgen prop) | n/a | tools/assetgen/props.py | P0 | Phase 4 environment v1 | planned |
| cottage-kit | building | cottage wall/roof/door kit | procedural (to design, Phase 3) | n/a | Phase 3 nature/building foundation | P0 | Phase 4 cottage interior/garden | planned |
| rocks-flora | nature | rocks + flora variety pack | procedural (to design, Phase 3) | n/a | Phase 3 nature/building foundation | P1 | Phase 4 environment v1 | planned |
| village-hall-signal-house | building | Signal House interior/exterior | procedural or handcrafted (TBD Phase 3) | n/a | Phase 3 nature/building foundation | P2 | Phase 10 Act II debate arc | planned |
