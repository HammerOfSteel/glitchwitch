"""Build all generated assets into assets/generated/.

Usage: python3 -m tools.assetgen.build
Deterministic: same inputs -> same bytes. Writes a manifest.json summary.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from . import (
    animation_contract,
    character,
    character_gen,
    character_validate,
    gltf,
    palette,
    props,
    rig_contract,
)
from .character_spec import SPEC_SCHEMA_VERSION

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "assets" / "generated"


def _walk_nodes(node):
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


def build_all() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"palette": {}, "props": {}, "characters": {}}

    png = palette.build_palette_png()
    (OUT_DIR / "palette_main.png").write_bytes(png)
    manifest["palette"]["palette_main.png"] = {
        "bytes": len(png),
        "sha256": hashlib.sha256(png).hexdigest(),
        "ramps": palette.ramp_names(),
    }

    for name in sorted(props.PROPS):
        builder = props.build_prop(name, seed=0)
        glb = gltf.build_glb(builder, name)
        (OUT_DIR / f"{name}.glb").write_bytes(glb)
        manifest["props"][name] = {
            "tris": builder.tri_count,
            "vertices": builder.vertex_count,
            "bytes": len(glb),
            "sha256": hashlib.sha256(glb).hexdigest(),
        }

    wren_rig, wren_clips = character_gen.generate(character.WREN_SPEC)
    character_validate.validate(wren_rig, wren_clips, tri_budget=character.TRI_BUDGET)
    wren_glb = gltf.build_scene_glb(wren_rig, wren_clips, "wren")
    (OUT_DIR / "wren.glb").write_bytes(wren_glb)
    resolved_parts = character_gen.resolved_parts_for(character.WREN_SPEC)
    manifest["characters"]["wren"] = {
        "archetype": character.WREN_SPEC.archetype,
        "seed": character.WREN_SPEC.seed,
        "resolved_parts": resolved_parts,
        "spec_schema_version": SPEC_SCHEMA_VERSION,
        "rig_contract_version": rig_contract.VERSION,
        "animation_contract_version": animation_contract.VERSION,
        "tris": sum(node.mesh.tri_count for node in _walk_nodes(wren_rig) if node.mesh),
        "bytes": len(wren_glb),
        "sha256": hashlib.sha256(wren_glb).hexdigest(),
        "clips": [clip.name for clip in wren_clips],
    }

    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    (OUT_DIR / "manifest.json").write_bytes(manifest_bytes + b"\n")
    return manifest


def main() -> int:
    manifest = build_all()
    print(f"assets/generated/ <- palette_main.png ({manifest['palette']['palette_main.png']['bytes']} B)")
    for name, info in manifest["props"].items():
        print(f"assets/generated/ <- {name}.glb  ({info['tris']} tris, {info['bytes']} B)")
    for name, info in manifest["characters"].items():
        print(
            f"assets/generated/ <- {name}.glb  ({info['tris']} tris, "
            f"{len(info['clips'])} clips, {info['bytes']} B)"
        )
    print("asset build OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
