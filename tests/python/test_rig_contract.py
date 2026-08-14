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
