"""Maps ArchetypeSpec.palette cell assignments onto each named object: every UV
coordinate is set to a single palette-cell center point (matching v1's
tools/assetgen/mesh.py MeshBuilder.add_face contract exactly — a flat-color
face samples one point, no gradient), and the object's material samples
assets/generated/palette_main.png (the same atlas PNG build.py already
generates via tools/assetgen/palette.build_palette_png() — see build.py's
existing palette-generation step). No new texture painting; this only wires up
the existing atlas.
"""
from __future__ import annotations

from pathlib import Path

import bpy

from .. import palette
from .archetype_spec import ArchetypeSpec

REPO_ROOT = Path(__file__).resolve().parents[3]
PALETTE_PNG_PATH = REPO_ROOT / "assets" / "generated" / "palette_main.png"
_SHARED_MATERIAL_NAME = "palette_atlas"


def _get_shared_material() -> bpy.types.Material:
    """One material shared by every object across every archetype build — they
    all sample the same atlas texture, differing only by UV coordinate, so a
    single material avoids creating one per (ramp, shade) combination."""
    material = bpy.data.materials.get(_SHARED_MATERIAL_NAME)
    if material is not None:
        return material
    if not PALETTE_PNG_PATH.exists():
        raise FileNotFoundError(
            f"{PALETTE_PNG_PATH} not found — build.py must generate "
            "assets/generated/palette_main.png (tools.assetgen.palette."
            "build_palette_png()) before running the Blender character build."
        )
    material = bpy.data.materials.new(_SHARED_MATERIAL_NAME)
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    tex_node = material.node_tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(str(PALETTE_PNG_PATH))
    tex_node.interpolation = "Closest"
    material.node_tree.links.new(
        tex_node.outputs["Color"], bsdf.inputs["Base Color"]
    )
    return material


def _set_flat_uv(obj: bpy.types.Object, uv: tuple[float, float]) -> None:
    uv_layer = obj.data.uv_layers.active or obj.data.uv_layers.new()
    for loop in uv_layer.data:
        loop.uv = uv


def apply(spec: ArchetypeSpec) -> dict:
    """Assign each spec.palette[object_name] = (ramp, shade) cell to that
    object: every UV coordinate becomes the cell's single center point, and
    the object's material is set to the shared palette_atlas material.

    Returns {"assigned": {object_name: [ramp, shade], ...}}. Validates every
    (ramp, shade) pair up front (raising KeyError/ValueError from
    palette.cell_uv, unwrapped, on the first invalid one) before touching any
    Blender object state, so a bad archetype spec never leaves a half-applied
    scene.
    """
    uvs = {
        obj_name: palette.cell_uv(ramp, shade)
        for obj_name, (ramp, shade) in spec.palette.items()
    }
    material = _get_shared_material()
    assigned = {}
    for obj_name, (ramp, shade) in spec.palette.items():
        obj = bpy.data.objects[obj_name]
        _set_flat_uv(obj, uvs[obj_name])
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
        assigned[obj_name] = [ramp, shade]
    return {"assigned": assigned}
