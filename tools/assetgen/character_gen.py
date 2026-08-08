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
    "villager": {
        "hips": (0.0, 0.40, 0.0), "torso": (0.0, 0.16, 0.0),
        "arm_l": (0.15, 0.10, 0.0), "arm_r": (-0.15, 0.10, 0.0),
        "head": (0.0, 0.20, 0.0), "hat": (0.0, 0.18, 0.0),
        "braid": (0.0, 0.0, 0.10),
        "boot_l": (0.08, 0.05, 0.0), "boot_r": (-0.08, 0.05, 0.0),
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
