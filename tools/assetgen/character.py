"""Wren — the witch herself, generated as a segmented rigid-part character.

No skinning: each body part is a named node, and animation clips drive node
TRS channels (the Animal Crossing lineage). Clips ending in "-loop" get
looping enabled by Godot's importer naming convention.
"""
from __future__ import annotations

import math

from .gltf import AnimChannel, AnimationClip, SceneNode
from .mesh import MeshBuilder, add_box, add_cylinder, add_lathe

TRI_BUDGET = 1500

# base pose (node-local translations)
HIPS_POS = (0.0, 0.46, 0.0)
TORSO_POS = (0.0, 0.14, 0.0)
ARM_L_POS = (0.163, 0.12, 0.0)
ARM_R_POS = (-0.163, 0.12, 0.0)
HEAD_POS = (0.0, 0.22, 0.0)
HAT_POS = (0.0, 0.20, 0.0)
BRAID_POS = (0.0, 0.02, 0.12)
BOOT_L_POS = (0.09, 0.06, 0.0)
BOOT_R_POS = (-0.09, 0.06, 0.0)
HAT_TILT_DEG = 8.0


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


# --- part meshes -------------------------------------------------------------

def _skirt() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [(0.21, -0.36), (0.19, -0.20), (0.155, -0.06), (0.13, 0.06)]
    add_lathe(builder, profile, 10, "void_plum", 2, cap_start=True, cap_end=True)
    return builder


def _torso() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [(0.125, -0.08), (0.15, 0.02), (0.13, 0.10), (0.10, 0.18)]
    add_lathe(builder, profile, 10, "rust", 2, cap_start=True, cap_end=True)
    return builder


def _arm() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.12, 0.0), (0.075, 0.24, 0.075), "rust", 1)
    add_box(builder, (0.0, -0.27, 0.0), (0.06, 0.06, 0.06), "cream", 3)
    return builder


def _head() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [
        (0.0, -0.04), (0.10, -0.03), (0.14, 0.04), (0.13, 0.12), (0.08, 0.18), (0.0, 0.20),
    ]
    add_lathe(builder, profile, 10, "cream", 3)
    # eyes on the -Z face (forward)
    for x in (-0.05, 0.05):
        add_box(builder, (x, 0.06, -0.135), (0.022, 0.03, 0.012), "void_plum", 0)
    return builder


def _hat() -> MeshBuilder:
    builder = MeshBuilder()
    add_cylinder(builder, (0.0, 0.0, 0.0), 0.20, 0.03, 10, "void_plum", 1, shade_top=2)
    cone_profile = [(0.125, 0.015), (0.10, 0.14), (0.05, 0.24), (0.0, 0.30)]
    add_lathe(builder, cone_profile, 10, "void_plum", 1)
    # the glitch band — a wink of magenta
    add_cylinder(builder, (0.0, 0.045, 0.0), 0.132, 0.035, 10, "glitch_magenta", 2,
                 cap_bottom=False, cap_top=False)
    return builder


def _braid() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.02, 0.02), (0.06, 0.08, 0.06), "honey", 2)
    add_box(builder, (0.0, -0.10, 0.045), (0.05, 0.08, 0.05), "honey", 1)
    add_box(builder, (0.0, -0.17, 0.06), (0.035, 0.07, 0.035), "honey", 2)
    return builder


def _boot() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.0, -0.01), (0.10, 0.12, 0.16), "bark", 1, top=("bark", 2))
    return builder


def build_rig() -> SceneNode:
    """Wren's node tree with meshes attached at rest pose."""
    hat = SceneNode("hat", mesh=_hat(), translation=HAT_POS,
                    rotation=quat_axis("z", HAT_TILT_DEG))
    braid = SceneNode("braid", mesh=_braid(), translation=BRAID_POS)
    head = SceneNode("head", mesh=_head(), translation=HEAD_POS, children=[hat, braid])
    arm_l = SceneNode("arm_l", mesh=_arm(), translation=ARM_L_POS)
    arm_r = SceneNode("arm_r", mesh=_arm(), translation=ARM_R_POS)
    torso = SceneNode("torso", mesh=_torso(), translation=TORSO_POS,
                      children=[arm_l, arm_r, head])
    hips = SceneNode("hips", mesh=_skirt(), translation=HIPS_POS, children=[torso])
    boot_l = SceneNode("boot_l", mesh=_boot(), translation=BOOT_L_POS)
    boot_r = SceneNode("boot_r", mesh=_boot(), translation=BOOT_R_POS)
    return SceneNode("wren", children=[hips, boot_l, boot_r])


