from __future__ import annotations

import hashlib

from tools.assetgen import character, character_gen, gltf

# Captured from the pre-migration character.build_rig()/build_animations()
# via the sha256 command in this task's Step 1.
#
# Updated once, deliberately: adding the "stone_wall" baked texture region to
# the palette atlas (tools/assetgen/palette.py) grew the atlas image's total
# height, which shifts every ramp cell's V-coordinate proportionally (still
# correct — same row, same relative pixel center — just a different literal
# float). That's expected fallout of any atlas resize, not a rig/mesh
# regression, so the pinned hash below was refreshed to match.
PRE_MIGRATION_SHA256 = "fec0e84ffe0e59d649bf3451bf50689fe9682bcc7f324e67d66a667d40c9d6db"


def test_wren_spec_produces_byte_identical_output():
    rig, clips = character_gen.generate(character.WREN_SPEC)
    data = gltf.build_scene_glb(rig, clips, "wren")
    assert hashlib.sha256(data).hexdigest() == PRE_MIGRATION_SHA256
