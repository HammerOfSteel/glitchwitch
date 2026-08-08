from __future__ import annotations

from tools.assetgen import character_gen, part_registry, rig_contract
from tools.assetgen.character_spec import CharacterSpec


def _wren_spec():
    return CharacterSpec(
        archetype="witch",
        seed=0,
        parts={
            "hips": "witch_skirt", "torso": "witch_torso", "arm": "witch_arm",
            "head": "witch_head", "headwear": "witch_hat", "hair": "witch_braid",
            "boot": "witch_boot",
        },
        animation_profile="witch",
    )


def test_generate_returns_rig_and_clips():
    rig, clips = character_gen.generate(_wren_spec())
    assert rig.name == "witch"
    assert len(clips) == 5  # idle, walk, run, wave, stir


def test_seeded_selection_branches_across_multiple_candidates(monkeypatch):
    """`_resolve_parts` must genuinely pick different candidates for different
    seeds (and be stable for the same seed) once a slot has more than one
    registered part id — this is the branching path most tests never exercise
    because both current archetypes only register a single candidate per slot."""
    from tools.assetgen.mesh import MeshBuilder

    def _mesh():
        return MeshBuilder()

    fake_registry = {
        "witch": {
            **part_registry._REGISTRY["witch"],
            "headwear": {
                "witch_hat": _mesh,
                "witch_hat_variant_a": _mesh,
                "witch_hat_variant_b": _mesh,
            },
        }
    }
    monkeypatch.setattr(part_registry, "_REGISTRY", fake_registry)

    def _resolve(seed):
        spec = CharacterSpec(archetype="witch", seed=seed)
        return character_gen._resolve_parts(spec)["headwear"]

    picks = {_resolve(seed) for seed in range(20)}
    assert len(picks) > 1, "seeded selection never branched across 20 seeds"
    assert _resolve(7) == _resolve(7), "same seed must resolve the same part id"


def test_generated_rig_has_all_mandatory_nodes():
    rig, _clips = character_gen.generate(_wren_spec())

    def collect_names(node, acc):
        acc.add(node.name)
        for child in node.children:
            collect_names(child, acc)
        return acc

    names = collect_names(rig, set())
    assert rig_contract.MANDATORY_NODE_NAMES <= names


def test_generation_is_deterministic():
    rig1, clips1 = character_gen.generate(_wren_spec())
    rig2, clips2 = character_gen.generate(_wren_spec())
    from tools.assetgen import gltf
    glb1 = gltf.build_scene_glb(rig1, clips1, "witch")
    glb2 = gltf.build_scene_glb(rig2, clips2, "witch")
    assert glb1 == glb2


def test_unknown_archetype_raises_value_error():
    import pytest
    from tools.assetgen.character_spec import CharacterSpec
    with pytest.raises(ValueError, match="archetype"):
        character_gen.generate(CharacterSpec(archetype="nope", seed=0))
