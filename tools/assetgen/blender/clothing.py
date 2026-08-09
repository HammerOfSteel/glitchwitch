"""Adds and binds clothing/hair geometry to the loaded base armature, per an
ArchetypeSpec's `clothing` list. Delegates the actual mesh-building for each
named piece to tools/assetgen/blender/clothing_parts/<piece>.py — this module
only knows how to look a piece up, build it, apply the same bevel+subsurf
authoring style check, and bind it to the armature. Adding a new piece means
adding a new clothing_parts/ file and one PART_BUILDERS entry, not editing the
add/bind logic here.
"""
from __future__ import annotations

import bpy

from .archetype_spec import ArchetypeSpec
from .clothing_parts import boots, tunic

PART_BUILDERS = {
    "tunic": tunic.build,
    "boots": boots.build,
}


class UnknownClothingPieceError(RuntimeError):
    pass


def apply(spec: ArchetypeSpec) -> dict:
    """Build and bind every clothing piece named in spec.clothing."""
    armature_obj = bpy.data.objects["Armature"]
    added = []
    for piece in spec.clothing:
        if piece not in PART_BUILDERS:
            raise UnknownClothingPieceError(
                f"no clothing_parts builder registered for {piece!r}; "
                f"known pieces: {sorted(PART_BUILDERS)}"
            )
        obj = PART_BUILDERS[piece]()
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        obj.parent_type = "ARMATURE"
        added.append(obj.name)
    return {"added_objects": added}
