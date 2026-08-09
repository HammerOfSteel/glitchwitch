"""Tests for Blender toolchain detection (does NOT require Blender installed —
uses a fake `blender --version` output via monkeypatched subprocess)."""
import subprocess

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