# --- animation authoring ------------------------------------------------------

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


def _idle() -> AnimationClip:
    duration, steps = 2.4, 12
    omega = 2.0 * math.pi / duration

    def breathe(t):
        return (HIPS_POS[0], HIPS_POS[1] + 0.006 * math.sin(omega * t), HIPS_POS[2])

    return AnimationClip("idle-loop", [
        _pos_channel("hips", duration, steps, breathe),
        _rot_channel("torso", duration, steps,
                     lambda t: quat_axis("x", 1.8 * math.sin(omega * t))),
        _rot_channel("arm_l", duration, steps,
                     lambda t: quat_axis("x", 2.0 * math.sin(omega * t))),
        _rot_channel("arm_r", duration, steps,
                     lambda t: quat_axis("x", -2.0 * math.sin(omega * t))),
        _rot_channel("hat", duration, steps,
                     lambda t: quat_axis("z", HAT_TILT_DEG + 1.5 * math.sin(omega * t))),
        _rot_channel("braid", duration, steps,
                     lambda t: quat_axis("x", 3.0 * math.sin(omega * t + 0.8))),
    ])


def _gait(name: str, duration: float, stride: float, lift: float, swing_deg: float,
          bob: float, lean_deg: float, sway_deg: float) -> AnimationClip:
    steps = 12
    omega = 2.0 * math.pi / duration

    def boot_fn(base, sign):
        def fn(t):
            phase = math.sin(omega * t) * sign
            height = max(0.0, phase) * lift
            return (base[0], base[1] + height, base[2] + stride * phase)
        return fn

    def hips_fn(t):
        return (
            HIPS_POS[0],
            HIPS_POS[1] + bob * (0.5 - 0.5 * math.cos(2.0 * omega * t)),
            HIPS_POS[2],
        )

    return AnimationClip(name, [
        _pos_channel("boot_l", duration, steps, boot_fn(BOOT_L_POS, 1.0)),
        _pos_channel("boot_r", duration, steps, boot_fn(BOOT_R_POS, -1.0)),
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
                     lambda t: quat_axis("z", HAT_TILT_DEG + 2.0 * math.sin(omega * t))),
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


def build_animations():
    return [
        _idle(),
        _gait("walk-loop", 0.8, 0.07, 0.03, 14.0, 0.012, 3.0, 3.0),
        _gait("run-loop", 0.5, 0.10, 0.05, 25.0, 0.025, 8.0, 4.0),
        _wave(),
        _stir(),
    ]


def flattened_builder() -> MeshBuilder:
    """Rest-pose merge of all parts (for budgets and preview renders)."""
    merged = MeshBuilder()

    def rotate_point(quat, point):
        if quat is None:
            return point
        qx, qy, qz, qw = quat
        # v' = v + 2*q_vec x (q_vec x v + w*v)
        ux, uy, uz = qy * point[2] - qz * point[1], qz * point[0] - qx * point[2], \
            qx * point[1] - qy * point[0]
        ux, uy, uz = ux + qw * point[0], uy + qw * point[1], uz + qw * point[2]
        cx, cy, cz = qy * uz - qz * uy, qz * ux - qx * uz, qx * uy - qy * ux
        return (point[0] + 2.0 * cx, point[1] + 2.0 * cy, point[2] + 2.0 * cz)

    def walk(node, base):
        origin = tuple(base[i] + node.translation[i] for i in range(3))
        if node.mesh is not None:
            for face_start in range(0, len(node.mesh.indices), 3):
                idx = node.mesh.indices[face_start:face_start + 3]
                points = []
                for i in idx:
                    local = rotate_point(node.rotation, node.mesh.positions[i])
                    points.append(tuple(local[k] + origin[k] for k in range(3)))
                ramp_shade = _uv_to_cell(node.mesh.uvs[idx[0]])
                merged.add_face(points, ramp_shade[0], ramp_shade[1])
        for child in node.children:
            walk(child, origin)

    walk(build_rig(), (0.0, 0.0, 0.0))
    return merged


def _uv_to_cell(uv):
    from . import palette
    width, height = palette.atlas_size_px()
    col = int(uv[0] * width) // palette.CELL_PX
    row = int(uv[1] * height) // palette.CELL_PX
    return palette.RAMPS[row][0], min(col, palette.SHADES - 1)
