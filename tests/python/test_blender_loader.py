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
    # Corrupt the loaded armature in-memory to prove assert_structure() fails
    # loud rather than silently continuing.
    driver = '''
import sys
sys.path.insert(0, ".")
import bpy
from tools.assetgen.blender import loader

loader.load_base()
bpy.data.objects["Armature"].data.bones["Hips"].name = "NotHips"
try:
    loader.assert_structure()
    print("RESULT:" + __import__("json").dumps({"raised": False}))
except loader.BaseAssetStructureError as exc:
    print("RESULT:" + __import__("json").dumps({"raised": True, "message": str(exc)}))
'''
    result = run_in_blender(driver)
    assert result["raised"] is True
    assert "Hips" in result["message"]


@requires_blender
def test_assert_structure_raises_on_wrong_armature_object_type():
    driver = '''
import sys
sys.path.insert(0, ".")
import bpy
from tools.assetgen.blender import loader

loader.load_base()
real_armature = bpy.data.objects["Armature"]
real_armature.name = "Armature_real"
wrong_armature = bpy.data.objects["body"].copy()
wrong_armature.data = bpy.data.objects["body"].data
wrong_armature.name = "Armature"
bpy.context.collection.objects.link(wrong_armature)
try:
    loader.assert_structure()
    print("RESULT:" + __import__("json").dumps({"raised": False}))
except Exception as exc:
    print("RESULT:" + __import__("json").dumps({
        "raised": True,
        "type": type(exc).__name__,
        "message": str(exc),
    }))
'''
    result = run_in_blender(driver)
    assert result["raised"] is True
    assert result["type"] == "BaseAssetStructureError"
    assert "type 'ARMATURE'" in result["message"]
