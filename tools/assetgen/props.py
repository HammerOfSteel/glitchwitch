"""Proof props for the Phase 0 look-dev diorama.

Every generator is deterministic: variation comes only from an explicit seed
fed through random.Random. Budgets are asserted in tests (<= 600 tris).
"""
from __future__ import annotations

import math
import random

from .mesh import MeshBuilder, add_box, add_cone, add_cylinder, add_lathe
from . import palette


def build_ground_tile(_seed: int = 0) -> MeshBuilder:
    """2x2 m grass tile with a soft dirt skirt."""
    builder = MeshBuilder()
    add_box(builder, (0, -0.1, 0), (2.0, 0.2, 2.0), "wood", 0,
            top=("moss", 2), bottom=("bark", 0))
    return builder


def build_crate(_seed: int = 0) -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0, 0.3, 0), (0.6, 0.6, 0.6), "wood", 2, top=("wood", 3))
    # edge slats
    for x in (-0.28, 0.28):
        for z in (-0.28, 0.28):
            add_box(builder, (x, 0.3, z), (0.08, 0.64, 0.08), "wood", 1)
    return builder


def build_fence(_seed: int = 0) -> MeshBuilder:
    """One fence segment: two posts, two rails."""
    builder = MeshBuilder()
    for x in (-0.5, 0.5):
        add_box(builder, (x, 0.45, 0), (0.1, 0.9, 0.1), "wood", 1, top=("wood", 2))
    for y in (0.35, 0.65):
        add_box(builder, (0, y, 0), (1.1, 0.08, 0.06), "wood", 2)
    return builder


def build_mug(_seed: int = 0) -> MeshBuilder:
    """The witch's tea mug — lathed body with a chunky handle."""
    builder = MeshBuilder()
    profile = [
        (0.0, 0.0),      # bottom center
        (0.16, 0.0),     # bottom edge
        (0.18, 0.06),    # belly
        (0.17, 0.26),    # wall
        (0.13, 0.28),    # lip inward (top face ring)
        (0.13, 0.06),    # inner wall down
        (0.0, 0.06),     # inner bottom
    ]
    add_lathe(builder, profile, 10, "ceramic", 2, shade_top=None)
    # handle: three small blocks forming a C
    handle = MeshBuilder()
    add_box(handle, (0.24, 0.20, 0), (0.10, 0.05, 0.06), "ceramic", 1)
    add_box(handle, (0.24, 0.10, 0), (0.10, 0.05, 0.06), "ceramic", 1)
    add_box(handle, (0.28, 0.15, 0), (0.05, 0.16, 0.06), "ceramic", 1)
    builder.merge(handle)
    return builder


def build_jar(_seed: int = 0) -> MeshBuilder:
    """A labeled pantry jar — the hashmap's unit of storage."""
    builder = MeshBuilder()
    profile = [
        (0.0, 0.0),
        (0.14, 0.0),
        (0.16, 0.05),
        (0.16, 0.24),
        (0.11, 0.30),    # shoulder
        (0.11, 0.34),    # neck
    ]
    add_lathe(builder, profile, 10, "clay", 2)
    # lid
    add_cylinder(builder, (0, 0.36, 0), 0.12, 0.05, 10, "metal", 2, shade_top=3)
    # label quad (front)
    builder.add_face(
        [(-0.07, 0.08, 0.161), (0.07, 0.08, 0.161), (0.07, 0.20, 0.161), (-0.07, 0.20, 0.161)],
        "cream", 3,
    )
    return builder


def build_pine(seed: int = 0) -> MeshBuilder:
    """Small pine — canopy shades vary gently with the seed."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    add_cylinder(builder, (0, 0.25, 0), 0.09, 0.5, 8, "bark", 1, cap_top=False)
    layers = [
        (0.55, 0.45, 0.42),
        (0.45, 0.72, 0.40),
        (0.32, 0.98, 0.38),
    ]
    for radius, base_y, height in layers:
        shade = rng.choice([1, 1, 2])
        add_cone(builder, (0, base_y, 0), radius, height, 9, "pine", shade)
    return builder


def build_planter(_seed: int = 0) -> MeshBuilder:
    """Raised garden bed — a soil-topped box for the cottage garden."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.2, 0), (0.9, 0.4, 0.5), "wood", 1, top=("clay", 0))
    return builder


