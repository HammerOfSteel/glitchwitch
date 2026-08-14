# tests/python/test_character_spec.py
from __future__ import annotations

import pytest

from tools.assetgen.character_spec import CharacterSpec


def test_spec_requires_archetype_and_seed():
    spec = CharacterSpec(archetype="witch", seed=42)
    assert spec.archetype == "witch"
    assert spec.seed == 42
    assert spec.parts == {}
    assert spec.animation_profile == "default"


def test_spec_rejects_non_int_seed():
    with pytest.raises(TypeError):
        CharacterSpec(archetype="witch", seed="42")


def test_spec_accepts_explicit_part_choices():
    spec = CharacterSpec(archetype="witch", seed=1, parts={"headwear": "witch_hat"})
    assert spec.parts["headwear"] == "witch_hat"
