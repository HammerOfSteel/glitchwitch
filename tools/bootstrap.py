#!/usr/bin/env python3
"""Fetch pinned external tooling for Glitch Witch.

Nothing binary is committed to this repository; this script reproduces the
tooling layer at exact pinned versions (tools/versions.json):

  --gdunit      gdUnit4 addon        -> addons/gdUnit4/
  --godot       Godot editor binary  -> .tooling/godot
  --templates   export templates     -> ~/.local/share/godot/export_templates/
  --all         gdunit + godot

Stdlib only. Python 3.9+.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import stat
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_FILE = REPO_ROOT / "tools" / "versions.json"
USER_AGENT = "glitchwitch-bootstrap/1.0"


def load_versions() -> dict:
    with VERSIONS_FILE.open(encoding="utf-8") as handle:
        return json.load(handle)


def fetch(url: str) -> bytes:
    print(f"  fetching {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=600) as response:
        return response.read()


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def install_gdunit(versions: dict, force: bool = False) -> None:
    target = REPO_ROOT / "addons" / "gdUnit4"
    plugin_cfg = target / "plugin.cfg"
    if plugin_cfg.is_file() and not force:
        print(f"gdUnit4 already present at {target} (use --force to refresh)")
        return
    info = versions["gdunit4"]
    data = fetch(info["zip"])
    if target.exists():
        shutil.rmtree(target)
    prefix = None
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            marker = "addons/gdUnit4/"
            index = name.find(marker)
            if index == -1:
                continue
            relative = name[index + len(marker):]
            if not relative or name.endswith("/"):
                continue
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, destination.open("wb") as sink:
                shutil.copyfileobj(source, sink)
            prefix = prefix or name[:index]
    if not plugin_cfg.is_file():
        sys.exit("bootstrap error: gdUnit4 zip did not contain addons/gdUnit4/plugin.cfg")
    cfg_text = plugin_cfg.read_text(encoding="utf-8")
    expected = info["tag"].lstrip("v")
    if expected not in cfg_text:
        print(f"  WARNING: plugin.cfg does not mention version {expected}")
    print(f"gdUnit4 {info['tag']} installed -> {target}")


def install_godot(versions: dict, force: bool = False) -> None:
    tooling = REPO_ROOT / ".tooling"
    binary = tooling / "godot"
    if binary.is_file() and not force:
        print(f"Godot already present at {binary} (use --force to refresh)")
        return
    info = versions["godot"]
    data = fetch(info["linux_zip"])
    digest = sha256_of(data)
    if digest != info["linux_sha256"]:
        sys.exit(
            "bootstrap error: Godot zip sha256 mismatch\n"
            f"  expected {info['linux_sha256']}\n  got      {digest}"
        )
    tooling.mkdir(exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [n for n in archive.namelist() if n.endswith(".x86_64")]
        if len(names) != 1:
            sys.exit(f"bootstrap error: unexpected zip contents: {archive.namelist()}")
        with archive.open(names[0]) as source, binary.open("wb") as sink:
            shutil.copyfileobj(source, sink)
    binary.chmod(binary.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Godot {info['version']} installed -> {binary}")


def install_templates(versions: dict, force: bool = False) -> None:
    info = versions["godot"]
    version_dir = info["version"].replace("-", ".")
    home = Path(os.environ.get("HOME", "~")).expanduser()
    target = home / ".local" / "share" / "godot" / "export_templates" / version_dir
    if (target / "version.txt").is_file() and not force:
        print(f"export templates already present at {target}")
        return
    data = fetch(info["templates"])
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in archive.namelist():
            if not name.startswith("templates/") or name.endswith("/"):
                continue
            destination = target / name[len("templates/"):]
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, destination.open("wb") as sink:
                shutil.copyfileobj(source, sink)
    print(f"export templates installed -> {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gdunit", action="store_true")
    parser.add_argument("--godot", action="store_true")
    parser.add_argument("--templates", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not any([args.gdunit, args.godot, args.templates, args.all]):
        parser.print_help()
        return 2
    versions = load_versions()
    if args.gdunit or args.all:
        install_gdunit(versions, args.force)
    if args.godot or args.all:
        install_godot(versions, args.force)
    if args.templates:
        install_templates(versions, args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
