from __future__ import annotations

import hashlib

from tools.assetgen import character, character_gen, gltf

# Captured from the pre-migration character.build_rig()/build_animations()
# via the sha256 command in this task's Step 1.
PRE_MIGRATION_SHA256 = "dd5dbd16cfe1cdb35cd46937f65906dfe30b2c7634fa230885b9511274450159"


def test_wren_spec_produces_byte_identical_output():
    rig, clips = character_gen.generate(character.WREN_SPEC)
    data = gltf.build_scene_glb(rig, clips, "wren")
    assert hashlib.sha256(data).hexdigest() == PRE_MIGRATION_SHA256