def build_rock(seed: int = 0) -> MeshBuilder:
    """A low, faceted rock — scatterable or occasional hero placement."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    width = rng.uniform(0.35, 0.5)
    depth = rng.uniform(0.3, 0.45)
    height = rng.uniform(0.2, 0.32)
    add_box(builder, (0, height / 2.0, 0), (width, height, depth), "stone", 1,
            top=("stone", 2))
    return builder


def build_well(_seed: int = 0) -> MeshBuilder:
    """Small stone well — the cottage garden's water source."""
    builder = MeshBuilder()
    profile = [
        (0.0, 0.0),
        (0.35, 0.0),
        (0.37, 0.5),
        (0.35, 0.55),  # lip
    ]
    add_lathe(builder, profile, 12, "stone", 1, cap_start=True, cap_end=True)
    return builder


def build_grass_tuft(seed: int = 0) -> MeshBuilder:
    """A small clump of tapered, leaning blades — double-sided cards so the
    clump reads as solid grass from any camera angle, not a thin cross."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    blade_count = 5
    shades = (1, 2, 2, 3)
    for i in range(blade_count):
        angle = (2.0 * math.pi / blade_count) * i + rng.uniform(-0.2, 0.2)
        height = rng.uniform(0.16, 0.3)
        half_width = rng.uniform(0.02, 0.035)
        lean = rng.uniform(0.03, 0.08)  # tip drifts outward as the blade leans
        dx = math.cos(angle) * half_width
        dz = math.sin(angle) * half_width
        tip = (
            math.cos(angle) * lean,
            height,
            math.sin(angle) * lean,
        )
        shade = shades[i % len(shades)]
        # Tapered triangle (wide base, pointed tip) reads far more like a
        # blade of grass than a rectangle.
        builder.add_double_face(
            [(-dx, 0.0, -dz), (dx, 0.0, dz), tip],
            "moss", shade,
        )
    return builder


def build_flower(seed: int = 0) -> MeshBuilder:
    """A small daisy-like flower: a thin stem, a ring of angled petals, and
    a bright center hub — reads as an actual flower instead of a flat
    quad."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    stem_height = rng.uniform(0.16, 0.22)
    add_cylinder(builder, (0, stem_height * 0.5, 0), 0.008, stem_height, 5,
                 "moss", 1, cap_top=False)
    petal_count = 6
    petal_len = rng.uniform(0.045, 0.06)
    petal_shade = rng.choice([2, 3])
    tilt = 0.35  # petals angle upward slightly, like an open bloom
    for i in range(petal_count):
        angle = (2.0 * math.pi / petal_count) * i
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        inner = (cos_a * 0.012, stem_height, sin_a * 0.012)
        outer = (
            cos_a * petal_len,
            stem_height + tilt * petal_len,
            sin_a * petal_len,
        )
        side = (-sin_a, 0.0, cos_a)
        half = 0.016
        p0 = (inner[0] - side[0] * half, inner[1], inner[2] - side[2] * half)
        p1 = (inner[0] + side[0] * half, inner[1], inner[2] + side[2] * half)
        builder.add_double_face([p0, p1, outer], "cream", petal_shade)
    # Center hub: a small flattened cone so the flower has a raised, bright
    # middle instead of an empty gap between petal bases.
    add_cylinder(builder, (0, stem_height + 0.006, 0), 0.02, 0.012, 6,
                 "honey", 3, cap_top=True, cap_bottom=False)
    return builder


