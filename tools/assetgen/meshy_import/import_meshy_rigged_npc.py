"""Builds a rigged+animated Meshy AI NPC body GLB (idle/walk/run only) from
a "*_rigged_animated_meshy.zip" export - the same export shape as Wren's
(one Character_output.glb + one Merged_Animations.glb), just for a
background NPC instead of the player avatar.

See tools/assetgen/meshy_import/import_wren_meshy.py (the original,
Wren-specific version of this script) and
tools/assetgen/meshy_import/merge_meshy_rigged_npc.py (the generalized
Blender merge logic this wraps).

Usage:
    python tools/assetgen/meshy_import/import_meshy_rigged_npc.py \\
        --source /path/to/Name_rigged_animated_meshy.zip \\
        --name ansel_rowe

Output: assets/thirdparty/meshy-ai/NPCs/rigged/<name>/<name>.glb
(gitignored, like the rest of assets/thirdparty/ - rebuild locally with
this script; the source zip is never committed).
"""
from __future__ import annotations

import argparse
import re
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

# NOTE: must match the existing "NPCs" casing (not "npcs") — this repo's
# working tree already has assets/thirdparty/meshy-ai/NPCs/ (the source
# zips), and macOS/Windows default filesystems are case-insensitive, so a
# differently-cased sibling directory silently collides with it instead of
# creating a separate folder.
NPCS_DIR = REPO_ROOT / "assets" / "thirdparty" / "meshy-ai" / "NPCs" / "rigged"
MERGE_SCRIPT = Path(__file__).resolve().parent / "merge_meshy_rigged_npc.py"
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _extract(zip_path: Path, dest: Path) -> tuple[Path, Path]:
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(dest)
    glbs = sorted(dest.rglob("*.glb"))
    character = next(g for g in glbs if "Character_output" in g.name)
    animations = next(g for g in glbs if "Animations" in g.name)
    return character, animations


def build(source: Path, name: str) -> Path:
    check_blender_available()
    executable, env = blender_subprocess_config()
    out_dir = NPCS_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.glb"

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
        help="Path to Name_rigged_animated_meshy.zip (Meshy AI rigged+"
        "animated character export).",
    )
    parser.add_argument(
        "--name",
        required=True,
        help="snake_case NPC id, e.g. ansel_rowe. Used for the output "
        "folder/file name (assets/thirdparty/meshy-ai/NPCs/rigged/<name>/<name>.glb).",
    )
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"Source zip not found: {args.source}", file=sys.stderr)
        return 1
    if not NAME_PATTERN.match(args.name):
        print(f"--name must be snake_case (e.g. ansel_rowe), got: {args.name!r}", file=sys.stderr)
        return 1

    try:
        out_path = build(args.source, args.name)
    except (BlenderNotFoundError, BlenderVersionTooOldError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Wrote rigged NPC body to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
