# Character Procedural Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if
> subagents available) or superpowers:executing-plans to implement this plan. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `tools/assetgen/character.py` (a hard-coded Wren-only script) into a
deterministic, data-driven procedural character pipeline — spec schema, part
registry, rig contract, animation contract, generator, validator — while keeping
Wren's generated GLB byte-identical, and produce the Asset Inventory Matrix that
unblocks the next asset-production phase.

**Architecture:** Four new modules under `tools/assetgen/` (`character_spec.py`,
`part_registry.py`, `rig_contract.py`, `animation_contract.py`) plus a generator
(`character_gen.py`) and validator (`character_validate.py`). `character.py` becomes
a thin module exporting Wren's canonical `CharacterSpec`. `build.py` is updated to
call the generator instead of `character.build_rig()`/`build_animations()` directly.
Full design: `docs/superpowers/specs/2026-08-08-character-procedural-pipeline-design.md`.

**Tech Stack:** Pure-stdlib Python 3 (no dependencies), pytest, existing
`tools/assetgen/mesh.py` (MeshBuilder, add_box/add_cylinder/add_lathe) and
`tools/assetgen/gltf.py` (SceneNode, AnimChannel, AnimationClip, build_scene_glb).

---

## Chunk 1: Spec schema, rig contract, and part registry

### Task 1: `CharacterSpec` schema

**Files:**
- Create: `tools/assetgen/character_spec.py`
- Test: `tests/python/test_character_spec.py`

- [x] **Step 1: Write the failing test**

```python
# tests/python/test_character_spec.py
from __future__ import annotations

import pytest

from tools.assetgen.character_spec import CharacterSpec


def test_spec_requires_archetype_and_seed():
    spec = CharacterSpec(archetype="witch", seed=42)
    assert spec.archetype == "witch"
    assert spec.seed == 42
    assert spec.parts == {}
    assert spec.animation_profile == "default"


def test_spec_rejects_non_int_seed():
    with pytest.raises(TypeError):
        CharacterSpec(archetype="witch", seed="42")


def test_spec_accepts_explicit_part_choices():
    spec = CharacterSpec(archetype="witch", seed=1, parts={"headwear": "witch_hat"})
    assert spec.parts["headwear"] == "witch_hat"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_character_spec.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.assetgen.character_spec'`

- [x] **Step 3: Write minimal implementation**

```python
# tools/assetgen/character_spec.py
"""CharacterSpec: the input contract for the procedural character pipeline.

A CharacterSpec is plain data — archetype id, seed, optional explicit part
choices, and an animation profile name. Same spec -> same generated character
(see character_gen.py for the determinism guarantee).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Bumped on breaking changes to this schema (new required fields, changed
# semantics of existing fields). Recorded per-character in build.py's manifest.
SPEC_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CharacterSpec:
    archetype: str
    seed: int
    parts: dict = field(default_factory=dict)
    palette_profile: str = "default"
    animation_profile: str = "default"
    root_name: str = ""  # defaults to archetype if left blank; see __post_init__

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise TypeError(f"seed must be int, got {type(self.seed).__name__}")
        if not isinstance(self.archetype, str) or not self.archetype:
            raise TypeError("archetype must be a non-empty str")
        if not self.root_name:
            object.__setattr__(self, "root_name", self.archetype)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_character_spec.py -v`
Expected: PASS (3 passed)

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/character_spec.py tests/python/test_character_spec.py
git commit -m "feat(character-pipeline): add CharacterSpec schema"
```

---

### Task 2: Rig contract — canonical slot → node mapping

**Files:**
- Create: `tools/assetgen/rig_contract.py`
- Test: `tests/python/test_rig_contract.py`

- [x] **Step 1: Write the failing test**

```python
# tests/python/test_rig_contract.py
from __future__ import annotations

import pytest

from tools.assetgen import rig_contract


def test_slot_order_is_alphabetical():
    assert rig_contract.SLOT_ORDER == (
        "accessory", "arm", "boot", "hair", "head", "headwear", "hips", "torso",
    )


def test_slot_to_node_names_mapping():
    assert rig_contract.SLOT_NODE_NAMES["hips"] == ("hips",)
    assert rig_contract.SLOT_NODE_NAMES["torso"] == ("torso",)
    assert rig_contract.SLOT_NODE_NAMES["arm"] == ("arm_l", "arm_r")
    assert rig_contract.SLOT_NODE_NAMES["head"] == ("head",)
    assert rig_contract.SLOT_NODE_NAMES["headwear"] == ("hat",)
    assert rig_contract.SLOT_NODE_NAMES["hair"] == ("braid",)
    assert rig_contract.SLOT_NODE_NAMES["boot"] == ("boot_l", "boot_r")


def test_mandatory_nodes_includes_headwear_and_hair():
    # hat/braid nodes are structurally mandatory even though the mesh they
    # carry may be an empty placeholder for a given archetype.
    assert "hat" in rig_contract.MANDATORY_NODE_NAMES
    assert "braid" in rig_contract.MANDATORY_NODE_NAMES


def test_version_is_an_int():
    assert isinstance(rig_contract.VERSION, int)


def test_parent_of_topology_matches_wren_tree():
    assert rig_contract.PARENT_OF["torso"] == "hips"
    assert rig_contract.PARENT_OF["arm_l"] == "torso"
    assert rig_contract.PARENT_OF["hat"] == "head"
    assert rig_contract.PARENT_OF["braid"] == "head"
    assert rig_contract.PARENT_OF["hips"] is None  # child of the root node


def test_loop_clip_names_include_baseline_loops():
    assert {"idle-loop", "walk-loop", "run-loop"} <= rig_contract.LOOP_CLIP_NAMES
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_rig_contract.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [x] **Step 3: Write minimal implementation**

