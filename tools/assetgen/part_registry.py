"""Part library registry: named mesh builders per archetype + slot.

Canonical part builders are moved verbatim from the pre-pipeline character.py
(Wren's hand-authored meshes) — see the "witch" archetype entries below. New
archetypes add their own entries; the registry never overwrites an existing
part id.
"""
from __future__ import annotations

from .mesh import MeshBuilder, add_box, add_cylinder, add_lathe


# --- witch archetype: Wren's canonical parts (moved from character.py) -------

def witch_skirt() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [(0.21, -0.36), (0.19, -0.20), (0.155, -0.06), (0.13, 0.06)]
    add_lathe(builder, profile, 10, "void_plum", 2, cap_start=True, cap_end=True)
    return builder


def witch_torso() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [(0.125, -0.08), (0.15, 0.02), (0.13, 0.10), (0.10, 0.18)]
    add_lathe(builder, profile, 10, "rust", 2, cap_start=True, cap_end=True)
    return builder


def witch_arm() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.12, 0.0), (0.075, 0.24, 0.075), "rust", 1)
    add_box(builder, (0.0, -0.27, 0.0), (0.06, 0.06, 0.06), "cream", 3)
    return builder


def witch_head() -> MeshBuilder:
    builder = MeshBuilder()
    profile = [
        (0.0, -0.04), (0.10, -0.03), (0.14, 0.04), (0.13, 0.12), (0.08, 0.18), (0.0, 0.20),
    ]
    add_lathe(builder, profile, 10, "cream", 3)
    # eyes on the -Z face (forward)
    for x in (-0.05, 0.05):
        add_box(builder, (x, 0.06, -0.135), (0.022, 0.03, 0.012), "void_plum", 0)
    return builder


def witch_hat() -> MeshBuilder:
    builder = MeshBuilder()
    add_cylinder(builder, (0.0, 0.0, 0.0), 0.20, 0.03, 10, "void_plum", 1, shade_top=2)
    cone_profile = [(0.125, 0.015), (0.10, 0.14), (0.05, 0.24), (0.0, 0.30)]
    add_lathe(builder, cone_profile, 10, "void_plum", 1)
    # the glitch band — a wink of magenta
    add_cylinder(builder, (0.0, 0.045, 0.0), 0.132, 0.035, 10, "glitch_magenta", 2,
                 cap_bottom=False, cap_top=False)
    return builder


def witch_braid() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.02, 0.02), (0.06, 0.08, 0.06), "honey", 2)
    add_box(builder, (0.0, -0.10, 0.045), (0.05, 0.08, 0.05), "honey", 1)
    add_box(builder, (0.0, -0.17, 0.06), (0.035, 0.07, 0.035), "honey", 2)
    return builder


def witch_boot() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.0, -0.01), (0.10, 0.12, 0.16), "bark", 1, top=("bark", 2))
    return builder


# --- villager archetype: simple proof-of-pipeline parts ---------------------

def empty_placeholder() -> MeshBuilder:
    """Zero-geometry mesh for a structurally-mandatory-but-visually-absent slot."""
    return MeshBuilder()


def villager_torso() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.05, 0.0), (0.28, 0.32, 0.22), "moss", 2)
    return builder


def villager_head() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.0, 0.0), (0.24, 0.24, 0.22), "cream", 3)
    return builder


def villager_arm() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, -0.12, 0.0), (0.07, 0.22, 0.07), "moss", 1)
    return builder


def villager_boot() -> MeshBuilder:
    builder = MeshBuilder()
    add_box(builder, (0.0, 0.0, -0.01), (0.09, 0.10, 0.14), "bark", 1)
    return builder


# --- registry ------------------------------------------------------------

# archetype -> slot -> {part_id: builder_fn}
_REGISTRY = {
    "witch": {
        "hips": {"witch_skirt": witch_skirt},
        "torso": {"witch_torso": witch_torso},
        "arm": {"witch_arm": witch_arm},
        "head": {"witch_head": witch_head},
        "headwear": {"witch_hat": witch_hat},
        "hair": {"witch_braid": witch_braid},
        "boot": {"witch_boot": witch_boot},
    },
    "villager": {
        "hips": {"villager_hips_placeholder": empty_placeholder},
        "torso": {"villager_torso": villager_torso},
        "arm": {"villager_arm": villager_arm},
        "head": {"villager_head": villager_head},
        "headwear": {"villager_no_hat": empty_placeholder},
        "hair": {"villager_no_hair": empty_placeholder},
        "boot": {"villager_boot": villager_boot},
    },
}


def candidates_for(archetype: str, slot: str) -> list:
    """Sorted list of part ids available for archetype+slot (empty if none)."""
    return sorted(_REGISTRY.get(archetype, {}).get(slot, {}).keys())


def build_part(archetype: str, slot: str, part_id: str) -> MeshBuilder:
    try:
        builder_fn = _REGISTRY[archetype][slot][part_id]
    except KeyError as exc:
        raise ValueError(
            f"no part '{part_id}' for archetype '{archetype}' slot '{slot}'"
        ) from exc
    return builder_fn()


def register(archetype: str, slot: str, part_id: str, builder_fn) -> None:
    """Register a new part builder (used by future archetypes).

    Raises ValueError if the (archetype, slot, part_id) combination is already registered.
    """
    slot_dict = _REGISTRY.setdefault(archetype, {}).setdefault(slot, {})
    if part_id in slot_dict:
        raise ValueError(
            f"part '{part_id}' is already registered for archetype '{archetype}' slot '{slot}'"
        )
    slot_dict[part_id] = builder_fn
