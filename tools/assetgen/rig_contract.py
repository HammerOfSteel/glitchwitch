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