def build_cottage_wall(_seed: int = 0) -> MeshBuilder:
    """One 2m wall segment: timber frame plus a whitewashed infill panel."""
    builder = MeshBuilder()
    add_box(builder, (0, 1.0, 0), (2.0, 2.0, 0.2), "cream", 2)
    for x in (-0.95, 0.95):
        add_box(builder, (x, 1.0, 0), (0.1, 2.0, 0.22), "bark", 1)
    add_box(builder, (0, 1.95, 0), (2.0, 0.1, 0.22), "bark", 1)
    add_box(builder, (0, 0.05, 0), (2.0, 0.1, 0.22), "bark", 1)
    return builder


def build_cottage_corner(_seed: int = 0) -> MeshBuilder:
    """An L-shaped corner post joining two wall segments."""
    builder = MeshBuilder()
    add_box(builder, (0, 1.0, 0), (0.2, 2.0, 0.2), "bark", 1)
    add_box(builder, (0, 1.95, 0), (0.24, 0.1, 0.24), "bark", 2)
    return builder


def build_cottage_roof(_seed: int = 0) -> MeshBuilder:
    """A flat two-panel roof placeholder (not actually pitched — both
    panels sit at the same height side by side). Good enough to read as
    "roof-shaped" from a distance; a true pitched/mitred ridge is left for
    a later, non-placeholder pass."""
    builder = MeshBuilder()
    add_box(builder, (-0.55, 0.15, 0), (1.3, 0.1, 2.2), "honey", 2)
    add_box(builder, (0.55, 0.15, 0), (1.3, 0.1, 2.2), "honey", 2)
    return builder


def _add_pitched_roof(builder: MeshBuilder, width: float, depth: float, eave_y: float,
                       rise: float, overhang: float, ramp: str, shade: int) -> None:
    """A simple two-slope gable roof: ridge runs along X, sloping down to
    eaves on +Z/-Z, with a triangular gable fill at each end so the
    underside of the overhang doesn't read as open sky."""
    hw = width / 2.0 + overhang
    hd = depth / 2.0 + overhang
    ridge_y = eave_y + rise
    l_front = (-hw, eave_y, hd)
    l_back = (-hw, eave_y, -hd)
    l_ridge = (-hw, ridge_y, 0.0)
    r_front = (hw, eave_y, hd)
    r_back = (hw, eave_y, -hd)
    r_ridge = (hw, ridge_y, 0.0)
    builder.add_face([l_front, r_front, r_ridge, l_ridge], ramp, shade)  # front slope
    builder.add_face([r_back, l_back, l_ridge, r_ridge], ramp, shade)    # back slope
    builder.add_face([l_front, l_ridge, l_back], ramp, max(shade - 1, 0))  # left gable underside
    builder.add_face([r_back, r_ridge, r_front], ramp, max(shade - 1, 0))  # right gable underside


