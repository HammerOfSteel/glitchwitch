from __future__ import annotations

from tools.assetgen import part_registry


def test_witch_archetype_has_all_baseline_slots():
    for slot in ("hips", "torso", "arm", "head", "headwear", "hair", "boot"):
        candidates = part_registry.candidates_for("witch", slot)
        assert len(candidates) >= 1, f"no candidates for witch/{slot}"


def test_candidates_are_returned_in_sorted_order():
    candidates = part_registry.candidates_for("witch", "headwear")
    assert candidates == sorted(candidates)


def test_unknown_archetype_slot_combo_returns_empty():
    assert part_registry.candidates_for("nonexistent_archetype", "torso") == []


def test_build_part_returns_mesh_builder():
    from tools.assetgen.mesh import MeshBuilder

    candidates = part_registry.candidates_for("witch", "torso")
    builder = part_registry.build_part("witch", "torso", candidates[0])
    assert isinstance(builder, MeshBuilder)
    assert builder.tri_count > 0


def test_witch_skirt_matches_pre_migration_geometry():
    # Regression guard: the moved _skirt() builder must produce the exact
    # same triangle count as the original character.py implementation.
    builder = part_registry.build_part("witch", "hips", "witch_skirt")
    assert builder.tri_count == 80


def test_register_raises_on_duplicate():
    # Verify register() prevents overwriting existing (archetype, slot, part_id) combinations.
    from tools.assetgen.mesh import MeshBuilder

    def dummy_builder():
        return MeshBuilder()

    # Try to register a new part for a new archetype/slot
    part_registry.register("test_archetype", "test_slot", "test_part", dummy_builder)

    # Attempting to register the same combination again should raise ValueError
    try:
        part_registry.register("test_archetype", "test_slot", "test_part", dummy_builder)
        assert False, "Expected ValueError for duplicate registration"
    except ValueError as e:
        assert "test_part" in str(e)
        assert "test_archetype" in str(e)
        assert "test_slot" in str(e)
