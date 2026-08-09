import pytest

from tools.assetgen.blender.archetype_spec import ArchetypeSpec


def test_archetype_spec_requires_name_and_bone_scales():
    spec = ArchetypeSpec(
        name="villager",
        bone_scales={"Spine": 1.0, "UpLeg.L": 0.95, "UpLeg.R": 0.95},
        clothing=["tunic", "boots"],
        palette={"tunic": ("wood", 1), "boots": ("bark", 0)},
        clips=["idle", "walk", "run", "wave", "stir"],
    )
    assert spec.name == "villager"
    assert spec.bone_scales["Spine"] == 1.0


def test_archetype_spec_rejects_unknown_bone_name():
    with pytest.raises(ValueError, match="unknown bone"):
        ArchetypeSpec(
            name="villager",
            bone_scales={"NotARealBone": 1.0},
            clothing=[],
            palette={},
            clips=["idle", "walk", "run", "wave", "stir"],
        )


def test_archetype_spec_rejects_clothing_without_palette_entry():
    with pytest.raises(ValueError, match="no palette entry"):
        ArchetypeSpec(
            name="villager",
            bone_scales={},
            clothing=["tunic"],
            palette={},  # missing "tunic"
            clips=["idle", "walk", "run", "wave", "stir"],
        )


def test_archetype_spec_rejects_missing_mandatory_clip():
    with pytest.raises(ValueError, match="missing mandatory clip"):
        ArchetypeSpec(
            name="villager",
            bone_scales={},
            clothing=[],
            palette={},
            clips=["idle", "walk"],  # missing run/wave/stir
        )
