"""The palette color script — single source of truth for Glitch Witch's colors.

Generates a flat-color atlas PNG (stdlib only, byte-deterministic: fixed zlib
level, no ancillary chunks). Meshes UV-map onto cell centers; colorblind-safe
alternate palettes later become alternate PNGs with identical layout.

Layout: one ramp per row, shades 0..3 left to right (0 = darkest).
"""
from __future__ import annotations

import random
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

# Baked, non-flat texture regions appended below the ramp rows — for faces
# that need real per-pixel detail (coursed masonry, grain) instead of one
# flat palette color. Each entry is (name, width_px, height_px). Order is
# append-only, same rule as RAMPS: existing UVs must stay valid.
TEXTURES = [
    ("stone_wall", 88, 96),
]
TEXTURE_INDEX = {name: i for i, (name, _, _) in enumerate(TEXTURES)}


def ramp_names():
    return [name for name, _ in RAMPS]


def hex_to_rgb(value: str):
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _ramps_height_px():
    return len(RAMPS) * CELL_PX


def atlas_size_px():
    width = COLS * CELL_PX
    for _, tex_width, _ in TEXTURES:
        width = max(width, tex_width)
    height = _ramps_height_px() + sum(tex_height for _, _, tex_height in TEXTURES)
    return width, height


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


def texture_uv_rect(name: str):
    """Normalized (u0, v0, u1, v1) bounding box of a baked texture region,
    for mesh faces that map real per-vertex UV corners across it (instead
    of the single-point flat-color UV that cell_uv gives ramp faces)."""
    if name not in TEXTURE_INDEX:
        raise KeyError(f"unknown texture: {name}")
    y0 = _ramps_height_px()
    for tex_name, tex_width, tex_height in TEXTURES:
        if tex_name == name:
            width, height = atlas_size_px()
            return (
                0.0, round(y0 / height, 6),
                round(tex_width / width, 6), round((y0 + tex_height) / height, 6),
            )
        y0 += tex_height
    raise KeyError(name)  # pragma: no cover — guarded by TEXTURE_INDEX check above


def _stone_wall_pixels():
    """Procedurally generate a coursed-stone masonry texture sized to cover
    a whole cottage wall face as one baked image (~11x12 stones at 8px
    each): rows of stones in a running-bond offset, each stone a jittered
    (dithered, not flat) shade of the "stone" ramp, separated by darker
    mortar lines. Deterministic (fixed seed) — baked once into the palette
    atlas so a wall can be a single untiled quad (no internal mesh seams
    for the toon outline pass to catch) while still reading as real stone
    grain rather than one flat color."""
    width, height = TEXTURES[TEXTURE_INDEX["stone_wall"]][1:]
    stone_w, stone_h = 8, 8
    cols, rows = width // stone_w, height // stone_h
    shades = [hex_to_rgb(value) for value in RAMPS[RAMP_INDEX["stone"]][1]]
    mortar = tuple(max(0, c - 30) for c in shades[0])
    rng = random.Random(20260810)
    pixels = [[shades[1] for _ in range(width)] for _ in range(height)]
    for row in range(rows):
        shift = (stone_w // 2) if row % 2 else 0
        for col in range(cols):
            base = rng.choice([shades[1], shades[1], shades[2], shades[2], shades[0], shades[3]])
            for dy in range(stone_h):
                for dx in range(stone_w):
                    x = (col * stone_w + dx + shift) % width
                    y = row * stone_h + dy
                    if dx == 0 or dy == 0:
                        pixels[y][x] = mortar
                    else:
                        jitter = rng.randint(-8, 8)
                        pixels[y][x] = tuple(max(0, min(255, c + jitter)) for c in base)
    return pixels


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

    # Baked, non-flat texture regions (e.g. stone_wall masonry grain).
    texture_generators = {"stone_wall": _stone_wall_pixels}
    for tex_name, _, _ in TEXTURES:
        for pixel_row in texture_generators[tex_name]():
            row_bytes = bytearray()
            for x in range(width):
                if x < len(pixel_row):
                    red, green, blue = pixel_row[x]
                    row_bytes += bytes((red, green, blue, 255))
                else:
                    row_bytes += bytes((0, 0, 0, 0))
            rows.append(bytes(row_bytes))

    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(raw, 9))
        + _png_chunk(b"IEND", b"")
    )
