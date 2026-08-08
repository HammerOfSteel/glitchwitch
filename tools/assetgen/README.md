# tools/assetgen — Character Pipeline

## Adding a new part
1. Write a builder function in `part_registry.py` returning a `MeshBuilder`
   (reuse `add_box`/`add_cylinder`/`add_lathe` from `mesh.py`).
2. Register it: `_REGISTRY[archetype][slot][part_id] = builder_fn`, or call
   `part_registry.register(archetype, slot, part_id, builder_fn)` from another
   module.
3. Part ids must be unique per archetype+slot; candidates are returned sorted,
   so seeded selection is deterministic.

## Adding a new archetype
1. Add rig pose entries to `character_gen._ARCHETYPE_POSE` for every node in
   `rig_contract.SLOT_NODE_NAMES` (or reuse an existing pose set).
2. Register at least one part per baseline slot (`hips`, `torso`, `arm`, `head`,
   `boot`); `headwear`/`hair` can use `part_registry.empty_placeholder()` if the
   archetype has none visually.
3. Optionally add an `animation_contract.BASELINE_PROFILE_CLIPS` entry if the
   archetype needs clips beyond `idle`/`walk`/`run`.

## Running the validator standalone

```python
from tools.assetgen import character_gen, character_validate
from tools.assetgen.character_spec import CharacterSpec

rig, clips = character_gen.generate(CharacterSpec(archetype="villager", seed=1))
character_validate.validate(rig, clips)  # raises ValueError with details on failure
```

## Rebuilding all generated assets

`python3 -m tools.assetgen.build` — writes `assets/generated/manifest.json` with
per-character `archetype`, `seed`, `resolved_parts`, and contract version metadata.

## Done-gate checklist (from the spec)

- [x] Wren regenerated through the new pipeline, byte-identical to Phase 1 output
      (`tests/python/test_character_migration.py`).
- [x] At least one additional archetype (`villager`) generated end-to-end with a
      distinct seed (`tests/python/test_villager_archetype.py`).
- [x] Validator catches missing node, missing clip, and over-budget tri count in
      tests (`tests/python/test_character_validate.py`); part-incompatibility is
      covered by `part_registry`'s `ValueError` on unknown part id
      (`tests/python/test_part_registry.py`).
- [x] Full pytest suite green (`python3 -m pytest tests/python -v`).
- [x] Tooling doc written (this file).
- [x] Asset Inventory Matrix populated (`docs/asset-inventory.md`).
