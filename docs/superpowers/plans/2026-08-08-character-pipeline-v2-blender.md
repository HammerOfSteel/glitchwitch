# Character Pipeline v2 (Blender-Backed) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the v1 raw-triangle-math character pipeline with a Blender-backed
one — a hand-authored (scripted, not mouse-sculpted) skinned humanoid base mesh with
real subdivision/bevel smoothing, layered archetype clothing, and bone-based
animation — so Wren and the villager reach a "soft toy diorama" visual bar instead of
flat boxes, while props/nature/buildings stay on the existing pure-Python pipeline.

**Architecture:** A new `tools/assetgen/blender/` package of small, single-purpose
modules (loader, proportions, clothing, materials, animate, export, validate),
orchestrated by `blender/build_character.py`, invoked headless via `blender
--background --python` from `build.py`. A one-time hand-authored `base_humanoid.blend`
is the committed source-of-truth body mesh; everything downstream is scripted and
deterministic given that file plus an archetype spec.

**Tech Stack:** Python 3.9 (stdlib only, same as v1), Blender 5.0+ (`bpy` inside
Blender's own Python — NOT importable from the system `python3`, hence all Blender
code runs via subprocess/headless invocation or the live MCP socket, never `import
bpy` directly in `tools/assetgen`'s own test-run Python), Godot 4.7 for in-engine
verification, pytest for the existing test suite style.

**Spec:** `docs/superpowers/specs/2026-08-08-character-pipeline-v2-blender-design.md`
(read this first — it has the full rationale, the unit-interface table, the
acceptance/fallback criteria for the base mesh, and the exact Godot animation-name
contract this plan must satisfy).

---

## Chunk 1: Toolchain, design-bible edit, and the base humanoid mesh

### Task 1: Blender toolchain check and MCP client helper

**Files:**
- Create: `tools/assetgen/blender/__init__.py`
- Create: `tools/assetgen/blender/toolchain.py`
- Create: `tools/assetgen/blender/mcp_client.py`
- Test: `tests/python/test_blender_toolchain.py`

- [ ] **Step 1: Write the failing test for version detection**

```python
# tests/python/test_blender_toolchain.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_blender_toolchain.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.assetgen.blender'`

- [ ] **Step 3: Write the implementation**

```python
# tools/assetgen/blender/__init__.py
"""Blender-backed character mesh generation (v2 pipeline).

See docs/superpowers/specs/2026-08-08-character-pipeline-v2-blender-design.md
for the full architecture. This package never `import bpy` at module scope —
bpy only exists inside a running Blender process. Code here either (a) shells
out to `blender --background --python <script>` (the reproducible build path)
or (b) is executed *as* one of those scripts, run by Blender's own
interpreter, where `import bpy` is valid.
"""
```

```python
# tools/assetgen/blender/toolchain.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_blender_toolchain.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Write the MCP client helper (dev-loop convenience, not build-critical)**

```python
# tools/assetgen/blender/mcp_client.py
"""Client for the blender-mcp addon's raw execute socket.

Dev-iteration convenience only (see spec's "Dev iteration loop" section) — the
reproducible build path never uses this, it always shells out to headless
`blender --background --python`. This lets a script be sent to a *running*
Blender instance (with the blender-mcp addon's server active on
127.0.0.1:9876) so changes are visible live in that Blender window.
"""
from __future__ import annotations

import json
import socket


class BlenderMCPError(RuntimeError):
    pass


def run(code: str, host: str = "127.0.0.1", port: int = 9876, timeout: float = 30) -> dict:
    """Execute `code` inside the running Blender process and return its result dict.

    `code` must set a `result = {...}` (JSON-serializable) variable, matching the
    blender-mcp addon's execute-request contract.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        request = {"type": "execute", "code": code, "strict_json": True}
        sock.sendall((json.dumps(request) + "\0").encode("utf-8"))
        buf = b""
        while b"\0" not in buf:
            chunk = sock.recv(1 << 20)
            if not chunk:
                break
            buf += chunk
    except OSError as exc:
        raise BlenderMCPError(
            "could not reach blender-mcp at "
            f"{host}:{port} — is Blender running with the addon enabled?"
        ) from exc
    finally:
        sock.close()

    text = buf.split(b"\0", 1)[0].decode("utf-8", errors="replace")
    response = json.loads(text)
    if response.get("status") != "ok":
        raise BlenderMCPError(response.get("message", str(response)))
    return response.get("result", {})
```

No test for `mcp_client.py` itself (it requires a live Blender+addon to exercise
meaningfully, and the spec explicitly scopes this as a dev-convenience path, not the
reproducible build path — the reproducible path is covered by `toolchain.py`'s tests
and later headless-invocation tests in Task 8).

- [ ] **Step 6: Commit**

```bash
git add tools/assetgen/blender/__init__.py tools/assetgen/blender/toolchain.py \
        tools/assetgen/blender/mcp_client.py tests/python/test_blender_toolchain.py
git commit -m "Add Blender toolchain detection and MCP dev-loop client"
```

---

### Task 1b: `tools/assetgen/README.md` Blender toolchain section

**Files:**
- Modify: `tools/assetgen/README.md`

- [ ] **Step 1: Add the section**

Add a new section near the top of `tools/assetgen/README.md`, above "Adding a new
part":

```markdown
## Blender toolchain (characters only)

Character generation (Wren, villager, future NPCs) requires **Blender 5.0+** on
`PATH` as `blender`. Props/nature/buildings do not need Blender — they stay on the
pure-Python pipeline.

Install Blender from https://www.blender.org/download/ (or your OS package
manager) and confirm it's on `PATH`:

```bash
blender --version   # must print "Blender 5.0" or higher
```

`python3 -m tools.assetgen.build` checks this automatically before attempting a
character build and fails with a clear message (not a cryptic subprocess error) if
Blender is missing or too old. See `tools/assetgen/blender/toolchain.py`.

For live iteration on character meshes (watching changes in a running Blender
window instead of the screenshot/re-import round trip), install the `blender-mcp`
addon and start its server from within Blender; `tools/assetgen/blender/mcp_client.py`
then talks to it over `127.0.0.1:9876`. This is a dev convenience only — it is
never required for `make assets` to succeed.
```

- [ ] **Step 2: Commit**

```bash
git add tools/assetgen/README.md
git commit -m "Document Blender toolchain requirement in assetgen README"
```

---

### Task 2: Design bible policy amendment

**Files:**
- Modify: `docs/design-bible.md:129-140` (the "Asset pipeline (decision record)" section)

- [ ] **Step 1: Apply the amendment**

Replace the current "Asset pipeline (decision record)" section's bullets with:

```markdown
## Asset pipeline (decision record)

- `tools/assetgen` is **pure Python (stdlib only)** for props, nature, and building
  assets: mesh kit → GLB writer, palette → PNG writer. Deterministic under fixed
  seeds; byte-hash tested. Rationale: zero heavy dependencies in CI/sandbox, total
  reproducibility, fast iteration.
- **Characters are Blender-backed (revised policy, character-pipeline-v2):**
  `tools/assetgen/blender/` drives a headless `blender --background --python`
  invocation. **One committed binary source asset**,
  `tools/assetgen/blender/base_humanoid.blend`, is the shared skinned body mesh —
  this is a deliberate, scoped exception to "nothing binary is committed," not a
  general policy change. Everything downstream of that file (proportions,
  clothing, materials, animation, export) is scripted and deterministic given the
  base file plus an archetype spec/seed. Blender 5.0+ becomes a required build-time
  dependency whenever `make assets` (re)generates a character.
- **CC0 skinned bases (KayKit / Quaternius)** remain the documented fallback — no
  longer "instead of Blender," but *for the base mesh itself* if scripted `bpy`
  topology authoring doesn't clear the acceptance bar in
  `docs/superpowers/specs/2026-08-08-character-pipeline-v2-blender-design.md`.
- `assets/generated/` and `assets/thirdparty/` remain build outputs, ignored by git,
  rebuilt by `make assets` / bootstrap — this is unchanged. The one exception is the
  committed `base_humanoid.blend` *source* asset itself, which lives under
  `tools/assetgen/blender/` (alongside the code that consumes it), not under
  `assets/generated/`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/design-bible.md
git commit -m "Amend design bible asset-pipeline policy for Blender-backed characters"
```

---

### Task 3: Base humanoid mesh — scripted authoring (exploratory task)

This task is inherently iterative 3D-modeling work, not deterministic TDD — there is
no "write a failing test, then pass it" for mesh topology quality. Follow the spec's
"Feasibility and fallback" acceptance bar instead. Work via the live Blender MCP loop
(`mcp_client.run(...)`) so progress is visible in the user's Blender window, then
freeze the final result as the headless-buildable script plus the committed `.blend`.

**Files:**
- Create: `tools/assetgen/blender/body_dims.py` (shared dimension constants — see
  below; imported by both this script and Chunk 2's `clothing_parts/` modules so
  clothing stays sized/positioned consistently with the body it layers over)
- Create: `tools/assetgen/blender/author_base_humanoid.py` (the script; re-runnable,
  not auto-run by `make assets`)
- Create: `tools/assetgen/blender/base_humanoid.blend` (committed binary output of
  running the script once)
- Test: `tests/python/test_base_humanoid_asset.py`

- [ ] **Step 0: Write the shared dimension constants module**

```python
# tools/assetgen/blender/body_dims.py
"""Shared body-proportion constants (units = meters, total standing height 1.0m
to match the existing v1 character scale in tools/assetgen/character.py).

This is a plain-data module (no bpy import) so it's importable both by Blender
scripts (author_base_humanoid.py, clothing_parts/*.py) and by plain pytest-run
Python if ever needed for a non-Blender consistency check. These are STARTING
values, not open choices — adjust only if a render check (Task 3 Step 2) fails
the acceptance bar, and note any change in a comment here.
"""
from __future__ import annotations

DIMS = {
    "head_height": 0.28,      # ~28% of total height -> chibi-adjacent per spec
    "torso_height": 0.32,
    "torso_width": 0.24,
    "hip_width": 0.22,
    "upper_arm_length": 0.16,
    "lower_arm_length": 0.14,
    "hand_length": 0.08,
    "upper_leg_length": 0.20,
    "lower_leg_length": 0.18,
    "foot_length": 0.10,
    "bevel_width": 0.01,       # bevel modifier width, all parts start equal
    "bevel_segments": 4,
    "subsurf_levels": 2,
}
```

Commit this alongside Step 6's commit (it's part of the same "author the base
mesh" unit of work, not a separate task).

- [ ] **Step 1: Draft the control-cage + armature script**

Write `author_base_humanoid.py` as a standalone Blender script (has `import bpy` at
module scope — this file is only ever run *by* Blender, headless or live, never
imported by plain `python3`). Structure:

```python
"""Authors tools/assetgen/blender/base_humanoid.blend from scratch.

Run via: blender --background --python tools/assetgen/blender/author_base_humanoid.py
(or send this file's contents through mcp_client.run(...) for live iteration).

This is NOT part of the `make assets` build — it's a one-time (or deliberately
re-run) authoring step. Re-running it overwrites base_humanoid.blend; commit the
result deliberately, same ritual as any other design-bible-governed asset.

Concrete decisions locked in (not left open for "decide during iteration"):
- Body parts are built as separate bmesh objects, then joined
  (bpy.ops.object.join) into ONE mesh object named "body" before armature
  binding. A single skinned mesh is the standard glTF/Blender-exporter shape and
  avoids weight-painting complexity across object boundaries. Clothing (added
  later, per-archetype, in Chunk 2's Task 7) stays as SEPARATE mesh objects
  bound to the same armature — only the base body itself is a single joined
  mesh.
- Output path is always relative to this script's own location:
  Path(__file__).parent / "base_humanoid.blend" — i.e.
  tools/assetgen/blender/base_humanoid.blend — not a hand-typed absolute path.
"""
import bpy
import bmesh
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from body_dims import DIMS  # see this task's Step 0

OUTPUT_PATH = Path(__file__).resolve().parent / "base_humanoid.blend"

# 1. Clear default scene.
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

# 2. Build a low-res control cage per body part (torso, head, upper/lower arm,
#    hand, upper/lower leg, foot) via bmesh, using DIMS above for initial sizing.
#    Add one loop cut at each of shoulder/elbow/hip/knee/waist (bpy.ops.mesh
#    .loopcut_slide equivalent via bmesh.ops.subdivide_edgering on the ring at
#    that bend point) so bends hold shape under subdivision — this is the
#    concrete mechanism, not "add loop cuts" left abstract.
# 3. Mirror modifier (use_axis=(True, False, False), i.e. mirror across local X)
#    for left/right symmetry: build the right-side limbs once, mirror to left.
# 4. Bevel modifier (width=DIMS["bevel_width"], segments=DIMS["bevel_segments"])
#    + Subsurf modifier (levels=DIMS["subsurf_levels"]) + shade_smooth() on every
#    body-part object, applied in that order (bevel before subsurf) so edges stay
#    crisp enough to read as "soft toy" rather than a featureless blob.
# 5. bpy.ops.object.join() all body-part objects into one mesh object named "body"
#    (see "Concrete decisions" above — this is fixed, not an iteration choice).
# 6. Build the Armature: Hips (root) -> Spine -> Neck -> Head; Shoulder -> Arm ->
#    ForeArm -> Hand per side; UpLeg -> Leg -> Foot -> ToeBase per side (simplify
#    spine to 1-2 bones per spec, not the reference's 3). Bone head/tail positions
#    come directly from DIMS above (e.g. Hips at torso_height/2 from the ground,
#    Spine tail at Hips head + torso_height, etc.) so the skeleton always matches
#    whatever DIMS values were last used to build the mesh.
#    Left/right naming convention (fixed, not left to iteration — Chunk 2's
#    archetype_spec.KNOWN_BONES and clothing/proportions units both hard-code
#    this exact scheme): every paired bone uses a ".L"/".R" suffix, e.g.
#    "Shoulder.L", "UpLeg.R" — this matches Blender's own Mirror
#    modifier/vertex-group auto-mirroring convention (Blender specifically
#    recognizes ".L"/".R", "_L"/"_R", "Left"/"Right" as mirrorable suffixes;
#    ".L"/".R" is used here since it's the terser, Blender-native default), so
#    the Mirror modifier used for body/clothing symmetry (Step 3, and
#    clothing_parts/boots.py in Chunk 2) auto-flips vertex groups without
#    manual remapping. Unpaired bones (Hips, Spine, Neck, Head) have no suffix.

# 7. Parent "body" mesh to armature with automatic weights
#    (bpy.ops.object.parent_set(type='ARMATURE_AUTO')). Automatic weights are the
#    default outcome; only hand-correct a vertex group via bmesh/vertex_groups if
#    Step 2's pose-extreme render check in a specific area shows visible bleed
#    (e.g. hip vertices moving when only the hand bone is posed) — don't
#    pre-emptively hand-paint weights that automatic weighting already gets right.
# 8. UV-unwrap onto the palette atlas cell layout (see tools/assetgen/palette.py
#    for the existing cell coordinates prop-side; reuse the same atlas image
#    dimensions so the palette system doesn't need a second atlas).
# 9. Save: bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_PATH))

result = {"status": "authored", "objects": [o.name for o in bpy.data.objects]}
```

Send this script's contents through `mcp_client.run(...)` for live iteration
(or run it headless: `blender --background --python
tools/assetgen/blender/author_base_humanoid.py`), checking a render after each
numbered step group (see Step 2) rather than writing the whole script blind and
checking only at the end.

- [ ] **Step 2: Iterate against the acceptance bar**

After each meaningful change, render a check image to a repo-local, gitignored
scratch path (`artifacts/` is already gitignored per `.gitignore` — reuse it rather
than `/tmp`, which isn't guaranteed to persist/be inspectable across tool calls in
every environment) and view it:

```python
mcp_client.run(SCRIPT_CODE)  # from Task 3 Step 1, or a focused sub-step
mcp_client.run('''
import bpy
from pathlib import Path
scene = bpy.context.scene
out = Path(bpy.data.filepath).resolve().parents[3] / "artifacts" / "base_humanoid_check.png"
# bpy.data.filepath is .../tools/assetgen/blender/base_humanoid.blend, so
# parents[3] is the repo root (parents[0]=blender, [1]=assetgen, [2]=tools).
out.parent.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(out)
scene.render.resolution_x = 800
scene.render.resolution_y = 800
bpy.ops.render.render(write_still=True)
result = {"rendered": str(out)}
''')
```

Then `view` the PNG at `artifacts/base_humanoid_check.png`. Repeat until, per the
spec's acceptance bar, within what's checkable in this chunk: (a) the mesh
deforms without pinching/collapsing across idle/walk/run/wave/stir-style test
poses (pose the armature manually via `bpy.ops.pose...` and re-render at extremes
to check), (b) the silhouette reads as "soft toy humanoid," judged against the
LoA-remake/Animal Crossing reference bar. Full structural validation (bone
names, vertex-group weights via a loader) requires `blender/loader.py`, which
doesn't exist yet — that check is deferred to the later chunk that builds it;
this chunk's own regression test (Step 4) only confirms the file was committed
and isn't a stub.

**Escalation checkpoint (concrete, replaces "reasonable number of iteration
passes"):** if 5 iteration passes (each pass = one script revision + render +
visual check) do not converge on the acceptance bar, stop and raise the documented
fallback (retopologize/adapt a CC0 KayKit/Quaternius base instead) to the user
explicitly before proceeding — do not silently swap approaches or keep iterating
indefinitely.

- [ ] **Step 3: Save the final `.blend` and commit it**

```bash
git add tools/assetgen/blender/body_dims.py \
        tools/assetgen/blender/author_base_humanoid.py \
        tools/assetgen/blender/base_humanoid.blend
git commit -m "Author base_humanoid.blend: skinned chibi-proportioned body mesh"
```

- [ ] **Step 4: Write a structural regression test**

This can't check visual quality (see above), but can catch gross breakage (file
missing, wrong object/bone names) cheaply without needing a live Blender:

```python
# tests/python/test_base_humanoid_asset.py
"""Structural checks on the committed base_humanoid.blend.

Does NOT require Blender/bpy to run — a .blend file is a custom binary format we
don't parse here. This test only asserts the file exists and is non-trivially
sized (catches "forgot to commit" / "committed an empty file" mistakes). Real
structural validation (bone names, mesh presence, vertex-group weights) requires
a live Blender/bpy process and is added later once `blender/loader.py` exists (a
later chunk covering the archetype-variation units), exercised via a
`test_blender_loader.py` that invokes headless Blender.
"""
from pathlib import Path

BASE_BLEND = (
    Path(__file__).resolve().parents[2]
    / "tools" / "assetgen" / "blender" / "base_humanoid.blend"
)


def test_base_humanoid_blend_exists():
    assert BASE_BLEND.exists(), (
        f"{BASE_BLEND} missing — run "
        "tools/assetgen/blender/author_base_humanoid.py and commit its output"
    )


def test_base_humanoid_blend_is_nontrivial_size():
    # A real authored mesh+armature .blend is comfortably >100KB; guards against
    # committing a stub/empty file by mistake.
    assert BASE_BLEND.stat().st_size > 100_000
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_base_humanoid_asset.py -v`
Expected: PASS (2 tests) — only after Step 3's commit exists

- [ ] **Step 6: Commit the test**

```bash
git add tests/python/test_base_humanoid_asset.py
git commit -m "Add structural existence test for base_humanoid.blend"
```

---

## Chunk 2: Archetype spec data + loader/proportions/clothing/materials units

This chunk builds the four architecture-table units that turn `base_humanoid.blend`
plus a data-only archetype description into a fully dressed, correctly-proportioned
(but not yet animated/exported) Blender scene. It does not touch animation, export, or
Godot — those are Chunk 3.

**Shared testing approach for this chunk:** every module below (`loader.py`,
`proportions.py`, `clothing.py`, `materials.py`) contains `import bpy` and therefore
cannot be imported directly by pytest (see plan header's Tech Stack note). Each
module's automated tests instead shell out to `blender --background --python` running
a tiny driver script that imports the module *inside* Blender's interpreter, calls its
function, and prints a JSON result line that the pytest test parses from stdout. This
pattern is written once as a shared helper (Task 4) and reused by every later task in
this chunk and Chunk 3.

All of this chunk's automated tests are skipped (not failed) when `blender` isn't on
`PATH`, using `toolchain.check_blender_available()` from Task 1 in a pytest
`skipif`/fixture — consistent with `toolchain.py` already being the single place that
knows how to detect Blender, and so contributors without Blender installed still get a
clean `pytest` run (skipped, not red) on the rest of the suite.

### Task 4: Headless-Blender test helper + `ArchetypeSpec` data contract

**Files:**
- Create: `tools/assetgen/blender/archetype_spec.py`
- Create: `tests/python/blender_test_helpers.py`
- Test: `tests/python/test_archetype_spec.py`

- [ ] **Step 1: Write the failing test for `ArchetypeSpec`**

```python
# tests/python/test_archetype_spec.py
import pytest

from tools.assetgen.blender.archetype_spec import ArchetypeSpec


def test_archetype_spec_requires_name_and_bone_scales():
    spec = ArchetypeSpec(
        name="villager",
        bone_scales={"Spine": 1.0, "UpLeg.L": 0.95, "UpLeg.R": 0.95},
        clothing=["tunic", "boots"],
        palette={"tunic": ("wood", 1), "boots": ("bark", 0)},
        clips=["idle", "walk", "run", "wave", "stir"],
    )
    assert spec.name == "villager"
    assert spec.bone_scales["Spine"] == 1.0


def test_archetype_spec_rejects_unknown_bone_name():
    with pytest.raises(ValueError, match="unknown bone"):
        ArchetypeSpec(
            name="villager",
            bone_scales={"NotARealBone": 1.0},
            clothing=[],
            palette={},
            clips=["idle", "walk", "run", "wave", "stir"],
        )


def test_archetype_spec_rejects_clothing_without_palette_entry():
    with pytest.raises(ValueError, match="no palette entry"):
        ArchetypeSpec(
            name="villager",
            bone_scales={},
            clothing=["tunic"],
            palette={},  # missing "tunic"
            clips=["idle", "walk", "run", "wave", "stir"],
        )


def test_archetype_spec_rejects_missing_mandatory_clip():
    with pytest.raises(ValueError, match="missing mandatory clip"):
        ArchetypeSpec(
            name="villager",
            bone_scales={},
            clothing=[],
            palette={},
            clips=["idle", "walk"],  # missing run/wave/stir
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_archetype_spec.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.assetgen.blender.archetype_spec'`

- [ ] **Step 3: Write the implementation**

```python
# tools/assetgen/blender/archetype_spec.py
"""ArchetypeSpec: the data-only input contract for the v2 archetype-variation
units (proportions.py, clothing.py, materials.py, animate.py).

Deliberately separate from the existing tools/assetgen/character_spec.py
(v1's CharacterSpec) rather than extending it: v1's CharacterSpec describes a
part-registry-based mesh recipe (parts dict of PartSpec choices) which has no
meaning for the Blender pipeline (armature bone scales, clothing mesh names,
palette-cell assignments instead). Keeping them separate avoids a shared class
that means two different things depending on which pipeline reads it. `build.py`
picks which spec type to construct based on whether an archetype is on the v1 or
v2 (Blender) path.

Bone names are validated against the base armature's known bone list (mirrors
rig_contract.py's role for v1: fail loud if a spec references a bone that
doesn't exist, rather than silently no-op-ing in Blender).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Must match the armature built by author_base_humanoid.py (Chunk 1, Task 3,
# step 6), including its fixed ".L"/".R" left/right suffix convention
# (Blender's own Mirror-modifier/vertex-group auto-mirroring naming scheme —
# see Task 3 step 6's comment). Kept here (not re-derived from the live
# .blend, which would require bpy) so this module stays pure-Python and
# independently testable.
KNOWN_BONES = frozenset({
    "Hips", "Spine", "Neck", "Head",
    "Shoulder.L", "Arm.L", "ForeArm.L", "Hand.L",
    "Shoulder.R", "Arm.R", "ForeArm.R", "Hand.R",
    "UpLeg.L", "Leg.L", "Foot.L", "ToeBase.L",
    "UpLeg.R", "Leg.R", "Foot.R", "ToeBase.R",
})

# Matches avatar.gd's MOTION_CLIPS + GESTURE_CLIPS exactly (see spec's Godot
# integration contract) — every archetype must define all five, even if some
# turn out to be visually identical to another archetype's, so `animate.py`
# always has a full clip set to bake.
MANDATORY_CLIPS = ("idle", "walk", "run", "wave", "stir")


@dataclass(frozen=True)
class ArchetypeSpec:
    name: str
    bone_scales: dict[str, float] = field(default_factory=dict)
    clothing: list[str] = field(default_factory=list)
    palette: dict[str, tuple[str, int]] = field(default_factory=dict)
    clips: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ArchetypeSpec.name must be non-empty")
        for bone in self.bone_scales:
            if bone not in KNOWN_BONES:
                raise ValueError(f"unknown bone name in bone_scales: {bone!r}")
        for piece in self.clothing:
            if piece not in self.palette:
                raise ValueError(f"clothing piece {piece!r} has no palette entry")
        missing = [c for c in MANDATORY_CLIPS if c not in self.clips]
        if missing:
            raise ValueError(f"missing mandatory clip(s): {missing}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_archetype_spec.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write the shared headless-Blender test helper**

This is infrastructure only (no test of its own beyond being exercised by every
later task's tests in this chunk and Chunk 3).

```python
# tests/python/blender_test_helpers.py
"""Shared helper for tests that need to run code inside a real headless Blender
process (any tools/assetgen/blender module that `import bpy`s).

Pattern: write a small driver script to a temp file that imports the module
under test, calls one of its functions, and writes `{"result": ...}` as the last
line of stdout. `run_in_blender()` invokes `blender --background --python
<driver>` and parses that last line as JSON. This mirrors the *shape* of the MCP
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
import sys
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
    try:
        proc = subprocess.run(
            ["blender", "--background", "--python", str(driver_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
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
    return json.loads(result_lines[-1][len("RESULT:"):])
```

- [ ] **Step 6: Commit**

```bash
git add tools/assetgen/blender/archetype_spec.py tests/python/blender_test_helpers.py \
        tests/python/test_archetype_spec.py
git commit -m "Add ArchetypeSpec data contract and headless-Blender test helper"
```

---

### Task 5: `blender/loader.py`

**Files:**
- Create: `tools/assetgen/blender/loader.py`
- Test: `tests/python/test_blender_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_blender_loader.py
from tests.python.blender_test_helpers import requires_blender, run_in_blender


@requires_blender
def test_load_base_asserts_expected_structure():
    driver = '''
import sys
sys.path.insert(0, ".")
from tools.assetgen.blender import loader

info = loader.load_base()
print("RESULT:" + __import__("json").dumps(info))
'''
    result = run_in_blender(driver)
    assert result["mesh_object"] == "body"
    assert result["armature_object"] == "Armature"
    assert "Hips" in result["bone_names"]
    assert "Spine" in result["bone_names"]


@requires_blender
def test_load_base_raises_on_missing_bone(tmp_path, monkeypatch):
    # Uses a deliberately corrupted copy of base_humanoid.blend (Armature
    # renamed) to prove load_base() fails loud rather than silently continuing.
    driver = '''
import sys
sys.path.insert(0, ".")
import bpy
from tools.assetgen.blender import loader

loader.load_base()
bpy.data.armatures["Armature"].bones[0].name = "NotHips"
try:
    loader.assert_structure()
    print("RESULT:" + __import__("json").dumps({"raised": False}))
except loader.BaseAssetStructureError as exc:
    print("RESULT:" + __import__("json").dumps({"raised": True, "message": str(exc)}))
'''
    result = run_in_blender(driver)
    assert result["raised"] is True
    assert "Hips" in result["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_blender_loader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.assetgen.blender.loader'`
(or SKIPPED if Blender isn't installed in this environment — in that case, still
write and commit the implementation; verification happens wherever Blender is
available, per this chunk's shared skip policy above.)

- [ ] **Step 3: Write the implementation**

```python
# tools/assetgen/blender/loader.py
"""Loads base_humanoid.blend and asserts it has the structure every downstream
unit (proportions/clothing/materials/animate) assumes. This is the guard
against base_humanoid.blend drifting (re-authored, renamed) in a way that
silently breaks everything built on top of it — see spec's "Malformed/drifted
base asset" error-handling note.
"""
from __future__ import annotations

from pathlib import Path

import bpy

from .archetype_spec import KNOWN_BONES

BASE_BLEND_PATH = Path(__file__).resolve().parent / "base_humanoid.blend"

EXPECTED_MESH_OBJECT = "body"
EXPECTED_ARMATURE_OBJECT = "Armature"


class BaseAssetStructureError(RuntimeError):
    pass


def load_base(path: Path = BASE_BLEND_PATH) -> dict:
    """Load base_humanoid.blend into the current Blender session, replacing
    whatever scene is currently open, then assert its structure.

    Returns assert_structure()'s summary dict (mesh_object, armature_object,
    bone_names) so callers (tests, build_character.py) get the structure
    summary directly from load_base() without a second call.
    """
    bpy.ops.wm.open_mainfile(filepath=str(path))
    return assert_structure()


def assert_structure() -> dict:
    """Assert the loaded scene has the expected mesh/armature/bone names.

    Returns a summary dict (mesh_object, armature_object, bone_names) on
    success. Raises BaseAssetStructureError naming exactly what's wrong on
    failure — no silent fallback, per the spec's error-handling section.
    """
    if EXPECTED_MESH_OBJECT not in bpy.data.objects:
        raise BaseAssetStructureError(
            f"expected mesh object '{EXPECTED_MESH_OBJECT}' not found; "
            f"found objects: {sorted(o.name for o in bpy.data.objects)}"
        )
    if EXPECTED_ARMATURE_OBJECT not in bpy.data.objects:
        raise BaseAssetStructureError(
            f"expected armature object '{EXPECTED_ARMATURE_OBJECT}' not found; "
            f"found objects: {sorted(o.name for o in bpy.data.objects)}"
        )
    armature_obj = bpy.data.objects[EXPECTED_ARMATURE_OBJECT]
    actual_bones = {bone.name for bone in armature_obj.data.bones}
    missing = KNOWN_BONES - actual_bones
    if missing:
        raise BaseAssetStructureError(
            f"armature missing expected bone(s): {sorted(missing)}; "
            f"found: {sorted(actual_bones)}"
        )
    return {
        "mesh_object": EXPECTED_MESH_OBJECT,
        "armature_object": EXPECTED_ARMATURE_OBJECT,
        "bone_names": sorted(actual_bones),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_blender_loader.py -v`
Expected: PASS (2 tests), or SKIPPED if no Blender available locally.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/blender/loader.py tests/python/test_blender_loader.py
git commit -m "Add blender/loader.py: base asset load + structure assertions"
```

---

### Task 6: `blender/proportions.py`

**Files:**
- Create: `tools/assetgen/blender/proportions.py`
- Test: `tests/python/test_blender_proportions.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_blender_proportions.py
from tests.python.blender_test_helpers import requires_blender, run_in_blender


@requires_blender
def test_apply_proportions_scales_named_bones():
    driver = '''
import sys, json
sys.path.insert(0, ".")
from tools.assetgen.blender import loader, proportions
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager",
    bone_scales={"UpLeg.L": 0.9, "UpLeg.R": 0.9},
    clothing=[],
    palette={},
    clips=["idle", "walk", "run", "wave", "stir"],
)
info = proportions.apply(spec)
print("RESULT:" + json.dumps(info))
'''
    result = run_in_blender(driver)
    assert result["scaled_bones"] == {"UpLeg.L": 0.9, "UpLeg.R": 0.9}


@requires_blender
def test_apply_proportions_is_a_noop_for_unlisted_bones():
    driver = '''
import sys, json
sys.path.insert(0, ".")
import bpy
from tools.assetgen.blender import loader, proportions
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
armature_obj = bpy.data.objects["Armature"]
before = armature_obj.pose.bones["Spine"].scale.to_tuple()

spec = ArchetypeSpec(
    name="villager", bone_scales={"UpLeg.L": 0.9}, clothing=[], palette={},
    clips=["idle", "walk", "run", "wave", "stir"],
)
proportions.apply(spec)
after = armature_obj.pose.bones["Spine"].scale.to_tuple()
print("RESULT:" + json.dumps({"before": before, "after": after}))
'''
    result = run_in_blender(driver)
    assert result["before"] == result["after"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_blender_proportions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named
'tools.assetgen.blender.proportions'` (or SKIPPED without Blender)

- [ ] **Step 3: Write the implementation**

```python
# tools/assetgen/blender/proportions.py
"""Applies an ArchetypeSpec's bone_scales to the currently-loaded base armature.

No clothing, no materials, no animation — see architecture table's
responsibility split. Scaling is applied as pose-bone scale (not edit-mode bone
length changes) so it composes cleanly with the auto-weighted mesh deformation
already baked into base_humanoid.blend; it does not touch bones not listed in
bone_scales (they keep scale (1, 1, 1)).

Scope note: the spec's unit table describes this stage's input as "bone scale
factors / shape-key values" — shape-key-driven proportion variation (e.g.
smooth silhouette blends rather than rigid per-bone scaling) is intentionally
deferred; ArchetypeSpec only carries bone_scales for now (see
archetype_spec.py, Task 4). If bone scaling alone doesn't produce visually
acceptable per-archetype variation during Wren/villager migration (Chunk 4),
add shape-key support to ArchetypeSpec and this module then, rather than
building it speculatively now.
"""
from __future__ import annotations

import bpy

from .archetype_spec import ArchetypeSpec


def apply(spec: ArchetypeSpec) -> dict:
    """Scale each named bone in spec.bone_scales; leave all others untouched.

    Returns {"scaled_bones": {bone_name: factor, ...}} for test/log inspection.
    """
    armature_obj = bpy.data.objects["Armature"]
    bpy.context.view_layer.objects.active = armature_obj
    bpy.ops.object.mode_set(mode="POSE")
    for bone_name, factor in spec.bone_scales.items():
        pose_bone = armature_obj.pose.bones[bone_name]
        pose_bone.scale = (factor, factor, factor)
    bpy.ops.object.mode_set(mode="OBJECT")
    return {"scaled_bones": dict(spec.bone_scales)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_blender_proportions.py -v`
Expected: PASS (2 tests), or SKIPPED if no Blender available locally.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/blender/proportions.py tests/python/test_blender_proportions.py
git commit -m "Add blender/proportions.py: per-archetype bone scaling"
```

---

### Task 7: `blender/clothing.py`

**Files:**
- Create: `tools/assetgen/blender/clothing.py`
- Create: `tools/assetgen/blender/clothing_parts/__init__.py`
- Create: `tools/assetgen/blender/clothing_parts/tunic.py`
- Create: `tools/assetgen/blender/clothing_parts/boots.py`
- Test: `tests/python/test_blender_clothing.py`

**Design note carried from the spec:** "Each clothing piece is its own small
authored mesh (same bevel+subsurf treatment), not part of the base body mesh."
`clothing_parts/` holds one small script-module per piece (mirrors the base
mesh's per-part construction style from Task 3), each exposing a single
`build() -> bpy.types.Object` function that returns an unparented mesh object
positioned in the base armature's rest pose space. `clothing.py` itself is the
generic add-and-bind orchestrator; it does not know how to build any specific
piece — that keeps clothing.py from growing without bound as more pieces are
added later (new pieces are new files under clothing_parts/, not new branches
inside clothing.py).

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_blender_clothing.py
from tests.python.blender_test_helpers import requires_blender, run_in_blender


@requires_blender
def test_apply_clothing_adds_and_parents_pieces():
    driver = '''
import sys, json
sys.path.insert(0, ".")
import bpy
from tools.assetgen.blender import loader, clothing
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager", bone_scales={}, clothing=["tunic", "boots"],
    palette={"tunic": ("wood", 1), "boots": ("bark", 0)},
    clips=["idle", "walk", "run", "wave", "stir"],
)
info = clothing.apply(spec)
armature = bpy.data.objects["Armature"]
parented_ok = all(
    obj.parent == armature and obj.parent_type == "ARMATURE"
    for obj in bpy.data.objects
    if obj.name in info["added_objects"]
)
print("RESULT:" + json.dumps({**info, "parented_ok": parented_ok}))
'''
    result = run_in_blender(driver)
    assert set(result["added_objects"]) == {"tunic", "boots"}
    assert result["parented_ok"] is True


@requires_blender
def test_apply_clothing_raises_on_unknown_piece():
    driver = '''
import sys, json
sys.path.insert(0, ".")
from tools.assetgen.blender import loader, clothing
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager", bone_scales={}, clothing=["not_a_real_piece"],
    palette={"not_a_real_piece": ("wood", 1)},
    clips=["idle", "walk", "run", "wave", "stir"],
)
try:
    clothing.apply(spec)
    print("RESULT:" + json.dumps({"raised": False}))
except clothing.UnknownClothingPieceError as exc:
    print("RESULT:" + json.dumps({"raised": True, "message": str(exc)}))
'''
    result = run_in_blender(driver)
    assert result["raised"] is True
    assert "not_a_real_piece" in result["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_blender_clothing.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named
'tools.assetgen.blender.clothing'` (or SKIPPED without Blender)

- [ ] **Step 3: Write the clothing part scripts**

```python
# tools/assetgen/blender/clothing_parts/__init__.py
"""One module per clothing/hair piece. Each exposes build() -> bpy.types.Object,
registered in clothing.py's PART_BUILDERS map below (Step 4)."""
```

```python
# tools/assetgen/blender/clothing_parts/tunic.py
"""Builds the 'tunic' clothing piece: a simple beveled+subsurfed torso wrap,
sized to sit just outside the base body mesh's torso silhouette so it reads as
a garment rather than a re-skinned body part."""
from __future__ import annotations

import bpy
import bmesh

from ..body_dims import DIMS

# Small outward margin so the tunic reads as a garment layered over the body
# mesh, not a re-skinned duplicate of the torso.
_MARGIN = 0.02


def build() -> bpy.types.Object:
    mesh = bpy.data.meshes.new("tunic_mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(
        bm,
        vec=(
            DIMS["torso_width"] / 2 + _MARGIN,
            (DIMS["torso_width"] * 0.7) / 2 + _MARGIN,
            DIMS["torso_height"] / 2 + _MARGIN,
        ),
        verts=bm.verts,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("tunic", mesh)
    bpy.context.collection.objects.link(obj)
    # torso midpoint height: legs (upper+lower) + half the torso height, all
    # from body_dims.DIMS — matches wherever author_base_humanoid.py placed
    # the torso, rather than a separately hand-tuned number.
    obj.location = (
        0.0,
        0.0,
        DIMS["upper_leg_length"] + DIMS["lower_leg_length"] + DIMS["torso_height"] / 2,
    )

    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = DIMS["bevel_width"]
    bevel.segments = DIMS["bevel_segments"]
    subsurf = obj.modifiers.new("Subsurf", "SUBSURF")
    subsurf.levels = DIMS["subsurf_levels"]
    return obj
```

```python
# tools/assetgen/blender/clothing_parts/boots.py
"""Builds the 'boots' clothing piece: a pair of simple beveled+subsurfed foot
coverings, one per side (Mirror modifier, matching the ".L"/".R" convention
fixed in Chunk 1 Task 3 step 6), joined into a single 'boots' object."""
from __future__ import annotations

import bpy
import bmesh

from ..body_dims import DIMS


def build() -> bpy.types.Object:
    mesh = bpy.data.meshes.new("boots_mesh")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(
        bm,
        vec=(
            DIMS["foot_length"] / 2,
            DIMS["hip_width"] / 2,
            DIMS["foot_length"] / 3,
        ),
        verts=bm.verts,
    )
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("boots", mesh)
    bpy.context.collection.objects.link(obj)
    # Offset to one side (hip_width/2) so the Mirror modifier produces the
    # other boot at -hip_width/2; height is half the foot's own thickness,
    # i.e. resting on the ground plane.
    obj.location = (DIMS["hip_width"] / 2, 0.0, DIMS["foot_length"] / 6)

    mirror = obj.modifiers.new("Mirror", "MIRROR")
    mirror.use_axis = (True, False, False)
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = DIMS["bevel_width"]
    bevel.segments = DIMS["bevel_segments"]
    subsurf = obj.modifiers.new("Subsurf", "SUBSURF")
    subsurf.levels = DIMS["subsurf_levels"]
    return obj
```

- [ ] **Step 4: Write `clothing.py`**

```python
# tools/assetgen/blender/clothing.py
"""Adds and binds clothing/hair geometry to the loaded base armature, per an
ArchetypeSpec's `clothing` list. Delegates the actual mesh-building for each
named piece to tools/assetgen/blender/clothing_parts/<piece>.py — this module
only knows how to look a piece up, build it, apply the same bevel+subsurf
authoring style check, and bind it to the armature. Adding a new piece means
adding a new clothing_parts/ file and one PART_BUILDERS entry, not editing the
add/bind logic here.
"""
from __future__ import annotations

import bpy

from .archetype_spec import ArchetypeSpec
from .clothing_parts import boots, tunic

PART_BUILDERS = {
    "tunic": tunic.build,
    "boots": boots.build,
}


class UnknownClothingPieceError(RuntimeError):
    pass


def apply(spec: ArchetypeSpec) -> dict:
    """Build and bind every clothing piece named in spec.clothing.

    Returns {"added_objects": [name, ...]}. Raises UnknownClothingPieceError
    naming the piece if spec.clothing references something not in
    PART_BUILDERS (ArchetypeSpec itself only validates palette entries exist,
    not that the piece is buildable — that's this module's job).
    """
    armature_obj = bpy.data.objects["Armature"]
    added = []
    for piece in spec.clothing:
        if piece not in PART_BUILDERS:
            raise UnknownClothingPieceError(
                f"no clothing_parts builder registered for {piece!r}; "
                f"known pieces: {sorted(PART_BUILDERS)}"
            )
        obj = PART_BUILDERS[piece]()
        # Automatic weights so clothing deforms with the same pose as the
        # body mesh it's layered over (same mechanism as the base mesh's own
        # binding in author_base_humanoid.py Step 7). parent_set(type=
        # 'ARMATURE_AUTO') sets both obj.parent and obj.parent_type itself —
        # do not pre-assign them, the operator needs the mesh selected (not
        # yet parented) and the armature selected+active to compute weights
        # against the correct source pose.
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        added.append(obj.name)
    return {"added_objects": added}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_blender_clothing.py -v`
Expected: PASS (2 tests), or SKIPPED if no Blender available locally.

- [ ] **Step 6: Commit**

```bash
git add tools/assetgen/blender/clothing.py tools/assetgen/blender/clothing_parts/ \
        tests/python/test_blender_clothing.py
git commit -m "Add blender/clothing.py: per-archetype clothing add+bind"
```

---

### Task 8: `blender/materials.py`

**Files:**
- Create: `tools/assetgen/blender/materials.py`
- Test: `tests/python/test_blender_materials.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/python/test_blender_materials.py
from tests.python.blender_test_helpers import requires_blender, run_in_blender

# Shared setup snippet: materials.py samples assets/generated/palette_main.png,
# which build.py normally generates before invoking the Blender build (see
# Chunk 3's build_character.py orchestration). These tests write it themselves
# so this chunk's tests don't depend on running build.py first.
_WRITE_PALETTE_PNG = '''
from pathlib import Path
from tools.assetgen import palette
png_path = Path("assets/generated/palette_main.png")
png_path.parent.mkdir(parents=True, exist_ok=True)
png_path.write_bytes(palette.build_palette_png())
'''


@requires_blender
def test_apply_materials_assigns_palette_cells():
    driver = _WRITE_PALETTE_PNG + '''
import sys, json
sys.path.insert(0, ".")
import bpy
from tools.assetgen.blender import loader, clothing, materials
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager", bone_scales={}, clothing=["tunic"],
    palette={"tunic": ("wood", 1)},
    clips=["idle", "walk", "run", "wave", "stir"],
)
clothing.apply(spec)
info = materials.apply(spec)
tunic_obj = bpy.data.objects["tunic"]
uv_layer = tunic_obj.data.uv_layers.active
all_same_point = len({tuple(round(c, 6) for c in loop.uv) for loop in uv_layer.data}) == 1
has_material = len(tunic_obj.data.materials) == 1 and tunic_obj.data.materials[0] is not None
print("RESULT:" + json.dumps({**info, "all_same_point": all_same_point, "has_material": has_material}))
'''
    result = run_in_blender(driver)
    assert result["assigned"] == {"tunic": ["wood", 1]}
    assert result["all_same_point"] is True
    assert result["has_material"] is True


@requires_blender
def test_apply_materials_raises_on_unknown_ramp():
    driver = _WRITE_PALETTE_PNG + '''
import sys, json
sys.path.insert(0, ".")
from tools.assetgen.blender import loader, clothing, materials
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager", bone_scales={}, clothing=["tunic"],
    palette={"tunic": ("not_a_real_ramp", 0)},
    clips=["idle", "walk", "run", "wave", "stir"],
)
clothing.apply(spec)
try:
    materials.apply(spec)
    print("RESULT:" + json.dumps({"raised": False}))
except KeyError as exc:
    print("RESULT:" + json.dumps({"raised": True, "message": str(exc)}))
'''
    result = run_in_blender(driver)
    assert result["raised"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/python/test_blender_materials.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named
'tools.assetgen.blender.materials'` (or SKIPPED without Blender)

- [ ] **Step 3: Write the implementation**

```python
# tools/assetgen/blender/materials.py
"""Maps ArchetypeSpec.palette cell assignments onto each named object: every UV
coordinate is set to a single palette-cell center point (matching v1's
tools/assetgen/mesh.py MeshBuilder.add_face contract exactly — a flat-color
face samples one point, no gradient), and the object's material samples
assets/generated/palette_main.png (the same atlas PNG build.py already
generates via tools/assetgen/palette.build_palette_png() — see build.py's
existing palette-generation step). No new texture painting; this only wires up
the existing atlas.
"""
from __future__ import annotations

from pathlib import Path

import bpy

from .. import palette
from .archetype_spec import ArchetypeSpec

REPO_ROOT = Path(__file__).resolve().parents[3]
PALETTE_PNG_PATH = REPO_ROOT / "assets" / "generated" / "palette_main.png"
_SHARED_MATERIAL_NAME = "palette_atlas"


def _get_shared_material() -> bpy.types.Material:
    """One material shared by every object across every archetype build — they
    all sample the same atlas texture, differing only by UV coordinate, so a
    single material avoids creating one per (ramp, shade) combination."""
    material = bpy.data.materials.get(_SHARED_MATERIAL_NAME)
    if material is not None:
        return material
    if not PALETTE_PNG_PATH.exists():
        raise FileNotFoundError(
            f"{PALETTE_PNG_PATH} not found — build.py must generate "
            "assets/generated/palette_main.png (tools.assetgen.palette."
            "build_palette_png()) before running the Blender character build."
        )
    material = bpy.data.materials.new(_SHARED_MATERIAL_NAME)
    material.use_nodes = True
    bsdf = material.node_tree.nodes["Principled BSDF"]
    tex_node = material.node_tree.nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(str(PALETTE_PNG_PATH))
    tex_node.interpolation = "Closest"  # flat color cells: no bilinear bleed
    material.node_tree.links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
    return material


def _set_flat_uv(obj: bpy.types.Object, uv: tuple[float, float]) -> None:
    uv_layer = obj.data.uv_layers.active or obj.data.uv_layers.new()
    for loop in uv_layer.data:
        loop.uv = uv


def apply(spec: ArchetypeSpec) -> dict:
    """Assign each spec.palette[object_name] = (ramp, shade) cell to that
    object: every UV coordinate becomes the cell's single center point, and
    the object's material is set to the shared palette_atlas material.

    Returns {"assigned": {object_name: [ramp, shade], ...}}. Validates every
    (ramp, shade) pair up front (raising KeyError/ValueError from
    palette.cell_uv, unwrapped, on the first invalid one) before touching any
    Blender object state, so a bad archetype spec never leaves a half-applied
    scene.
    """
    uvs = {
        obj_name: palette.cell_uv(ramp, shade)
        for obj_name, (ramp, shade) in spec.palette.items()
    }
    material = _get_shared_material()
    assigned = {}
    for obj_name, (ramp, shade) in spec.palette.items():
        obj = bpy.data.objects[obj_name]
        _set_flat_uv(obj, uvs[obj_name])
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
        assigned[obj_name] = [ramp, shade]
    return {"assigned": assigned}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/python/test_blender_materials.py -v`
Expected: PASS (2 tests), or SKIPPED if no Blender available locally.

- [ ] **Step 5: Commit**

```bash
git add tools/assetgen/blender/materials.py tests/python/test_blender_materials.py
git commit -m "Add blender/materials.py: palette-cell UV/material assignment"
```