```python
# tools/assetgen/rig_contract.py
"""Rig contract: canonical slot -> node-name mapping and required rig shape.

Mirrors Wren's existing node tree (see character.py's build_rig, pre-migration).
Registry *slot* names (used in CharacterSpec.parts / part_registry.py) are the
catalog/compatibility vocabulary; rig *node* names are what animation channels
and structural validation target. Both are fixed for this phase — no
per-archetype renaming.
"""
from __future__ import annotations

VERSION = 1

# Fixed alphabetical slot order — the order seeded part-selection consumes
# slots in (see character_gen.py). Must stay alphabetical; tested directly.
SLOT_ORDER = (
    "accessory", "arm", "boot", "hair", "head", "headwear", "hips", "torso",
)

# slot -> tuple of rig node names it fills. Single-node slots get a 1-tuple;
# left/right-mirrored slots (arm, boot) get both node names.
SLOT_NODE_NAMES = {
    "accessory": (),  # archetype-defined extra node(s) under torso; no baseline anim target
    "arm": ("arm_l", "arm_r"),
    "boot": ("boot_l", "boot_r"),
    "hair": ("braid",),
    "head": ("head",),
    "headwear": ("hat",),
    "hips": ("hips",),
    "torso": ("torso",),
}

# Every node the baseline animation contract targets unconditionally. These
# must always exist in a built rig, even if the part filling that slot for a
# given archetype is an invisible placeholder mesh.
MANDATORY_NODE_NAMES = frozenset(
    {"hips", "torso", "arm_l", "arm_r", "head", "hat", "braid", "boot_l", "boot_r"}
)


def all_node_names() -> frozenset:
    """Every node name any slot can produce (for validator lookups)."""
    names = set(MANDATORY_NODE_NAMES)
    for node_names in SLOT_NODE_NAMES.values():
        names.update(node_names)
    return frozenset(names)


# Required parent -> children topology, mirroring Wren's pre-pipeline node tree
# (character.py's original build_rig): hips, boot_l, and boot_r are direct
# children of the root, torso hangs off hips, arms/head hang off torso, hat/braid
# hang off head. Used by character_validate.py to check rig topology, independent
# of which meshes fill each node.
PARENT_OF = {
    "hips": None,       # child of the root node (name varies by spec.root_name)
    "boot_l": None,     # child of the root node
    "boot_r": None,     # child of the root node
    "torso": "hips",
    "arm_l": "torso",
    "arm_r": "torso",
    "head": "torso",
    "hat": "head",
    "braid": "head",
}

# Loop clips must close their animation cycle (first keyframe value == last)
# for every channel — reuses the check pattern from the pre-pipeline
# test_character.py::test_loop_clips_close_their_cycles.
LOOP_CLIP_NAMES = frozenset({"idle-loop", "walk-loop", "run-loop", "stir-loop"})
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_rig_contract.py -v`
Expected: PASS (6 passed)

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/rig_contract.py tests/python/test_rig_contract.py
git commit -m "feat(character-pipeline): add rig contract slot/node mapping"
```

---

### Task 3: Part registry — move Wren's canonical part builders

This is a **mechanical move**, not a rewrite: `_skirt`, `_torso`, `_arm`, `_head`,
`_hat`, `_braid`, `_boot` from `character.py` move into `part_registry.py` verbatim
(same geometry, same profile tuples, same palette ramp names), registered under the
`witch` archetype. This is required for Wren's post-migration output to stay
byte-identical.

**Files:**
- Create: `tools/assetgen/part_registry.py`
- Modify: `tools/assetgen/character.py` (no deletions yet — `_skirt`/`_torso`/`_arm`/
  `_head`/`_hat`/`_braid`/`_boot` are copied verbatim into `part_registry.py` but
  left in place in `character.py` too, so `build_rig`/`build_animations`/
  `flattened_builder`/`TRI_BUDGET`/pose constants keep working unchanged; the
  duplicated functions are removed from `character.py` in Task 7)
- Test: `tests/python/test_part_registry.py`

- [x] **Step 1: Write the failing test**

```python
# tests/python/test_part_registry.py
from __future__ import annotations

import pytest

from tools.assetgen import part_registry


def test_witch_archetype_has_all_baseline_slots():
    for slot in ("hips", "torso", "arm", "head", "headwear", "hair", "boot"):
        candidates = part_registry.candidates_for("witch", slot)
        assert len(candidates) >= 1, f"no candidates for witch/{slot}"


def test_candidates_are_returned_in_sorted_order():
    candidates = part_registry.candidates_for("witch", "headwear")
    assert candidates == sorted(candidates)


def test_unknown_archetype_slot_combo_returns_empty():
    assert part_registry.candidates_for("nonexistent_archetype", "torso") == []


def test_build_part_returns_mesh_builder():
    from tools.assetgen.mesh import MeshBuilder
    candidates = part_registry.candidates_for("witch", "torso")
    builder = part_registry.build_part("witch", "torso", candidates[0])
    assert isinstance(builder, MeshBuilder)
    assert builder.tri_count > 0


def test_witch_skirt_matches_pre_migration_geometry():
    # Regression guard: the moved _skirt() builder must produce the exact
    # same triangle count as the original character.py implementation.
    builder = part_registry.build_part("witch", "hips", "witch_skirt")
    assert builder.tri_count == 20  # lathe: 10 segments, 1 ring pair, both caps
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_part_registry.py -v`
Expected: FAIL with `ModuleNotFoundError`

Before implementing, verify the expected tri_count for `witch_skirt` empirically
against the *current* (pre-migration) `character._skirt()`:

Run: `python3 -c "from tools.assetgen.character import _skirt; print(_skirt().tri_count)"`

Use that printed number in the test above (the plan's placeholder of `20` is an
estimate — replace it with the actual printed value before proceeding).

- [x] **Step 3: Write minimal implementation**

Move the seven private builder functions out of `character.py` verbatim into
`part_registry.py`, renaming them to public, registry-keyed names. Copy the exact
bodies from `tools/assetgen/character.py` (current lines ~52–110) — do not alter any
profile tuples, box sizes, or ramp/shade arguments.

```python
# tools/assetgen/part_registry.py
"""Part library registry: named mesh builders per archetype + slot.

Canonical part builders are moved verbatim from the pre-pipeline character.py
(Wren's hand-authored meshes) — see the "witch" archetype entries below. New
archetypes add their own entries; the registry never overwrites an existing
part id.
"""
from __future__ import annotations

from .mesh import MeshBuilder, add_box, add_cylinder, add_lathe

# --- witch archetype: Wren's canonical parts (moved from character.py) -------

def witch_skirt() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [(0.21, -0.36), (0.19, -0.20), (0.155, -0.06), (0.13, 0.06)]
    add_lathe(builder, profile, 10, "void_plum", 2, cap_start=True, cap_end=True)
    return builder


def witch_torso() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [(0.125, -0.08), (0.15, 0.02), (0.13, 0.10), (0.10, 0.18)]
    add_lathe(builder, profile, 10, "rust", 2, cap_start=True, cap_end=True)
    return builder


def witch_arm() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.12, 0.0), (0.075, 0.24, 0.075), "rust", 1)
    add_box(builder, (0.0, -0.27, 0.0), (0.06, 0.06, 0.06), "cream", 3)
    return builder


def witch_head() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [
        (0.0, -0.04), (0.10, -0.03), (0.14, 0.04), (0.13, 0.12), (0.08, 0.18), (0.0, 0.20),
    ]
    add_lathe(builder, profile, 10, "cream", 3)
    for x in (-0.05, 0.05):
        add_box(builder, (x, 0.06, -0.135), (0.022, 0.03, 0.012), "void_plum", 0)
    return builder


def witch_hat() -> MeshBuilder:
    builder = MeshBuilder()
    add_cylinder(builder, (0.0, 0.0, 0.0), 0.20, 0.03, 10, "void_plum", 1, shade_top=2)
    cone_profile = [(0.125, 0.015), (0.10, 0.14), (0.05, 0.24), (0.0, 0.30)]
    add_lathe(builder, cone_profile, 10, "void_plum", 1)
    add_cylinder(builder, (0.0, 0.045, 0.0), 0.132, 0.035, 10, "glitch_magenta", 2,
                 cap_bottom=False, cap_top=False)
    return builder


def witch_braid() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.02, 0.02), (0.06, 0.08, 0.06), "honey", 2)
    add_box(builder, (0.0, -0.10, 0.045), (0.05, 0.08, 0.05), "honey", 1)
    add_box(builder, (0.0, -0.17, 0.06), (0.035, 0.07, 0.035), "honey", 2)
    return builder


def witch_boot() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.0, -0.01), (0.10, 0.12, 0.16), "bark", 1, top=("bark", 2))
    return builder


