"""Builds the real Wren body GLB from the user's Meshy AI "dressed, rigged,
animated" export.

Unlike `placeholders/fetch_wren_placeholder.py` (which bridges a temporary
Seren stand-in into a placeholder GLB), this imports the actual final Wren
model sourced from Meshy AI - see docs/character-art-prompts.md and
docs/asset-inventory.md.

Usage:
    python tools/assetgen/meshy_import/import_wren_meshy.py \\
        --source /path/to/dressed_rigged_animated_meshy.zip

The source zip is expected to contain exactly two GLBs: one with the
skinned mesh ("*_Character_output.glb") and one with the animation clips
("*_Merged_Animations.glb") - this matches the export shape Meshy AI
produces for a rigged+animated character.

Output: assets/thirdparty/meshy-ai/wren/wren.glb
(gitignored, like the rest of assets/thirdparty/ - rebuild locally with
this script; the source zip is never committed).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSETGEN_DIR = REPO_ROOT / "tools" / "assetgen"
sys.path.insert(0, str(ASSETGEN_DIR))

from blender.toolchain import (  # noqa: E402
    BlenderNotFoundError,
    BlenderVersionTooOldError,
    blender_subprocess_config,
    check_blender_available,
)

OUT_DIR = REPO_ROOT / "assets" / "thirdparty" / "meshy-ai" / "wren"
MERGE_SCRIPT = Path(__file__).resolve().parent / "merge_wren_meshy.py"


def _extract(zip_path: Path, dest: Path) -> tuple[Path, Path]:
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(dest)
    glbs = sorted(dest.rglob("*.glb"))
    character = next(g for g in glbs if "Character_output" in g.name)
    animations = next(g for g in glbs if "Animations" in g.name)
    return character, animations


def build(source: Path) -> Path:
    check_blender_available()
    executable, env = blender_subprocess_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "wren.glb"

    with tempfile.TemporaryDirectory() as tmp:
        character_glb, animations_glb = _extract(source, Path(tmp))
        result = subprocess.run(
            [
                executable,
                "--background",
                "--python",
                str(MERGE_SCRIPT),
                "--",
                str(character_glb),
                str(animations_glb),
                str(out_path),
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Blender merge failed:\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        print(result.stdout)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to dressed_rigged_animated_meshy.zip (or similar Meshy "
        "AI rigged+animated character export).",
    )
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"Source zip not found: {args.source}", file=sys.stderr)
        return 1

    try:
        out_path = build(args.source)
    except (BlenderNotFoundError, BlenderVersionTooOldError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Wrote real Wren body to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
