"""ArchetypeSpec: the data-only input contract for the v2 archetype-variation
units (proportions.py, clothing.py, materials.py, animate.py).

Deliberately separate from the existing tools/assetgen/character_spec.py
(v1's CharacterSpec) rather than extending it: v1's CharacterSpec describes a
part-registry-based mesh recipe (parts dict of PartSpec choices) which has no
meaning for the Blender pipeline (armature bone scales, clothing mesh names,
palette-cell assignments instead). Keeping them separate avoids a shared class
that means two different things depending on which pipeline reads it. `build.py`
picks which spec type to construct based on whether an archetype is on the v1 or
v2 (Blender) path.

Bone names are validated against the base armature's known bone list (mirrors
rig_contract.py's role for v1: fail loud if a spec references a bone that
doesn't exist, rather than silently no-op-ing in Blender).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Must match the armature built by author_base_humanoid.py (Chunk 1, Task 3,
# step 6), including its fixed ".L"/".R" left/right suffix convention
# (Blender's own Mirror-modifier/vertex-group auto-mirroring naming scheme —
# see Task 3 step 6's comment). Kept here (not re-derived from the live
# .blend, which would require bpy) so this module stays pure-Python and
# independently testable.
KNOWN_BONES = frozenset({
    "Hips", "Spine", "Neck", "Head",
    "Shoulder.L", "Arm.L", "ForeArm.L", "Hand.L",
    "Shoulder.R", "Arm.R", "ForeArm.R", "Hand.R",
    "UpLeg.L", "Leg.L", "Foot.L", "ToeBase.L",
    "UpLeg.R", "Leg.R", "Foot.R", "ToeBase.R",
})

# Matches avatar.gd's MOTION_CLIPS + GESTURE_CLIPS exactly (see spec's Godot
# integration contract) — every archetype must define all five, even if some
# turn out to be visually identical to another archetype's, so `animate.py`
# always has a full clip set to bake.
MANDATORY_CLIPS = ("idle", "walk", "run", "wave", "stir")


@dataclass(frozen=True)
class ArchetypeSpec:
    name: str
    bone_scales: dict[str, float] = field(default_factory=dict)
    clothing: list[str] = field(default_factory=list)
    palette: dict[str, tuple[str, int]] = field(default_factory=dict)
    clips: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ArchetypeSpec.name must be non-empty")
        for bone in self.bone_scales:
            if bone not in KNOWN_BONES:
                raise ValueError(f"unknown bone name in bone_scales: {bone!r}")
        for piece in self.clothing:
            if piece not in self.palette:
                raise ValueError(f"clothing piece {piece!r} has no palette entry")
        missing = [c for c in MANDATORY_CLIPS if c not in self.clips]
        if missing:
            raise ValueError(f"missing mandatory clip(s): {missing}")
