from tests.python.blender_test_helpers import requires_blender, run_in_blender


@requires_blender
def test_bake_clips_produces_expected_action_names():
    driver = '''
import sys, json
sys.path.insert(0, ".")
import bpy
from tools.assetgen.blender import loader, animate
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager", bone_scales={}, clothing=[], palette={},
    clips=["idle", "walk", "run", "wave", "stir"],
)
info = animate.bake(spec)
action_names = sorted(a.name for a in bpy.data.actions)
print("RESULT:" + json.dumps({**info, "action_names": action_names}))
'''
    result = run_in_blender(driver)
    assert result["baked"] == [
        "idle-loop", "walk-loop", "run-loop", "wave", "stir",
    ]
    assert result["action_names"] == [
        "idle-loop", "run-loop", "stir", "walk-loop", "wave",
    ]


@requires_blender
def test_bake_clips_raises_on_unbuildable_clip():
    driver = '''
import sys, json
sys.path.insert(0, ".")
from tools.assetgen.blender import loader, animate
from tools.assetgen.blender.archetype_spec import ArchetypeSpec

loader.load_base()
spec = ArchetypeSpec(
    name="villager", bone_scales={}, clothing=[], palette={},
    clips=["idle", "walk", "run", "wave", "stir", "not_a_real_clip"],
)
try:
    animate.bake(spec)
    print("RESULT:" + json.dumps({"raised": False}))
except animate.UnknownClipError as exc:
    print("RESULT:" + json.dumps({"raised": True, "message": str(exc)}))
'''
    result = run_in_blender(driver)
    assert result["raised"] is True
    assert "not_a_real_clip" in result["message"]
