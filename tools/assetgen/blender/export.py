"""Exports the fully assembled scene (base body + clothing + materials +
baked Actions) as a glTF binary (.glb), using a fixed, pinned option set, then
re-imports it into a throwaway scene to confirm it parses cleanly before
returning success — see spec's export.py responsibility row.
"""
from __future__ import annotations

from pathlib import Path

import bpy

from .archetype_spec import ArchetypeSpec

# Pinned glTF export options (documented here, not scattered across call
# sites): GLB binary, Y-up (Blender's exporter handles the Z-up -> Y-up
# conversion automatically to match glTF/Godot convention), export every
# baked Action as its own separate animation clip (not merged into one NLA
# track — required so Godot's AnimationPlayer gets 5 distinct clips), and
# apply modifiers (Bevel/Subsurf/Mirror) so the exported mesh is the smoothed
# result, not the low-poly control cage.
EXPORT_KWARGS = dict(
    export_format="GLB",
    export_yup=True,
    export_animation_mode="ACTIONS",
    export_apply=True,
    export_animations=True,
)


def export(spec: ArchetypeSpec, output_path: str) -> dict:
    """Export the current scene to output_path (a .glb), then re-import it
    into a throwaway scene to confirm the exported file parses cleanly.

    Returns {"path": output_path, "reimport_ok": bool}. Does not raise on a
    re-import parse failure — that's reported as reimport_ok=False so the
    caller (build_character.py) can decide how to surface it alongside
    validate.py's deeper checks, rather than this module owning two different
    kinds of failure reporting.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out), **EXPORT_KWARGS)

    # Re-import into a throwaway scene (not the current one, so the export
    # source scene is untouched) purely as a parse smoke test. Track the
    # original scene explicitly and always restore it via
    # bpy.context.window.scene, rather than checking name == "Scene" (which
    # breaks if the source scene was ever renamed) or relying on whatever
    # scene an operator happens to leave active.
    original_scene = bpy.context.window.scene
    scratch_scene = bpy.data.scenes.new("export_reimport_scratch")
    reimport_ok = True
    try:
        bpy.context.window.scene = scratch_scene
        bpy.ops.import_scene.gltf(filepath=str(out))
    except RuntimeError:
        reimport_ok = False
    finally:
        bpy.context.window.scene = original_scene
        bpy.data.scenes.remove(scratch_scene)

    return {"path": str(out), "reimport_ok": reimport_ok}
