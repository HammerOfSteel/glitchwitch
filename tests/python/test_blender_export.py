from tests.python.blender_test_helpers import (
    requires_blender,
    run_in_blender,
    scratch_output_path,
)


@requires_blender
def test_export_writes_glb_and_reimports_cleanly():
    out_path = scratch_output_path(".glb")
    driver = f'''
import sys, json
sys.path.insert(0, ".")
from tools.assetgen.blender import loader, animate, export
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager", bone_scales={{}}, clothing=[], palette={{}},
    clips=["idle", "walk", "run", "wave", "stir"],
)
animate.bake(spec)
info = export.export(spec, r"{out_path}")
print("RESULT:" + json.dumps(info))
'''
    try:
        result = run_in_blender(driver)
        assert result["path"] == str(out_path)
        assert out_path.exists()
        assert out_path.stat().st_size > 0
        assert result["reimport_ok"] is True
    finally:
        out_path.unlink(missing_ok=True)
