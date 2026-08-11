"""palette_uv.json export: every (ramp, shade) cell_uv, byte-deterministic."""
from __future__ import annotations

import json

from tools.assetgen import palette


def test_every_ramp_shade_pair_is_present():
    data = json.loads(palette.build_palette_uv_json())
    for name in palette.ramp_names():
        for shade in range(palette.SHADES):
            key = f"{name}/{shade}"
            assert key in data, key


def test_values_match_cell_uv_exactly():
    data = json.loads(palette.build_palette_uv_json())
    for name in palette.ramp_names():
        for shade in range(palette.SHADES):
            key = f"{name}/{shade}"
            assert data[key] == list(palette.cell_uv(name, shade))


def test_json_is_byte_deterministic():
    first = palette.build_palette_uv_json()
    second = palette.build_palette_uv_json()
    assert first == second
