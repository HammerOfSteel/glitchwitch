"""Builds the 'tunic' clothing piece: a simple beveled+subsurfed torso wrap,
sized to sit just outside the base body mesh's torso silhouette so it reads as
a garment rather than a re-skinned body part."""
from __future__ import annotations

import bmesh
import bpy

from ..body_dims import DIMS

_MARGIN = 0.02


def build() -> bpy.types.Object:
    mesh = bpy.data.meshes.new("tunic_mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(
        bm,
        vec=(
            DIMS["torso_width"] / 2 + _MARGIN,
            (DIMS["torso_width"] * 0.7) / 2 + _MARGIN,
            DIMS["torso_height"] / 2 + _MARGIN,
        ),
        verts=bm.verts,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("tunic", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (
        0.0,
        0.0,
        DIMS["upper_leg_length"] + DIMS["lower_leg_length"] + DIMS["torso_height"] / 2,
    )

    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = DIMS["bevel_width"]
    bevel.segments = DIMS["bevel_segments"]
    subsurf = obj.modifiers.new("Subsurf", "SUBSURF")
    subsurf.levels = DIMS["subsurf_levels"]
    return obj