# --- registry ------------------------------------------------------------

# archetype -> slot -> {part_id: builder_fn}
_REGISTRY = {
    "witch": {
        "hips": {"witch_skirt": witch_skirt},
        "torso": {"witch_torso": witch_torso},
        "arm": {"witch_arm": witch_arm},
        "head": {"witch_head": witch_head},
        "headwear": {"witch_hat": witch_hat},
        "hair": {"witch_braid": witch_braid},
        "boot": {"witch_boot": witch_boot},
    },
}


def candidates_for(archetype: str, slot: str) -> list:
    """Sorted list of part ids available for archetype+slot (empty if none)."""
    return sorted(_REGISTRY.get(archetype, {}).get(slot, {}).keys())


def build_part(archetype: str, slot: str, part_id: str) -> MeshBuilder:
    try:
        builder_fn = _REGISTRY[archetype][slot][part_id]
    except KeyError as exc:
        raise ValueError(
            f"no part '{part_id}' for archetype '{archetype}' slot '{slot}'"
        ) from exc
    return builder_fn()


def register(archetype: str, slot: str, part_id: str, builder_fn) -> None:
    """Register a new part builder (used by future archetypes)."""
    _REGISTRY.setdefault(archetype, {}).setdefault(slot, {})[part_id] = builder_fn
```

Do **not** yet delete `_skirt`/`_torso`/etc. from `character.py` — Task 7 (Wren
migration) removes them once `character_gen.py` exists and the byte-identical
regression test is in place. Leaving them temporarily duplicated is fine; it keeps
every task's test suite green independently.

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_part_registry.py -v`
Expected: PASS (5 passed) — update the `test_witch_skirt_matches_pre_migration_geometry`
assertion with the real tri_count from Step 2 before running.

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/part_registry.py tests/python/test_part_registry.py
git commit -m "feat(character-pipeline): add part registry with witch archetype parts"
```

---

## Chunk 2: Animation contract, generator, and validator

### Task 4: Animation contract — parameterized baseline clips

Move `_idle`, `_gait`, `_wave`, `_stir`, `_sample`, `_rot_channel`, `_pos_channel`,
`quat_axis`, `quat_mul` from `character.py` into `animation_contract.py`, generalizing
the hard-coded `HIPS_POS`/`ARM_L_POS`/etc. constants into function parameters (a
`RigPose` mapping of node name -> rest translation, passed in instead of imported
module-level constants).

**Files:**
- Create: `tools/assetgen/animation_contract.py`
- No changes yet to `tools/assetgen/character.py:9-49, 128-255` (math helpers +
  animation builders): leave them in place so `build_rig()`, `build_animations()`,
  `flattened_builder()`, and `build.py`/`test_character.py` keep working unchanged.
  They are only removed in Task 7 once `character.py`'s `build_animations()` wrapper
  delegates to `animation_contract`/`character_gen` instead. Wren's specific rest
  pose values (currently the `HIPS_POS`/`ARM_L_POS`/etc. constants at lines 16-26
  of `character.py`) are duplicated into `character_gen.py`'s `_ARCHETYPE_POSE["witch"]`
  table in Task 5 — `animation_contract.build_baseline_clips()` itself takes a
  generic `pose: dict[str, tuple]` parameter and has no knowledge of Wren specifically.
- Test: `tests/python/test_animation_contract.py`

- [x] **Step 1: Write the failing test**

```python
# tests/python/test_animation_contract.py
from __future__ import annotations

import math

import pytest

from tools.assetgen import animation_contract, rig_contract

WREN_POSE = {
    "hips": (0.0, 0.46, 0.0), "torso": (0.0, 0.14, 0.0),
    "arm_l": (0.163, 0.12, 0.0), "arm_r": (-0.163, 0.12, 0.0),
    "head": (0.0, 0.22, 0.0), "hat": (0.0, 0.20, 0.0),
    "braid": (0.0, 0.02, 0.12),
    "boot_l": (0.09, 0.06, 0.0), "boot_r": (-0.09, 0.06, 0.0),
}


def test_baseline_clip_names():
    clips = animation_contract.build_baseline_clips(WREN_POSE, hat_tilt_deg=8.0)
    names = {clip.name for clip in clips}
    assert {"idle-loop", "walk-loop", "run-loop"} <= names


def test_baseline_clips_only_target_mandatory_nodes():
    clips = animation_contract.build_baseline_clips(WREN_POSE, hat_tilt_deg=8.0)
    for clip in clips:
        for channel in clip.channels:
            assert channel.node_name in rig_contract.MANDATORY_NODE_NAMES


def test_rotation_keyframes_are_unit_quaternions():
    clips = animation_contract.build_baseline_clips(WREN_POSE, hat_tilt_deg=8.0)
    for clip in clips:
        for channel in clip.channels:
            if channel.path != "rotation":
                continue
            for quat in channel.values:
                length = math.sqrt(sum(c * c for c in quat))
                assert abs(length - 1.0) < 1e-4
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_animation_contract.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [x] **Step 3: Write minimal implementation**

