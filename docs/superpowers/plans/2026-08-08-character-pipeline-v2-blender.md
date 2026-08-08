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
- Create: `tools/assetgen/blender/author_base_humanoid.py` (the script; re-runnable,
  not auto-run by `make assets`)
- Create: `tools/assetgen/blender/base_humanoid.blend` (committed binary output of
  running the script once)
- Test: `tests/python/test_base_humanoid_asset.py`

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
  later, per-archetype, in Task 6) stays as SEPARATE mesh objects bound to the
  same armature — only the base body itself is a single joined mesh.
- Output path is always relative to this script's own location:
  Path(__file__).parent / "base_humanoid.blend" — i.e.
  tools/assetgen/blender/base_humanoid.blend — not a hand-typed absolute path.
"""
import bpy
import bmesh
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent / "base_humanoid.blend"

# Concrete first-pass dimensions (units = meters, total standing height 1.0m to
# match the existing v1 character scale in tools/assetgen/character.py). These
# are STARTING values, not open choices — adjust only if Step 2's render checks
# fail the acceptance bar, and note any change here in the docstring above.
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
git add tools/assetgen/blender/author_base_humanoid.py \
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
