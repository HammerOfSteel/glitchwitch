"""Detects and validates the Blender executable required for character builds."""
from __future__ import annotations

import re
import subprocess

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
