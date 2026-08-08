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
