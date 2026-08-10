"""Proof props for the Phase 0 look-dev diorama.

Every generator is deterministic: variation comes only from an explicit seed
fed through random.Random. Budgets are asserted in tests (<= 600 tris).
"""
from __future__ import annotations

import math
import random

from .mesh import MeshBuilder, add_box, add_cone, add_cylinder, add_lathe


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
    """A few crossed blade quads — cheap enough to scatter densely."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    for i in range(3):
        angle = (math.pi / 3.0) * i
        height = rng.uniform(0.18, 0.28)
        half_width = 0.05
        dx = math.cos(angle) * half_width
        dz = math.sin(angle) * half_width
        builder.add_face(
            [
                (-dx, 0.0, -dz), (dx, 0.0, dz),
                (dx, height, dz), (-dx, height, -dz),
            ],
            "moss", 2,
        )
    return builder


def build_flower(seed: int = 0) -> MeshBuilder:
    """A single small flower — stem plus a flat bloom quad."""
    rng = random.Random(seed)
    builder = MeshBuilder()
    add_cylinder(builder, (0, 0.09, 0), 0.01, 0.18, 5, "moss", 1, cap_top=False)
    bloom_shade = rng.choice([0, 1, 2])
    builder.add_face(
        [
            (-0.05, 0.18, 0.1), (0.05, 0.18, 0.1),
            (0.05, 0.18, 0.0), (-0.05, 0.18, 0.0),
        ],
        "honey", bloom_shade,
    )
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


PROPS = {
    "bed": build_bed,
    "chair": build_chair,
    "cottage_corner": build_cottage_corner,
    "cottage_roof": build_cottage_roof,
    "cottage_wall": build_cottage_wall,
    "crate": build_crate,
    "fence": build_fence,
    "flower": build_flower,
    "grass_tuft": build_grass_tuft,
    "ground_tile": build_ground_tile,
    "hearth": build_hearth,
    "interior_floor": build_interior_floor,
    "interior_wall": build_interior_wall,
    "jar": build_jar,
    "mug": build_mug,
    "pine": build_pine,
    "planter": build_planter,
    "rock": build_rock,
    "rug": build_rug,
    "shelf": build_shelf,
    "table": build_table,
    "well": build_well,
}

TRI_BUDGET = 600

HERO_TRI_BUDGET = 1500

# Props allowed to spend the hero budget instead of the regular one — kept
# to a short, explicit list so budget creep needs a deliberate edit here.
HERO_PROPS: set[str] = {"cottage_wall", "cottage_corner", "cottage_roof", "hearth", "bed"}


def build_prop(name: str, seed: int = 0) -> MeshBuilder:
    if name not in PROPS:
        raise KeyError(f"unknown prop: {name}")
    return PROPS[name](seed)
