"""Bakes the five mandatory clips (idle, walk, run, wave, stir) as Blender
Actions on the loaded base armature, named to satisfy avatar.gd's exact
contract: idle-loop/walk-loop/run-loop (looping motion clips) and wave/stir
(bare, one-shot gestures) — see this chunk's header note on why `stir` is
deliberately NOT "stir-loop" (a v1 animation_contract.py bug this module does
not repeat).

Poses are simple, new-rig-appropriate keyframe animations (not a literal port
of v1's animation_contract.py, which references bones — hat, braid — that
don't exist on this base armature; hat/braid-equivalent accessory animation,
if any archetype needs it, is layered on top later as archetype-specific
clothing-bone animation, out of scope for this baseline bake). All angles are
in degrees, converted to radians for Blender's rotation_euler.
"""
from __future__ import annotations

import math

import bpy

from .archetype_spec import ArchetypeSpec

FPS = 24


class UnknownClipError(RuntimeError):
    pass


def _new_action(name: str) -> bpy.types.Action:
    action = bpy.data.actions.new(name)
    return action


def _keyframe(
    pose_bone, frame: int, euler_deg: tuple[float, float, float]
) -> None:
    pose_bone.rotation_mode = "XYZ"
    pose_bone.rotation_euler = tuple(math.radians(d) for d in euler_deg)
    pose_bone.keyframe_insert(data_path="rotation_euler", frame=frame)


def _bake_idle(armature_obj) -> bpy.types.Action:
    action = _new_action("idle-loop")
    armature_obj.animation_data.action = action
    duration_frames = int(2.4 * FPS)
    torso = armature_obj.pose.bones["Spine"]
    arm_l = armature_obj.pose.bones["Arm.L"]
    arm_r = armature_obj.pose.bones["Arm.R"]
    for frame in range(duration_frames + 1):
        t = frame / FPS
        breathe = 1.8 * math.sin(2 * math.pi * t / 2.4)
        _keyframe(torso, frame, (breathe, 0.0, 0.0))
        _keyframe(
            arm_l, frame, (2.0 * math.sin(2 * math.pi * t / 2.4), 0.0, 0.0)
        )
        _keyframe(
            arm_r, frame, (-2.0 * math.sin(2 * math.pi * t / 2.4), 0.0, 0.0)
        )
    return action


def _bake_gait(
    armature_obj, name: str, duration: float, swing_deg: float
) -> bpy.types.Action:
    action = _new_action(name)
    armature_obj.animation_data.action = action
    duration_frames = int(duration * FPS)
    leg_l = armature_obj.pose.bones["UpLeg.L"]
    leg_r = armature_obj.pose.bones["UpLeg.R"]
    arm_l = armature_obj.pose.bones["Arm.L"]
    arm_r = armature_obj.pose.bones["Arm.R"]
    for frame in range(duration_frames + 1):
        t = frame / FPS
        phase = math.sin(2 * math.pi * t / duration)
        _keyframe(leg_l, frame, (swing_deg * phase, 0.0, 0.0))
        _keyframe(leg_r, frame, (-swing_deg * phase, 0.0, 0.0))
        _keyframe(arm_l, frame, (-swing_deg * phase, 0.0, 0.0))
        _keyframe(arm_r, frame, (swing_deg * phase, 0.0, 0.0))
    return action


def _bake_wave(armature_obj) -> bpy.types.Action:
    action = _new_action("wave")
    armature_obj.animation_data.action = action
    arm_r = armature_obj.pose.bones["Arm.R"]
    keyframes = [
        (0, (0.0, 0.0, 0.0)),
        (6, (0.0, 0.0, 150.0)),
        (12, (0.0, 0.0, 130.0)),
        (16, (0.0, 0.0, 150.0)),
        (22, (0.0, 0.0, 130.0)),
        (29, (0.0, 0.0, 0.0)),
    ]
    for frame, euler_deg in keyframes:
        _keyframe(arm_r, frame, euler_deg)
    return action


def _bake_stir(armature_obj) -> bpy.types.Action:
    action = _new_action("stir")
    armature_obj.animation_data.action = action
    duration_frames = int(1.6 * FPS)
    fore_arm_r = armature_obj.pose.bones["ForeArm.R"]
    for frame in range(duration_frames + 1):
        t = frame / FPS
        pitch = 30.0 + 18.0 * math.sin(2 * math.pi * t / 1.6)
        _keyframe(fore_arm_r, frame, (pitch, 0.0, 0.0))
    return action


_CLIP_BUILDERS = {
    "idle": _bake_idle,
    "walk": lambda armature_obj: _bake_gait(armature_obj, "walk-loop", 0.8, 14.0),
    "run": lambda armature_obj: _bake_gait(armature_obj, "run-loop", 0.5, 25.0),
    "wave": _bake_wave,
    "stir": _bake_stir,
}


def bake(spec: ArchetypeSpec) -> dict:
    """Bake every clip named in spec.clips as a Blender Action on the loaded
    armature. Returns {"baked": [action_name, ...]} in the exact Godot-facing
    names (idle-loop, walk-loop, run-loop, wave, stir), in spec.clips order.

    Raises UnknownClipError naming the clip if spec.clips references something
    not in _CLIP_BUILDERS (ArchetypeSpec itself only checks the 5 mandatory
    clips are present, not that every listed clip is buildable — mirrors
    clothing.py's UnknownClothingPieceError pattern for the same reason).
    """
    armature_obj = bpy.data.objects["Armature"]
    if armature_obj.animation_data is None:
        armature_obj.animation_data_create()
    baked = []
    for clip in spec.clips:
        if clip not in _CLIP_BUILDERS:
            raise UnknownClipError(
                f"no animate.py builder registered for clip {clip!r}; "
                f"known clips: {sorted(_CLIP_BUILDERS)}"
            )
        action = _CLIP_BUILDERS[clip](armature_obj)
        baked.append(action.name)
    return {"baked": baked}
