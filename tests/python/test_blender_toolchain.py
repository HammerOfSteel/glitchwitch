"""Tests for Blender toolchain detection (does NOT require Blender installed —
uses a fake `blender --version` output via monkeypatched subprocess)."""
import os
import subprocess
from pathlib import Path

import pytest

from tools.assetgen.blender import toolchain


def test_parses_version_string():
    fake_output = "Blender 5.2.0 LTS\nbuild date: 2026-07-14\n"
    assert toolchain.parse_version(fake_output) == (5, 2, 0)


def test_check_blender_available_raises_with_clear_message(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no such file: blender")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(toolchain.BlenderNotFoundError) as exc:
        toolchain.check_blender_available()
    assert "tools/assetgen/README.md" in str(exc.value)


def test_check_blender_available_raises_on_old_version(monkeypatch):
    class FakeResult:
        stdout = "Blender 4.2.0\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())
    with pytest.raises(toolchain.BlenderVersionTooOldError):
        toolchain.check_blender_available(minimum=(5, 0, 0))


def test_blender_subprocess_config_resolves_app_bundle_and_sets_pythonhome(
    tmp_path, monkeypatch
):
    app = tmp_path / "Blender.app" / "Contents"
    executable = app / "MacOS" / "Blender"
    bundled_python = app / "Resources" / "5.2" / "python"
    bundled_python.mkdir(parents=True)
    executable.parent.mkdir(parents=True, exist_ok=True)
    executable.write_text("")

    monkeypatch.setattr(
        toolchain.shutil, "which", lambda name, path=None: str(executable)
    )
    env = {"PATH": os.environ.get("PATH", "")}

    resolved, child_env = toolchain.blender_subprocess_config(environ=env)

    assert resolved == str(executable.resolve())
    assert child_env["PYTHONHOME"] == str(bundled_python)


def test_blender_subprocess_config_preserves_existing_pythonhome(monkeypatch):
    monkeypatch.setattr(toolchain.shutil, "which", lambda name, path=None: None)

    resolved, child_env = toolchain.blender_subprocess_config(
        environ={"PYTHONHOME": "/already/set"}
    )

    assert resolved == "blender"
    assert child_env["PYTHONHOME"] == "/already/set"


def test_blender_subprocess_config_resolves_against_passed_path(monkeypatch):
    calls = []

    def fake_which(name, path=None):
        calls.append((name, path))
        return None

    monkeypatch.setattr(toolchain.shutil, "which", fake_which)

    toolchain.blender_subprocess_config(environ={"PATH": "/custom/bin"})

    assert calls == [("blender", "/custom/bin")]
