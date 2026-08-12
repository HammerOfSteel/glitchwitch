# Dialogue Engine (T5.1) — Design Spec

Date: 2026-08-12
Status: Approved (pending spec review)
Roadmap: Phase 5 — Narrative Spine, T5.1 "Dialogue engine (JSON graphs,
conditions, portraits, animalese voices)"

## 1. Goal & scope

Build the first slice of the narrative spine: a data-driven dialogue engine
capable of playing branching, condition-gated conversations, with a working
on-screen dialogue box (procedural placeholder portraits + animalese blip
audio), and prove the whole path end-to-end by wiring a demo conversation to
the existing demo villager in `cottage_garden`.

**Explicitly out of scope for this slice** (deferred to later Phase 5 tasks):
- Quest engine / quest state (T5.2) — dialogue can *set flags*, but nothing
  consumes them as quest state yet.
- Persistent/versioned save data (T5.4) — dialogue flags are in-memory only
  and reset on game restart.
- Real portrait art (paused per the external-asset pivot) — placeholder
  procedural portraits only.
- Menu-navigation input scheme (gamepad/keyboard choice cursor) — choices are
  selected via mouse click or number keys for now.
- Authoring tools (visual node-graph editor) — dialogue is hand-authored JSON.
- The pilot NPC / full quest→reward loop (T5.6) — this slice only proves a
  single demo conversation on the existing placeholder villager.

## 2. Data format: JSON dialogue graphs

Dialogue lives as JSON files under `res://data/dialogue/`. Example
(`res://data/dialogue/demo_villager.json`):

```json
{
  "start": "greet",
  "nodes": {
    "greet": {
      "speaker": "Villager",
      "text": "Oh! You're the one from the cottage.",
      "next": "ask_weather"
    },
    "ask_weather": {
      "speaker": "Villager",
      "text": "Fancy some small talk?",
      "choices": [
        { "text": "Sure.", "next": "chat", "set_flag": "talked_to_villager" },
        { "text": "Not now.", "next": null }
      ]
    },
    "chat": {
      "speaker": "Villager",
      "text": "The moss has been doing well this week.",
      "condition": { "flag": "talked_to_villager", "equals": false },
      "next": null
    }
  }
}
```

Node fields:
- `speaker` (String, required) — display name.
- `text` (String, required) — the line shown/typed out.
- `next` (String or null, optional) — id of the following node; `null` or
  absent ends the conversation.
- `choices` (Array, optional) — mutually exclusive with `next`. Each entry:
  `text` (String, required), `next` (String or null, required),
  `set_flag` (String, optional — sets `flags[set_flag] = true` when chosen).
- `condition` (Object, optional) — `{"flag": String, "equals": bool}`. A node
  reached with a condition that evaluates false is treated as if `next` were
  `null` (conversation ends there) — this is the entire condition language
  for this slice; richer boolean composition (`any`/`all`/`not`) is
  deliberately deferred until a real content need demonstrates it's
  necessary (YAGNI).

`DialogueGraph` (`src/core/dialogue_graph.gd`, `class_name DialogueGraph`,
extends `RefCounted`) loads and validates this JSON:
- `static func load_from_file(path: String) -> DialogueGraph`
- Validates: `start` exists in `nodes`; every `next`/`choices[].next` either
  is `null` or refers to an existing node id; every node has non-empty
  `speaker`/`text`; a node cannot have both `next` and `choices`. Raises
  (via `push_error` + returns `null`) on any violation — mirrors the
  fail-loud spirit of `character_validate.py` but scaled to this format's
  much smaller surface.

## 3. Runtime: `DialogueRunner` autoload