```python
# tools/assetgen/animation_contract.py
"""Animation contract: mandatory baseline clip set, parameterized by rest pose.

Moved from character.py's hard-coded Wren clips — the math is identical, but
rest-pose positions and the hat tilt are now function parameters instead of
module-level constants, so any archetype's rig (with its own limb-length/pose)
gets correctly-scaled gait clips.
"""
from __future__ import annotations

import math

from .gltf import AnimChannel, AnimationClip

VERSION = 1


def quat_axis(axis: str, degrees: float):
    half = math.radians(degrees) / 2.0
    s, c = math.sin(half), math.cos(half)
    if axis == "x":
        return (s, 0.0, 0.0, c)
    if axis == "y":
        return (0.0, s, 0.0, c)
    if axis == "z":
        return (0.0, 0.0, s, c)
    raise ValueError(axis)


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _sample(duration: float, steps: int, fn):
    times, values = [], []
    for i in range(steps + 1):
        t = round(duration * i / steps, 5)
        times.append(t)
        values.append(fn(t))
    return times, values


def _rot_channel(node: str, duration: float, steps: int, fn) -> AnimChannel:
    times, values = _sample(duration, steps, fn)
    return AnimChannel(node, "rotation", times, values)


def _pos_channel(node: str, duration: float, steps: int, fn) -> AnimChannel:
    times, values = _sample(duration, steps, fn)
    return AnimChannel(node, "translation", times, values)


def _idle(pose: dict, hat_tilt_deg: float) -> AnimationClip:
    duration, steps = 2.4, 12
    omega = 2.0 * math.pi / duration
    hips = pose["hips"]

    def breathe(t):
        return (hips[0], hips[1] + 0.006 * math.sin(omega * t), hips[2])

    return AnimationClip("idle-loop", [
        _pos_channel("hips", duration, steps, breathe),
        _rot_channel("torso", duration, steps,
                     lambda t: quat_axis("x", 1.8 * math.sin(omega * t))),
        _rot_channel("arm_l", duration, steps,
                     lambda t: quat_axis("x", 2.0 * math.sin(omega * t))),
        _rot_channel("arm_r", duration, steps,
                     lambda t: quat_axis("x", -2.0 * math.sin(omega * t))),
        _rot_channel("hat", duration, steps,
                     lambda t: quat_axis("z", hat_tilt_deg + 1.5 * math.sin(omega * t))),
        _rot_channel("braid", duration, steps,
                     lambda t: quat_axis("x", 3.0 * math.sin(omega * t + 0.8))),
    ])


def _gait(name: str, pose: dict, hat_tilt_deg: float, duration: float, stride: float,
          lift: float, swing_deg: float, bob: float, lean_deg: float,
          sway_deg: float) -> AnimationClip:
    steps = 12
    omega = 2.0 * math.pi / duration
    hips = pose["hips"]
    boot_l, boot_r = pose["boot_l"], pose["boot_r"]

    def boot_fn(base, sign):
        def fn(t):
            phase = math.sin(omega * t) * sign
            height = max(0.0, phase) * lift
            return (base[0], base[1] + height, base[2] + stride * phase)
        return fn

    def hips_fn(t):
        return (hips[0], hips[1] + bob * (0.5 - 0.5 * math.cos(2.0 * omega * t)), hips[2])

    return AnimationClip(name, [
        _pos_channel("boot_l", duration, steps, boot_fn(boot_l, 1.0)),
        _pos_channel("boot_r", duration, steps, boot_fn(boot_r, -1.0)),
        _pos_channel("hips", duration, steps, hips_fn),
        _rot_channel("hips", duration, steps,
                     lambda t: quat_axis("z", sway_deg * math.sin(omega * t))),
        _rot_channel("torso", duration, steps, lambda _t: quat_axis("x", lean_deg)),
        _rot_channel("arm_l", duration, steps,
                     lambda t: quat_axis("x", -swing_deg * math.sin(omega * t))),
        _rot_channel("arm_r", duration, steps,
                     lambda t: quat_axis("x", swing_deg * math.sin(omega * t))),
        _rot_channel("braid", duration, steps,
                     lambda t: quat_axis("x", 5.0 * math.sin(omega * t + 1.2))),
        _rot_channel("hat", duration, steps,
                     lambda t: quat_axis("z", hat_tilt_deg + 2.0 * math.sin(omega * t))),
    ])


def _wave() -> AnimationClip:
    raised = quat_axis("z", 150.0)

    def at(t):
        if t <= 0.0 or t >= 1.2:
            return quat_axis("z", 0.0)
        if t < 0.25:
            return quat_axis("z", 150.0 * (t / 0.25))
        if t > 1.05:
            return quat_axis("z", 150.0 * (1.2 - t) / 0.15)
        wiggle = 18.0 * math.sin((t - 0.25) * math.pi * 5.0)
        return quat_mul(raised, quat_axis("x", wiggle))

    times = [0.0, 0.25, 0.45, 0.65, 0.85, 1.05, 1.2]
    return AnimationClip("wave", [
        AnimChannel("arm_r", "rotation", times, [at(t) for t in times]),
        AnimChannel("torso", "rotation", [0.0, 0.3, 0.9, 1.2], [
            quat_axis("z", 0.0), quat_axis("z", -4.0),
            quat_axis("z", -4.0), quat_axis("z", 0.0),
        ]),
    ])


def _stir() -> AnimationClip:
    duration, steps = 1.6, 16
    omega = 2.0 * math.pi / duration

    def stir_arm(t):
        pitch = quat_axis("x", 30.0 + 18.0 * math.sin(omega * t))
        roll = quat_axis("z", -20.0 + 14.0 * math.cos(omega * t))
        return quat_mul(roll, pitch)

    return AnimationClip("stir-loop", [
        _rot_channel("arm_r", duration, steps, stir_arm),
        _rot_channel("torso", duration, steps,
                     lambda t: quat_axis("x", 4.0 + 1.5 * math.sin(omega * t))),
    ])


BASELINE_PROFILE_CLIPS = {
    "default": ("idle", "walk", "run"),
    "witch": ("idle", "walk", "run", "wave", "stir"),
}


def build_baseline_clips(pose: dict, hat_tilt_deg: float = 0.0,
                          profile: str = "default") -> list:
    """Build the clip set for `profile`. `pose` maps node name -> rest translation
    for hips/boot_l/boot_r (required for every profile)."""
    wanted = BASELINE_PROFILE_CLIPS.get(profile, BASELINE_PROFILE_CLIPS["default"])
    builders = {
        "idle": lambda: _idle(pose, hat_tilt_deg),
        "walk": lambda: _gait("walk-loop", pose, hat_tilt_deg, 0.8, 0.07, 0.03, 14.0, 0.012, 3.0, 3.0),
        "run": lambda: _gait("run-loop", pose, hat_tilt_deg, 0.5, 0.10, 0.05, 25.0, 0.025, 8.0, 4.0),
        "wave": _wave,
        "stir": _stir,
    }
    return [builders[key]() for key in wanted]
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_animation_contract.py -v`
Expected: PASS (3 passed)

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/animation_contract.py tests/python/test_animation_contract.py
git commit -m "feat(character-pipeline): add parameterized animation contract"
```

---

### Task 5: Generator/assembler

**Files:**
- Create: `tools/assetgen/character_gen.py`
- Test: `tests/python/test_character_gen.py`

- [x] **Step 1: Write the failing test**

```python
# tests/python/test_character_gen.py
from __future__ import annotations

from tools.assetgen import character_gen, rig_contract
from tools.assetgen.character_spec import CharacterSpec


def _wren_spec():
    return CharacterSpec(
        archetype="witch",
        seed=0,
        parts={
            "hips": "witch_skirt", "torso": "witch_torso", "arm": "witch_arm",
            "head": "witch_head", "headwear": "witch_hat", "hair": "witch_braid",
            "boot": "witch_boot",
        },
        animation_profile="witch",
    )


def test_generate_returns_rig_and_clips():
    rig, clips = character_gen.generate(_wren_spec())
    assert rig.name == "witch"
    assert len(clips) == 5  # idle, walk, run, wave, stir


def test_generated_rig_has_all_mandatory_nodes():
    rig, _clips = character_gen.generate(_wren_spec())

    def collect_names(node, acc):
        acc.add(node.name)
        for child in node.children:
            collect_names(child, acc)
        return acc

    names = collect_names(rig, set())
    assert rig_contract.MANDATORY_NODE_NAMES <= names


def test_generation_is_deterministic():
    rig1, clips1 = character_gen.generate(_wren_spec())
    rig2, clips2 = character_gen.generate(_wren_spec())
    from tools.assetgen import gltf
    glb1 = gltf.build_scene_glb(rig1, clips1, "witch")
    glb2 = gltf.build_scene_glb(rig2, clips2, "witch")
    assert glb1 == glb2


def test_unknown_archetype_raises_value_error():
    import pytest
    from tools.assetgen.character_spec import CharacterSpec
    with pytest.raises(ValueError, match="archetype"):
        character_gen.generate(CharacterSpec(archetype="nope", seed=0))
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_character_gen.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [x] **Step 3: Write minimal implementation**