def _add_stone_wall_box(builder: MeshBuilder, center, size, ramp: str, rng: random.Random) -> None:
    """Axis-aligned box whose four vertical side faces are each a single
    quad mapped across the whole baked stone-masonry texture (see
    palette.texture_uv_rect("stone_wall")) — real stone grain, and (crucially)
    no internal mesh seams for the toon outline pass to catch, unlike an
    earlier subdivided-block version. Top/bottom stay flat single-shade
    (hidden under the roof / against the ground)."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    u0, v0, u1, v1 = palette.texture_uv_rect("stone_wall")
    top_shade = 3
    bottom_shade = 0

    top = [(cx - hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz + hz),
           (cx + hx, cy + hy, cz + hz), (cx + hx, cy + hy, cz - hz)]
    builder.add_face(top, ramp, top_shade)
    bottom = [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz),
              (cx + hx, cy - hy, cz + hz), (cx - hx, cy - hy, cz + hz)]
    builder.add_face(bottom, ramp, bottom_shade)

    def face(points):
        # Occasionally mirror horizontally so all four walls don't show the
        # exact same texture orientation.
        left_u, right_u = (u1, u0) if rng.random() < 0.5 else (u0, u1)
        uvs = [(left_u, v1), (right_u, v1), (right_u, v0), (left_u, v0)]
        builder.add_textured_face(points, uvs)

    face([(cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz),
          (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)])  # +Z
    face([(cx + hx, cy - hy, cz - hz), (cx - hx, cy - hy, cz - hz),
          (cx - hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz - hz)])  # -Z
    face([(cx + hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz - hz),
          (cx + hx, cy + hy, cz - hz), (cx + hx, cy + hy, cz + hz)])  # +X
    face([(cx - hx, cy - hy, cz - hz), (cx - hx, cy - hy, cz + hz),
          (cx - hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz - hz)])  # -X


def build_cottage_facade(_seed: int = 0) -> MeshBuilder:
    """A two-story stone cottage exterior: stone walls, two rows of
    sash-style windows, a dark cottage door, a pitched slate roof, and a
    chimney with a pot — one hero placement instead of an assembled
    wall/corner/roof kit.

    Scaled and styled after a reference Welsh terraced-house model (stone
    walls, slate roof, two chimney pots, front garden) the user pointed to
    — this isn't a literal copy, just matched for size/material feel: a
    real two-story house rather than a single small shed. Exterior-only
    (no interior geometry — cottage_interior.tscn is the separate walkable
    scene), so it can be a solid shell.
    """
    builder = MeshBuilder()
    rng = random.Random(_seed)
    width, depth = 4.4, 3.4
    eave_y = 3.6  # two floors' worth of wall height

    # Stone wall shell — coursed fieldstone blocks, not a flat panel.
    _add_stone_wall_box(builder, (0, eave_y / 2.0, 0), (width, eave_y, depth), "stone", rng)

    # Quoins: lighter stone corner posts for definition. Sized a hair proud
    # of the wall shell (not flush) so their outer faces don't sit exactly
    # coplanar with the wall's own outer faces — coplanar geometry causes
    # z-fighting flicker at the cottage's vertical edges.
    hx, hz = width / 2.0 - 0.1, depth / 2.0 - 0.1
    for x in (-hx, hx):
        for z in (-hz, hz):
            add_box(builder, (x, eave_y / 2.0, z), (0.28, eave_y, 0.28), "stone", 2)

    # Foundation course and first-floor stringcourse for two-story readability.
    # (Proud of the wall shell by the same +0.04 margin as the stringcourse
    # below, not flush — flush would z-fight along the entire base perimeter.)
    add_box(builder, (0, 0.08, 0), (width + 0.04, 0.16, depth + 0.04), "stone", 0)
    floor_y = eave_y / 2.0
    add_box(builder, (0, floor_y, 0), (width + 0.04, 0.14, depth + 0.04), "stone", 2)

    # Door, centered on the front (-Z) face, dark cottage-green.
    door_w, door_h = 0.95, 1.9
    door_z = -depth / 2.0 - 0.03
    add_box(builder, (0, door_h / 2.0, door_z), (door_w + 0.2, door_h + 0.2, 0.06), "clay", 1)
    add_box(builder, (0, door_h / 2.0, door_z - 0.02), (door_w, door_h, 0.05), "pine", 0,
            top=("pine", 1))

    # Ground-floor windows flanking the door, first-floor windows above.
    win_size = 0.62
    ground_y = door_h * 0.55
    first_y = eave_y - 0.95
    for wx in (-1.35, 1.35):
        for wy in (ground_y, first_y):
            add_box(builder, (wx, wy, door_z), (win_size + 0.14, win_size + 0.14, 0.05),
                    "cream", 3)
            add_box(builder, (wx, wy, door_z - 0.02), (win_size, win_size, 0.04), "metal", 0)

    # Side window (+X wall), for detail from other viewing angles.
    win_x = width / 2.0 + 0.03
    add_box(builder, (win_x, first_y, 0), (0.06, win_size + 0.14, win_size + 0.14), "cream", 3)
    add_box(builder, (win_x + 0.01, first_y, 0), (0.05, win_size, win_size), "metal", 0)

    # Pitched slate roof with overhang.
    overhang = 0.4
    rise = 1.3
    _add_pitched_roof(builder, width, depth, eave_y, rise, overhang, "metal", 1)
    ridge_y = eave_y + rise

    # Chimney with a pot, offset toward one gable end.
    chimney_x = hx - 0.4
    add_box(builder, (chimney_x, ridge_y + 0.35, 0), (0.4, 0.7, 0.4), "stone", 1,
            top=("stone", 2))
    add_cylinder(builder, (chimney_x, ridge_y + 0.78, 0), 0.1, 0.24, 8, "rust", 2,
                 cap_top=True, cap_bottom=False)

    return builder


def build_interior_wall(_seed: int = 0) -> MeshBuilder:
    """One 2m interior wall segment: plastered panel with a wood baseboard."""
    builder = MeshBuilder()
    add_box(builder, (0, 1.2, 0), (2.0, 2.4, 0.15), "cream", 1, top=("cream", 2))
    add_box(builder, (0, 0.08, 0), (2.0, 0.16, 0.17), "wood", 1)
    return builder


def build_interior_floor(_seed: int = 0) -> MeshBuilder:
    """2x2 m interior floor tile — wood plank boards."""
    builder = MeshBuilder()
    add_box(builder, (0, -0.05, 0), (2.0, 0.1, 2.0), "wood", 2, top=("wood", 3))
    return builder


def build_hearth(_seed: int = 0) -> MeshBuilder:
    """Stone fireplace: base block with a dark firebox decal and an ember
    glow accent quad (decals, not a carved recess — add_box can't
    subtract). A hero prop — the interior's lighting focal point."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.5, 0), (0.9, 1.0, 0.5), "stone", 1, top=("stone", 2))
    builder.add_face(
        [(-0.28, 0.08, 0.251), (0.28, 0.08, 0.251),
         (0.28, 0.55, 0.251), (-0.28, 0.55, 0.251)],
        "stone", 0,
    )
    builder.add_face(
        [(-0.18, 0.1, 0.252), (0.18, 0.1, 0.252),
         (0.18, 0.4, 0.252), (-0.18, 0.4, 0.252)],
        "honey", 3,
    )
    return builder