New autoload singleton, following the existing `GameClockService`/
`GameClock` naming split (script `class_name` differs from the autoload
name to avoid Godot's self-collision restriction):

- Script: `src/core/dialogue_runner.gd`, `class_name DialogueRunnerService`
- Registered in `project.godot` as autoload `DialogueRunner`

State:
- `flags: Dictionary` (`String -> bool`), in-memory only, persists for the
  process lifetime (not saved/loaded — see scope note above).
- `_graph: DialogueGraph`, `_current_node_id: String`, both null/empty when
  no conversation is active.

Signals:
- `line_shown(speaker: String, text: String)`
- `choices_shown(speaker: String, text: String, options: Array[String])`
- `ended`

API:
- `start(graph: DialogueGraph) -> void` — sets `_graph`, jumps to
  `graph.start`, then calls the internal node-resolution step below.
- `advance() -> void` — no-op if the current node has `choices`; otherwise
  follows `next` (or ends if `next` is null/absent) and resolves the next
  node.
- `choose(index: int) -> void` — no-op if the current node doesn't have
  `choices` or `index` is out of range; otherwise applies `set_flag` (if
  present) then follows that choice's `next` and resolves.
- `is_active() -> bool` — true whenever a conversation is in progress; used
  by `Player` to suppress movement/interaction input for the duration.

Internal node resolution (shared by `start`/`advance`/`choose`): given a
target node id, if it's null/empty, emit `ended` and clear `_graph`/
`_current_node_id`. Otherwise look up the node; if it has a `condition` that
evaluates false, treat it exactly as if `next` were null (ends there — this
keeps the condition model trivial: a gated node simply doesn't play). If it
has `choices`, emit `choices_shown`; otherwise emit `line_shown`.

## 4. UI: `DialogueBox`

New scene: `src/ui/dialogue_box/dialogue_box.tscn` +
`src/ui/dialogue_box/dialogue_box.gd` (`class_name DialogueBox`, extends
`Control`), instanced once as a child of `Main`'s existing `UI` `CanvasLayer`
in `src/main/main.tscn` (alongside the pre-existing `Banner`), anchored to
the bottom of the screen (same general area as `InteractPrompt`, which is
hidden while dialogue is active to avoid overlap).

Layout (bottom panel, hidden by default):
- A small circular portrait placeholder — a `Panel`/`ColorRect` styled
  circular via a `StyleBoxFlat` with `corner_radius_*` set, containing a
  `Label` showing the speaker's first initial. Color is derived
  deterministically by hashing the speaker name string into a hue (no art
  dependency, no new per-NPC config needed).
- Speaker name `Label` + dialogue text `Label` (or `RichTextLabel` for
  potential future styling, kept plain for now).
- A `VBoxContainer` of `Button`s for choices, populated on
  `choices_shown`, cleared/hidden otherwise.

Behavior:
- Connects to `DialogueRunner`'s `line_shown`/`choices_shown`/`ended`
  signals in `_ready()`.
  - `line_shown`: show the box, set portrait/name/text, hide choice
    buttons, start the typewriter reveal (see §5).
  - `choices_shown`: show the box, set portrait/name/text (the prompt
    line), populate one `Button` per option, hide on button `pressed`
    calling `DialogueRunner.choose(i)`.
  - `ended`: hide the box.
- Input: while the box is visible and no choices are shown, pressing the
  existing `interact` action (bound to `E`) calls
  `DialogueRunner.advance()` — reuses the interact key already used to open
  the conversation, since "confirm" and "talk" are the same cozy verb here.
  Choice buttons are selected by mouse click, or by pressing number keys
  1–9 (mapped positionally, not a new InputMap action — read via
  `Input.is_key_pressed`/`_unhandled_input` on `KEY_1`..`KEY_9`) — deferred
  proper menu-navigation input scheme per the scope note above.

## 5. Animalese audio

New pure-ish helper: `src/core/animalese.gd`, `class_name Animalese`,
extends `RefCounted` (no autoload needed — it's a stateless generator, same
shape as `TimeOfDayCurve`).

- `static func blip_for_seed(seed: int) -> AudioStreamWAV` — generates a
  short (~60ms), procedurally synthesized sine-burst blip as 16-bit PCM
  mono at a sample rate of 22050Hz, pitched deterministically from `seed`
  (map `seed`'s low bits to a frequency in a pleasant "small critter" range,
  e.g. 180–420 Hz, via the same `RandomNumberGenerator.seed = seed` pattern
  used elsewhere in this codebase — e.g. `VillagerDna.random()`). Cached
  per seed (a small `Dictionary[int, AudioStreamWAV]` inside `Animalese`) so
  repeated calls for the same speaker don't re-synthesize every keystroke.
- `DialogueBox` reveals `text` one character at a time (typewriter effect,
  fixed interval e.g. 30ms/char) via a `Timer`, and for each revealed
  non-whitespace/non-punctuation character, plays
  `Animalese.blip_for_seed(current_speaker_seed)` through a single
  `AudioStreamPlayer` child (retriggering `play()` — brief overlaps are fine
  and match the genre's chattery feel).
- Speaker→seed mapping for the demo: the demo villager's dialogue trigger
  passes its own `VillagerDna.seed` through to whatever mechanism hands the
  speaker's voice seed to `DialogueBox` (simplest option: `DialogueRunner`
  gains a parallel `voice_seed: int` set alongside `start(graph, voice_seed)`,
  defaulting to a fixed constant if omitted, so non-NPC/system dialogue
  still has *a* voice). This reuses the existing per-NPC determinism
  convention rather than inventing a new voice-profile system.

## 6. Demo integration

- `cottage_garden.tscn`: add an `Interactable` node as a child of
  `DemoVillager` (verb `"Talk"`, `display_name` = the villager's
  `VillagerDna.name`, matching `Interactable`'s existing
  `prompt_text()` convention already used elsewhere).
- `cottage_garden.gd`: after `_add_demo_villager()` builds the villager,
  connect the new `Interactable`'s `interacted` signal to a small handler
  that calls
  `DialogueRunner.start(DialogueGraph.load_from_file("res://data/dialogue/demo_villager.json"), villager_dna.seed)`.
- `Player`: while `DialogueRunner.is_active()` is true, `input_enabled` is
  set to `false` (reusing the existing export, no new player code beyond
  one signal connection: `DialogueRunner.line_shown`/`choices_shown` sets
  `input_enabled = false` the first time, `ended` sets it back to `true`).
  Concretely, `Player._ready()` connects `DialogueRunner.ended` to a new
  tiny handler; the initial `false` is set directly by whatever triggers
  `DialogueRunner.start()` (the villager's interact handler pauses the
  player itself, since it already has a reference to it via the `interact()`
  call's `by: Node` argument) — this avoids `Player` needing to poll
  `is_active()` every frame.
- `demo_villager.json` content: a short 3-4 line conversation exercising a
  linear line, a branching choice, a flag `set_flag`, and a `condition`-
  gated node (so re-talking to the villager after choosing "Sure" shows a
  different follow-up) — directly demonstrating every mechanic in one
  place.

## 7. Testing

New/updated gdUnit test files, following this codebase's existing
conventions (`tests/unit/test_*.gd`, `scene_runner` for scene-level tests):

- `test_dialogue_graph.gd` — loads a small fixture JSON, asserts
  `start`/nodes/choices parse correctly; asserts validation fails (returns
  `null`) for: missing `start` node, dangling `next` reference, a node with
  both `next` and `choices`, a node missing `speaker`/`text`.
- `test_dialogue_runner.gd` — linear `start`→`advance`→`ended` sequence
  emits the right signals in order; a `choices_shown` conversation with
  `choose(i)` correctly sets the flag and follows that branch; a
  `condition`-gated node is skipped (ends immediately) when its flag isn't
  set, and plays when it is; `is_active()` reflects state correctly across
  the whole lifecycle. Uses an `after_test()` hook to reset
  `DialogueRunner.flags = {}` between tests (same established pattern as
  `GameClock.debug_override_hour`, since this is another shared-autoload
  test-isolation concern).
- `test_animalese.gd` — `blip_for_seed()` is deterministic (same seed twice
  → identical PCM data), different seeds produce different pitches
  (frequency content differs — check via zero-crossing count or similar
  simple signal property, not exact sample comparison), and the per-seed
  cache returns the same `AudioStreamWAV` instance on repeated calls.
- `test_cottage_garden.gd` — append a test asserting the demo villager has
  a child `Interactable` with `verb == "Talk"` and that its `interacted`
  signal is connected to something that ends up calling
  `DialogueRunner.start` (practically: trigger `interact()` on it and
  assert `DialogueRunner.is_active()` becomes true, then assert it's false
  again after driving `DialogueRunner` to `ended` via `advance()` calls
  through the demo script's actual node count) — a real integration check,
  not just a signal-connection existence check.

## 8. Risks / open questions carried forward (not blocking this slice)

- The number-key/mouse-click choice selection is a known placeholder;
  proper gamepad-friendly menu navigation is expected to land alongside
  T5.5 (settings/accessibility) or whenever the first real multi-choice
  quest content demands it.
- `DialogueRunner.flags` being in-memory-only means talking to the demo
  villager twice in the same play session will correctly show the gated
  follow-up line, but restarting the game resets that — this is the
  explicitly accepted trade-off pending T5.4.
