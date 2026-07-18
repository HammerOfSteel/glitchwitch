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


class SceneNode:
    """A named node in a GLB scene graph (rigid-part animation rig)."""

    def __init__(self, name, mesh=None, translation=(0.0, 0.0, 0.0),
                 rotation=None, children=None):
        self.name = name
        self.mesh = mesh
        self.translation = tuple(translation)
        self.rotation = tuple(rotation) if rotation is not None else None  # quat xyzw
        self.children = list(children) if children else []


class AnimChannel:
    """One animated property: node + path + keyframes."""

    def __init__(self, node_name, path, times, values):
        if path not in ("translation", "rotation", "scale"):
            raise ValueError(f"bad channel path: {path}")
        if len(times) != len(values):
            raise ValueError("times/values length mismatch")
        self.node_name = node_name
        self.path = path
        self.times = list(times)
        self.values = [tuple(v) for v in values]


class AnimationClip:
    def __init__(self, name, channels):
        self.name = name
        self.channels = list(channels)

    @property
    def duration(self):
        return max((channel.times[-1] for channel in self.channels), default=0.0)


def _flatten_nodes(root: SceneNode):
    ordered = []

    def walk(node):
        index = len(ordered)
        ordered.append(node)
        child_indices = []
        for child in node.children:
            child_indices.append(walk(child))
        node._child_indices = child_indices  # noqa: SLF001 - build-time cache
        return index

    walk(root)
    return ordered


def build_scene_glb(root: SceneNode, animations, name: str) -> bytes:
    """Multi-node GLB with optional node TRS animations (rigid-part rig)."""
    ordered = _flatten_nodes(root)
    node_index = {node.name: i for i, node in enumerate(ordered)}
    if len(node_index) != len(ordered):
        raise ValueError("duplicate node names in scene graph")

    blob = b""
    buffer_views = []
    accessors = []

    def add_view(data: bytes, target=None):
        nonlocal blob
        blob = _pad(blob)
        view = {"buffer": 0, "byteOffset": len(blob), "byteLength": len(data)}
        if target is not None:
            view["target"] = target
        buffer_views.append(view)
        blob += data
        return len(buffer_views) - 1

    def add_accessor(view, component_type, count, acc_type, minimum=None, maximum=None):
        accessor = {
            "bufferView": view, "componentType": component_type,
            "count": count, "type": acc_type,
        }
        if minimum is not None:
            accessor["min"] = minimum
        if maximum is not None:
            accessor["max"] = maximum
        accessors.append(accessor)
        return len(accessors) - 1

    meshes = []
    gltf_nodes = []
    for node in ordered:
        entry = {"name": node.name}
        if any(abs(c) > 1e-9 for c in node.translation):
            entry["translation"] = list(node.translation)
        if node.rotation is not None:
            entry["rotation"] = list(node.rotation)
        if node._child_indices:
            entry["children"] = node._child_indices
        if node.mesh is not None:
            builder = node.mesh
            positions = b"".join(struct.pack("<fff", *p) for p in builder.positions)
            normals = b"".join(struct.pack("<fff", *n) for n in builder.normals)
            uvs = b"".join(struct.pack("<ff", *uv) for uv in builder.uvs)
            use_u32 = builder.vertex_count > 0xFFFF
            index_format = "<I" if use_u32 else "<H"
            indices = b"".join(struct.pack(index_format, i) for i in builder.indices)
            mins = [min(p[i] for p in builder.positions) for i in range(3)]
            maxs = [max(p[i] for p in builder.positions) for i in range(3)]
            pos_acc = add_accessor(
                add_view(positions, _TARGET_ARRAY), _COMPONENT_F32,
                builder.vertex_count, "VEC3", mins, maxs,
            )
            norm_acc = add_accessor(
                add_view(normals, _TARGET_ARRAY), _COMPONENT_F32,
                builder.vertex_count, "VEC3",
            )
            uv_acc = add_accessor(
                add_view(uvs, _TARGET_ARRAY), _COMPONENT_F32,
                builder.vertex_count, "VEC2",
            )
            idx_acc = add_accessor(
                add_view(indices, _TARGET_ELEMENT),
                _COMPONENT_U32 if use_u32 else _COMPONENT_U16,
                len(builder.indices), "SCALAR",
            )
            meshes.append({
                "name": node.name + "_mesh",
                "primitives": [{
                    "attributes": {"POSITION": pos_acc, "NORMAL": norm_acc, "TEXCOORD_0": uv_acc},
                    "indices": idx_acc,
                    "mode": 4,
                }],
            })
            entry["mesh"] = len(meshes) - 1
        gltf_nodes.append(entry)

    gltf_animations = []
    for clip in animations or []:
        samplers = []
        channels = []
        for channel in clip.channels:
            if channel.node_name not in node_index:
                raise ValueError(f"animation targets unknown node: {channel.node_name}")
            times = b"".join(struct.pack("<f", t) for t in channel.times)
            input_acc = add_accessor(
                add_view(times), _COMPONENT_F32, len(channel.times), "SCALAR",
                [min(channel.times)], [max(channel.times)],
            )
            if channel.path == "rotation":
                values = b"".join(struct.pack("<ffff", *v) for v in channel.values)
                out_type = "VEC4"
            else:
                values = b"".join(struct.pack("<fff", *v) for v in channel.values)
                out_type = "VEC3"
            output_acc = add_accessor(
                add_view(values), _COMPONENT_F32, len(channel.values), out_type,
            )
            samplers.append({
                "input": input_acc, "interpolation": "LINEAR", "output": output_acc,
            })
            channels.append({
                "sampler": len(samplers) - 1,
                "target": {"node": node_index[channel.node_name], "path": channel.path},
            })
        gltf_animations.append({"name": clip.name, "channels": channels, "samplers": samplers})

    blob = _pad(blob)
    document = {
        "asset": {"version": "2.0", "generator": "glitchwitch-assetgen"},
        "scene": 0,
        "scenes": [{"nodes": [0], "name": name}],
        "nodes": gltf_nodes,
        "buffers": [{"byteLength": len(blob)}],
        "bufferViews": buffer_views,
        "accessors": accessors,
    }
    if meshes:
        document["meshes"] = meshes
    if gltf_animations:
        document["animations"] = gltf_animations

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