```python
# tools/assetgen/character_gen.py
"""Generator/assembler: CharacterSpec -> (SceneNode rig, list[AnimationClip]).

Resolves part choices (explicit spec.parts win; otherwise a seeded, sorted
pick from part_registry candidates), builds the rig via a per-archetype pose
table, attaches part meshes at their rig-contract node names, and generates
the animation-contract clip set for the requested profile.
"""
from __future__ import annotations

import random

from . import animation_contract, part_registry, rig_contract
from .animation_contract import quat_axis
from .gltf import SceneNode

# archetype -> node name -> rest-pose translation. Extend per new archetype;
# "witch" values match Wren's pre-pipeline HIPS_POS/TORSO_POS/etc. constants.
_ARCHETYPE_POSE = {
    "witch": {
        "hips": (0.0, 0.46, 0.0), "torso": (0.0, 0.14, 0.0),
        "arm_l": (0.163, 0.12, 0.0), "arm_r": (-0.163, 0.12, 0.0),
        "head": (0.0, 0.22, 0.0), "hat": (0.0, 0.20, 0.0),
        "braid": (0.0, 0.02, 0.12),
        "boot_l": (0.09, 0.06, 0.0), "boot_r": (-0.09, 0.06, 0.0),
    },
}
_ARCHETYPE_HAT_TILT_DEG = {"witch": 8.0}


def _resolve_parts(spec) -> dict:
    """slot -> part_id. Explicit non-None choices win; an explicit `None` (or an
    absent slot) means "let the generator pick deterministically from the seed"."""
    if spec.archetype not in _ARCHETYPE_POSE:
        raise ValueError(f"unknown archetype: {spec.archetype!r}")
    rng = random.Random(spec.seed)
    resolved = {}
    for slot in rig_contract.SLOT_ORDER:
        explicit = spec.parts.get(slot)
        if explicit is not None:
            resolved[slot] = explicit
            continue
        candidates = part_registry.candidates_for(spec.archetype, slot)
        if not candidates:
            continue  # no registry entries for this slot+archetype (e.g. accessory)
        resolved[slot] = candidates[rng.randrange(len(candidates))]
    return resolved


def _build_rig(spec, resolved_parts: dict) -> SceneNode:
    pose = _ARCHETYPE_POSE[spec.archetype]

    def node_for(slot: str, node_name: str) -> SceneNode:
        part_id = resolved_parts.get(slot)
        mesh = part_registry.build_part(spec.archetype, slot, part_id) if part_id else None
        if mesh is not None and mesh.tri_count == 0:
            # empty placeholder (e.g. villager's no-hat/no-hair slot) — gltf.py's
            # build_scene_glb raises on zero-vertex meshes, so the node carries
            # no mesh at all; it still exists structurally for animation targeting.
            mesh = None
        return SceneNode(node_name, mesh=mesh, translation=pose[node_name])

    hat = node_for("headwear", "hat")
    hat.rotation = quat_axis("z", _ARCHETYPE_HAT_TILT_DEG.get(spec.archetype, 0.0))
    braid = node_for("hair", "braid")
    head_node = node_for("head", "head")
    head_node.children = [hat, braid]
    arm_l = SceneNode("arm_l", mesh=part_registry.build_part(spec.archetype, "arm", resolved_parts["arm"]),
                       translation=pose["arm_l"])
    arm_r = SceneNode("arm_r", mesh=part_registry.build_part(spec.archetype, "arm", resolved_parts["arm"]),
                       translation=pose["arm_r"])
    torso = node_for("torso", "torso")
    torso.children = [arm_l, arm_r, head_node]
    hips = node_for("hips", "hips")
    hips.children = [torso]
    boot_l = SceneNode("boot_l", mesh=part_registry.build_part(spec.archetype, "boot", resolved_parts["boot"]),
                        translation=pose["boot_l"])
    boot_r = SceneNode("boot_r", mesh=part_registry.build_part(spec.archetype, "boot", resolved_parts["boot"]),
                        translation=pose["boot_r"])
    return SceneNode(spec.root_name, children=[hips, boot_l, boot_r])


def generate(spec):
    """Returns (SceneNode rig, list[AnimationClip]) for the given CharacterSpec."""
    resolved_parts = _resolve_parts(spec)
    rig = _build_rig(spec, resolved_parts)
    pose = _ARCHETYPE_POSE[spec.archetype]
    clips = animation_contract.build_baseline_clips(
        pose, hat_tilt_deg=_ARCHETYPE_HAT_TILT_DEG.get(spec.archetype, 0.0),
        profile=spec.animation_profile,
    )
    return rig, clips


def _rotate_point(quat, point):
    if quat is None:
        return point
    qx, qy, qz, qw = quat
    ux, uy, uz = qy * point[2] - qz * point[1], qz * point[0] - qx * point[2], \
        qx * point[1] - qy * point[0]
    ux, uy, uz = ux + qw * point[0], uy + qw * point[1], uz + qw * point[2]
    cx, cy, cz = qy * uz - qz * uy, qz * ux - qx * uz, qx * uy - qy * ux
    return (point[0] + 2.0 * cx, point[1] + 2.0 * cy, point[2] + 2.0 * cz)


def flatten_rig(rig):
    """Rest-pose merge of every node's mesh into one MeshBuilder (for triangle
    budget checks and preview renders). Moved verbatim from the pre-pipeline
    character.flattened_builder(), generalized to take any generated rig."""
    from . import palette
    from .mesh import MeshBuilder

    merged = MeshBuilder()

    def uv_to_cell(uv):
        width, height = palette.atlas_size_px()
        col = int(uv[0] * width) // palette.CELL_PX
        row = int(uv[1] * height) // palette.CELL_PX
        return palette.RAMPS[row][0], min(col, palette.SHADES - 1)

    def walk(node, base):
        origin = tuple(base[i] + node.translation[i] for i in range(3))
        if node.mesh is not None:
            for face_start in range(0, len(node.mesh.indices), 3):
                idx = node.mesh.indices[face_start:face_start + 3]
                points = []
                for i in idx:
                    local = _rotate_point(node.rotation, node.mesh.positions[i])
                    points.append(tuple(local[k] + origin[k] for k in range(3)))
                ramp_shade = uv_to_cell(node.mesh.uvs[idx[0]])
                merged.add_face(points, ramp_shade[0], ramp_shade[1])
        for child in node.children:
            walk(child, origin)

    walk(rig, (0.0, 0.0, 0.0))
    return merged


def resolved_parts_for(spec) -> dict:
    """Public accessor so build.py/manifest code can record what a seed picked."""
    return _resolve_parts(spec)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_character_gen.py -v`
Expected: PASS (4 passed)

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/character_gen.py tests/python/test_character_gen.py
git commit -m "feat(character-pipeline): add generator/assembler"
```

---

### Task 6: Validator

**Files:**
- Create: `tools/assetgen/character_validate.py`
- Test: `tests/python/test_character_validate.py`

- [x] **Step 1: Write the failing test**

```python
# tests/python/test_character_validate.py
from __future__ import annotations

import pytest

from tools.assetgen import character_gen, character_validate
from tools.assetgen.character_spec import CharacterSpec
from tools.assetgen.gltf import AnimationClip, SceneNode


def _wren_spec():
    return CharacterSpec(
        archetype="witch", seed=0,
        parts={
            "hips": "witch_skirt", "torso": "witch_torso", "arm": "witch_arm",
            "head": "witch_head", "headwear": "witch_hat", "hair": "witch_braid",
            "boot": "witch_boot",
        },
        animation_profile="witch",
    )


