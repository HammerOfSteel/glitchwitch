"""Orchestrator: calls every archetype-variation unit in the fixed order the
spec's architecture table requires, for one ArchetypeSpec, producing a
validated .glb. This is the only module build.py shells out to for character
builds (see Task 13) — it's invoked directly as a Blender `--python` script
(not via an intermediate driver file), so it also exposes a `__main__` CLI
entry point satisfying the spec's error-handling contract: a non-zero exit
code and a structured `ERROR:<json>` line on stderr naming which stage failed.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.assetgen.blender import (  # noqa: E402
    animate,
    clothing,
    export,
    loader,
    materials,
    proportions,
    validate,
)
from tools.assetgen.blender.archetype_spec import ArchetypeSpec  # noqa: E402


def build(spec: ArchetypeSpec, output_path: str) -> dict:
    """Run the fixed-order Blender character build pipeline for one spec."""
    loader.load_base()
    proportions.apply(spec)
    clothing.apply(spec)
    materials.apply(spec)
    animate.bake(spec)
    export_info = export.export(spec, output_path)

    report = validate.check_file(output_path)
    errors = list(report.errors)
    if not export_info["reimport_ok"]:
        errors.append("exported GLB failed to re-import cleanly")

    return {"ok": not errors, "path": export_info["path"], "errors": errors}


def _cli_main(argv: list[str]) -> int:
    """CLI entry point for Blender `--python ... --` invocations."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    try:
        spec = ArchetypeSpec(**json.loads(args.spec_json))
    except Exception as exc:  # noqa: BLE001
        print(
            "ERROR:" + json.dumps({"stage": "spec", "message": str(exc)}),
            file=sys.stderr,
        )
        return 1

    try:
        result = build(spec, args.output)
    except Exception as exc:  # noqa: BLE001
        print(
            "ERROR:" + json.dumps({"stage": "build", "message": str(exc)}),
            file=sys.stderr,
        )
        return 1

    print("RESULT:" + json.dumps(result))
    if not result["ok"]:
        print(
            "ERROR:"
            + json.dumps(
                {"stage": "validate", "message": "; ".join(result["errors"])}
            ),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    raise SystemExit(_cli_main(argv))
