"""One-off Blender script: merge a Meshy AI rigged character mesh GLB with
its Meshy AI animation-library GLB into a single body GLB with named clips
(idle/walk/run) Godot's rigged-NPC loader expects.

Generalized from merge_wren_meshy.py once a second and third rigged Meshy
export (Ansel Rowe, Torben Ask) turned out to ship the exact same stock
~20-clip animation library (idle/walk/run plus combat/swim/sleep/etc. clips
from Meshy's generic biped library) - see docs/character-inventory.md.
Glitch Witch has no combat, so only the clips relevant to overworld
locomotion are kept; the rest are dropped so they don't ship in the GLB or
show up as confusing options in the AnimationPlayer.

Run headless: blender --background --python merge_meshy_rigged_npc.py -- <char.glb> <anims.glb> <out.glb>
"""
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
char_path, anims_path, out_path = argv

# Clean scene.
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import the character (mesh + skeleton + skin).
char_actions_before = set(bpy.data.actions.keys())
bpy.ops.import_scene.gltf(filepath=char_path)
char_armature = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
# The character export bakes its own rest-pose action (e.g.
# "Armature|clip0|baselayer") - drop it once imported since idle/walk/run
# come from the dedicated animation-library file below.
for name, action in list(bpy.data.actions.items()):
    if name not in char_actions_before:
        bpy.data.actions.remove(action)
char_armature.animation_data_clear()

# Import the animation-only file into the same scene. The glTF importer only
# leaves ONE action wired up as the armature's active action even when the
# source file contains multiple clips (they all still land in bpy.data.actions
# with their original armature as the actions' fake_user/id_root) - so collect
# every imported action directly rather than trusting the active pointer.
actions_before = set(bpy.data.actions.keys())
bpy.ops.import_scene.gltf(filepath=anims_path)
imported_actions = {
    name: a for name, a in bpy.data.actions.items() if name not in actions_before
}

# Only keep the clips Glitch Witch's overworld locomotion actually uses -
# this is a no-combat cozy game, so the combat/mage/swim/sleep clips in
# Meshy's stock animation library are intentionally dropped.
clip_keep_rename = {
    "Idle_02": "idle",
    "Walking": "walk",
    "Running": "run",
}

if char_armature.animation_data is None:
    char_armature.animation_data_create()

kept_names: set[str] = set()
for source_name, new_name in clip_keep_rename.items():
    action = imported_actions.get(source_name)
    if action is None:
        print(f"WARNING: expected clip {source_name!r} not found in {anims_path}")
        continue
    action.name = new_name
    kept_names.add(new_name)
    # Push each source action onto an NLA track on the character armature so
    # glTF export picks up multiple named actions instead of overwriting.
    track = char_armature.animation_data.nla_tracks.new()
    track.name = new_name
    track.strips.new(new_name, int(action.frame_range[0]), action)

# Drop every unused imported action (and the anims-only file's own throwaway
# armature/objects) so the exported GLB only contains idle/walk/run.
for name, action in list(imported_actions.items()):
    if action.name not in kept_names:
        bpy.data.actions.remove(action)

keep = {char_armature} | set(char_armature.children_recursive)
for obj in list(bpy.context.scene.objects):
    if obj not in keep:
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format="GLB",
    export_animations=True,
    export_nla_strips=True,
    export_force_sampling=True,
)
print(f"Wrote merged rigged NPC GLB to {out_path}")
