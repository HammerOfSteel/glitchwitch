"""Shared body-proportion constants (units = meters, total standing height 1.0m
to match the existing v1 character scale in tools/assetgen/character.py).

This is a plain-data module (no bpy import) so it's importable both by Blender
scripts (author_base_humanoid.py, clothing_parts/*.py) and by plain pytest-run
Python if ever needed for a non-Blender consistency check. These are STARTING
values, not open choices — adjust only if a render check (Task 3 Step 2) fails
the acceptance bar, and note any change in a comment here.
"""
from __future__ import annotations

DIMS = {
    "head_height": 0.28,      # ~28% of total height -> chibi-adjacent per spec
    "torso_height": 0.32,
    # Render-check tweak: widened torso/hips slightly so the silhouette reads as
    # a soft toy humanoid instead of a mannequin-thin placeholder.
    "torso_width": 0.26,
    "hip_width": 0.24,
    "upper_arm_length": 0.16,
    "lower_arm_length": 0.14,
    "hand_length": 0.09,
    "upper_leg_length": 0.20,
    "lower_leg_length": 0.18,
    "foot_length": 0.12,
    "bevel_width": 0.01,       # bevel modifier width, all parts start equal
    "bevel_segments": 4,
    "subsurf_levels": 2,
}
