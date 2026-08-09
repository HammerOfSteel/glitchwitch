from tests.python.blender_test_helpers import requires_blender, run_in_blender

# Shared setup snippet: materials.py samples assets/generated/palette_main.png,
# which build.py normally generates before invoking the Blender build (see
# Chunk 3's build_character.py orchestration). These tests write it themselves
# so this chunk's tests don't depend on running build.py first.
_WRITE_PALETTE_PNG = '''
import sys
sys.path.insert(0, ".")
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
