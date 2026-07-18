"""Mesh kit + GLB exporter + props: structure, budgets, determinism."""
from __future__ import annotations

import math

import pytest

from tools.assetgen import gltf, mesh, props


# --- mesh kit ---------------------------------------------------------------

def test_box_has_twelve_triangles():
    builder = mesh.MeshBuilder()
    mesh.add_box(builder, (0, 0, 0), (1, 1, 1), "wood", 1)
    assert builder.tri_count == 12
    assert builder.vertex_count == 24  # 6 faces * 4 flat-shaded verts


def test_face_normals_are_unit_length():
    builder = mesh.MeshBuilder()
    mesh.add_cone(builder, (0, 0, 0), 0.5, 1.0, 9, "pine", 1)
    for normal in builder.normals:
        length = math.sqrt(sum(c * c for c in normal))
        assert abs(length - 1.0) < 1e-3


def test_merge_offsets_positions_and_indices():
    a = mesh.MeshBuilder()
    mesh.add_box(a, (0, 0, 0), (1, 1, 1), "wood", 1)
    b = mesh.MeshBuilder()
    mesh.add_box(b, (0, 0, 0), (1, 1, 1), "wood", 1)
    a.merge(b, offset=(5.0, 0.0, 0.0))
    assert a.tri_count == 24
    assert max(i for i in a.indices) == a.vertex_count - 1
    xs = [p[0] for p in a.positions[24:]]
    assert min(xs) >= 4.0


def test_lathe_rejects_short_profiles():
    builder = mesh.MeshBuilder()
    with pytest.raises(ValueError):
        mesh.add_lathe(builder, [(1.0, 0.0)], 8, "wood", 1)


# --- glb exporter -----------------------------------------------------------

def test_glb_roundtrip_structure():
    builder = props.build_prop("mug")
    glb = gltf.build_glb(builder, "mug")
    parsed = gltf.parse_glb(glb)
    doc = parsed["json"]

    assert doc["asset"]["version"] == "2.0"
    accessors = doc["accessors"]
    assert accessors[0]["count"] == builder.vertex_count          # POSITION
    assert accessors[1]["count"] == builder.vertex_count          # NORMAL
    assert accessors[2]["count"] == builder.vertex_count          # TEXCOORD_0
    assert accessors[3]["count"] == builder.tri_count * 3         # indices
    assert doc["meshes"][0]["primitives"][0]["mode"] == 4

    # bin blob is 4-aligned and large enough for all views
    assert len(parsed["bin"]) % 4 == 0
    for view in doc["bufferViews"]:
        assert view["byteOffset"] + view["byteLength"] <= len(parsed["bin"])


def test_glb_position_bounds_match_accessor_min_max():
    builder = props.build_prop("fence")
    doc = gltf.parse_glb(gltf.build_glb(builder, "fence"))["json"]
    mins = doc["accessors"][0]["min"]
    maxs = doc["accessors"][0]["max"]
    for axis in range(3):
        values = [p[axis] for p in builder.positions]
        assert abs(mins[axis] - min(values)) < 1e-6
        assert abs(maxs[axis] - max(values)) < 1e-6


# --- props ------------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(props.PROPS))
def test_prop_builds_within_budget(name):
    builder = props.build_prop(name, seed=0)
    assert builder.tri_count > 0
    assert builder.tri_count <= props.TRI_BUDGET, (
        f"{name}: {builder.tri_count} tris over budget {props.TRI_BUDGET}"
    )
    assert len(builder.positions) == len(builder.normals) == len(builder.uvs)
    assert max(builder.indices) == builder.vertex_count - 1


@pytest.mark.parametrize("name", sorted(props.PROPS))
def test_prop_glb_is_deterministic(name):
    first = gltf.build_glb(props.build_prop(name, seed=0), name)
    second = gltf.build_glb(props.build_prop(name, seed=0), name)
    assert first == second, f"{name}: GLB bytes must be deterministic"


def test_pine_seed_variation_is_deterministic_per_seed():
    a1 = gltf.build_glb(props.build_prop("pine", seed=7), "pine")
    a2 = gltf.build_glb(props.build_prop("pine", seed=7), "pine")
    assert a1 == a2


def test_unknown_prop_raises():
    with pytest.raises(KeyError):
        props.build_prop("dragon")
