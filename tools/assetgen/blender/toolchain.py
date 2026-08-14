"""Detects and validates the Blender executable required for character builds."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

README_HINT = (
    "Blender 5.0+ is required to (re)generate characters. "
    "See tools/assetgen/README.md's 'Blender toolchain' section for install "
    "instructions."
)


class BlenderNotFoundError(RuntimeError):
    pass


class BlenderVersionTooOldError(RuntimeError):
    pass


_VERSION_RE = re.compile(r"Blender (\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(version_output: str) -> tuple[int, int, int]:
    match = _VERSION_RE.search(version_output)
    if not match:
        raise ValueError(f"could not parse Blender version from: {version_output!r}")
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def check_blender_available(
    executable: str = "blender",
    minimum: tuple[int, int, int] = (5, 0, 0),
) -> tuple[int, int, int]:
    """Raise a clear, actionable error if Blender is missing or too old.

    Returns the detected (major, minor, patch) version on success.
    """
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise BlenderNotFoundError(
            f"`{executable}` executable not found on PATH. {README_HINT}"
        ) from exc

    version = parse_version(result.stdout)
    if version < minimum:
        raise BlenderVersionTooOldError(
            f"Blender {'.'.join(map(str, version))} found, but "
            f"{'.'.join(map(str, minimum))}+ is required. {README_HINT}"
        )
    return version


def blender_subprocess_config(
    executable: str = "blender",
    environ: dict[str, str] | None = None,
) -> tuple[str, dict[str, str]]:
    """Return the executable/env pair to use for Blender `--python` subprocesses.

    On macOS, some PATH entries point at the app bundle's `.../MacOS/Blender`
    binary directly. In that case, `blender --version` works but `blender
    --python ...` can fail unless PYTHONHOME points at the bundled Python tree.
    """
    env = dict(os.environ if environ is None else environ)
    blender_path = shutil.which(executable, path=env.get("PATH"))
    resolved = str(Path(blender_path).resolve()) if blender_path else executable
    binary = Path(resolved)
    if binary.parts[-4:] != ("Blender.app", "Contents", "MacOS", "Blender"):
        return resolved, env

    resources_dir = binary.parents[1] / "Resources"
    version_dirs = sorted(
        path for path in resources_dir.glob("[0-9]*.[0-9]*") if path.is_dir()
    )
    if not version_dirs:
        return resolved, env

    bundled_python = version_dirs[-1] / "python"
    if bundled_python.is_dir():
        env.setdefault("PYTHONHOME", str(bundled_python))
    return resolved, env
