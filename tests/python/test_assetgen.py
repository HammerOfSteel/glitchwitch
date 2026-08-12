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


def _signed_volume(builder: mesh.MeshBuilder) -> float:
    """Divergence-theorem volume: positive iff faces wind outward."""
    total = 0.0
    for t in range(builder.tri_count):
        i0, i1, i2 = builder.indices[3 * t:3 * t + 3]
        p0 = builder.positions[i0]
        p1 = builder.positions[i1]
        p2 = builder.positions[i2]
        cx = p1[1] * p2[2] - p1[2] * p2[1]
        cy = p1[2] * p2[0] - p1[0] * p2[2]
        cz = p1[0] * p2[1] - p1[1] * p2[0]
        total += (p0[0] * cx + p0[1] * cy + p0[2] * cz) / 6.0
    return total


def test_box_winds_outward():
    builder = mesh.MeshBuilder()
    mesh.add_box(builder, (0, 0, 0), (1, 2, 3), "wood", 1)
    volume = _signed_volume(builder)
    assert abs(volume - 6.0) < 0.01, volume  # 1*2*3, positive


def test_cylinder_winds_outward():
    builder = mesh.MeshBuilder()
    mesh.add_cylinder(builder, (0, 0, 0), 1.0, 2.0, 24, "stone", 1)
    volume = _signed_volume(builder)
    expected = math.pi * 2.0  # approximated by 24 segments, slightly less
    assert volume > expected * 0.9, volume


def test_cone_winds_outward():
    builder = mesh.MeshBuilder()
    mesh.add_cone(builder, (0, 0, 0), 1.0, 3.0, 24, "pine", 1)
    volume = _signed_volume(builder)
    expected = math.pi / 3.0 * 3.0
    assert volume > expected * 0.85, volume


@pytest.mark.parametrize(
    "name", ["crate", "ground_tile", "pine", "jar", "planter", "rock", "well",
              "interior_wall", "interior_floor", "hearth", "table", "chair",
              "shelf", "bed", "hedge", "stone_stile", "lane_path", "signpost"]
)
def test_closed_props_have_positive_volume(name):
    volume = _signed_volume(props.build_prop(name, seed=0))
    assert volume > 0.0, f"{name}: negative signed volume {volume} (inward faces)"


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
    budget = props.HERO_TRI_BUDGET if name in props.HERO_PROPS else props.TRI_BUDGET
    assert builder.tri_count <= budget, (
        f"{name}: {builder.tri_count} tris over budget {budget}"
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


@pytest.mark.parametrize("name", ["grass_tuft", "flower"])
def test_scatter_props_export_as_single_primitive(name):
    doc = gltf.parse_glb(gltf.build_glb(props.build_prop(name, seed=0), name))["json"]
    assert len(doc["meshes"][0]["primitives"]) == 1


@pytest.mark.parametrize("name", ["cottage_wall", "cottage_corner", "cottage_roof"])
def test_cottage_kit_pieces_are_hero_props(name):
    # These pieces opt into the higher HERO_TRI_BUDGET allowance (see
    # HERO_PROPS in props.py) since a modular building kit has more surface
    # detail than a single small prop. They don't need to actually exceed
    # the regular TRI_BUDGET to justify the exception — the exception exists
    # so kit pieces have headroom to gain detail later without a fresh budget
    # negotiation, not because these specific placeholders demand it.
    assert name in props.HERO_PROPS
    builder = props.build_prop(name, seed=0)
    assert 0 < builder.tri_count <= props.HERO_TRI_BUDGET


def test_cottage_facade_quoins_are_proud_of_wall_face():
    # Regression: the quoin (corner post) boxes used to be sized so their
    # outer faces sat exactly flush (coplanar) with the stone wall shell's
    # own outer faces — at x = +/-width/2 and z = +/-depth/2. Perfectly
    # coplanar geometry z-fights (flickers) at render time, which is exactly
    # the "glitchy edges" reported at the cottage's corners. Quoins must
    # extend measurably past the wall face instead of sitting flush with it.
    #
    # Isolated to the y=0 (ground-corner) vertices in the quoin's own x/z
    # region (|x| > 1.9, near the corner) so unrelated geometry that also
    # touches y=0 near the wall face (door frame, foundation course) can't
    # mask a regression back to flush quoins.
    builder = props.build_prop("cottage_facade", seed=0)
    width, depth = 4.4, 3.4
    corner_base = [
        p for p in builder.positions if abs(p[1]) < 1e-6 and abs(p[0]) > 1.9
    ]
    assert corner_base, "expected quoin/wall geometry at the base corners"
    max_x = max(abs(p[0]) for p in corner_base)
    max_z = max(abs(p[2]) for p in corner_base)
    assert max_x > width / 2.0 + 0.03, "quoins are flush with (not proud of) the wall's X face"
    assert max_z > depth / 2.0 + 0.03, "quoins are flush with (not proud of) the wall's Z face"


def test_cottage_facade_foundation_course_is_proud_of_wall_face():
    # Regression: the foundation course box used to be sized exactly
    # width x depth — flush with the stone wall shell's own outer faces
    # all the way around the base perimeter. That coplanar geometry
    # z-fights (flickers) along the whole base of the cottage, which is
    # the most visible instance of the "glitchy edges" reported. The
    # foundation must be proud of the wall face (like the first-floor
    # stringcourse already is), not flush with it.
    builder = props.build_prop("cottage_facade", seed=0)
    width, depth = 4.4, 3.4
    foundation_band = [p for p in builder.positions if 1e-6 < p[1] <= 0.2]
    offenders = [
        p for p in foundation_band
        if abs(abs(p[0]) - width / 2.0) < 1e-6 or abs(abs(p[2]) - depth / 2.0) < 1e-6
    ]
    assert not offenders, (
        f"foundation course is flush with the wall's outer face: {offenders}"
    )
