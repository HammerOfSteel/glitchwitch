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
