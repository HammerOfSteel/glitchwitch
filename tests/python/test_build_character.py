import json
import subprocess
import sys

from tests.python.blender_test_helpers import (
    REPO_ROOT,
    requires_blender,
    run_in_blender,
    scratch_output_path,
)
from tools.assetgen.blender import toolchain


@requires_blender
def test_build_character_runs_all_units_in_order():
    out_path = scratch_output_path('.glb')
    driver = f'''
import sys, json
sys.path.insert(0, ".")
from tools.assetgen.blender import build_character
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

spec = ArchetypeSpec(
    name="villager", bone_scales={{"UpLeg.L": 0.95, "UpLeg.R": 0.95}},
    clothing=[], palette={{}},
    clips=["idle", "walk", "run", "wave", "stir"],
)
info = build_character.build(spec, r"{out_path}")
print("RESULT:" + json.dumps(info))
'''
    try:
        result = run_in_blender(driver)
        assert result["ok"] is True
        assert result["path"] == str(out_path)
        assert out_path.exists()
    finally:
        out_path.unlink(missing_ok=True)


@requires_blender
def test_build_character_cli_writes_glb_and_exits_zero():
    out_path = scratch_output_path('.glb')
    spec_json = json.dumps({
        "name": "villager", "bone_scales": {}, "clothing": [], "palette": {},
        "clips": ["idle", "walk", "run", "wave", "stir"],
    })
    script_path = REPO_ROOT / "tools/assetgen/blender/build_character.py"
    blender_executable, blender_env = toolchain.blender_subprocess_config()
    try:
        proc = subprocess.run(
            [blender_executable, "--background", "--python", str(script_path), "--",
             "--spec-json", spec_json, "--output", str(out_path)],
            capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT), env=blender_env,
        )
        assert proc.returncode == 0, proc.stderr
        assert out_path.exists()
        result_lines = [
            line for line in proc.stdout.splitlines() if line.startswith("RESULT:")
        ]
        info = json.loads(result_lines[-1][len("RESULT:"):])
        assert info["ok"] is True
    finally:
        out_path.unlink(missing_ok=True)


@requires_blender
def test_build_character_cli_exits_nonzero_with_structured_stderr_on_bad_spec():
    script_path = REPO_ROOT / "tools/assetgen/blender/build_character.py"
    # Missing mandatory clips -> ArchetypeSpec construction itself raises.
    spec_json = json.dumps({
        "name": "villager", "bone_scales": {}, "clothing": [], "palette": {},
        "clips": ["idle"],
    })
    blender_executable, blender_env = toolchain.blender_subprocess_config()
    proc = subprocess.run(
        [blender_executable, "--background", "--python", str(script_path), "--",
         "--spec-json", spec_json, "--output", "/dev/null/unused.glb"],
        capture_output=True, text=True, timeout=120, cwd=str(REPO_ROOT), env=blender_env,
    )
    assert proc.returncode != 0
    error_lines = [
        line for line in proc.stderr.splitlines() if line.startswith("ERROR:")
    ]
    assert error_lines, proc.stderr
    payload = json.loads(error_lines[-1][len("ERROR:"):])
    assert "stage" in payload and "message" in payload


@requires_blender
def test_cli_main_exits_nonzero_and_reports_error_on_reported_validation_failure():
    # Exercises _cli_main's "reported (non-exception) ok=False" branch. Runs
    # inside headless Blender (via run_in_blender), like every other test in
    # this chunk — build_character.py transitively imports bpy (through
    # animate.py/clothing.py/etc.), so it can't be imported in the host pytest
    # process at all, monkeypatched or not.
    driver = '''
import sys, json
sys.path.insert(0, ".")
from tools.assetgen.blender import build_character

def fake_build(spec, output_path):
    return {"ok": False, "path": output_path, "errors": ["tri count too high"]}

build_character.build = fake_build
spec_json = json.dumps({
    "name": "villager", "bone_scales": {}, "clothing": [], "palette": {},
    "clips": ["idle", "walk", "run", "wave", "stir"],
})
exit_code = build_character._cli_main(["--spec-json", spec_json, "--output", "unused.glb"])
print("RESULT:" + json.dumps({"exit_code": exit_code}))
'''
    result = run_in_blender(driver)
    assert result["exit_code"] == 1
