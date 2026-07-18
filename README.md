# Glitch Witch

[![ci](https://github.com/HammerOfSteel/glitchwitch/actions/workflows/ci.yml/badge.svg)](https://github.com/HammerOfSteel/glitchwitch/actions/workflows/ci.yml)

A cozy low-poly 3D RPG about debugging a small world with kindness — set in 202X, at the very edge of the singularity.

> Salt and star, thread and flame,
> time may stutter, love stays the same.

You are **Wren**, a young hearth-witch inheriting Great-Aunt Maren's cottage in **Mosslane Hollow** — a hedge-country village mostly off the grid, while the outside world hums with news of something waking in the networks. In the Hollow it surfaces early, and small: the kettle whistles twice in the same breath, a blackbird repeats its flight, a shadow lags behind its cat.

Your grimoire calls these *seams*. Your job is not to fight them. Your job is to put the kettle on.

**Glitch Witch** is played in the key of [Little Witch in the Woods](https://littlewitchinthewoods.wiki.gg/): gather ingredients, brew in the cauldron, befriend the village, unlock the map with your craft — woven through a chaptered main story, dense side quests, hidden quests, and daily RNG "drift" quests. Wholesome by default, and unafraid of the stark stuff: automation taking a postman's route, grief that wants a rollback that doesn't exist, a teenager's anxiety at a future being rewritten mid-sentence.

The game is built from the album [**glitchwitch** by Dancing Salamanders](https://www.dancingsalamanders.com/music/glitchwitch) — every track is a system or a quest chain, and the album's three acts are the game's three acts: *house as cosmos*, *seams & glitches*, *consent to the pattern*.

Maybe we're simulated, maybe we're storied — either way, **love is the runtime**.

## Status

🚶‍♀️ **Phase 1 — Player & Camera** built (Wren walks!); Phase 0 merged-as-built. See [ROADMAP.md](ROADMAP.md).

| | |
|---|---|
| Engine | Godot 4.7.1-stable (pinned in `.godot-version`) |
| Renderer | GL Compatibility (toy-render look, web-friendly) |
| Language | GDScript (strict typing) + Python 3.9+ for tooling |
| Camera | Third person, with first-person **Witch Sight** toggle |
| Assets | Code-first: procedural meshes, generated palettes, CC0 rigged characters restyled |
| Tests | gdUnit4 (game) + pytest (tools), green gate per phase |

## Quickstart

Requirements: Python 3.9+, Godot 4.7.1 (or let the bootstrap fetch it), internet for first-time setup.

```sh
# 1. Fetch pinned tooling (gdUnit4 addon, optionally the Godot editor binary)
python3 tools/bootstrap.py --all

# 2. Generate all procedural assets (meshes, palettes) into assets/generated/
python3 -m tools.assetgen.build

# 3. Run the test suites
python3 -m pytest tests/python -q          # tooling + content tests
.tooling/godot --headless --path . --import
.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit

# 4. Play / open in editor
.tooling/godot --path .
```

`make setup assets test` wraps the same steps where `make` is available.

> **Note:** generated assets and downloaded addons are intentionally **not** committed.
> The repo is text-only; everything binary is reproduced deterministically from code
> (`tools/assetgen`) or fetched at pinned versions (`tools/bootstrap.py`). Run steps 1–2
> after every fresh clone.

## Repository layout

```
src/            GDScript & scenes (main, core, shaders, lookdev, ...)
assets/         generated/ (build output, gitignored) · thirdparty/ (pinned fetches, gitignored)
content/        data-driven game content: quests, dialogue, recipes, schedules (JSON + schemas)
docs/           design-bible.md · story-bible.md
tests/          unit/ (gdUnit4) · python/ (pytest)
tools/          assetgen/ (procedural asset pipeline) · bootstrap.py (pinned fetches)
```

## CI (one-time setup)

CI runs on GitHub Actions. Because automation tokens cannot write inside
`.github/workflows/`, the workflow file is added **once, manually**: copy
[`tools/ci/workflow.stub.yml`](tools/ci/workflow.stub.yml) to
`.github/workflows/ci.yml` and commit. The stub is static by design — all CI
logic lives in [`tools/ci/run.sh`](tools/ci/run.sh), which evolves with the
project without ever touching the workflow file again. Jobs: `tools`
(pytest + GDScript style), `godot` (headless gdUnit4 suite), `export`
(Linux + Web smoke builds, uploaded as artifacts).

## Contributing & workflow

Development follows a strict ritual — one branch per phase, one push per task, one commit
per subtask, tests with every task, and a fully green suite before a phase merges.
See [CONTRIBUTING.md](CONTRIBUTING.md). The full plan lives in [ROADMAP.md](ROADMAP.md),
the aesthetics in [docs/design-bible.md](docs/design-bible.md), and the world in
[docs/story-bible.md](docs/story-bible.md).

## Credits

- Concept, music, and world: [Dancing Salamanders](https://www.dancingsalamanders.com/) — album *glitchwitch*
- Built with [Godot Engine](https://godotengine.org/) (MIT)
- Testing via [gdUnit4](https://github.com/godot-gdunit-labs/gdUnit4) (MIT), fetched at a pinned version
- Third-party CC0 assets will be listed in [LICENSES.md](LICENSES.md) as they are adopted

Licensing is documented in [LICENSES.md](LICENSES.md).
