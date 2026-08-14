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

RigPose = dict[str, tuple[float, float, float]]


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
    times = []
    values = []
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


def _idle(pose: RigPose, hat_tilt_deg: float) -> AnimationClip:
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


def _gait(name: str, pose: RigPose, hat_tilt_deg: float, duration: float, stride: float,
          lift: float, swing_deg: float, bob: float, lean_deg: float,
          sway_deg: float) -> AnimationClip:
    steps = 12
    omega = 2.0 * math.pi / duration
    hips = pose["hips"]
    boot_l = pose["boot_l"]
    boot_r = pose["boot_r"]

    def boot_fn(base, sign):
        def fn(t):
            phase = math.sin(omega * t) * sign
            height = max(0.0, phase) * lift
            return (base[0], base[1] + height, base[2] + stride * phase)
        return fn

    def hips_fn(t):
        return (
            hips[0],
            hips[1] + bob * (0.5 - 0.5 * math.cos(2.0 * omega * t)),
            hips[2],
        )

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
    times = [0.0, 0.25, 0.45, 0.65, 0.85, 1.05, 1.2]
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


def build_baseline_clips(pose: RigPose, hat_tilt_deg: float = 0.0,
                         profile: str = "default") -> list[AnimationClip]:
    """Build the clip set for `profile`.

    `pose` maps node name -> rest translation for hips/boot_l/boot_r (required
    for every profile).
    """
    wanted = BASELINE_PROFILE_CLIPS.get(profile, BASELINE_PROFILE_CLIPS["default"])
    builders = {
        "idle": lambda: _idle(pose, hat_tilt_deg),
        "walk": lambda: _gait(
            "walk-loop", pose, hat_tilt_deg, 0.8, 0.07, 0.03, 14.0, 0.012, 3.0, 3.0
        ),
        "run": lambda: _gait(
            "run-loop", pose, hat_tilt_deg, 0.5, 0.10, 0.05, 25.0, 0.025, 8.0, 4.0
        ),
        "wave": _wave,
        "stir": _stir,
    }
    return [builders[key]() for key in wanted]
