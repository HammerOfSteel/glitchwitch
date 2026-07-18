# Contributing — the working ritual

This project is built with a strict, calm discipline. Like the witch's craft: small
gestures, correctly ordered, verified by kettle-light. These rules apply to every
contributor, human or agent.

## The branching ritual

- **One phase, one branch.** Every phase from [ROADMAP.md](ROADMAP.md) gets a branch
  named `phase/NN-short-name` (e.g. `phase/00-foundation`), cut from `main`.
- **One task, one push.** Work inside a phase is divided into tasks (`T0.1`, `T0.2`, ...).
  A task is pushed when it is complete — and a task is only complete **with its tests**.
- **One subtask, one commit.** Every commit is a coherent subtask with a
  [conventional commit](https://www.conventionalcommits.org/) message.
- **Phase gate.** A phase merges to `main` via PR only when the **entire** test suite is
  green in CI and the phase produces a playable/inspectable artifact. Each merged phase
  is tagged `v0.<phase+1>.0` (Phase 0 → `v0.1.0`). Release is `v1.0.0`.

## Commit style

```
<type>(<scope>): <imperative summary>

types:  feat · fix · test · docs · chore · ci · refactor · perf
scopes: repo · project · tooling · assetgen · lookdev · player · camera · world ·
        time · dialogue · quests · journal · saves · settings · inventory ·
        gathering · brewing · sigils · anomaly · mending · leaven · divination ·
        npc · village · audio · act1 · act2 · act3 · postgame · release
```

Examples:

```
feat(brewing): add stir-pattern evaluation to Kettle Logic minigame
test(quests): property tests for quest state machine transitions
docs(story): outline the No Fast-Forward grief chain
```

## Tests are part of the definition of done

- Every task lands with tests. No exceptions — a task without tests is a draft.
- Suites:
  - `tests/python/` — pytest for tooling, asset determinism, content schemas, repo lint.
  - `tests/unit/` — gdUnit4 for game logic and scene smoke tests (run headless).
- Phase gate = **all** tests green (not just the new ones), CI passing on the phase branch.

Run everything locally:

```sh
python3 -m pytest tests/python -q
.tooling/godot --headless --path . --import
.tooling/godot --headless --path . -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit
```

## Code style

- **GDScript:** strict typing everywhere (`var x: int`, typed funcs), `snake_case`
  filenames, one class per file, `class_name` for reusable types. `gdlint`/`gdformat`
  (gdtoolkit) must pass — CI enforces both.
- **Python:** 3.9-compatible, stdlib-only for `tools/assetgen` core (no pip deps in the
  asset pipeline — determinism and portability beat convenience). pytest for tests.
- **Content is data.** Quests, dialogue, recipes, schedules live in `content/` as JSON
  validated by schemas and content-lint tests. Systems read data; they do not hardcode it.
- **No binaries in the repo.** Generated assets are rebuilt (`tools/assetgen`), third-party
  assets and addons are fetched at pinned versions (`tools/bootstrap.py`). If a binary
  seems unavoidable, it goes through a design discussion first.

## Design guardrails

- Read [docs/design-bible.md](docs/design-bible.md) before adding visuals or systems, and
  [docs/story-bible.md](docs/story-bible.md) before writing characters or quests.
- Stark-subject quest chains follow the care guidelines in the story bible: content
  notes, off-ramps, hope without erasure. Cozy is the default register.
- Accessibility is a feature, not a phase: reduce-glitch mode, rebindable input, and
  readable text ship with the systems that need them.

## The kindly checklist (before every push)

1. Does it run? (`--import` clean, no script errors)
2. Do all tests pass, old and new?
3. Is every commit one subtask with a conventional message?
4. Is new content data-driven and schema-valid?
5. Would the design bible recognize this as Glitch Witch?

*Trailing fears trimmed, tabs to spaces — verify vibes at a human pace.*
