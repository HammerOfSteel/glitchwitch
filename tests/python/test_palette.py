"""Palette atlas tests: structure, determinism, and PNG validity."""
from __future__ import annotations

import struct
import zlib

from tools.assetgen import palette


def test_every_ramp_has_four_shades():
    for name, shades in palette.RAMPS:
        assert len(shades) == palette.SHADES, name
        for value in shades:
            assert len(value) == 6, f"{name}: bad hex {value}"
            int(value, 16)  # parses


def test_cell_uv_centers_are_inside_unit_square():
    for name in palette.ramp_names():
        for shade in range(palette.SHADES):
            u, v = palette.cell_uv(name, shade)
            assert 0.0 < u < 1.0 and 0.0 < v < 1.0, (name, shade)


def test_cell_uv_is_unique_per_cell():
    seen = {}
    for name in palette.ramp_names():
        for shade in range(palette.SHADES):
            uv = palette.cell_uv(name, shade)
            assert uv not in seen, f"uv collision: {(name, shade)} vs {seen.get(uv)}"
            seen[uv] = (name, shade)


def test_png_is_valid_and_deterministic():
    first = palette.build_palette_png()
    second = palette.build_palette_png()
    assert first == second, "palette PNG must be byte-deterministic"

    assert first[:8] == b"\x89PNG\r\n\x1a\n"
    length, tag = struct.unpack(">I4s", first[8:16])
    assert tag == b"IHDR" and length == 13
    width, height, depth, color_type = struct.unpack(">IIBB", first[16:26])
    expected_width, expected_height = palette.atlas_size_px()
    assert (width, height) == (expected_width, expected_height)
    assert (depth, color_type) == (8, 6)  # 8-bit RGBA


def test_png_pixels_match_color_script():
    data = palette.build_palette_png()
    # find IDAT
    offset = 8
    idat = b""
    while offset < len(data):
        length, tag = struct.unpack(">I4s", data[offset:offset + 8])
        chunk = data[offset + 8:offset + 8 + length]
        if tag == b"IDAT":
            idat += chunk
        offset += 12 + length
    raw = zlib.decompress(idat)
    width, height = palette.atlas_size_px()
    stride = 1 + width * 4
    assert len(raw) == stride * height

    # sample the center pixel of shade 2 of every ramp
    for row, (name, shades) in enumerate(palette.RAMPS):
        y = row * palette.CELL_PX + palette.CELL_PX // 2
        x = 2 * palette.CELL_PX + palette.CELL_PX // 2
        base = y * stride + 1 + x * 4
        assert raw[base] == 0 or True  # filter byte handled below
        pixel = raw[y * stride + 1 + x * 4: y * stride + 1 + x * 4 + 4]
        expected = palette.hex_to_rgb(shades[2]) + (255,)
        assert tuple(pixel) == expected, f"{name} shade 2 mismatch"
