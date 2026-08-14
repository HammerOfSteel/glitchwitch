"""Parses an exported character .glb directly (JSON chunk only) and asserts
the bone-hierarchy/skinning/bounding-box/tri-budget/clip-name gate described
in the spec's Testing section — the automated check that would have caught
the "floating disconnected villager" class of bug (correct-looking parts,
wrong connectivity or scale) automatically instead of relying on a human
looking at a screenshot.

Deliberately has no `import bpy` — this operates on the exported file's bytes,
so it's plain-Python testable (see this task's test file for hand-built GLB
fixtures) and can also be run standalone against any already-built .glb
without needing Blender at all.
"""
from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field

from .archetype_spec import KNOWN_BONES

TRI_BUDGET = 1500
EXPECTED_CLIP_NAMES = frozenset({"idle-loop", "walk-loop", "run-loop", "wave", "stir"})
MIN_HEIGHT_M = 0.5  # a character shorter than this is almost certainly a bug
MAX_HEIGHT_M = 2.5


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)


def _parse_glb_json_chunk(glb_bytes: bytes) -> dict:
    magic, version, length = struct.unpack_from("<III", glb_bytes, 0)
    if magic != 0x46546C67:
        raise ValueError("not a GLB file (bad magic)")
    chunk_length, chunk_type = struct.unpack_from("<II", glb_bytes, 12)
    if chunk_type != 0x4E4F534A:  # "JSON"
        raise ValueError("first GLB chunk is not JSON")
    json_bytes = glb_bytes[20:20 + chunk_length]
    return json.loads(json_bytes.decode("utf-8"))


def _check_bone_hierarchy(gltf: dict, errors: list[str]) -> None:
    """Every mandatory bone name from KNOWN_BONES (Chunk 1/2's armature
    convention) must be present among exported node names, and the root
    (Hips) must have at least one child. This is the direct check for an
    armature that got exported disconnected from the rest of the rig (as
    opposed to the bounding-box height check below, which only catches
    disconnection indirectly, via an implausible resulting size).
    """
    node_names = {n.get("name") for n in gltf.get("nodes", [])}
    missing_bones = KNOWN_BONES - node_names
    for bone in sorted(missing_bones):
        errors.append(f"missing expected bone {bone!r} in exported node hierarchy")

    hips_nodes = [n for n in gltf.get("nodes", []) if n.get("name") == "Hips"]
    if hips_nodes and not hips_nodes[0].get("children"):
        errors.append("Hips node has no children — armature hierarchy looks disconnected")


def _check_skinning(gltf: dict, errors: list[str]) -> None:
    """Every mesh primitive must be skinned (JOINTS_0/WEIGHTS_0 attributes
    present). An unskinned mesh is exactly the "floating disconnected
    villager" bug: a correct-looking mesh sitting in the scene with no bone
    deformation wired up at all, which the bounding-box/tri checks alone
    would not catch (an unskinned mesh can still have a perfectly plausible
    height and tri count).
    """
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            attrs = prim.get("attributes", {})
            if "JOINTS_0" not in attrs or "WEIGHTS_0" not in attrs:
                errors.append(
                    "mesh primitive is missing JOINTS_0/WEIGHTS_0 attributes "
                    "— not skinned to the armature"
                )


def _count_tris(gltf: dict) -> int:
    """Mode 4 = TRIANGLES. Prefer the primitive's `indices` accessor count
    (glTF's indexed-triangle-list convention, which is what Blender's glTF
    exporter always produces) over the raw POSITION vertex count — POSITION
    holds deduplicated vertices shared across faces, so `POSITION.count / 3`
    undercounts (or is simply wrong) for any indexed mesh. Only fall back to
    POSITION/3 for a primitive with no `indices` (a non-indexed export,
    which this pipeline doesn't produce but which is valid glTF).
    """
    total_tris = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            if prim.get("mode", 4) != 4:
                continue
            if "indices" in prim:
                accessor = gltf["accessors"][prim["indices"]]
                total_tris += accessor["count"] // 3
            else:
                accessor_index = prim.get("attributes", {}).get("POSITION")
                if accessor_index is None:
                    continue
                accessor = gltf["accessors"][accessor_index]
                total_tris += accessor["count"] // 3
    return total_tris


def check(glb_bytes: bytes) -> ValidationReport:
    errors: list[str] = []
    gltf = _parse_glb_json_chunk(glb_bytes)

    # Clip-name check.
    actual_clip_names = {a.get("name") for a in gltf.get("animations", [])}
    missing_clips = EXPECTED_CLIP_NAMES - actual_clip_names
    for clip in sorted(missing_clips):
        errors.append(f"missing expected animation clip {clip!r}")
    extra_clips = actual_clip_names - EXPECTED_CLIP_NAMES
    for clip in sorted(extra_clips):
        errors.append(f"unexpected animation clip {clip!r} (not in avatar.gd's contract)")

    _check_bone_hierarchy(gltf, errors)
    _check_skinning(gltf, errors)

    total_tris = _count_tris(gltf)
    if total_tris > TRI_BUDGET:
        errors.append(f"tri count {total_tris} exceeds budget of {TRI_BUDGET}")

    # Bounding-box / proportion check: walk only the POSITION accessor of
    # each mesh primitive (not every VEC3 accessor in the file — normals,
    # tangents, and morph-target deltas are also VEC3 and would corrupt this
    # if scanned indiscriminately) and take the overall Y-axis span as
    # "standing height."
    y_min, y_max = None, None
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            accessor_index = prim.get("attributes", {}).get("POSITION")
            if accessor_index is None:
                continue
            accessor = gltf["accessors"][accessor_index]
            if accessor.get("type") != "VEC3" or "min" not in accessor or "max" not in accessor:
                continue
            lo, hi = accessor["min"][1], accessor["max"][1]
            y_min = lo if y_min is None else min(y_min, lo)
            y_max = hi if y_max is None else max(y_max, hi)
    if y_min is None:
        errors.append("no POSITION accessor with bounding-box min/max found")
    else:
        height = y_max - y_min
        if height < MIN_HEIGHT_M:
            errors.append(
                f"bounding-box height {height:.3f}m is below the minimum "
                f"plausible height {MIN_HEIGHT_M}m — likely a disconnected/"
                "collapsed mesh"
            )
        elif height > MAX_HEIGHT_M:
            errors.append(
                f"bounding-box height {height:.3f}m exceeds the maximum "
                f"plausible height {MAX_HEIGHT_M}m"
            )

    return ValidationReport(ok=not errors, errors=errors)


def check_file(path: str) -> ValidationReport:
    """Convenience wrapper: read a .glb file from disk and check() it."""
    with open(path, "rb") as f:
        return check(f.read())
