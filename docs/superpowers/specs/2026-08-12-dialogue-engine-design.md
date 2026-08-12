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
      "condition": { "flag": "talked_to_villager", "equals": true },
      "next": "chat_repeat",
      "else": "ask_weather"
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
      "next": null
    },
    "chat_repeat": {
      "speaker": "Villager",
      "text": "Back again? The moss is still doing wonderfully.",
      "next": null
    }
  }
}
```

Walking this example: the first time the player talks, `talked_to_villager`
is unset, so `greet`'s condition (`equals: true`) is false and the runner
follows `else` into `ask_weather`; choosing "Sure." sets the flag and plays
`chat`. The *next* time the player talks, `greet`'s condition is now true, so
the runner follows `next` straight to `chat_repeat`, skipping the question
entirely — this is what demonstrates conditions, `else`-fallback, choices,
and flag-setting all in one small graph, and is also the mechanism for
"re-talking shows a different follow-up" referenced in §6.

Node fields:
- `speaker` (String, required) — display name.
- `text` (String, required) — the line shown/typed out.
- `next` (String or null, optional) — id of the following node; `null` or
  absent ends the conversation. Mutually exclusive with `choices`.
- `choices` (Array, optional) — mutually exclusive with `next`. Each entry:
  `text` (String, required), `next` (String or null, required),
  `set_flag` (String, optional — sets `flags[set_flag] = true` when chosen).
- `condition` (Object, optional) — `{"flag": String, "equals": bool}`.
- `else` (String or null, optional) — only meaningful alongside `condition`.

Condition/else semantics (the entire condition language for this slice;
richer boolean composition — `any`/`all`/`not` — is deliberately deferred
until real content demonstrates a need, per YAGNI): a node with no
`condition` always proceeds via its `next`/`choices` as normal. A node
*with* a `condition` evaluates it against `flags` (a flag absent from
`flags` counts as `false`); if it evaluates true, the node proceeds
normally via `next`/`choices`; if false, the runner follows `else` instead
(recursing into that node) — or, if `else` is absent, ends the conversation
there (equivalent to `next: null`).

`DialogueGraph` (`src/core/dialogue_graph.gd`, `class_name DialogueGraph`,
extends `RefCounted`) loads and validates this JSON:
- `static func load_from_file(path: String) -> DialogueGraph`
- Validates: `start` exists in `nodes`; every `next`/`else`/`choices[].next`
  either is `null` or refers to an existing node id; every node has
  non-empty `speaker`/`text`; a node cannot have both `next` and `choices`.
  Raises (via `push_error` + returns `null`) on any violation — mirrors the
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
- `start(graph: DialogueGraph, voice_seed: int = 0) -> void` — sets
  `_graph` and `_voice_seed`, jumps to `graph.start`, then calls the
  internal node-resolution step below. `voice_seed` drives `Animalese`
  (see §5); the default lets non-NPC/system dialogue still have *a* voice
  without every caller needing to supply one.
- `advance() -> void` — no-op if the current node has `choices`; otherwise
  follows `next` (or ends if `next` is null/absent) and resolves the next
  node.
- `choose(index: int) -> void` — no-op if the current node doesn't have
  `choices` or `index` is out of range; otherwise applies `set_flag` (if
  present) then follows that choice's `next` and resolves.
- `is_active() -> bool` — true whenever a conversation is in progress.
  Exposed as the source of truth for "is a conversation open", but note
  `Player` does not poll it every frame to gate input (see §6) — pausing
  and resuming happens explicitly at the two lifecycle edges (interact
  triggers `start()`, `DialogueRunner.ended` fires), which is sufficient
  and avoids per-frame polling. `is_active()` remains useful for tests and
  any other code that needs a point-in-time check (e.g. §7's integration
  test).
- `current_voice_seed() -> int` — the `voice_seed` passed to the active
  `start()` call (or the default), read by `DialogueBox` to drive
  `Animalese` (see §5).

Internal node resolution (shared by `start`/`advance`/`choose`): given a
target node id, if it's null/empty, emit `ended` and clear `_graph`/
`_current_node_id`. Otherwise look up the node. If it has a `condition`:
evaluate it against `flags` (a missing flag counts as `false`); if it
evaluates true, fall through to the normal `next`/`choices` handling below;
if it evaluates false, recurse into resolving the node's `else` id (which
itself may be null, ending the conversation there). If the node has no
`condition`, or its condition evaluated true, proceed normally: if it has
`choices`, emit `choices_shown`; otherwise emit `line_shown`.

## 4. UI: `DialogueBox`

New scene: `src/ui/dialogue_box/dialogue_box.tscn` +
`src/ui/dialogue_box/dialogue_box.gd` (`class_name DialogueBox`, extends
`Control`). This is instanced as a child of `Player`'s existing `HUD`
`CanvasLayer` in `src/player/player.tscn`, as a sibling of the existing
`InteractPrompt` node (not in `src/main/main.tscn`, which is only a
boot/banner scene — `Player` is what's actually instanced wherever the
player exists, including inside `cottage_garden.tscn`, so anchoring the UI
to `Player`'s own `HUD` is what makes it show up in every zone the player
enters, not just one). Anchored to the bottom of the screen, same general
area as `InteractPrompt`.

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
- **`InteractPrompt` overlap**: `InteractPrompt` gains one new public
  method, `func force_hide() -> void: visible = false`, keeping it
  otherwise unaware of `DialogueRunner` (it stays a purely presentational
  component, per its existing doc comment). The wiring lives in `Player`,
  which already connects `resolver.focus_changed` to `prompt.on_focus_changed`
  in `_ready()` — it additionally connects `DialogueRunner.line_shown` and
  `DialogueRunner.choices_shown` to `prompt.force_hide`, and
  `DialogueRunner.ended` to a small handler that calls
  `prompt.on_focus_changed(resolver.focused())` (using `FocusResolver`'s
  existing `focused()` getter) so the prompt's visibility is corrected
  immediately based on current focus, rather than waiting for a fresh
  `focus_changed` event. This direct connection is necessary because
  `focus_changed` only fires when the focused interactable *changes* — if
  the player is already focused on the villager (prompt already visible)
  when they press interact, no new `focus_changed` event occurs, so
  relying on that signal alone would leave the prompt overlapping the
  dialogue box for the whole conversation.
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
  `Animalese.blip_for_seed(DialogueRunner.current_voice_seed())` through a
  single `AudioStreamPlayer` child (retriggering `play()` — brief overlaps
  are fine and match the genre's chattery feel).
- Speaker→seed mapping for the demo: the demo villager's dialogue trigger
  passes its own `VillagerDna.seed` as the `voice_seed` argument to
  `DialogueRunner.start(graph, voice_seed)` (see §6); `DialogueBox` then
  reads it back via `DialogueRunner.current_voice_seed()`. This reuses the
  existing per-NPC determinism convention rather than inventing a new
  voice-profile system.

## 6. Demo integration

- `cottage_garden.gd`'s `_add_demo_villager()` builds `DemoVillager`
  entirely at runtime (it is *not* an authored node in `cottage_garden.tscn`
  — confirmed: the `.tscn` has no such node, it's `add_child()`-ed from
  code). The new `Interactable` is therefore also created and attached in
  code, in the same function, immediately after the villager is built:
  ```gdscript
  var talk := Interactable.new()
  talk.verb = "Talk"
  talk.display_name = dna.name
  villager.add_child(talk)
  talk.interacted.connect(_on_demo_villager_interacted.bind(dna.seed))
  ```
  (`Interactable` extends `Area3D`, but `FocusResolver` doesn't do
  physics/area-overlap queries — it just scans the `"interactables"` group
  and checks `global_position` directly, so no `CollisionShape3D` is
  required for `talk` to be reachable; one isn't added.)
- The handler:
  ```gdscript
  func _on_demo_villager_interacted(by: Node, voice_seed: int) -> void:
      var graph := DialogueGraph.load_from_file("res://data/dialogue/demo_villager.json")
      if graph == null:
          push_error("demo_villager.json failed to load/validate")
          return
      var player := by as Player
      if player != null:
          player.input_enabled = false
      DialogueRunner.start(graph, voice_seed)
  ```
  Loading and validating the graph happens *before* touching
  `player.input_enabled`, so a malformed/missing dialogue file simply
  no-ops (logs an error, player stays in control) instead of stranding the
  player with movement disabled and no conversation to end it.
  `by` is the node passed into `Interactable.interact(by)`, which traces
  back to `FocusResolver.interact_focused(by)`'s caller — `Player`'s own
  `_unhandled_input` calls `resolver.interact_focused(self)`, so `by` is
  the `Player` instance itself; this is how the villager's interact handler
  gets a reference to pause the player without `Player` needing to poll
  `DialogueRunner.is_active()` every frame.
- `Player`: connects `DialogueRunner.ended` once in `_ready()` to a small
  handler that sets `input_enabled = true` back. Pairing "pause on
  interact-triggered start" with "resume on `ended`" fully covers the
  lifecycle without `Player` needing any other `DialogueRunner` awareness.
- `demo_villager.json` content: the 4-node example graph from §2 (linear
  line, `condition`+`else` branching, player choice, `set_flag`) — directly
  demonstrating every mechanic in one place, including the re-talk
  follow-up.
## 7. Testing

New/updated gdUnit test files, following this codebase's existing
conventions (`tests/unit/test_*.gd`, `scene_runner` for scene-level tests):

- `test_dialogue_graph.gd` — loads a small fixture JSON, asserts
  `start`/nodes/choices parse correctly; asserts validation fails (returns
  `null`) for: missing `start` node, dangling `next`/`else` reference, a
  node with both `next` and `choices`, a node missing `speaker`/`text`.
- `test_dialogue_runner.gd` — linear `start`→`advance`→`ended` sequence
  emits the right signals in order; a `choices_shown` conversation with
  `choose(i)` correctly sets the flag and follows that branch; a
  `condition`-gated node follows `else` when its flag evaluates false and
  follows `next`/`choices` normally when true; a `condition`-gated node
  with no `else` ends immediately when false; `is_active()` and
  `current_voice_seed()` reflect state correctly across the whole
  lifecycle. Uses an `after_test()` hook to reset
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
  assert `DialogueRunner.is_active()` becomes true; then, since the demo
  graph's `greet` node routes into `ask_weather`'s `choices` on a first
  encounter, call `DialogueRunner.choose(1)` — "Not now." — to reach `next:
  null` and end the conversation; assert `is_active()` becomes false) — a
  real integration check, not just a signal-connection existence check.

## 8. Risks / open questions carried forward (not blocking this slice)

- The number-key/mouse-click choice selection is a known placeholder;
  proper gamepad-friendly menu navigation is expected to land alongside
  T5.5 (settings/accessibility) or whenever the first real multi-choice
  quest content demands it.
- `DialogueRunner.flags` being in-memory-only means talking to the demo
  villager twice in the same play session will correctly show the gated
  follow-up line, but restarting the game resets that — this is the
  explicitly accepted trade-off pending T5.4.
