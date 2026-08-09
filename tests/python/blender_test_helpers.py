"""Shared helper for tests that need to run code inside a real headless Blender
process (any tools/assetgen/blender module that `import bpy`s).

Pattern: write a small driver script to a repo-local scratch file that imports
the module under test, calls one of its functions, and writes `RESULT:<json>` as
the last line of stdout. `run_in_blender()` invokes `blender --background
--python <driver>` and parses that line's JSON payload. This mirrors the *shape*
of the MCP
`result = {...}` contract (see mcp_client.py) — every unit function under test
returns a plain dict, never prints or uses global state — but the wire format is
necessarily different: mcp_client.py talks to a long-running Blender process over
a raw socket, while this helper launches a fresh headless `blender --background`
process per test and can only observe it through stdout/exit code. So the
convention shared across all three invokers (this test helper, build_character.py
calling the same functions directly in-process, and the live MCP socket for
iteration) is "unit functions return a plain JSON-serializable dict" — not an
identical transport.
"""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

import pytest

from tools.assetgen.blender import toolchain

REPO_ROOT = Path(__file__).resolve().parents[2]
# Repo-local scratch dir for generated driver scripts — gitignored, not the
# system /tmp (this harness's driver scripts must stay under the repo/worktree
# so they're inspectable and don't depend on a shared, environment-specific
# temp filesystem). Reuses the same "artifacts/" gitignore entry as Chunk 1's
# render-check scratch path.
SCRATCH_DIR = REPO_ROOT / "artifacts" / "blender_test_drivers"


def blender_available() -> bool:
    try:
        toolchain.check_blender_available()
        return True
    except (toolchain.BlenderNotFoundError, toolchain.BlenderVersionTooOldError):
        return False

requires_blender = pytest.mark.skipif(
    not blender_available(), reason="blender executable not found or too old"
)


def run_in_blender(driver_code: str, timeout: float = 120) -> dict:
    """Run `driver_code` inside headless Blender; return its parsed `result` dict.

    `driver_code` must print exactly one line of the form `RESULT:<json>` before
    exiting (see existing tasks in this chunk for the convention each module's
    driver script follows).
    """
    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    driver_path = SCRATCH_DIR / f"driver_{uuid.uuid4().hex}.py"
    driver_path.write_text(driver_code)
    blender_executable, blender_env = toolchain.blender_subprocess_config()
    try:
        proc = subprocess.run(
            [blender_executable, "--background", "--python", str(driver_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
            env=blender_env,
        )
    finally:
        driver_path.unlink(missing_ok=True)

    result_lines = [
        line for line in proc.stdout.splitlines() if line.startswith("RESULT:")
    ]
    if not result_lines:
        raise AssertionError(
            "no RESULT: line in Blender stdout — "
            f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
        )
    return json.loads(result_lines[-1][len("RESULT:") :])
