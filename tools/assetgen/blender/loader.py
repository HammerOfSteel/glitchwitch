"""Load and validate the shared Blender base humanoid asset.

This is the drift guard for `base_humanoid.blend`: every downstream unit
assumes a specific mesh object, armature object, and bone naming contract, so
we fail loudly if the authored base asset is renamed or otherwise malformed.
"""
from __future__ import annotations

from pathlib import Path

import bpy

from .archetype_spec import KNOWN_BONES

BASE_BLEND_PATH = Path(__file__).resolve().parent / "base_humanoid.blend"

EXPECTED_MESH_OBJECT = "body"
EXPECTED_ARMATURE_OBJECT = "Armature"


class BaseAssetStructureError(RuntimeError):
    pass


def load_base(path: Path = BASE_BLEND_PATH) -> dict:
    """Open the base .blend file in the current Blender session and validate it."""
    bpy.ops.wm.open_mainfile(filepath=str(path))
    return assert_structure()


def assert_structure() -> dict:
    """Validate the loaded scene's object/bone contract and return a summary."""
    object_names = sorted(obj.name for obj in bpy.data.objects)
    if EXPECTED_MESH_OBJECT not in bpy.data.objects:
        raise BaseAssetStructureError(
            f"expected mesh object '{EXPECTED_MESH_OBJECT}' not found; "
            f"found objects: {object_names}"
        )
    if EXPECTED_ARMATURE_OBJECT not in bpy.data.objects:
        raise BaseAssetStructureError(
            f"expected armature object '{EXPECTED_ARMATURE_OBJECT}' not found; "
            f"found objects: {object_names}"
        )

    mesh_obj = bpy.data.objects[EXPECTED_MESH_OBJECT]
    if mesh_obj.type != "MESH":
        raise BaseAssetStructureError(
            f"expected mesh object '{EXPECTED_MESH_OBJECT}' to be type 'MESH'; "
            f"found type '{mesh_obj.type}'"
        )

    armature_obj = bpy.data.objects[EXPECTED_ARMATURE_OBJECT]
    if armature_obj.type != "ARMATURE":
        raise BaseAssetStructureError(
            f"expected armature object '{EXPECTED_ARMATURE_OBJECT}' to be type "
            f"'ARMATURE'; found type '{armature_obj.type}'"
        )
    actual_bones = {bone.name for bone in armature_obj.data.bones}
    missing = KNOWN_BONES - actual_bones
    if missing:
        raise BaseAssetStructureError(
            f"armature missing expected bone(s): {sorted(missing)}; "
            f"found: {sorted(actual_bones)}"
        )
    return {
        "mesh_object": EXPECTED_MESH_OBJECT,
        "armature_object": EXPECTED_ARMATURE_OBJECT,
        "bone_names": sorted(actual_bones),
    }
