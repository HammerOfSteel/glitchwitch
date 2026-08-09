"""One-off Blender script: merge the Seren character mesh GLB with the
Seren animations-only GLB into a single placeholder GLB with named clips
Godot's WrenAvatar-style loader expects (idle/walk/run).

Run headless: blender --background --python merge_seren.py -- <char.glb> <anims.glb> <out.glb>
"""
import sys
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
char_path, anims_path, out_path = argv

# Clean scene.
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import the character (mesh + skeleton + skin).
bpy.ops.import_scene.gltf(filepath=char_path)
char_armature = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")

# Import the animation-only file into the same scene. The glTF importer only
# leaves ONE action wired up as the armature's active action even when the
# source file contains multiple clips (they all still land in bpy.data.actions
# with their original armature as the actions' fake_user/id_root) - so collect
# every imported action directly rather than trusting the active pointer.
actions_before = set(bpy.data.actions.keys())
bpy.ops.import_scene.gltf(filepath=anims_path)
anim_armatures = [
    o for o in bpy.context.scene.objects
    if o.type == "ARMATURE" and o is not char_armature
]
imported_actions = [
    a for name, a in bpy.data.actions.items() if name not in actions_before
]

clip_rename = {
    "Walking": "walk",
    "Running": "run",
}

if char_armature.animation_data is None:
    char_armature.animation_data_create()

for action in imported_actions:
    new_name = clip_rename.get(action.name, action.name)
    action.name = new_name
    # Push each source action onto an NLA track on the character armature so
    # glTF export picks up multiple named actions instead of overwriting.
    track = char_armature.animation_data.nla_tracks.new()
    track.name = new_name
    track.strips.new(new_name, int(action.frame_range[0]), action)

# The character file's own baked-in clip is the rest/base pose - reuse it
# directly as "idle" (the source has no dedicated idle/wave/stir clips; this
# is placeholder-quality only).
base_action = next(
    (a for a in bpy.data.actions if a.name.startswith("Armature|clip0")), None
)
if base_action is not None:
    base_action.name = "idle"
    idle_track = char_armature.animation_data.nla_tracks.new()
    idle_track.name = "idle"
    idle_track.strips.new("idle", int(base_action.frame_range[0]), base_action)

# Remove the now-empty animation-only armature + its proxy mesh objects
# (the anims-only export carries its own throwaway skinned mesh + stray
# primitives) before export - keep only the real character's objects.
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
print(f"Wrote merged placeholder GLB to {out_path}")
