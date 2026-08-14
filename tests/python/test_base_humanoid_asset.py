"""Structural checks on the committed base_humanoid.blend.

Does NOT require Blender/bpy to run — a .blend file is a custom binary format we
don't parse here. This test only asserts the file exists and is non-trivially
sized (catches "forgot to commit" / "committed an empty file" mistakes). Real
structural validation (bone names, mesh presence, vertex-group weights) requires
a live Blender/bpy process and is added later once `blender/loader.py` exists (a
later chunk covering the archetype-variation units), exercised via a
`test_blender_loader.py` that invokes headless Blender.
"""
from pathlib import Path

BASE_BLEND = (
    Path(__file__).resolve().parents[2]
    / "tools"
    / "assetgen"
    / "blender"
    / "base_humanoid.blend"
)


def test_base_humanoid_blend_exists():
    assert BASE_BLEND.exists(), (
        f"{BASE_BLEND} missing — run "
        "tools/assetgen/blender/author_base_humanoid.py and commit its output"
    )


def test_base_humanoid_blend_is_nontrivial_size():
    # A real authored mesh+armature .blend is comfortably >100KB; guards against
    # committing a stub/empty file by mistake.
    assert BASE_BLEND.stat().st_size > 100_000