def test_valid_character_passes():
    rig, clips = character_gen.generate(_wren_spec())
    character_validate.validate(rig, clips)  # should not raise


def test_missing_mandatory_node_raises():
    rig = SceneNode("broken", children=[SceneNode("hips")])  # missing torso, arms, etc.
    with pytest.raises(ValueError, match="missing"):
        character_validate.validate(rig, [])


def test_missing_baseline_clip_raises():
    rig, _clips = character_gen.generate(_wren_spec())
    with pytest.raises(ValueError, match="idle-loop"):
        character_validate.validate(rig, [AnimationClip("wave", [])])


def test_over_budget_tri_count_raises():
    rig, clips = character_gen.generate(_wren_spec())
    with pytest.raises(ValueError, match="budget"):
        character_validate.validate(rig, clips, tri_budget=1)


def test_bad_topology_raises():
    # torso must be a child of hips, not a sibling — include every mandatory
    # node so this fails topology, not the earlier missing-node check.
    bad_rig = SceneNode("wren", children=[
        SceneNode("hips"),
        SceneNode("torso", children=[
            SceneNode("arm_l"), SceneNode("arm_r"),
            SceneNode("head", children=[SceneNode("hat"), SceneNode("braid")]),
        ]),
        SceneNode("boot_l"), SceneNode("boot_r"),
    ])
    with pytest.raises(ValueError, match="parent"):
        character_validate.validate(bad_rig, [])


def test_non_closing_loop_clip_raises():
    from tools.assetgen.gltf import AnimChannel
    rig, clips = character_gen.generate(_wren_spec())
    broken_idle = AnimationClip("idle-loop", [
        AnimChannel("hips", "translation", [0.0, 1.0], [(0.0, 0.0, 0.0), (0.0, 1.0, 0.0)]),
    ])
    other_clips = [c for c in clips if c.name != "idle-loop"]
    with pytest.raises(ValueError, match="does not close"):
        character_validate.validate(rig, [broken_idle] + other_clips)
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_character_validate.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [x] **Step 3: Write minimal implementation**

```python
# tools/assetgen/character_validate.py
"""Validator: checks a generated (rig, clips) pair against the rig/animation
contracts. Raises ValueError naming exactly what failed — no silent fallbacks.
"""
from __future__ import annotations

from . import rig_contract

MANDATORY_CLIP_NAMES = ("idle-loop", "walk-loop", "run-loop")
DEFAULT_TRI_BUDGET = 1500


def _collect_node_names(node, acc) -> set:
    acc.add(node.name)
    for child in node.children:
        _collect_node_names(child, acc)
    return acc


def _tri_count(node) -> int:
    total = node.mesh.tri_count if node.mesh is not None else 0
    for child in node.children:
        total += _tri_count(child)
    return total


def _collect_parent_map(node, parent_name, acc) -> dict:
    """node name -> actual parent name (None for direct children of the root)."""
    acc[node.name] = parent_name
    for child in node.children:
        _collect_parent_map(child, node.name, acc)
    return acc


def _check_topology(rig) -> None:
    actual_parents = _collect_parent_map(rig, None, {})
    root_name = rig.name
    for node_name, expected_parent in rig_contract.PARENT_OF.items():
        if node_name not in actual_parents:
            continue  # already reported by the mandatory-node check
        actual_parent = actual_parents[node_name]
        if expected_parent is None:
            # PARENT_OF[node] is None -> must be a direct child of the root,
            # i.e. its actual parent name must equal the rig's own root name.
            if actual_parent != root_name:
                raise ValueError(
                    f"node '{node_name}' expected as a direct child of root "
                    f"'{root_name}', found under '{actual_parent}'"
                )
        elif actual_parent != expected_parent:
            raise ValueError(
                f"node '{node_name}' expected under parent '{expected_parent}', "
                f"found under '{actual_parent}'"
            )


def _check_loop_closure(clips) -> None:
    for clip in clips:
        if clip.name not in rig_contract.LOOP_CLIP_NAMES:
            continue
        for channel in clip.channels:
            first, last = channel.values[0], channel.values[-1]
            for a, b in zip(first, last):
                if abs(a - b) >= 1e-4:
                    raise ValueError(
                        f"loop clip '{clip.name}' channel '{channel.node_name}/"
                        f"{channel.path}' does not close its cycle"
                    )


def validate(rig, clips, tri_budget: int = DEFAULT_TRI_BUDGET) -> None:
    node_names = _collect_node_names(rig, set())
    missing_nodes = rig_contract.MANDATORY_NODE_NAMES - node_names
    if missing_nodes:
        raise ValueError(f"rig missing mandatory node(s): {sorted(missing_nodes)}")

    _check_topology(rig)

    clip_names = {clip.name for clip in clips}
    missing_clips = set(MANDATORY_CLIP_NAMES) - clip_names
    if missing_clips:
        raise ValueError(f"missing mandatory clip(s): {sorted(missing_clips)}")

    for clip in clips:
        for channel in clip.channels:
            if channel.node_name not in node_names:
                raise ValueError(
                    f"clip '{clip.name}' targets unknown node '{channel.node_name}'"
                )

    _check_loop_closure(clips)

    tris = _tri_count(rig)
    if tris > tri_budget:
        raise ValueError(f"triangle budget exceeded: {tris} > {tri_budget}")
```

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_character_validate.py -v`
Expected: PASS (6 passed)

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/character_validate.py tests/python/test_character_validate.py
git commit -m "feat(character-pipeline): add rig/animation validator"
```

---

## Chunk 3: Wren migration, second archetype, and asset inventory

### Task 7: Migrate Wren to the pipeline (byte-identical regression)

**Files:**
- Modify: `tools/assetgen/character.py` (replace with a thin module that keeps
  `build_rig()`/`build_animations()`/`flattened_builder()`/`TRI_BUDGET` as
  backward-compatible wrappers — see below)
- Modify: `tools/assetgen/build.py:13, 42-49` (call `character_gen.generate` instead
  of `character.build_rig()`/`character.build_animations()`)
- No changes needed: `tests/python/test_character.py` (its existing calls to
  `character.build_rig()`/`character.build_animations()` keep working unchanged
  through the new wrappers — this is the regression proof)
- Test: `tests/python/test_character_migration.py`

- [x] **Step 1: Write the failing test**

First, capture the pre-migration reference GLB bytes as a fixture so this test can
prove nothing changed:

```bash
python3 -c "
from tools.assetgen import character, gltf
data = gltf.build_scene_glb(character.build_rig(), character.build_animations(), 'wren')
import hashlib
print(hashlib.sha256(data).hexdigest())
"
```

Record the printed hash, then write:

```python
# tests/python/test_character_migration.py
from __future__ import annotations

import hashlib

from tools.assetgen import character, character_gen, gltf

# Captured from the pre-migration character.build_rig()/build_animations()
# via the sha256 command in this task's Step 1. Replace with the real value.
PRE_MIGRATION_SHA256 = "REPLACE_WITH_CAPTURED_HASH"


def test_wren_spec_produces_byte_identical_output():
    rig, clips = character_gen.generate(character.WREN_SPEC)
    data = gltf.build_scene_glb(rig, clips, "wren")
    assert hashlib.sha256(data).hexdigest() == PRE_MIGRATION_SHA256
```

