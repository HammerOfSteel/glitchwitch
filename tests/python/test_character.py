"""Wren the witch: rig structure, clip validity, budgets, determinism."""
from __future__ import annotations

import math

import pytest

from tools.assetgen import character, gltf

EXPECTED_NODES = {
    "wren", "hips", "torso", "arm_l", "arm_r", "head", "hat", "braid",
    "boot_l", "boot_r",
}
EXPECTED_CLIPS = {"idle-loop", "walk-loop", "run-loop", "wave", "stir-loop"}
LOOP_CLIPS = {"idle-loop", "walk-loop", "run-loop", "stir-loop"}


def _build():
    return gltf.build_scene_glb(character.build_rig(), character.build_animations(), "wren")


def test_wren_glb_is_deterministic():
    assert _build() == _build()


def test_rig_contains_expected_nodes():
    doc = gltf.parse_glb(_build())["json"]
    names = {node["name"] for node in doc["nodes"]}
    assert EXPECTED_NODES <= names


def test_all_clips_present_with_sane_durations():
    clips = {clip.name: clip for clip in character.build_animations()}
    assert set(clips) == EXPECTED_CLIPS
    assert clips["idle-loop"].duration == pytest.approx(2.4, abs=0.01)
    assert clips["walk-loop"].duration == pytest.approx(0.8, abs=0.01)
    assert clips["run-loop"].duration == pytest.approx(0.5, abs=0.01)
    assert clips["stir-loop"].duration == pytest.approx(1.6, abs=0.01)
    assert clips["wave"].duration == pytest.approx(1.2, abs=0.01)


def test_channels_target_existing_nodes_and_match_lengths():
    doc = gltf.parse_glb(_build())["json"]
    node_count = len(doc["nodes"])
    accessors = doc["accessors"]
    for animation in doc["animations"]:
        for channel in animation["channels"]:
            assert 0 <= channel["target"]["node"] < node_count
            sampler = animation["samplers"][channel["sampler"]]
            input_acc = accessors[sampler["input"]]
            output_acc = accessors[sampler["output"]]
            assert input_acc["count"] == output_acc["count"]
            assert "min" in input_acc and "max" in input_acc
            expected_type = "VEC4" if channel["target"]["path"] == "rotation" else "VEC3"
            assert output_acc["type"] == expected_type


def test_rotation_keyframes_are_unit_quaternions():
    for clip in character.build_animations():
        for channel in clip.channels:
            if channel.path != "rotation":
                continue
            for quat in channel.values:
                length = math.sqrt(sum(c * c for c in quat))
                assert abs(length - 1.0) < 1e-4, (clip.name, channel.node_name)


def test_loop_clips_close_their_cycles():
    for clip in character.build_animations():
        if clip.name not in LOOP_CLIPS:
            continue
        for channel in clip.channels:
            first, last = channel.values[0], channel.values[-1]
            for a, b in zip(first, last):
                assert abs(a - b) < 1e-4, (
                    f"{clip.name}/{channel.node_name}/{channel.path} does not close"
                )


def test_flattened_tri_budget():
    builder = character.flattened_builder()
    assert 200 < builder.tri_count <= character.TRI_BUDGET, builder.tri_count


def test_animation_channel_rejects_unknown_node():
    bad_clip = gltf.AnimationClip("bad", [
        gltf.AnimChannel("no_such_node", "rotation", [0.0], [(0, 0, 0, 1)]),
    ])
    with pytest.raises(ValueError):
        gltf.build_scene_glb(character.build_rig(), [bad_clip], "bad")
