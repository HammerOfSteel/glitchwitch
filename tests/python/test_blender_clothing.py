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
