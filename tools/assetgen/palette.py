"""The palette color script — single source of truth for Glitch Witch's colors.

Generates a flat-color atlas PNG (stdlib only, byte-deterministic: fixed zlib
level, no ancillary chunks). Meshes UV-map onto cell centers; colorblind-safe
alternate palettes later become alternate PNGs with identical layout.

Layout: one ramp per row, shades 0..3 left to right (0 = darkest).
"""
from __future__ import annotations

import struct
import zlib

CELL_PX = 8
COLS = 8  # grid width in cells; shades occupy the first SHADES columns
SHADES = 4

# name -> 4 shades, dark to light. Keep rows in deliberate order; adding new
# ramps APPENDS rows (existing UVs stay valid). Never reorder.
RAMPS = [
    ("wood", ["5a3d2b", "7a5236", "9c6b46", "b98a5e"]),
    ("bark", ["4a3527", "5f4633", "745740", "8a6b4e"]),
    ("leaf", ["2e5d3a", "3f7a4c", "55975f", "74b378"]),
    ("moss", ["3c5d44", "4f7a56", "68976b", "86b385"]),
    ("pine", ["27493a", "355f4a", "45775c", "588f6f"]),
    ("stone", ["5d5d66", "77777f", "919199", "adadb3"]),
    ("cream", ["c9b795", "dfd0ae", "f0e3c4", "f9f0da"]),
    ("ceramic", ["6f8f8a", "8fb0a8", "b3cec6", "d7e6e0"]),
    ("clay", ["8a5a40", "a56f4e", "bf855e", "d69c70"]),
    ("metal", ["55606b", "6e7a85", "8b97a1", "aab4bd"]),
    ("rust", ["8a4a33", "a55d3d", "bf7349", "d68a57"]),
    ("honey", ["9c6f2e", "c08c3a", "dda94e", "f0c46a"]),
    ("sky", ["87b7d4", "a3cbe2", "c2def0", "e0f0fa"]),
    ("water", ["3f6d8a", "528aa8", "6ba7c4", "8fc4dd"]),
    ("glitch_magenta", ["8a1f7a", "b32b9c", "e04fd1", "ff7ae8"]),
    ("glitch_cyan", ["1f7a8a", "2b9cb3", "4fd8e0", "7af0ff"]),
    ("void_plum", ["2a1f3d", "3a2b54", "4d3a6e", "634d8a"]),
]

RAMP_INDEX = {name: row for row, (name, _) in enumerate(RAMPS)}


def ramp_names():
    return [name for name, _ in RAMPS]


def hex_to_rgb(value: str):
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def atlas_size_px():
    return COLS * CELL_PX, len(RAMPS) * CELL_PX


def cell_uv(ramp: str, shade: int):
    """UV center of a palette cell, for mesh face mapping. V grows downward."""
    if ramp not in RAMP_INDEX:
        raise KeyError(f"unknown ramp: {ramp}")
    if not 0 <= shade < SHADES:
        raise ValueError(f"shade out of range: {shade}")
    width, height = atlas_size_px()
    u = ((shade + 0.5) * CELL_PX) / width
    v = ((RAMP_INDEX[ramp] + 0.5) * CELL_PX) / height
    return round(u, 6), round(v, 6)


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def build_palette_png() -> bytes:
    """Byte-deterministic RGBA PNG of the palette atlas."""
    width, height = atlas_size_px()
    rows = []
    for row_index in range(len(RAMPS)):
        _, shades = RAMPS[row_index]
        pixel_row = bytearray()
        for x in range(width):
            cell = min(x // CELL_PX, COLS - 1)
            if cell < SHADES:
                red, green, blue = hex_to_rgb(shades[cell])
                pixel_row += bytes((red, green, blue, 255))
            else:
                pixel_row += bytes((0, 0, 0, 0))  # reserved cells: transparent
        for _ in range(CELL_PX):
            rows.append(bytes(pixel_row))
    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