def build_table(_seed: int = 0) -> MeshBuilder:
    """Simple wood table: top plus four legs."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.72, 0), (1.1, 0.06, 0.7), "wood", 2, top=("wood", 3))
    for x in (-0.48, 0.48):
        for z in (-0.28, 0.28):
            add_box(builder, (x, 0.35, z), (0.08, 0.7, 0.08), "wood", 1)
    return builder


def build_chair(_seed: int = 0) -> MeshBuilder:
    """Simple wood chair: seat, backrest, four legs."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.45, 0), (0.42, 0.05, 0.42), "wood", 2)
    add_box(builder, (0, 0.75, -0.19), (0.42, 0.55, 0.05), "wood", 1)
    for x in (-0.17, 0.17):
        for z in (-0.17, 0.17):
            add_box(builder, (x, 0.22, z), (0.06, 0.44, 0.06), "wood", 1)
    return builder


def build_shelf(_seed: int = 0) -> MeshBuilder:
    """Wall shelf: back panel plus two shelf boards, sized to host jar/mug
    props as set-dressing."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.9, -0.06), (1.0, 1.2, 0.03), "wood", 1)
    for y in (0.5, 1.3):
        add_box(builder, (0, y, 0.1), (1.0, 0.04, 0.26), "wood", 2, top=("wood", 3))
    return builder


def build_rug(_seed: int = 0) -> MeshBuilder:
    """Flat woven rug — a single ground-hugging quad, facing up."""
    builder = MeshBuilder()
    builder.add_face(
        [(-0.9, 0.005, -0.6), (-0.9, 0.005, 0.6),
         (0.9, 0.005, 0.6), (0.9, 0.005, -0.6)],
        "rust", 2,
    )
    return builder


def build_bed(_seed: int = 0) -> MeshBuilder:
    """Bed frame, mattress, and pillow blockout. A hero prop — the alcove's
    focal furniture piece."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.25, 0), (1.0, 0.4, 1.9), "wood", 1)
    add_box(builder, (0, 0.9, -0.9), (1.0, 0.7, 0.1), "wood", 2)
    add_box(builder, (0, 0.5, 0.05), (0.94, 0.2, 1.7), "cream", 2, top=("cream", 3))
    add_box(builder, (0, 0.66, -0.65), (0.7, 0.14, 0.32), "cream", 3)
    return builder