Run: `python3 -m pytest tests/python/test_character_migration.py -v`
Expected: FAIL — `character.WREN_SPEC` doesn't exist yet.

- [x] **Step 2: Confirm the failure reason is "not yet migrated", not a bad hash**

Run: `python3 -m pytest tests/python/test_character_migration.py -v`
Expected: FAIL with `AttributeError: module 'tools.assetgen.character' has no
attribute 'WREN_SPEC'`

- [x] **Step 3: Replace `character.py` with a thin module**

Remove the moved functions (`_skirt`, `_torso`, `_arm`, `_head`, `_hat`, `_braid`,
`_boot`, `quat_axis`, `quat_mul`, `_sample`, `_rot_channel`, `_pos_channel`, `_idle`,
`_gait`, `_wave`, `_stir`) — they now live in `part_registry.py` and
`animation_contract.py`. Keep `build_rig`, `build_animations`, and
`flattened_builder` as thin wrappers delegating to `character_gen.generate(WREN_SPEC)`
(see code below) — `tests/python/test_character.py` calls all three directly, so
they must remain importable with identical behavior. Keep `TRI_BUDGET` too, since
`flattened_builder`'s callers check tri counts against it.

```bash
grep -rn "character.build_rig\|character.build_animations\|character.flattened_builder\|character\._skirt\|character\._torso" --include="*.py" tools tests
```

Rewrite `tools/assetgen/character.py`:

```python
"""Wren — the witch, expressed as her canonical CharacterSpec.

The generation logic lives in character_gen.py (generic pipeline);
part meshes live in part_registry.py (witch archetype entries); animation
clips live in animation_contract.py. This module only pins Wren's specific,
fixed identity so build.py and tests have a stable import.
"""
from __future__ import annotations

from . import character_gen
from .character_spec import CharacterSpec

TRI_BUDGET = 1500

WREN_SPEC = CharacterSpec(
    archetype="witch",
    seed=0,
    parts={
        "hips": "witch_skirt", "torso": "witch_torso", "arm": "witch_arm",
        "head": "witch_head", "headwear": "witch_hat", "hair": "witch_braid",
        "boot": "witch_boot",
    },
    animation_profile="witch",
    root_name="wren",  # preserves the pre-migration root node name for byte-identical GLB output
)


def build_rig():
    """Wren's rig — thin wrapper kept for backward-compatible imports (see
    test_character.py, which calls character.build_rig() directly)."""
    rig, _clips = character_gen.generate(WREN_SPEC)
    return rig


def build_animations():
    """Wren's animation clips — thin wrapper kept for backward-compatible
    imports (see test_character.py, which calls character.build_animations()
    directly in several assertions)."""
    _rig, clips = character_gen.generate(WREN_SPEC)
    return clips


def flattened_builder():
    """Rest-pose merge of Wren's rig (for budgets/preview renders) — thin
    wrapper kept for backward-compatible imports (see test_character.py)."""
    rig, _clips = character_gen.generate(WREN_SPEC)
    return character_gen.flatten_rig(rig)
```

Update `tools/assetgen/build.py`:

```python
# tools/assetgen/build.py — replace the character section
from . import (
    animation_contract, character, character_gen, character_validate, gltf,
    palette, props, rig_contract,
)
from .character_spec import SPEC_SCHEMA_VERSION
# ...
    wren_rig, wren_clips = character_gen.generate(character.WREN_SPEC)
    character_validate.validate(wren_rig, wren_clips, tri_budget=character.TRI_BUDGET)
    wren_glb = gltf.build_scene_glb(wren_rig, wren_clips, "wren")
    (OUT_DIR / "wren.glb").write_bytes(wren_glb)
    resolved_parts = character_gen.resolved_parts_for(character.WREN_SPEC)
    manifest["characters"]["wren"] = {
        "archetype": character.WREN_SPEC.archetype,
        "seed": character.WREN_SPEC.seed,
        "resolved_parts": resolved_parts,
        "spec_schema_version": SPEC_SCHEMA_VERSION,
        "rig_contract_version": rig_contract.VERSION,
        "animation_contract_version": animation_contract.VERSION,
        "tris": sum(node.mesh.tri_count for node in _walk_nodes(wren_rig) if node.mesh),
        "bytes": len(wren_glb),
        "sha256": hashlib.sha256(wren_glb).hexdigest(),
        "clips": [clip.name for clip in wren_clips],
    }
```

(Add a small `_walk_nodes` helper to `build.py` or reuse
`character_validate._collect_node_names`-style traversal — pick whichever keeps
`build.py` shortest; a one-off generator function is fine:)

```python
def _walk_nodes(node):
    yield node
    for child in node.children:
        yield from _walk_nodes(child)
```

Add the needed imports (`rig_contract`, `animation_contract`) to `build.py`'s import
line.

`tests/python/test_character.py` needs **no changes at all**. Because `character.py`
keeps `build_rig()` and `build_animations()` as thin wrappers around
`character_gen.generate(WREN_SPEC)`, every existing call in that file
(`character.build_rig()`, `character.build_animations()`, the `_build()` helper, and
the unknown-node test's direct `gltf.build_scene_glb(character.build_rig(), ...)`
call) keeps working unchanged, exercising the new pipeline underneath. This is the
proof that the refactor is behavior-preserving: the same test file, untouched,
still passes.

Now fill in the real hash in `test_character_migration.py` from Step 1's captured
value.

- [x] **Step 4: Run tests to verify everything passes**

Run: `python3 -m pytest tests/python/test_character.py tests/python/test_character_migration.py -v`
Expected: PASS — all of `test_character.py`'s original assertions pass unchanged,
plus the new byte-identical migration test.

Then run the full asset build to confirm `build.py` still works end-to-end:

