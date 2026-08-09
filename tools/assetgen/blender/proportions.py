"""Applies an ArchetypeSpec's bone_scales to the currently-loaded base armature.

No clothing, no materials, no animation — see architecture table's
responsibility split. Scaling is applied as pose-bone scale (not edit-mode bone
length changes) so it composes cleanly with the auto-weighted mesh deformation
already baked into base_humanoid.blend; it does not touch bones not listed in
bone_scales (they keep scale (1, 1, 1)).

Scope note: the spec's unit table describes this stage's input as "bone scale
factors / shape-key values" — shape-key-driven proportion variation (e.g.
smooth silhouette blends rather than rigid per-bone scaling) is intentionally
deferred; ArchetypeSpec only carries bone_scales for now (see
archetype_spec.py, Task 4). If bone scaling alone doesn't produce visually
acceptable per-archetype variation during Wren/villager migration (Chunk 5),
add shape-key support to ArchetypeSpec and this module then, rather than
building it speculatively now.
"""
from __future__ import annotations

import bpy

from .archetype_spec import ArchetypeSpec


def apply(spec: ArchetypeSpec) -> dict:
    """Scale each named bone in spec.bone_scales; leave all others untouched.

    Returns {"scaled_bones": {bone_name: factor, ...}} for test/log inspection.
    """
    armature_obj = bpy.data.objects["Armature"]
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="POSE")
    for bone_name, factor in spec.bone_scales.items():
        pose_bone = armature_obj.pose.bones[bone_name]
        pose_bone.scale = (factor, factor, factor)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"scaled_bones": dict(spec.bone_scales)}
