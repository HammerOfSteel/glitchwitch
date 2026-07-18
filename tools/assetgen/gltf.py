"""Minimal deterministic GLB (glTF 2.0 binary) writer. Stdlib only.

One mesh, one primitive, POSITION/NORMAL/TEXCOORD_0 + indices. No embedded
materials or textures — Godot-side ShaderMaterials bind the palette atlas
(see src/materials/). JSON is emitted with sorted keys and compact separators
so output is byte-stable.
"""
from __future__ import annotations

import json
import struct

from .mesh import MeshBuilder

_COMPONENT_F32 = 5126
_COMPONENT_U16 = 5123
_COMPONENT_U32 = 5125
_TARGET_ARRAY = 34962
_TARGET_ELEMENT = 34963


def _pad(data: bytes, alignment: int = 4, pad_byte: bytes = b"\x00") -> bytes:
    remainder = len(data) % alignment
    if remainder:
        data += pad_byte * (alignment - remainder)
    return data


def build_glb(builder: MeshBuilder, name: str) -> bytes:
    if builder.vertex_count == 0:
        raise ValueError("empty mesh")

    positions = b"".join(struct.pack("<fff", *p) for p in builder.positions)
    normals = b"".join(struct.pack("<fff", *n) for n in builder.normals)
    uvs = b"".join(struct.pack("<ff", *uv) for uv in builder.uvs)
    use_u32 = builder.vertex_count > 0xFFFF
    index_format = "<I" if use_u32 else "<H"
    indices = b"".join(struct.pack(index_format, i) for i in builder.indices)

    sections = [positions, normals, uvs, indices]
    targets = [_TARGET_ARRAY, _TARGET_ARRAY, _TARGET_ARRAY, _TARGET_ELEMENT]
    buffer_views = []
    blob = b""
    for section, target in zip(sections, targets):
        blob = _pad(blob)
        buffer_views.append({
            "buffer": 0,
            "byteOffset": len(blob),
            "byteLength": len(section),
            "target": target,
        })
        blob += section
    blob = _pad(blob)

    mins = [min(p[i] for p in builder.positions) for i in range(3)]
    maxs = [max(p[i] for p in builder.positions) for i in range(3)]

    accessors = [
        {
            "bufferView": 0, "componentType": _COMPONENT_F32,
            "count": builder.vertex_count, "type": "VEC3",
            "min": mins, "max": maxs,
        },
        {
            "bufferView": 1, "componentType": _COMPONENT_F32,
            "count": builder.vertex_count, "type": "VEC3",
        },
        {
            "bufferView": 2, "componentType": _COMPONENT_F32,
            "count": builder.vertex_count, "type": "VEC2",
        },
        {
            "bufferView": 3,
            "componentType": _COMPONENT_U32 if use_u32 else _COMPONENT_U16,
            "count": len(builder.indices), "type": "SCALAR",
        },
    ]

    document = {
        "asset": {"version": "2.0", "generator": "glitchwitch-assetgen"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{
            "name": name,
            "primitives": [{
                "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                "indices": 3,
                "mode": 4,
            }],
        }],
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }

    json_bytes = _pad(
        json.dumps(document, separators=(",", ":"), sort_keys=True).encode("utf-8"),
        pad_byte=b" ",
    )
    total = 12 + 8 + len(json_bytes) + 8 + len(blob)
    return (
        struct.pack("<III", 0x46546C67, 2, total)
        + struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes
        + struct.pack("<II", len(blob), 0x004E4942) + blob
    )


def parse_glb(data: bytes) -> dict:
    """Parse a GLB back into (json_doc, bin_blob) — used by tests."""
    magic, version, _length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67 or version != 2:
        raise ValueError("not a GLB v2 file")
    json_length, json_type = struct.unpack_from("<II", data, 12)
    if json_type != 0x4E4F534A:
        raise ValueError("first chunk is not JSON")
    json_doc = json.loads(data[20:20 + json_length].decode("utf-8"))
    offset = 20 + json_length
    bin_blob = b""
    if offset < len(data):
        bin_length, bin_type = struct.unpack_from("<II", data, offset)
        if bin_type != 0x004E4942:
            raise ValueError("second chunk is not BIN")
        bin_blob = data[offset + 8:offset + 8 + bin_length]
    return {"json": json_doc, "bin": bin_blob}
