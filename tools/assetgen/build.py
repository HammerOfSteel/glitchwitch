"""Build all generated assets into assets/generated/.

Usage: python3 -m tools.assetgen.build
Deterministic: same inputs -> same bytes. Writes a manifest.json summary.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from . import gltf, palette, props

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "assets" / "generated"


def build_all() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"palette": {}, "props": {}}

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

    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    (OUT_DIR / "manifest.json").write_bytes(manifest_bytes + b"\n")
    return manifest


def main() -> int:
    manifest = build_all()
    print(f"assets/generated/ <- palette_main.png ({manifest['palette']['palette_main.png']['bytes']} B)")
    for name, info in manifest["props"].items():
        print(f"assets/generated/ <- {name}.glb  ({info['tris']} tris, {info['bytes']} B)")
    print("asset build OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
