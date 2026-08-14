"""Blender-backed character mesh generation (v2 pipeline).

See docs/superpowers/specs/2026-08-08-character-pipeline-v2-blender-design.md
for the full architecture. This package never `import bpy` at module scope —
bpy only exists inside a running Blender process. Code here either (a) shells
out to `blender --background --python <script>` (the reproducible build path)
or (b) is executed *as* one of those scripts, run by Blender's own
interpreter, where `import bpy` is valid.
"""
