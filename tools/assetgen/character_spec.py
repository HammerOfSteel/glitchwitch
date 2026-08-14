"""CharacterSpec: the input contract for the procedural character pipeline.

A CharacterSpec is plain data — archetype id, seed, optional explicit part
choices, and an animation profile name. Same spec -> same generated character
(see character_gen.py for the determinism guarantee).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Bumped on breaking changes to this schema (new required fields, changed
# semantics of existing fields). Recorded per-character in build.py's manifest.
SPEC_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class CharacterSpec:
    archetype: str
    seed: int
    parts: dict = field(default_factory=dict)
    palette_profile: str = "default"
    animation_profile: str = "default"
    root_name: str = ""  # defaults to archetype if left blank; see __post_init__

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int) or isinstance(self.seed, bool):
            raise TypeError(f"seed must be int, got {type(self.seed).__name__}")
        if not isinstance(self.archetype, str) or not self.archetype:
            raise TypeError("archetype must be a non-empty str")
        if not self.root_name:
            object.__setattr__(self, "root_name", self.archetype)
