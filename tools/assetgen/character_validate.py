"""Validator: checks a generated (rig, clips) pair against the rig/animation
contracts. Raises ValueError naming exactly what failed — no silent fallbacks.
"""
from __future__ import annotations

from . import rig_contract

MANDATORY_CLIP_NAMES = ("idle-loop", "walk-loop", "run-loop")
DEFAULT_TRI_BUDGET = 1500


def _collect_node_names(node, acc) -> set:
    acc.add(node.name)
    for child in node.children:
        _collect_node_names(child, acc)
    return acc


def _tri_count(node) -> int:
    total = node.mesh.tri_count if node.mesh is not None else 0
    for child in node.children:
        total += _tri_count(child)
    return total


def _collect_parent_map(node, parent_name, acc) -> dict:
    """node name -> actual parent name (None for direct children of the root)."""
    acc[node.name] = parent_name
    for child in node.children:
        _collect_parent_map(child, node.name, acc)
    return acc


def _check_topology(rig) -> None:
    actual_parents = _collect_parent_map(rig, None, {})
    root_name = rig.name
    for node_name, expected_parent in rig_contract.PARENT_OF.items():
        if node_name not in actual_parents:
            continue  # already reported by the mandatory-node check
        actual_parent = actual_parents[node_name]
        if expected_parent is None:
            # PARENT_OF[node] is None -> must be a direct child of the root,
            # i.e. its actual parent name must equal the rig's own root name.
            if actual_parent != root_name:
                raise ValueError(
                    f"node '{node_name}' expected as a direct child of root "
                    f"'{root_name}', found under '{actual_parent}'"
                )
        elif actual_parent != expected_parent:
            raise ValueError(
                f"node '{node_name}' expected under parent '{expected_parent}', "
                f"found under '{actual_parent}'"
            )


def _check_loop_closure(clips) -> None:
    for clip in clips:
        if clip.name not in rig_contract.LOOP_CLIP_NAMES:
            continue
        for channel in clip.channels:
            first, last = channel.values[0], channel.values[-1]
            for a, b in zip(first, last):
                if abs(a - b) >= 1e-4:
                    raise ValueError(
                        f"loop clip '{clip.name}' channel '{channel.node_name}/"
                        f"{channel.path}' does not close its cycle"
                    )


def validate(rig, clips, tri_budget: int = DEFAULT_TRI_BUDGET) -> None:
    node_names = _collect_node_names(rig, set())
    missing_nodes = rig_contract.MANDATORY_NODE_NAMES - node_names
    if missing_nodes:
        raise ValueError(f"rig missing mandatory node(s): {sorted(missing_nodes)}")

    _check_topology(rig)

    clip_names = {clip.name for clip in clips}
    missing_clips = set(MANDATORY_CLIP_NAMES) - clip_names
    if missing_clips:
        raise ValueError(f"missing mandatory clip(s): {sorted(missing_clips)}")

    for clip in clips:
        for channel in clip.channels:
            if channel.node_name not in node_names:
                raise ValueError(
                    f"clip '{clip.name}' targets unknown node '{channel.node_name}'"
                )

    _check_loop_closure(clips)

    tris = _tri_count(rig)
    if tris > tri_budget:
        raise ValueError(f"triangle budget exceeded: {tris} > {tri_budget}")
