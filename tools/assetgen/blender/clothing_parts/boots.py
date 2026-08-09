"""Builds the 'boots' clothing piece: a pair of simple beveled+subsurfed foot
coverings, one per side (Mirror modifier, matching the ".L"/".R" convention
fixed in Chunk 1 Task 3 step 6), joined into a single 'boots' object."""
from __future__ import annotations

import bmesh
import bpy
from mathutils import Vector

from ..body_dims import DIMS


def build() -> bpy.types.Object:
    mesh = bpy.data.meshes.new("boots_mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(
        bm,
        vec=(
            DIMS["foot_length"] / 2,
            DIMS["hip_width"] / 2,
            DIMS["foot_length"] / 3,
        ),
        verts=bm.verts,
    )
    bmesh.ops.translate(
        bm,
        vec=Vector((DIMS["hip_width"] / 2, 0.0, 0.0)),
        verts=bm.verts,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("boots", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = (0.0, 0.0, DIMS["foot_length"] / 6)

    mirror = obj.modifiers.new("Mirror", "MIRROR")
    mirror.use_axis = (True, False, False)
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = DIMS["bevel_width"]
    bevel.segments = DIMS["bevel_segments"]
    subsurf = obj.modifiers.new("Subsurf", "SUBSURF")
    subsurf.levels = DIMS["subsurf_levels"]
    return obj
