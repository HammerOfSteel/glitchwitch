"""Repo lint — the required-files ritual.

Guards the repository's foundational contract:
- required documents exist and are non-trivial,
- the no-committed-binaries policy holds,
- markdown links between the core docs resolve.

Runs with plain pytest, stdlib only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = {
    "README.md": 1500,
    "CONTRIBUTING.md": 1500,
    "ROADMAP.md": 2500,
    "LICENSES.md": 400,
    "docs/design-bible.md": 3000,
    "docs/story-bible.md": 4000,
    ".gitignore": 100,
    ".gitattributes": 50,
    ".editorconfig": 100,
}

# Extensions considered text/source. Anything tracked outside this set fails
# the no-binaries policy (docs/design-bible.md, "Asset pipeline").
ALLOWED_EXTENSIONS = {
    ".md", ".py", ".gd", ".tscn", ".tres", ".godot", ".json", ".yml", ".yaml",
    ".cfg", ".toml", ".svg", ".gdshader", ".sh", ".editorconfig", ".uid",
    ".gitignore", ".gitattributes", ".gdignore", ".import", ".txt", ".gitkeep",
}

ALLOWED_FILENAMES = {
    ".godot-version", ".gdlintrc", "Makefile", "export_presets.cfg",
}

# Deliberate, scoped exceptions to the no-committed-binaries policy — see
# docs/design-bible.md's "Asset pipeline (decision record)" entry on
# character-pipeline-v2. Each entry here must be a specific tracked-file path
# (never a blanket extension like ".blend"), so this stays an intentional,
# reviewed allowlist rather than an open door for arbitrary binaries.
ALLOWED_BINARY_FILES = {
    "tools/assetgen/blender/base_humanoid.blend",
}

IGNORED_DIRS = {".git", ".godot", ".tooling", ".pytest_cache", "__pycache__",
                "assets", "addons", "build", "exports", "reports", "artifacts",
                ".venv"}


def tracked_files():
    for path in REPO_ROOT.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(REPO_ROOT)
        if any(part in IGNORED_DIRS for part in rel.parts):
            continue
        yield rel, path


def test_required_files_exist_and_are_substantial():
    problems = []
    for rel, min_size in REQUIRED_FILES.items():
        path = REPO_ROOT / rel
        if not path.is_file():
            problems.append(f"missing: {rel}")
        elif path.stat().st_size < min_size:
            problems.append(
                f"too small: {rel} ({path.stat().st_size} < {min_size} bytes)"
            )
    assert not problems, "; ".join(problems)


def test_no_binary_files_tracked():
    offenders = []
    for rel, path in tracked_files():
        if rel.as_posix() in ALLOWED_BINARY_FILES:
            continue
        suffix = path.suffix.lower() or path.name
        if (suffix not in ALLOWED_EXTENSIONS
                and path.name not in ALLOWED_EXTENSIONS
                and path.name not in ALLOWED_FILENAMES):
            offenders.append(str(rel))
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            offenders.append(f"{rel} (not valid utf-8)")
    assert not offenders, f"non-text files tracked: {offenders}"


def test_core_doc_cross_links_resolve():
    """Relative markdown links between core docs must point at real files."""
    link_re = re.compile(r"\]\((?!https?://|#|mailto:)([^)#]+)(?:#[^)]*)?\)")
    problems = []
    for doc in ["README.md", "CONTRIBUTING.md", "ROADMAP.md", "LICENSES.md",
                "docs/design-bible.md", "docs/story-bible.md"]:
        doc_path = REPO_ROOT / doc
        if not doc_path.is_file():
            continue  # covered by the required-files test
        for match in link_re.finditer(doc_path.read_text(encoding="utf-8")):
            target = (doc_path.parent / match.group(1)).resolve()
            if not target.exists():
                problems.append(f"{doc} -> {match.group(1)}")
    assert not problems, f"broken doc links: {problems}"


def test_roadmap_lists_all_twelve_phases():
    text = (REPO_ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    for n in range(12):
        assert f"## Phase {n} " in text, f"ROADMAP missing Phase {n}"
