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
