#!/usr/bin/env bash
# Canonical CI entrypoint.
#
# The .github/workflows/ci.yml stub is intentionally static and delegates every
# job here, so CI logic lives in a path that repo automation can maintain.
# Jobs: tools | godot | export | all
set -euo pipefail
cd "$(dirname "$0")/../.."

job="${1:-all}"

install_python_tools() {
	python3 -m pip install --quiet pytest "gdtoolkit==4.*"
}

generate_assets() {
	if [ -f tools/assetgen/build.py ]; then
		python3 -m tools.assetgen.build
	fi
}

job_tools() {
	install_python_tools
	generate_assets
	python3 -m pytest tests/python -q
	python3 -m gdtoolkit.linter src tests/unit
	python3 -m gdtoolkit.formatter --check src tests/unit
}

job_godot() {
	python3 tools/bootstrap.py --all
	generate_assets
	.tooling/godot --headless --path . --import
	.tooling/godot --headless --path . \
		-s addons/gdUnit4/bin/GdUnitCmdTool.gd -a tests/unit --ignoreHeadlessMode
	job_screenshot
}

job_screenshot() {
	# Look-dev screenshot needs a GL context; CI provides xvfb + llvmpipe.
	if [ "${CI:-}" = "true" ] && ! command -v xvfb-run >/dev/null 2>&1; then
		sudo apt-get update -qq && sudo apt-get install -y -qq xvfb
	fi
	if command -v xvfb-run >/dev/null 2>&1; then
		LIBGL_ALWAYS_SOFTWARE=1 xvfb-run -a --server-args="-screen 0 1280x720x24" \
			.tooling/godot --path . res://src/lookdev/screenshot.tscn
		echo "look-dev screenshot written to artifacts/"
	else
		echo "xvfb unavailable — skipping look-dev screenshot (CI produces it)"
	fi
}

job_export() {
	python3 tools/bootstrap.py --all
	python3 tools/bootstrap.py --templates
	generate_assets
	.tooling/godot --headless --path . --import
	mkdir -p build/linux build/web
	.tooling/godot --headless --path . --export-release "Linux" build/linux/glitchwitch.x86_64
	.tooling/godot --headless --path . --export-release "Web" build/web/index.html
	echo "export smoke OK:"
	ls -la build/linux build/web
}

case "$job" in
	tools) job_tools ;;
	godot) job_godot ;;
	export) job_export ;;
	all) job_tools; job_godot ;;
	*) echo "unknown job: $job" >&2; exit 2 ;;
esac