def build_hedge(_seed: int = 0) -> MeshBuilder:
    """One 2m hedge segment: a chunky moss-green box lining the lane."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.45, 0), (2.0, 0.9, 0.5), "moss", 1, top=("moss", 2))
    return builder


def build_stone_stile(_seed: int = 0) -> MeshBuilder:
    """A stepover crossing through a hedge row: two stone steps + a rail."""
    builder = MeshBuilder()
    for x in (-0.6, 0.6):
        add_box(builder, (x, 0.2, 0), (0.5, 0.4, 0.5), "stone", 1, top=("stone", 2))
    add_box(builder, (0, 0.55, 0), (1.3, 0.08, 0.08), "wood", 1)
    return builder


def build_lane_path(_seed: int = 0) -> MeshBuilder:
    """2x2 m lane path tile: dirt/clay ground distinct from grass."""
    builder = MeshBuilder()
    add_box(builder, (0, -0.1, 0), (2.0, 0.2, 2.0), "clay", 1,
            top=("clay", 2), bottom=("bark", 0))
    return builder


def build_signpost(_seed: int = 0) -> MeshBuilder:
    """A single wayfinding post with two arm-planks near the top."""
    builder = MeshBuilder()
    add_box(builder, (0, 0.6, 0), (0.1, 1.2, 0.1), "wood", 1, top=("wood", 2))
    add_box(builder, (0.25, 1.0, 0), (0.5, 0.1, 0.06), "wood", 2)
    add_box(builder, (-0.25, 0.85, 0), (0.5, 0.1, 0.06), "wood", 2)
    return builder


PROPS = {
    "bed": build_bed,
    "chair": build_chair,
    "cottage_corner": build_cottage_corner,
    "cottage_facade": build_cottage_facade,
    "cottage_roof": build_cottage_roof,
    "cottage_wall": build_cottage_wall,
    "crate": build_crate,
    "fence": build_fence,
    "flower": build_flower,
    "grass_tuft": build_grass_tuft,
    "ground_tile": build_ground_tile,
    "hearth": build_hearth,
    "hedge": build_hedge,
    "interior_floor": build_interior_floor,
    "interior_wall": build_interior_wall,
    "jar": build_jar,
    "lane_path": build_lane_path,
    "mug": build_mug,
    "pine": build_pine,
    "planter": build_planter,
    "rock": build_rock,
    "rug": build_rug,
    "shelf": build_shelf,
    "signpost": build_signpost,
    "stone_stile": build_stone_stile,
    "table": build_table,
    "well": build_well,
}

TRI_BUDGET = 600

HERO_TRI_BUDGET = 1500

# Props allowed to spend the hero budget instead of the regular one — kept
# to a short, explicit list so budget creep needs a deliberate edit here.
HERO_PROPS: set[str] = {
    "cottage_wall", "cottage_corner", "cottage_roof", "cottage_facade", "hearth", "bed",
}


def build_prop(name: str, seed: int = 0) -> MeshBuilder:
    if name not in PROPS:
        raise KeyError(f"unknown prop: {name}")
    return PROPS[name](seed)