Run: `python3 -m tools.assetgen.build`
Expected: `asset build OK`, with `wren.glb` byte-identical (compare
`assets/generated/manifest.json`'s `wren.sha256` to the same captured hash).

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/character.py tools/assetgen/build.py tests/python/test_character_migration.py
git commit -m "refactor(character-pipeline): migrate Wren to the procedural pipeline

Byte-identical output preserved (see test_character_migration.py)."
```

---

### Task 8: Second archetype proof — `villager`

Proves the pipeline isn't Wren-shaped underneath. A visually distinct but simple
archetype: no hat (empty headwear placeholder), no braid (empty hair placeholder), a
plainer torso/head.

**Files:**
- Modify: `tools/assetgen/part_registry.py` (add `villager` archetype entries +
  empty-placeholder builders for `headwear`/`hair`)
- Modify: `tools/assetgen/character_gen.py` (add `villager` to `_ARCHETYPE_POSE`)
- Test: `tests/python/test_villager_archetype.py`

- [x] **Step 1: Write the failing test**

```python
# tests/python/test_villager_archetype.py
from __future__ import annotations

from tools.assetgen import character_gen, character_validate, gltf
from tools.assetgen.character_spec import CharacterSpec


def _villager_spec(seed=1):
    return CharacterSpec(archetype="villager", seed=seed)  # all parts seed-resolved


def test_villager_generates_and_validates():
    rig, clips = character_gen.generate(_villager_spec())
    character_validate.validate(rig, clips)  # should not raise


def test_villager_is_deterministic_and_distinct_from_witch():
    from tools.assetgen import character
    rig_v, clips_v = character_gen.generate(_villager_spec())
    rig_w, clips_w = character_gen.generate(character.WREN_SPEC)
    glb_v = gltf.build_scene_glb(rig_v, clips_v, "villager")
    glb_w = gltf.build_scene_glb(rig_w, clips_w, "wren")
    assert glb_v != glb_w

    rig_v2, clips_v2 = character_gen.generate(_villager_spec())
    glb_v2 = gltf.build_scene_glb(rig_v2, clips_v2, "villager")
    assert glb_v == glb_v2


def test_villager_headwear_and_hair_are_empty_placeholders():
    rig, _clips = character_gen.generate(_villager_spec())

    def find(node, name):
        if node.name == name:
            return node
        for child in node.children:
            found = find(child, name)
            if found:
                return found
        return None

    hat = find(rig, "hat")
    braid = find(rig, "braid")
    assert hat is not None and hat.mesh is None
    assert braid is not None and braid.mesh is None
```

- [x] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_villager_archetype.py -v`
Expected: FAIL — `unknown archetype: 'villager'`

- [x] **Step 3: Write minimal implementation**

Add to `part_registry.py`:

```python
def empty_placeholder() -> MeshBuilder:
    """Zero-geometry mesh for a structurally-mandatory-but-visually-absent slot."""
    return MeshBuilder()


def villager_torso() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.05, 0.0), (0.28, 0.32, 0.22), "moss", 2)
    return builder


def villager_head() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.0, 0.0), (0.24, 0.24, 0.22), "cream", 3)
    return builder


def villager_arm() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.12, 0.0), (0.07, 0.22, 0.07), "moss", 1)
    return builder


def villager_boot() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.0, -0.01), (0.09, 0.10, 0.14), "bark", 1)
    return builder


_REGISTRY["villager"] = {
    "hips": {"villager_hips_placeholder": empty_placeholder},
    "torso": {"villager_torso": villager_torso},
    "arm": {"villager_arm": villager_arm},
    "head": {"villager_head": villager_head},
    "headwear": {"villager_no_hat": empty_placeholder},
    "hair": {"villager_no_hair": empty_placeholder},
    "boot": {"villager_boot": villager_boot},
}
```

Add to `character_gen.py`'s `_ARCHETYPE_POSE`:

```python
    "villager": {
        "hips": (0.0, 0.40, 0.0), "torso": (0.0, 0.16, 0.0),
        "arm_l": (0.15, 0.10, 0.0), "arm_r": (-0.15, 0.10, 0.0),
        "head": (0.0, 0.20, 0.0), "hat": (0.0, 0.18, 0.0),
        "braid": (0.0, 0.0, 0.10),
        "boot_l": (0.08, 0.05, 0.0), "boot_r": (-0.08, 0.05, 0.0),
    },
```

(`_ARCHETYPE_HAT_TILT_DEG` needs no `villager` entry — the default `0.0` from
`.get(..., 0.0)` applies.)

- [x] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_villager_archetype.py -v`
Expected: PASS (3 passed)

- [x] **Step 5: Commit**

```bash
git add tools/assetgen/part_registry.py tools/assetgen/character_gen.py tests/python/test_villager_archetype.py
git commit -m "feat(character-pipeline): add villager archetype as pipeline proof"
```

---

### Task 9: Asset Inventory Matrix

**Files:**
- Create: `docs/asset-inventory.md`

- [x] **Step 1: Write the inventory table**

Populate per the spec's source list: Wren, the 15-row `story-bible.md` cast table
entries (kids and cats already one row each there), plus Clack & Click and the
Kindlies as separate rows (named in the story bible's "The Pattern" section, not in
the cast table). Add placeholder nature/building rows.

```markdown
# Asset Inventory Matrix

Tracks every known-needed character/nature/building asset so future asset phases
have a backlog instead of guesswork. Populated per
`docs/superpowers/specs/2026-08-08-character-procedural-pipeline-design.md`.

| Asset ID | Category | Subtype | Procedural/Handcrafted | Rig/Anim | Dependencies | Priority | Gameplay dependency | Status |
|---|---|---|---|---|---|---|---|---|
| wren | character | witch (player) | procedural | witch rig/anim contract | part_registry witch entries | P0 | Phase 1 player avatar | done |
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
```

- [x] **Step 2: Commit**

```bash
git add docs/asset-inventory.md
git commit -m "docs: add Asset Inventory Matrix for character/nature/building backlog"
```

---

### Task 10: Full suite green + tooling doc

**Files:**
- Create: `tools/assetgen/README.md`

- [x] **Step 1: Run the full pytest suite**

Run: `python3 -m pytest tests/python -v`
Expected: all tests pass, including every test file created/modified in this plan.

- [x] **Step 2: Write the tooling doc**

```markdown
# tools/assetgen — Character Pipeline

## Adding a new part
1. Write a builder function in `part_registry.py` returning a `MeshBuilder`
   (reuse `add_box`/`add_cylinder`/`add_lathe` from `mesh.py`).
2. Register it: `_REGISTRY[archetype][slot][part_id] = builder_fn`, or call
   `part_registry.register(archetype, slot, part_id, builder_fn)` from another
   module.
3. Part ids must be unique per archetype+slot; candidates are returned sorted,
   so seeded selection is deterministic.

## Adding a new archetype
1. Add rig pose entries to `character_gen._ARCHETYPE_POSE` for every node in
   `rig_contract.SLOT_NODE_NAMES` (or reuse an existing pose set).
2. Register at least one part per baseline slot (`hips`, `torso`, `arm`, `head`,
   `boot`); `headwear`/`hair` can use `part_registry.empty_placeholder()` if the
   archetype has none visually.
3. Optionally add an `animation_contract.BASELINE_PROFILE_CLIPS` entry if the
   archetype needs clips beyond `idle`/`walk`/`run`.

## Running the validator standalone

```python
from tools.assetgen import character_gen, character_validate
from tools.assetgen.character_spec import CharacterSpec

rig, clips = character_gen.generate(CharacterSpec(archetype="villager", seed=1))
character_validate.validate(rig, clips)  # raises ValueError with details on failure
```

## Rebuilding all generated assets

`python3 -m tools.assetgen.build` — writes `assets/generated/manifest.json` with
per-character `archetype`, `seed`, `resolved_parts`, and contract version metadata.
```

- [x] **Step 3: Commit**

```bash
git add tools/assetgen/README.md
git commit -m "docs(character-pipeline): add tooling guide for parts/archetypes/validator"
```

---

## Done-gate checklist (from the spec)

- [x] Wren regenerated through the new pipeline, byte-identical to Phase 1 output
      (Task 7's `test_character_migration.py`).
- [x] At least one additional archetype (`villager`) generated end-to-end with a
      distinct seed (Task 8).
- [x] Validator catches missing node, missing clip, and over-budget tri count in
      tests (Task 6); part-incompatibility is covered by `part_registry`'s
      `ValueError` on unknown part id (Task 3).
- [x] Full pytest suite green (Task 10).
- [x] Tooling doc written (Task 10).
- [x] Asset Inventory Matrix populated (Task 9).
