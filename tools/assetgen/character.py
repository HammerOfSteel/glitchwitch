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
    root_name="wren",
)


def build_rig():
    """Wren's rig — thin wrapper kept for backward-compatible imports."""
    rig, _clips = character_gen.generate(WREN_SPEC)
    return rig


def build_animations():
    """Wren's animation clips — thin wrapper kept for backward-compatible imports."""
    _rig, clips = character_gen.generate(WREN_SPEC)
    return clips


def flattened_builder():
    """Rest-pose merge of Wren's rig for budgets/preview renders."""
    rig, _clips = character_gen.generate(WREN_SPEC)
    return character_gen.flatten_rig(rig)
