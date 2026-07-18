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


PROPS = {
    "crate": build_crate,
    "fence": build_fence,
    "ground_tile": build_ground_tile,
    "jar": build_jar,
    "mug": build_mug,
    "pine": build_pine,
}

TRI_BUDGET = 600


def build_prop(name: str, seed: int = 0) -> MeshBuilder:
    if name not in PROPS:
        raise KeyError(f"unknown prop: {name}")
    return PROPS[name](seed)
