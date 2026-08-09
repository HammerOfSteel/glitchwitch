import json
import struct

from tools.assetgen.blender import validate

# Minimal hand-built GLB fixtures (JSON chunk only, no binary buffer needed for
# node/animation-name assertions — bounding-box checks use accessor min/max,
# which glTF stores in the JSON chunk itself, not the binary blob).

# Chunk 1/2's armature convention (Task 3's design-bible amendment /
# archetype_spec.KNOWN_BONES) — every bone this fixture's node list must name
# for the hierarchy/skinning checks below to exercise real bone names.
_ALL_BONES = [
    "Hips", "Spine", "Neck", "Head",
    "Shoulder.L", "Arm.L", "ForeArm.L", "Hand.L",
    "Shoulder.R", "Arm.R", "ForeArm.R", "Hand.R",
    "UpLeg.L", "Leg.L", "Foot.L", "ToeBase.L",
    "UpLeg.R", "Leg.R", "Foot.R", "ToeBase.R",
]


def _make_glb(gltf_json: dict) -> bytes:
    json_bytes = json.dumps(gltf_json).encode("utf-8")
    json_bytes += b" " * (-len(json_bytes) % 4)  # glTF requires 4-byte alignment
    json_chunk = struct.pack("<II", len(json_bytes), 0x4E4F534A) + json_bytes  # "JSON"
    header = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_bytes))  # "glTF"
    return header + json_chunk


def _valid_gltf_json(tri_count: int = 100, skinned: bool = True) -> dict:
    # Node 0 is Hips (root, has children so the hierarchy reads as connected);
    # every other bone is a flat child of it — good enough for these
    # name/hierarchy assertions, since validate.py doesn't need the exact
    # real skeleton shape, just that every mandatory bone name is present and
    # Hips has children.
    nodes = [{"name": "Hips", "children": list(range(1, len(_ALL_BONES)))}]
    nodes += [{"name": name} for name in _ALL_BONES[1:]]

    attributes = {"POSITION": 0}
    if skinned:
        attributes["JOINTS_0"] = 1
        attributes["WEIGHTS_0"] = 2

    return {
        "nodes": nodes,
        "meshes": [
            {"primitives": [{"attributes": attributes, "indices": 3, "mode": 4}]},
        ],
        "accessors": [
            {
                "count": tri_count * 3 + 1,  # deliberately NOT a multiple of 3,
                # to prove the tri count comes from the indices accessor, not
                # from POSITION's raw vertex count
                "type": "VEC3",
                "min": [-0.2, 0.0, -0.15],
                "max": [0.2, 1.0, 0.15],
            },
            {"count": 1, "type": "VEC4"},  # JOINTS_0 placeholder accessor
            {"count": 1, "type": "VEC4"},  # WEIGHTS_0 placeholder accessor
            {"count": tri_count * 3, "type": "SCALAR"},  # indices accessor
        ],
        "animations": [
            {"name": "idle-loop"}, {"name": "walk-loop"}, {"name": "run-loop"},
            {"name": "wave"}, {"name": "stir"},
        ],
    }


def test_validate_passes_on_well_formed_glb():
    glb_bytes = _make_glb(_valid_gltf_json(tri_count=100))
    report = validate.check(glb_bytes)
    assert report.ok is True
    assert report.errors == []


def test_validate_fails_on_missing_clip():
    gltf_json = _valid_gltf_json()
    gltf_json["animations"] = [a for a in gltf_json["animations"] if a["name"] != "stir"]
    glb_bytes = _make_glb(gltf_json)
    report = validate.check(glb_bytes)
    assert report.ok is False
    assert any("stir" in e for e in report.errors)


def test_validate_fails_on_missing_bone():
    gltf_json = _valid_gltf_json()
    gltf_json["nodes"] = [n for n in gltf_json["nodes"] if n["name"] != "ForeArm.R"]
    # Drop ForeArm.R from Hips's children list too, so indices still line up.
    gltf_json["nodes"][0]["children"] = list(range(1, len(gltf_json["nodes"])))
    glb_bytes = _make_glb(gltf_json)
    report = validate.check(glb_bytes)
    assert report.ok is False
    assert any("ForeArm.R" in e for e in report.errors)


def test_validate_fails_on_disconnected_hips():
    gltf_json = _valid_gltf_json()
    gltf_json["nodes"][0]["children"] = []
    glb_bytes = _make_glb(gltf_json)
    report = validate.check(glb_bytes)
    assert report.ok is False
    assert any("Hips" in e and "children" in e for e in report.errors)


def test_validate_fails_on_unskinned_mesh():
    gltf_json = _valid_gltf_json(skinned=False)
    glb_bytes = _make_glb(gltf_json)
    report = validate.check(glb_bytes)
    assert report.ok is False
    assert any("skin" in e.lower() for e in report.errors)


def test_validate_fails_over_tri_budget():
    glb_bytes = _make_glb(_valid_gltf_json(tri_count=2000))
    report = validate.check(glb_bytes)
    assert report.ok is False
    assert any("tri" in e.lower() for e in report.errors)


def test_validate_fails_on_degenerate_bounding_box():
    gltf_json = _valid_gltf_json()
    # min == max on the Y axis -> zero height, the "floating disconnected
    # villager" class of bug this gate exists to catch.
    gltf_json["accessors"][0]["min"] = [-0.2, 0.5, -0.15]
    gltf_json["accessors"][0]["max"] = [0.2, 0.5, 0.15]
    glb_bytes = _make_glb(gltf_json)
    report = validate.check(glb_bytes)
    assert report.ok is False
    assert any("height" in e.lower() or "bounding" in e.lower() for e in report.errors)
