"""Builds the Wren placeholder GLB from an external Seren (Meshy AI) rigged
+ animated character export.

This is placeholder tooling only - not part of the deterministic
`tools/assetgen` procedural pipeline and not covered by the pytest suite.
It bridges a rigged/animated model from the user's separate `meshy` project
into a single Wren-shaped placeholder GLB with clips named idle/walk/run, so
Phase 4+ (world/gameplay) work isn't blocked while final character art is
sourced externally (Meshy AI generation or a proper procedural rebuild).

Usage:
    python tools/assetgen/placeholders/fetch_wren_placeholder.py \\
        --source /path/to/seren_dress_rigged_animated_glb.zip

The source zip is expected to contain exactly two GLBs: one with the
skinned mesh ("*_Character_output.glb") and one with the animation clips
("*_Merged_Animations.glb") - this matches the export shape Meshy AI
produces for a rigged+animated character.

Output: assets/thirdparty/wren_placeholder/wren_placeholder.glb
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

OUT_DIR = REPO_ROOT / "assets" / "thirdparty" / "wren_placeholder"
MERGE_SCRIPT = Path(__file__).resolve().parent / "merge_seren_placeholder.py"

DEFAULT_SOURCE_CANDIDATES = [
    Path.home()
    / "Documents"
    / "GitHub"
    / "HammerOfSteel"
    / "meshy"
    / "seren_dress_rigged_animated_glb.zip",
]


def _find_default_source() -> Path | None:
    for candidate in DEFAULT_SOURCE_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


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
    out_path = OUT_DIR / "wren_placeholder.glb"

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
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Path to seren_dress_rigged_animated_glb.zip (or similar "
        "Meshy AI rigged+animated export). Defaults to a search of the "
        "user's local meshy project checkout.",
    )
    args = parser.parse_args()

    source = args.source or _find_default_source()
    if source is None or not source.is_file():
        print(
            "Could not find a source zip. Pass --source /path/to/"
            "seren_dress_rigged_animated_glb.zip",
            file=sys.stderr,
        )
        return 1

    try:
        out_path = build(source)
    except (BlenderNotFoundError, BlenderVersionTooOldError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Wrote Wren placeholder to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
