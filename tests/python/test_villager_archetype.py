from __future__ import annotations

from tools.assetgen import character_gen, character_validate, gltf
from tools.assetgen.character_spec import CharacterSpec


def _villager_spec(seed=1):
    return CharacterSpec(archetype="villager", seed=seed)  # all parts seed-resolved


def test_villager_generates_and_validates():
    rig, clips = character_gen.generate(_villager_spec())
    character_validate.validate(rig, clips)  # should not raise


def test_villager_is_deterministic_and_distinct_from_witch():
    from tools.assetgen import character
    rig_v, clips_v = character_gen.generate(_villager_spec())
    rig_w, clips_w = character_gen.generate(character.WREN_SPEC)
    glb_v = gltf.build_scene_glb(rig_v, clips_v, "villager")
    glb_w = gltf.build_scene_glb(rig_w, clips_w, "wren")
    assert glb_v != glb_w

    rig_v2, clips_v2 = character_gen.generate(_villager_spec())
    glb_v2 = gltf.build_scene_glb(rig_v2, clips_v2, "villager")
    assert glb_v == glb_v2


def test_villager_headwear_and_hair_are_empty_placeholders():
    rig, _clips = character_gen.generate(_villager_spec())

    def find(node, name):
        if node.name == name:
            return node
        for child in node.children:
            found = find(child, name)
            if found:
                return found
        return None

    hat = find(rig, "hat")
    braid = find(rig, "braid")
    assert hat is not None and hat.mesh is None
    assert braid is not None and braid.mesh is None
