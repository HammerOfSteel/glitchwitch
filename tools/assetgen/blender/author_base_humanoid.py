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
  later, per-archetype, in Chunk 2's Task 7) stays as SEPARATE mesh objects
  bound to the same armature — only the base body itself is a single joined
  mesh.
- Output path is always relative to this script's own location:
  Path(__file__).parent / "base_humanoid.blend" — i.e.
  tools/assetgen/blender/base_humanoid.blend — not a hand-typed absolute path.
"""
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(REPO_ROOT))

from body_dims import DIMS
from tools.assetgen import palette

OUTPUT_PATH = SCRIPT_DIR / "base_humanoid.blend"
TOTAL_HEIGHT = 1.0
HEAD_TORSO_OVERLAP = 0.07
TORSO_LIFT = 0.03
HEAD_DROP = 0.03
FOOT_HEIGHT = max(0.02, TOTAL_HEIGHT - (
    DIMS["head_height"]
    + DIMS["torso_height"]
    + DIMS["upper_leg_length"]
    + DIMS["lower_leg_length"]
    - HEAD_TORSO_OVERLAP
))
TORSO_DEPTH = DIMS["torso_width"] * 0.82
HEAD_WIDTH = DIMS["head_height"] * 0.90
HEAD_DEPTH = DIMS["head_height"] * 0.84
UPPER_ARM_RADIUS = 0.05
LOWER_ARM_RADIUS = 0.045
HAND_THICKNESS = DIMS["hand_length"] * 0.68
UPPER_LEG_RADIUS = DIMS["hip_width"] * 0.22
LOWER_LEG_RADIUS = UPPER_LEG_RADIUS * 0.88
FOOT_WIDTH = DIMS["foot_length"] * 0.7
FOOT_DEPTH = DIMS["foot_length"] * 1.15
NECK_HEIGHT = 0.03
SHOULDER_Z = FOOT_HEIGHT + DIMS["lower_leg_length"] + DIMS["upper_leg_length"] + DIMS["torso_height"] * 0.78 + TORSO_LIFT
HIPS_Z = FOOT_HEIGHT + DIMS["lower_leg_length"] + DIMS["upper_leg_length"]
HEAD_CENTER_Z = (
    HIPS_Z
    + DIMS["torso_height"]
    + (DIMS["head_height"] / 2.0)
    - HEAD_TORSO_OVERLAP
    - HEAD_DROP
)
SHOULDER_X = (DIMS["torso_width"] / 2.0) - 0.005
HIP_X = DIMS["hip_width"] * 0.42
ARM_SWING = math.radians(34)
LEG_STANCE = 0.024


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    for armature in list(bpy.data.armatures):
        if armature.users == 0:
            bpy.data.armatures.remove(armature)
    for material in list(bpy.data.materials):
        if material.users == 0:
            bpy.data.materials.remove(material)
    for image in list(bpy.data.images):
        if image.users == 0:
            bpy.data.images.remove(image)


def mesh_object_from_bmesh(name: str, bm: bmesh.types.BMesh) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def cuboid(
    name: str,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    vertical_cuts: int = 0,
) -> bpy.types.Object:
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    if vertical_cuts:
        vertical_edges = [
            edge for edge in bm.edges
            if abs(edge.verts[0].co.z - edge.verts[1].co.z) > 0.9
        ]
        bmesh.ops.subdivide_edgering(
            bm,
            edges=vertical_edges,
            cuts=vertical_cuts,
            profile_shape="LINEAR",
            profile_shape_factor=0.0,
        )
    bmesh.ops.scale(bm, verts=bm.verts, vec=Vector((size[0] / 2.0, size[1] / 2.0, size[2] / 2.0)))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(location))
    return mesh_object_from_bmesh(name, bm)


def capsule_segment(
    name: str,
    start: Vector,
    end: Vector,
    radius_start: float,
    radius_end: float,
    ring_cuts: int,
) -> bpy.types.Object:
    bm = bmesh.new()
    vector = end - start
    length = vector.length
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=12,
        radius1=radius_start,
        radius2=radius_end,
        depth=length,
    )
    side_edges = [
        edge for edge in bm.edges
        if len(edge.link_faces) == 2
        and all(abs(vert.co.z) < (length / 2.0) - 1e-6 for vert in edge.verts)
    ]
    if side_edges and ring_cuts:
        bmesh.ops.subdivide_edgering(
            bm,
            edges=side_edges,
            cuts=ring_cuts,
            profile_shape="LINEAR",
            profile_shape_factor=0.0,
        )
    rotation = Vector((0.0, 0.0, 1.0)).rotation_difference(vector.normalized())
    bmesh.ops.rotate(bm, verts=bm.verts, cent=Vector((0.0, 0.0, 0.0)), matrix=rotation.to_matrix())
    bmesh.ops.translate(bm, verts=bm.verts, vec=start.lerp(end, 0.5))
    return mesh_object_from_bmesh(name, bm)


def set_object_active(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def add_smoothing_stack(obj: bpy.types.Object, mirror: bool = False) -> None:
    set_object_active(obj)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if mirror:
        mirror_mod = obj.modifiers.new(name="Mirror", type="MIRROR")
        mirror_mod.use_axis = (True, False, False)
        mirror_mod.use_clip = True
        mirror_mod.use_bisect_axis[0] = False
        bpy.ops.object.modifier_apply(modifier=mirror_mod.name)
    bevel = obj.modifiers.new(name="Bevel", type="BEVEL")
    bevel.width = DIMS["bevel_width"]
    bevel.segments = DIMS["bevel_segments"]
    bevel.limit_method = "ANGLE"
    bpy.ops.object.modifier_apply(modifier=bevel.name)
    subsurf = obj.modifiers.new(name="Subsurf", type="SUBSURF")
    subsurf.levels = DIMS["subsurf_levels"]
    subsurf.render_levels = DIMS["subsurf_levels"]
    bpy.ops.object.modifier_apply(modifier=subsurf.name)
    for polygon in obj.data.polygons:
        polygon.use_smooth = True


def ensure_uv_layer(obj: bpy.types.Object) -> bpy.types.MeshUVLoopLayer:
    uv_layer = obj.data.uv_layers.get("UVMap")
    if uv_layer is None:
        uv_layer = obj.data.uv_layers.new(name="UVMap")
    return uv_layer


def map_faces_to_palette_cell(obj: bpy.types.Object, ramp: str, shade: int) -> None:
    uv_layer = ensure_uv_layer(obj)
    u, v = palette.cell_uv(ramp, shade)
    for loop in uv_layer.data:
        loop.uv = (u, 1.0 - v)


def build_body_parts() -> list[bpy.types.Object]:
    torso_center_z = HIPS_Z + (DIMS["torso_height"] / 2.0) + TORSO_LIFT
    torso = cuboid(
        "torso",
        (DIMS["torso_width"], TORSO_DEPTH, DIMS["torso_height"]),
        (0.0, 0.0, torso_center_z),
        vertical_cuts=1,
    )
    head = cuboid(
        "head",
        (HEAD_WIDTH, HEAD_DEPTH, DIMS["head_height"]),
        (0.0, 0.0, HEAD_CENTER_Z),
        vertical_cuts=1,
    )
    hand_z = SHOULDER_Z - (DIMS["upper_arm_length"] * math.cos(ARM_SWING)) - (DIMS["lower_arm_length"] * math.cos(ARM_SWING))
    hand_x = SHOULDER_X + (DIMS["upper_arm_length"] * math.sin(ARM_SWING)) + (DIMS["lower_arm_length"] * math.sin(ARM_SWING))
    upper_arm = capsule_segment(
        "upper_arm.R",
        Vector((SHOULDER_X, 0.0, SHOULDER_Z)),
        Vector((SHOULDER_X + DIMS["upper_arm_length"] * math.sin(ARM_SWING), 0.0, SHOULDER_Z - DIMS["upper_arm_length"] * math.cos(ARM_SWING))),
        UPPER_ARM_RADIUS,
        UPPER_ARM_RADIUS * 0.92,
        ring_cuts=2,
    )
    lower_arm = capsule_segment(
        "lower_arm.R",
        Vector((SHOULDER_X + DIMS["upper_arm_length"] * math.sin(ARM_SWING), 0.0, SHOULDER_Z - DIMS["upper_arm_length"] * math.cos(ARM_SWING))),
        Vector((hand_x, 0.0, hand_z)),
        LOWER_ARM_RADIUS,
        LOWER_ARM_RADIUS * 0.9,
        ring_cuts=2,
    )
    hand = cuboid(
        "hand.R",
        (DIMS["hand_length"] * 1.05, HAND_THICKNESS * 1.05, DIMS["hand_length"] * 0.56),
        (hand_x + DIMS["hand_length"] * 0.18, 0.0, hand_z - 0.01),
    )
    foot_center = Vector((HIP_X + 0.01, 0.0, FOOT_HEIGHT / 2.0))
    upper_leg = capsule_segment(
        "upper_leg.R",
        Vector((HIP_X, 0.0, HIPS_Z - 0.005)),
        Vector((HIP_X + LEG_STANCE, 0.0, FOOT_HEIGHT + DIMS["lower_leg_length"])),
        UPPER_LEG_RADIUS,
        UPPER_LEG_RADIUS * 0.92,
        ring_cuts=2,
    )
    lower_leg = capsule_segment(
        "lower_leg.R",
        Vector((HIP_X + LEG_STANCE, 0.0, FOOT_HEIGHT + DIMS["lower_leg_length"])),
        Vector((HIP_X + 0.01, 0.0, FOOT_HEIGHT + 0.01)),
        LOWER_LEG_RADIUS,
        LOWER_LEG_RADIUS * 0.95,
        ring_cuts=2,
    )
    foot = cuboid(
        "foot.R",
        (FOOT_WIDTH, FOOT_DEPTH, FOOT_HEIGHT),
        (foot_center.x + 0.012, FOOT_DEPTH * 0.32, foot_center.z),
    )
    add_smoothing_stack(torso, mirror=False)
    add_smoothing_stack(head, mirror=False)
    map_faces_to_palette_cell(torso, "cream", 2)
    map_faces_to_palette_cell(head, "cream", 3)
    for obj in [upper_arm, lower_arm, hand, upper_leg, lower_leg, foot]:
        add_smoothing_stack(obj, mirror=True)
        map_faces_to_palette_cell(obj, "cream", 2)
    return [torso, head, upper_arm, lower_arm, hand, upper_leg, lower_leg, foot]


def join_body_parts(parts: list[bpy.types.Object]) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = "body"
    body.data.name = "body_mesh"
    return body


def build_armature() -> bpy.types.Object:
    armature_data = bpy.data.armatures.new("base_humanoid_armature")
    armature_object = bpy.data.objects.new("Armature", armature_data)
    bpy.context.collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    armature_object.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    edit_bones = armature_data.edit_bones

    hips = edit_bones.new("Hips")
    hips.head = (0.0, 0.0, HIPS_Z - 0.04)
    hips.tail = (0.0, 0.0, HIPS_Z + 0.04)

    spine = edit_bones.new("Spine")
    spine.head = hips.tail
    spine.tail = (0.0, 0.0, HIPS_Z + DIMS["torso_height"] * 0.72 + TORSO_LIFT)
    spine.parent = hips

    neck = edit_bones.new("Neck")
    neck.head = spine.tail
    neck.tail = (0.0, 0.0, TOTAL_HEIGHT - DIMS["head_height"])
    neck.parent = spine

    head = edit_bones.new("Head")
    head.head = neck.tail
    head.tail = (0.0, 0.0, TOTAL_HEIGHT)
    head.parent = neck

    for side, sign in (("L", -1), ("R", 1)):
        shoulder = edit_bones.new(f"Shoulder.{side}")
        shoulder.head = (sign * (SHOULDER_X - 0.025), 0.0, SHOULDER_Z + 0.005)
        shoulder.tail = (sign * SHOULDER_X, 0.0, SHOULDER_Z)
        shoulder.parent = spine

        arm = edit_bones.new(f"Arm.{side}")
        arm.head = shoulder.tail
        arm.tail = (
            sign * (SHOULDER_X + DIMS["upper_arm_length"] * math.sin(ARM_SWING)),
            0.0,
            SHOULDER_Z - DIMS["upper_arm_length"] * math.cos(ARM_SWING),
        )
        arm.parent = shoulder

        forearm = edit_bones.new(f"ForeArm.{side}")
        forearm.head = arm.tail
        forearm.tail = (
            sign * (SHOULDER_X + (DIMS["upper_arm_length"] + DIMS["lower_arm_length"]) * math.sin(ARM_SWING)),
            0.0,
            SHOULDER_Z - (DIMS["upper_arm_length"] + DIMS["lower_arm_length"]) * math.cos(ARM_SWING),
        )
        forearm.parent = arm

        hand = edit_bones.new(f"Hand.{side}")
        hand.head = forearm.tail
        hand.tail = (
            sign * (SHOULDER_X + (DIMS["upper_arm_length"] + DIMS["lower_arm_length"] + DIMS["hand_length"] * 0.55) * math.sin(ARM_SWING)),
            0.0,
            forearm.tail.z - DIMS["hand_length"] * 0.45,
        )
        hand.parent = forearm

        upleg = edit_bones.new(f"UpLeg.{side}")
        upleg.head = (sign * HIP_X, 0.0, HIPS_Z)
        upleg.tail = (sign * (HIP_X + LEG_STANCE), 0.0, FOOT_HEIGHT + DIMS["lower_leg_length"])
        upleg.parent = hips

        leg = edit_bones.new(f"Leg.{side}")
        leg.head = upleg.tail
        leg.tail = (sign * (HIP_X + 0.01), 0.0, FOOT_HEIGHT + 0.01)
        leg.parent = upleg

        foot = edit_bones.new(f"Foot.{side}")
        foot.head = leg.tail
        foot.tail = (sign * (HIP_X + 0.02), FOOT_DEPTH * 0.45, 0.015)
        foot.parent = leg

        toe = edit_bones.new(f"ToeBase.{side}")
        toe.head = foot.tail
        toe.tail = (sign * (HIP_X + 0.02), FOOT_DEPTH * 0.85, 0.015)
        toe.parent = foot

    bpy.ops.object.mode_set(mode="OBJECT")
    return armature_object


def parent_with_auto_weights(body: bpy.types.Object, armature_object: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    armature_object.select_set(True)
    bpy.context.view_layer.objects.active = armature_object
    bpy.ops.object.parent_set(type="ARMATURE_AUTO")


def ensure_body_material(body: bpy.types.Object) -> None:
    material = bpy.data.materials.new(name="body_palette_preview")
    material.diffuse_color = (0.94, 0.89, 0.77, 1.0)
    material.roughness = 0.88
    material.specular_intensity = 0.15
    if not body.data.materials:
        body.data.materials.append(material)


def add_preview_camera_and_light() -> None:
    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    camera.location = (1.7, -1.95, 1.18)
    camera.rotation_euler = (math.radians(77), 0.0, math.radians(42))
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    sun_data = bpy.data.lights.new(name="Sun", type="SUN")
    sun_data.energy = 1.8
    sun = bpy.data.objects.new("Sun", sun_data)
    sun.rotation_euler = (math.radians(40), math.radians(-10), math.radians(25))
    bpy.context.collection.objects.link(sun)

    fill_data = bpy.data.lights.new(name="Fill", type="AREA")
    fill_data.energy = 900
    fill_data.shape = "RECTANGLE"
    fill_data.size = 2.5
    fill = bpy.data.objects.new("Fill", fill_data)
    fill.location = (-1.8, -2.2, 1.2)
    fill.rotation_euler = (math.radians(72), 0.0, math.radians(-36))
    bpy.context.collection.objects.link(fill)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.world.color = (0.92, 0.95, 1.0)


def save_file() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_PATH))


def main() -> None:
    clear_scene()
    parts = build_body_parts()
    body = join_body_parts(parts)
    ensure_body_material(body)
    armature_object = build_armature()
    parent_with_auto_weights(body, armature_object)
    add_preview_camera_and_light()
    save_file()


main()
result = {"status": "authored", "objects": [o.name for o in bpy.data.objects]}
